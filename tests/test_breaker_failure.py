from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from energologic.protection import (
    BreakerFailureBinding,
    BreakerFailureProgramValidationError,
    BreakerFailureRuntimeInputError,
    breaker_failure_result_fingerprint,
    compile_breaker_failure_program,
    evaluate_breaker_failure_step,
    make_breaker_failure_snapshot,
    setting_card_from_dict,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "protection-settings.synthetic.json"
BF = "function:kl-1:breaker-failure"
MONITORED = "breaker:v-1-35"
BACKUP = "breaker:section-coupler"


def raw_fixture() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def card():
    return setting_card_from_dict(raw_fixture())


def binding(
    *,
    criterion_mode: str = "breaker_closed",
    start_behavior: str = "maintained",
    monitored_breaker_id: str = MONITORED,
):
    return BreakerFailureBinding(
        binding_id="binding:kl-1:bf",
        function_id=BF,
        monitored_breaker_id=monitored_breaker_id,
        criterion_mode=criterion_mode,
        start_behavior=start_behavior,
        provenance_ref="synthetic://ws9b/breaker-failure-binding",
    )


def program(
    *,
    criterion_mode: str = "breaker_closed",
    start_behavior: str = "maintained",
):
    return compile_breaker_failure_program(
        card(),
        binding(
            criterion_mode=criterion_mode,
            start_behavior=start_behavior,
        ),
        allow_incomplete_settings=True,
    )


def snap(
    time_s: str,
    *,
    start: bool,
    breaker_closed: bool | None = None,
    current_flow: bool | None = None,
    snapshot_id: str | None = None,
):
    return make_breaker_failure_snapshot(
        snapshot_id=snapshot_id or f"bf:{time_s}",
        time_s=time_s,
        start_active=start,
        breaker_closed=breaker_closed,
        current_flow_present=current_flow,
    )


class BreakerFailureFoundationTests(unittest.TestCase):
    def test_operational_summary_is_not_executable_by_default(self):
        with self.assertRaises(BreakerFailureProgramValidationError) as caught:
            compile_breaker_failure_program(card(), binding())
        self.assertIn(
            "incomplete_settings_scope",
            {item.code for item in caught.exception.issues},
        )

    def test_program_uses_explicit_delay_and_backup_target(self):
        compiled = program()
        self.assertEqual(compiled.delay_s, "0.2")
        self.assertEqual(compiled.binding.monitored_breaker_id, MONITORED)
        self.assertEqual(len(compiled.actions), 1)
        self.assertEqual(compiled.actions[0].target_id, BACKUP)
        self.assertEqual(compiled.actions[0].action_type, "trip")

    def test_no_start_needs_no_feedback(self):
        compiled = program()
        result = evaluate_breaker_failure_step(
            compiled,
            snap("0", start=False),
        )
        self.assertEqual(result.state.status, "inactive")
        self.assertEqual(result.events, ())
        self.assertEqual(result.requests, ())

    def test_breaker_closed_criterion_operates_at_exact_delay(self):
        compiled = program(criterion_mode="breaker_closed")
        pickup = evaluate_breaker_failure_step(
            compiled,
            snap("0", start=True, breaker_closed=True),
        )
        self.assertEqual(
            [item.event_type for item in pickup.events],
            ["pickup"],
        )
        self.assertEqual(pickup.state.status, "timing")

        before = evaluate_breaker_failure_step(
            compiled,
            snap("0.199", start=True, breaker_closed=True),
            state=pickup.state,
        )
        self.assertEqual(before.requests, ())

        operated = evaluate_breaker_failure_step(
            compiled,
            snap("0.2", start=True, breaker_closed=True),
            state=before.state,
        )
        self.assertEqual(
            [item.event_type for item in operated.events],
            ["operate"],
        )
        self.assertEqual(len(operated.requests), 1)
        self.assertEqual(operated.requests[0].target_id, BACKUP)
        self.assertEqual(
            operated.requests[0].cause,
            "breaker_failure_operated",
        )

    def test_current_flow_criterion_operates(self):
        compiled = program(criterion_mode="current_flow")
        pickup = evaluate_breaker_failure_step(
            compiled,
            snap("1", start=True, current_flow=True),
        )
        operated = evaluate_breaker_failure_step(
            compiled,
            snap("1.2", start=True, current_flow=True),
            state=pickup.state,
        )
        self.assertEqual(len(operated.requests), 1)

    def test_or_criterion_accepts_either_true_input(self):
        compiled = program(
            criterion_mode="breaker_closed_or_current_flow"
        )
        result = evaluate_breaker_failure_step(
            compiled,
            snap(
                "0",
                start=True,
                breaker_closed=False,
                current_flow=True,
            ),
        )
        self.assertEqual(result.state.status, "timing")

    def test_and_criterion_requires_both_true(self):
        compiled = program(
            criterion_mode="breaker_closed_and_current_flow"
        )
        inactive = evaluate_breaker_failure_step(
            compiled,
            snap(
                "0",
                start=True,
                breaker_closed=True,
                current_flow=False,
            ),
        )
        self.assertEqual(inactive.state.status, "inactive")

        picked = evaluate_breaker_failure_step(
            compiled,
            snap(
                "1",
                start=True,
                breaker_closed=True,
                current_flow=True,
            ),
            state=inactive.state,
        )
        self.assertEqual(picked.state.status, "timing")

    def test_missing_required_breaker_feedback_fails_closed(self):
        compiled = program(criterion_mode="breaker_closed")
        with self.assertRaises(BreakerFailureRuntimeInputError) as caught:
            evaluate_breaker_failure_step(
                compiled,
                snap("0", start=True),
            )
        self.assertEqual(
            caught.exception.issue.code,
            "missing_breaker_closed_feedback",
        )

    def test_missing_required_current_feedback_fails_closed(self):
        compiled = program(criterion_mode="current_flow")
        with self.assertRaises(BreakerFailureRuntimeInputError) as caught:
            evaluate_breaker_failure_step(
                compiled,
                snap("0", start=True),
            )
        self.assertEqual(
            caught.exception.issue.code,
            "missing_current_flow_feedback",
        )

    def test_maintained_start_drop_resets_without_backup_trip(self):
        compiled = program(start_behavior="maintained")
        pickup = evaluate_breaker_failure_step(
            compiled,
            snap("0", start=True, breaker_closed=True),
        )
        reset = evaluate_breaker_failure_step(
            compiled,
            snap("0.1", start=False),
            state=pickup.state,
        )
        self.assertEqual(
            [item.event_type for item in reset.events],
            ["reset"],
        )
        self.assertEqual(reset.state.status, "inactive")
        self.assertEqual(reset.requests, ())

    def test_latched_start_drop_continues_timing(self):
        compiled = program(start_behavior="latched")
        pickup = evaluate_breaker_failure_step(
            compiled,
            snap("0", start=True, breaker_closed=True),
        )
        held = evaluate_breaker_failure_step(
            compiled,
            snap("0.1", start=False, breaker_closed=True),
            state=pickup.state,
        )
        self.assertEqual(held.state.status, "timing")
        operated = evaluate_breaker_failure_step(
            compiled,
            snap("0.2", start=False, breaker_closed=True),
            state=held.state,
        )
        self.assertEqual(len(operated.requests), 1)

    def test_failure_criterion_clears_before_delay(self):
        compiled = program()
        pickup = evaluate_breaker_failure_step(
            compiled,
            snap("0", start=True, breaker_closed=True),
        )
        reset = evaluate_breaker_failure_step(
            compiled,
            snap("0.1", start=True, breaker_closed=False),
            state=pickup.state,
        )
        self.assertEqual(
            [item.event_type for item in reset.events],
            ["reset"],
        )
        self.assertEqual(reset.requests, ())

    def test_operated_state_does_not_repeat_backup_requests(self):
        compiled = program()
        pickup = evaluate_breaker_failure_step(
            compiled,
            snap("0", start=True, breaker_closed=True),
        )
        operated = evaluate_breaker_failure_step(
            compiled,
            snap("0.2", start=True, breaker_closed=True),
            state=pickup.state,
        )
        held = evaluate_breaker_failure_step(
            compiled,
            snap("0.3", start=True, breaker_closed=True),
            state=operated.state,
        )
        self.assertEqual(held.events, ())
        self.assertEqual(held.requests, ())
        self.assertEqual(held.state.status, "operated")

    def test_operated_state_resets_when_failure_clears(self):
        compiled = program()
        pickup = evaluate_breaker_failure_step(
            compiled,
            snap("0", start=True, breaker_closed=True),
        )
        operated = evaluate_breaker_failure_step(
            compiled,
            snap("0.2", start=True, breaker_closed=True),
            state=pickup.state,
        )
        reset = evaluate_breaker_failure_step(
            compiled,
            snap("0.3", start=True, breaker_closed=False),
            state=operated.state,
        )
        self.assertEqual(
            [item.event_type for item in reset.events],
            ["reset"],
        )
        self.assertEqual(reset.state.status, "inactive")

    def test_zero_delay_operates_on_pickup_step(self):
        data = raw_fixture()
        function = next(item for item in data["functions"] if item["id"] == BF)
        delay = function["stages"][0]["parameters"][0]["value"]
        delay["raw_text"] = "0 s"
        delay["source_value"] = "0"
        delay["normalized_value"] = "0"
        compiled = compile_breaker_failure_program(
            setting_card_from_dict(data),
            binding(),
            allow_incomplete_settings=True,
        )
        result = evaluate_breaker_failure_step(
            compiled,
            snap("0", start=True, breaker_closed=True),
        )
        self.assertEqual(
            [item.event_type for item in result.events],
            ["pickup", "operate"],
        )
        self.assertEqual(len(result.requests), 1)

    def test_time_reversal_fails_closed(self):
        compiled = program()
        first = evaluate_breaker_failure_step(
            compiled,
            snap("2", start=False),
        )
        with self.assertRaises(BreakerFailureRuntimeInputError) as caught:
            evaluate_breaker_failure_step(
                compiled,
                snap("1.9", start=False),
                state=first.state,
            )
        self.assertEqual(
            caught.exception.issue.code,
            "logical_time_reversal",
        )

    def test_state_from_different_binding_is_rejected(self):
        first_program = program(criterion_mode="breaker_closed")
        first = evaluate_breaker_failure_step(
            first_program,
            snap("0", start=False),
        )
        second_program = program(criterion_mode="current_flow")
        with self.assertRaises(BreakerFailureRuntimeInputError) as caught:
            evaluate_breaker_failure_step(
                second_program,
                snap("1", start=False),
                state=first.state,
            )
        self.assertEqual(
            caught.exception.issue.code,
            "state_program_mismatch",
        )

    def test_retrip_of_monitored_breaker_is_rejected(self):
        data = raw_fixture()
        function = next(item for item in data["functions"] if item["id"] == BF)
        function["stages"][0]["actions"][0]["target_id"] = MONITORED
        with self.assertRaises(BreakerFailureProgramValidationError) as caught:
            compile_breaker_failure_program(
                setting_card_from_dict(data),
                binding(),
                allow_incomplete_settings=True,
            )
        self.assertIn(
            "retrip_unsupported",
            {item.code for item in caught.exception.issues},
        )

    def test_extra_breaker_failure_parameter_is_not_guessed(self):
        data = raw_fixture()
        function = next(item for item in data["functions"] if item["id"] == BF)
        stage = function["stages"][0]
        extra = copy.deepcopy(stage["parameters"][0])
        extra["id"] = "parameter:bf:current-threshold"
        extra["semantic_key"] = "breaker_failure_current_threshold"
        extra["role"] = "pickup"
        extra["value"] = {
            "kind": "quantity",
            "raw_text": "0.1 kA",
            "source_value": "0.1",
            "source_unit": "kA",
            "quantity_kind": "current",
            "basis": "primary",
            "normalized_value": "100",
            "normalized_unit": "A",
        }
        stage["parameters"].append(extra)
        with self.assertRaises(BreakerFailureProgramValidationError) as caught:
            compile_breaker_failure_program(
                setting_card_from_dict(data),
                binding(),
                allow_incomplete_settings=True,
            )
        self.assertIn(
            "unsupported_stage_parameter",
            {item.code for item in caught.exception.issues},
        )

    def test_multiple_breaker_failure_stages_are_not_guessed(self):
        data = raw_fixture()
        function = next(item for item in data["functions"] if item["id"] == BF)
        duplicate = copy.deepcopy(function["stages"][0])
        duplicate["id"] = "stage:kl-1:breaker-failure-2"
        duplicate["parameters"][0]["id"] = "parameter:bf2:delay"
        duplicate["actions"][0]["id"] = "action:bf2:trip"
        function["stages"].append(duplicate)
        with self.assertRaises(BreakerFailureProgramValidationError) as caught:
            compile_breaker_failure_program(
                setting_card_from_dict(data),
                binding(),
                allow_incomplete_settings=True,
            )
        self.assertIn(
            "unsupported_stage_count",
            {item.code for item in caught.exception.issues},
        )

    def test_disabled_function_is_noop(self):
        data = raw_fixture()
        function = next(item for item in data["functions"] if item["id"] == BF)
        function["enabled"] = False
        compiled = compile_breaker_failure_program(
            setting_card_from_dict(data),
            binding(),
            allow_incomplete_settings=True,
        )
        result = evaluate_breaker_failure_step(
            compiled,
            snap("0", start=True),
        )
        self.assertFalse(compiled.enabled)
        self.assertEqual(result.events, ())
        self.assertEqual(result.requests, ())

    def test_result_fingerprint_and_requests_are_deterministic(self):
        compiled = program()
        first_pickup = evaluate_breaker_failure_step(
            compiled,
            snap(
                "0",
                start=True,
                breaker_closed=True,
                snapshot_id="bf:start",
            ),
        )
        second_pickup = evaluate_breaker_failure_step(
            compiled,
            snap(
                "0",
                start=True,
                breaker_closed=True,
                snapshot_id="bf:start",
            ),
        )
        self.assertEqual(first_pickup, second_pickup)

        first = evaluate_breaker_failure_step(
            compiled,
            snap(
                "0.2",
                start=True,
                breaker_closed=True,
                snapshot_id="bf:operate",
            ),
            state=first_pickup.state,
        )
        second = evaluate_breaker_failure_step(
            compiled,
            snap(
                "0.2",
                start=True,
                breaker_closed=True,
                snapshot_id="bf:operate",
            ),
            state=second_pickup.state,
        )
        self.assertEqual(first.requests, second.requests)
        self.assertEqual(
            breaker_failure_result_fingerprint(first),
            breaker_failure_result_fingerprint(second),
        )


if __name__ == "__main__":
    unittest.main()
