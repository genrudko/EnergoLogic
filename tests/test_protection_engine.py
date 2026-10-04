from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from energologic.protection import (
    MeasuredQuantity,
    ProtectionProgramValidationError,
    ProtectionRuntimeInputError,
    compile_protection_program,
    evaluate_protection_step,
    make_measured_quantity,
    make_snapshot,
    protection_step_fingerprint,
    setting_card_fingerprint,
    setting_card_from_dict,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "protection-settings.synthetic.json"

MTZ = "function:kl-1:mtz"
TO = "function:kl-1:to"
EARTH = "function:kl-1:earth-fault"
BF = "function:kl-1:breaker-failure"
PHASE = "measurement:kl-1:phase-current"
RESIDUAL = "measurement:kl-1:residual-current"


def raw_fixture() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def card():
    return setting_card_from_dict(raw_fixture())


def measured(
    measurement_input_id: str,
    value: str,
    *,
    unit: str = "A",
    basis: str = "primary",
):
    return make_measured_quantity(
        measurement_input_id=measurement_input_id,
        source_value=value,
        source_unit=unit,
        quantity_kind="current",
        basis=basis,
    )


def snapshot(
    time_s: str,
    *measurements,
    snapshot_id: str | None = None,
):
    return make_snapshot(
        snapshot_id=snapshot_id or f"snapshot:{time_s}",
        time_s=time_s,
        measurements=measurements,
    )


class ProtectionEngineFoundationTests(unittest.TestCase):
    def test_default_compile_is_explicit_about_unsupported_breaker_failure(self):
        program = compile_protection_program(card())
        self.assertEqual(
            program.unsupported_function_ids,
            (BF,),
        )
        self.assertEqual(
            {item.concept_id for item in program.stages},
            {
                "protection.overcurrent",
                "protection.instantaneous_overcurrent",
                "protection.earth_fault",
            },
        )

    def test_mtz_picks_up_at_exact_threshold_and_operates_at_exact_delay(self):
        program = compile_protection_program(card(), function_ids=[MTZ])

        step0 = evaluate_protection_step(
            program,
            snapshot("0", measured(PHASE, "600")),
        )
        self.assertEqual(
            [item.event_type for item in step0.events],
            ["pickup"],
        )
        self.assertEqual(step0.requests, ())
        self.assertEqual(step0.state.stages[0].status, "picked_up")

        step1 = evaluate_protection_step(
            program,
            snapshot("0.799", measured(PHASE, "600")),
            state=step0.state,
        )
        self.assertEqual(step1.events, ())
        self.assertEqual(step1.requests, ())
        self.assertEqual(step1.state.stages[0].status, "picked_up")

        step2 = evaluate_protection_step(
            program,
            snapshot("0.8", measured(PHASE, "600")),
            state=step1.state,
        )
        self.assertEqual(
            [item.event_type for item in step2.events],
            ["operate"],
        )
        self.assertEqual(len(step2.requests), 1)
        self.assertEqual(step2.requests[0].action_type, "trip")
        self.assertEqual(
            step2.requests[0].target_id,
            "breaker:v-1-35",
        )
        self.assertEqual(step2.state.stages[0].status, "operated")

    def test_mtz_below_threshold_does_not_pick_up(self):
        program = compile_protection_program(card(), function_ids=[MTZ])
        result = evaluate_protection_step(
            program,
            snapshot("0", measured(PHASE, "599.999")),
        )
        self.assertEqual(result.events, ())
        self.assertEqual(result.requests, ())
        self.assertEqual(result.state.stages[0].status, "inactive")

    def test_mtz_resets_below_pickup_and_timer_restarts(self):
        program = compile_protection_program(card(), function_ids=[MTZ])

        picked = evaluate_protection_step(
            program,
            snapshot("1", measured(PHASE, "700")),
        )
        reset = evaluate_protection_step(
            program,
            snapshot("1.4", measured(PHASE, "599")),
            state=picked.state,
        )
        self.assertEqual(
            [item.event_type for item in reset.events],
            ["reset"],
        )
        self.assertEqual(reset.state.stages[0].status, "inactive")

        picked_again = evaluate_protection_step(
            program,
            snapshot("2", measured(PHASE, "700")),
            state=reset.state,
        )
        self.assertEqual(
            picked_again.state.stages[0].pickup_started_at_s,
            "2",
        )
        before_delay = evaluate_protection_step(
            program,
            snapshot("2.799", measured(PHASE, "700")),
            state=picked_again.state,
        )
        self.assertEqual(before_delay.requests, ())
        operated = evaluate_protection_step(
            program,
            snapshot("2.8", measured(PHASE, "700")),
            state=before_delay.state,
        )
        self.assertEqual(len(operated.requests), 1)

    def test_operated_stage_emits_request_once_until_reset(self):
        program = compile_protection_program(card(), function_ids=[MTZ])

        picked = evaluate_protection_step(
            program,
            snapshot("0", measured(PHASE, "700")),
        )
        operated = evaluate_protection_step(
            program,
            snapshot("0.8", measured(PHASE, "700")),
            state=picked.state,
        )
        held = evaluate_protection_step(
            program,
            snapshot("1.0", measured(PHASE, "700")),
            state=operated.state,
        )
        self.assertEqual(held.events, ())
        self.assertEqual(held.requests, ())

        reset = evaluate_protection_step(
            program,
            snapshot("1.1", measured(PHASE, "500")),
            state=held.state,
        )
        self.assertEqual(
            [item.event_type for item in reset.events],
            ["reset"],
        )

    def test_instantaneous_stage_with_explicit_zero_delay_operates_same_step(self):
        program = compile_protection_program(card(), function_ids=[TO])
        result = evaluate_protection_step(
            program,
            snapshot("0", measured(PHASE, "1200")),
        )
        self.assertEqual(
            [item.event_type for item in result.events],
            ["pickup", "operate"],
        )
        self.assertEqual(len(result.requests), 1)
        self.assertEqual(result.state.stages[0].status, "operated")
        self.assertEqual(
            result.state.stages[0].pickup_started_at_s,
            "0",
        )
        self.assertEqual(
            result.state.stages[0].operated_at_s,
            "0",
        )

    def test_earth_fault_uses_residual_current_input(self):
        program = compile_protection_program(card(), function_ids=[EARTH])

        below = evaluate_protection_step(
            program,
            snapshot("0", measured(RESIDUAL, "79.999")),
        )
        self.assertEqual(below.events, ())

        picked = evaluate_protection_step(
            program,
            snapshot("1", measured(RESIDUAL, "80")),
            state=below.state,
        )
        self.assertEqual(
            [item.event_type for item in picked.events],
            ["pickup"],
        )
        operated = evaluate_protection_step(
            program,
            snapshot("1.5", measured(RESIDUAL, "80")),
            state=picked.state,
        )
        self.assertEqual(len(operated.requests), 1)

    def test_measurement_basis_mismatch_fails_closed(self):
        program = compile_protection_program(card(), function_ids=[MTZ])
        bad = MeasuredQuantity(
            measurement_input_id=PHASE,
            quantity_kind="current",
            basis="secondary",
            normalized_value="600",
            normalized_unit="A",
        )
        with self.assertRaises(ProtectionRuntimeInputError) as caught:
            evaluate_protection_step(
                program,
                snapshot("0", bad),
            )
        self.assertEqual(
            caught.exception.issue.code,
            "measurement_basis_mismatch",
        )

    def test_measurement_must_already_use_canonical_unit(self):
        program = compile_protection_program(card(), function_ids=[MTZ])
        bad = MeasuredQuantity(
            measurement_input_id=PHASE,
            quantity_kind="current",
            basis="primary",
            normalized_value="0.6",
            normalized_unit="kA",
        )
        with self.assertRaises(ProtectionRuntimeInputError) as caught:
            evaluate_protection_step(
                program,
                snapshot("0", bad),
            )
        self.assertEqual(
            caught.exception.issue.code,
            "measurement_not_normalized",
        )

    def test_missing_measurement_fails_closed(self):
        program = compile_protection_program(card(), function_ids=[MTZ])
        with self.assertRaises(ProtectionRuntimeInputError) as caught:
            evaluate_protection_step(
                program,
                snapshot("0"),
            )
        self.assertEqual(
            caught.exception.issue.code,
            "missing_measurement_inputs",
        )

    def test_duplicate_measurement_fails_closed(self):
        program = compile_protection_program(card(), function_ids=[MTZ])
        value = measured(PHASE, "600")
        with self.assertRaises(ProtectionRuntimeInputError) as caught:
            evaluate_protection_step(
                program,
                snapshot("0", value, value),
            )
        self.assertEqual(
            caught.exception.issue.code,
            "duplicate_measurement_input",
        )

    def test_logical_time_reversal_fails_closed(self):
        program = compile_protection_program(card(), function_ids=[MTZ])
        first = evaluate_protection_step(
            program,
            snapshot("2", measured(PHASE, "700")),
        )
        with self.assertRaises(ProtectionRuntimeInputError) as caught:
            evaluate_protection_step(
                program,
                snapshot("1.999", measured(PHASE, "700")),
                state=first.state,
            )
        self.assertEqual(
            caught.exception.issue.code,
            "logical_time_reversal",
        )

    def test_null_enabled_state_is_not_treated_as_enabled(self):
        data = raw_fixture()
        function = next(item for item in data["functions"] if item["id"] == MTZ)
        function["enabled"] = None
        program_card = setting_card_from_dict(data)
        with self.assertRaises(ProtectionProgramValidationError) as caught:
            compile_protection_program(program_card, function_ids=[MTZ])
        self.assertIn(
            "indeterminate_function_enabled",
            {item.code for item in caught.exception.issues},
        )

    def test_disabled_function_produces_no_runtime_stage(self):
        data = raw_fixture()
        function = next(item for item in data["functions"] if item["id"] == MTZ)
        function["enabled"] = False
        program = compile_protection_program(
            setting_card_from_dict(data),
            function_ids=[MTZ],
        )
        self.assertEqual(program.stages, ())
        result = evaluate_protection_step(
            program,
            snapshot("0"),
        )
        self.assertEqual(result.events, ())
        self.assertEqual(result.requests, ())

    def test_missing_delay_setting_fails_program_compile(self):
        data = raw_fixture()
        function = next(item for item in data["functions"] if item["id"] == MTZ)
        stage = function["stages"][0]
        stage["parameters"] = [
            item for item in stage["parameters"]
            if item["role"] != "delay"
        ]
        program_card = setting_card_from_dict(data)
        with self.assertRaises(ProtectionProgramValidationError) as caught:
            compile_protection_program(program_card, function_ids=[MTZ])
        self.assertIn(
            "invalid_delay_parameter_count",
            {item.code for item in caught.exception.issues},
        )

    def test_extra_algorithm_parameter_is_not_silently_ignored(self):
        data = raw_fixture()
        function = next(item for item in data["functions"] if item["id"] == MTZ)
        stage = function["stages"][0]
        extra = copy.deepcopy(stage["parameters"][0])
        extra["id"] = "parameter:kl-1:mtz-1:direction"
        extra["semantic_key"] = "direction"
        extra["role"] = "direction"
        extra["value"] = {
            "kind": "enum",
            "raw_text": "forward",
            "enum_value": "forward",
        }
        stage["parameters"].append(extra)
        program_card = setting_card_from_dict(data)
        with self.assertRaises(ProtectionProgramValidationError) as caught:
            compile_protection_program(program_card, function_ids=[MTZ])
        self.assertIn(
            "unsupported_stage_parameter",
            {item.code for item in caught.exception.issues},
        )

    def test_request_is_declarative_and_does_not_mutate_setting_card(self):
        program_card = card()
        before = setting_card_fingerprint(program_card)
        program = compile_protection_program(program_card, function_ids=[TO])
        result = evaluate_protection_step(
            program,
            snapshot("0", measured(PHASE, "1300")),
        )
        self.assertEqual(setting_card_fingerprint(program_card), before)
        self.assertEqual(result.requests[0].target_id, "breaker:v-1-35")
        self.assertEqual(result.requests[0].cause, "stage_operated")

    def test_request_and_step_fingerprints_are_deterministic(self):
        program = compile_protection_program(card(), function_ids=[TO])
        input_snapshot = snapshot(
            "0",
            measured(PHASE, "1300"),
            snapshot_id="snapshot:deterministic",
        )
        first = evaluate_protection_step(program, input_snapshot)
        second = evaluate_protection_step(program, input_snapshot)
        self.assertEqual(first.requests, second.requests)
        self.assertEqual(
            protection_step_fingerprint(first),
            protection_step_fingerprint(second),
        )

    def test_default_program_is_independent_of_measurement_tuple_order(self):
        program = compile_protection_program(card())
        first_snapshot = snapshot(
            "0",
            measured(PHASE, "100"),
            measured(RESIDUAL, "10"),
            snapshot_id="snapshot:ordered",
        )
        second_snapshot = snapshot(
            "0",
            measured(RESIDUAL, "10"),
            measured(PHASE, "100"),
            snapshot_id="snapshot:ordered",
        )
        first = evaluate_protection_step(program, first_snapshot)
        second = evaluate_protection_step(program, second_snapshot)
        self.assertEqual(
            protection_step_fingerprint(first),
            protection_step_fingerprint(second),
        )


if __name__ == "__main__":
    unittest.main()
