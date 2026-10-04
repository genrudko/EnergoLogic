from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from energologic.protection import (
    BinarySignal,
    BreakerFailureBinding,
    BreakerFailureProgramValidationError,
    BreakerFailureRuntimeInputError,
    breaker_failure_step_fingerprint,
    compile_breaker_failure_program,
    evaluate_breaker_failure_step,
    make_binary_signal,
    make_breaker_failure_snapshot,
    setting_card_fingerprint,
    setting_card_from_dict,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "protection-settings.synthetic.json"

BF = "function:kl-1:breaker-failure"
START = "signal:kl-1:bf-start"
OPEN = "signal:breaker:v-1-35:open"
MONITORED = "breaker:v-1-35"


def raw_fixture() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def card():
    return setting_card_from_dict(raw_fixture())


def binding() -> BreakerFailureBinding:
    return BreakerFailureBinding(
        function_id=BF,
        monitored_breaker_id=MONITORED,
        start_signal_id=START,
        breaker_open_signal_id=OPEN,
    )


def program():
    return compile_breaker_failure_program(
        card(),
        bindings=[binding()],
        allow_incomplete_settings=True,
    )


def snapshot(
    time_s: str,
    *,
    start: bool,
    breaker_open: bool,
    snapshot_id: str | None = None,
):
    return make_breaker_failure_snapshot(
        snapshot_id=snapshot_id or f"bf:{time_s}:{start}:{breaker_open}",
        time_s=time_s,
        signals=[
            make_binary_signal(START, start),
            make_binary_signal(OPEN, breaker_open),
        ],
    )


class BreakerFailureEngineTests(unittest.TestCase):
    def test_incomplete_setting_card_is_not_executable_by_default(self):
        with self.assertRaises(BreakerFailureProgramValidationError) as caught:
            compile_breaker_failure_program(
                card(),
                bindings=[binding()],
            )
        self.assertIn(
            "incomplete_settings_scope",
            {item.code for item in caught.exception.issues},
        )

    def test_full_configuration_compiles_without_incomplete_override(self):
        data = raw_fixture()
        data["settings_scope"] = "full_configuration"
        compiled = compile_breaker_failure_program(
            setting_card_from_dict(data),
            bindings=[binding()],
        )
        self.assertEqual(len(compiled.definitions), 1)

    def test_draft_setting_card_is_not_executable_by_default(self):
        data = raw_fixture()
        data["lifecycle_status"] = "draft"
        with self.assertRaises(BreakerFailureProgramValidationError) as caught:
            compile_breaker_failure_program(
                setting_card_from_dict(data),
                bindings=[binding()],
                allow_incomplete_settings=True,
            )
        self.assertIn(
            "non_authoritative_settings",
            {item.code for item in caught.exception.issues},
        )

    def test_program_compiles_explicit_binding_and_delay(self):
        compiled = program()
        self.assertEqual(len(compiled.definitions), 1)
        definition = compiled.definitions[0]
        self.assertEqual(definition.function_id, BF)
        self.assertEqual(definition.monitored_breaker_id, MONITORED)
        self.assertEqual(definition.delay_s, "0.2")

    def test_idle_without_start_remains_idle(self):
        result = evaluate_breaker_failure_step(
            program(),
            snapshot("0", start=False, breaker_open=False),
        )
        self.assertEqual(result.state.stages[0].status, "idle")
        self.assertEqual(result.events, ())
        self.assertEqual(result.requests, ())

    def test_start_with_closed_breaker_starts_timer(self):
        result = evaluate_breaker_failure_step(
            program(),
            snapshot("0", start=True, breaker_open=False),
        )
        self.assertEqual(result.state.stages[0].status, "timing")
        self.assertEqual(result.state.stages[0].timing_started_at_s, "0")
        self.assertEqual([item.event_type for item in result.events], ["start"])

    def test_operates_at_exact_delay_and_emits_configured_request(self):
        compiled = program()
        started = evaluate_breaker_failure_step(
            compiled,
            snapshot("1", start=True, breaker_open=False),
        )
        before = evaluate_breaker_failure_step(
            compiled,
            snapshot("1.199", start=True, breaker_open=False),
            state=started.state,
        )
        self.assertEqual(before.requests, ())
        operated = evaluate_breaker_failure_step(
            compiled,
            snapshot("1.2", start=True, breaker_open=False),
            state=before.state,
        )
        self.assertEqual(
            [item.event_type for item in operated.events],
            ["operate"],
        )
        self.assertEqual(len(operated.requests), 1)
        self.assertEqual(
            operated.requests[0].target_id,
            "breaker:section-coupler",
        )
        self.assertEqual(
            operated.requests[0].cause,
            "breaker_failure_operated",
        )

    def test_operated_state_does_not_repeat_request_while_condition_persists(self):
        compiled = program()
        started = evaluate_breaker_failure_step(
            compiled,
            snapshot("0", start=True, breaker_open=False),
        )
        operated = evaluate_breaker_failure_step(
            compiled,
            snapshot("0.2", start=True, breaker_open=False),
            state=started.state,
        )
        held = evaluate_breaker_failure_step(
            compiled,
            snapshot("0.3", start=True, breaker_open=False),
            state=operated.state,
        )
        self.assertEqual(held.events, ())
        self.assertEqual(held.requests, ())
        self.assertEqual(held.state.stages[0].status, "operated")

    def test_breaker_open_before_delay_resets_and_requires_start_clear(self):
        compiled = program()
        started = evaluate_breaker_failure_step(
            compiled,
            snapshot("0", start=True, breaker_open=False),
        )
        opened = evaluate_breaker_failure_step(
            compiled,
            snapshot("0.1", start=True, breaker_open=True),
            state=started.state,
        )
        self.assertEqual([item.event_type for item in opened.events], ["reset"])
        self.assertEqual(opened.events[0].cause, "breaker_open")
        self.assertEqual(
            opened.state.stages[0].status,
            "waiting_start_clear",
        )

        closed_again = evaluate_breaker_failure_step(
            compiled,
            snapshot("0.15", start=True, breaker_open=False),
            state=opened.state,
        )
        self.assertEqual(
            closed_again.state.stages[0].status,
            "waiting_start_clear",
        )
        self.assertEqual(closed_again.events, ())

        cleared = evaluate_breaker_failure_step(
            compiled,
            snapshot("0.2", start=False, breaker_open=False),
            state=closed_again.state,
        )
        self.assertEqual(cleared.state.stages[0].status, "idle")

        restarted = evaluate_breaker_failure_step(
            compiled,
            snapshot("0.3", start=True, breaker_open=False),
            state=cleared.state,
        )
        self.assertEqual(restarted.state.stages[0].status, "timing")
        self.assertEqual(
            restarted.state.stages[0].timing_started_at_s,
            "0.3",
        )

    def test_breaker_open_at_exact_delay_wins_over_operation(self):
        compiled = program()
        started = evaluate_breaker_failure_step(
            compiled,
            snapshot("0", start=True, breaker_open=False),
        )
        boundary = evaluate_breaker_failure_step(
            compiled,
            snapshot("0.2", start=True, breaker_open=True),
            state=started.state,
        )
        self.assertEqual(
            [item.event_type for item in boundary.events],
            ["reset"],
        )
        self.assertEqual(boundary.events[0].cause, "breaker_open")
        self.assertEqual(boundary.requests, ())
        self.assertEqual(
            boundary.state.stages[0].status,
            "waiting_start_clear",
        )

    def test_simultaneous_start_clear_and_breaker_open_has_explicit_cause(self):
        compiled = program()
        started = evaluate_breaker_failure_step(
            compiled,
            snapshot("0", start=True, breaker_open=False),
        )
        reset = evaluate_breaker_failure_step(
            compiled,
            snapshot("0.1", start=False, breaker_open=True),
            state=started.state,
        )
        self.assertEqual([item.event_type for item in reset.events], ["reset"])
        self.assertEqual(
            reset.events[0].cause,
            "start_removed_and_breaker_open",
        )
        self.assertEqual(reset.state.stages[0].status, "idle")

    def test_start_removed_before_delay_resets_to_idle(self):
        compiled = program()
        started = evaluate_breaker_failure_step(
            compiled,
            snapshot("0", start=True, breaker_open=False),
        )
        reset = evaluate_breaker_failure_step(
            compiled,
            snapshot("0.1", start=False, breaker_open=False),
            state=started.state,
        )
        self.assertEqual([item.event_type for item in reset.events], ["reset"])
        self.assertEqual(reset.events[0].cause, "start_removed")
        self.assertEqual(reset.state.stages[0].status, "idle")

    def test_start_while_breaker_already_open_is_consumed_until_start_clears(self):
        compiled = program()
        result = evaluate_breaker_failure_step(
            compiled,
            snapshot("0", start=True, breaker_open=True),
        )
        self.assertEqual(
            result.state.stages[0].status,
            "waiting_start_clear",
        )
        self.assertEqual(result.events, ())
        self.assertEqual(result.requests, ())

    def test_zero_delay_operates_in_same_step(self):
        data = raw_fixture()
        function = next(item for item in data["functions"] if item["id"] == BF)
        delay = function["stages"][0]["parameters"][0]["value"]
        delay["raw_text"] = "0 s"
        delay["source_value"] = "0"
        delay["normalized_value"] = "0"
        compiled = compile_breaker_failure_program(
            setting_card_from_dict(data),
            bindings=[binding()],
            allow_incomplete_settings=True,
        )
        result = evaluate_breaker_failure_step(
            compiled,
            snapshot("0", start=True, breaker_open=False),
        )
        self.assertEqual(
            [item.event_type for item in result.events],
            ["start", "operate"],
        )
        self.assertEqual(len(result.requests), 1)
        self.assertEqual(result.state.stages[0].status, "operated")

    def test_missing_signal_fails_closed(self):
        compiled = program()
        bad = make_breaker_failure_snapshot(
            snapshot_id="missing-open",
            time_s="0",
            signals=[make_binary_signal(START, True)],
        )
        with self.assertRaises(BreakerFailureRuntimeInputError) as caught:
            evaluate_breaker_failure_step(compiled, bad)
        self.assertEqual(caught.exception.issue.code, "missing_signals")

    def test_duplicate_signal_fails_closed(self):
        compiled = program()
        bad = make_breaker_failure_snapshot(
            snapshot_id="duplicate",
            time_s="0",
            signals=[
                make_binary_signal(START, True),
                make_binary_signal(START, True),
                make_binary_signal(OPEN, False),
            ],
        )
        with self.assertRaises(BreakerFailureRuntimeInputError) as caught:
            evaluate_breaker_failure_step(compiled, bad)
        self.assertEqual(caught.exception.issue.code, "duplicate_signal")

    def test_unknown_signal_fails_closed(self):
        compiled = program()
        bad = make_breaker_failure_snapshot(
            snapshot_id="unknown",
            time_s="0",
            signals=[
                make_binary_signal(START, True),
                make_binary_signal(OPEN, False),
                make_binary_signal("signal:extra", False),
            ],
        )
        with self.assertRaises(BreakerFailureRuntimeInputError) as caught:
            evaluate_breaker_failure_step(compiled, bad)
        self.assertEqual(caught.exception.issue.code, "unknown_signal")

    def test_time_reversal_fails_closed(self):
        compiled = program()
        first = evaluate_breaker_failure_step(
            compiled,
            snapshot("1", start=True, breaker_open=False),
        )
        with self.assertRaises(BreakerFailureRuntimeInputError) as caught:
            evaluate_breaker_failure_step(
                compiled,
                snapshot("0.999", start=True, breaker_open=False),
                state=first.state,
            )
        self.assertEqual(caught.exception.issue.code, "logical_time_reversal")

    def test_zero_delay_does_not_operate_if_breaker_is_already_open(self):
        data = raw_fixture()
        function = next(item for item in data["functions"] if item["id"] == BF)
        delay = function["stages"][0]["parameters"][0]["value"]
        delay["raw_text"] = "0 s"
        delay["source_value"] = "0"
        delay["normalized_value"] = "0"
        compiled = compile_breaker_failure_program(
            setting_card_from_dict(data),
            bindings=[binding()],
            allow_incomplete_settings=True,
        )
        result = evaluate_breaker_failure_step(
            compiled,
            snapshot("0", start=True, breaker_open=True),
        )
        self.assertEqual(result.requests, ())
        self.assertEqual(
            result.state.stages[0].status,
            "waiting_start_clear",
        )

    def test_signal_ids_must_be_distinct(self):
        bad_binding = BreakerFailureBinding(
            function_id=BF,
            monitored_breaker_id=MONITORED,
            start_signal_id=START,
            breaker_open_signal_id=START,
        )
        with self.assertRaises(BreakerFailureProgramValidationError) as caught:
            compile_breaker_failure_program(
                card(),
                bindings=[bad_binding],
                allow_incomplete_settings=True,
            )
        self.assertIn(
            "signal_identity_collision",
            {item.code for item in caught.exception.issues},
        )

    def test_enabled_breaker_failure_function_requires_binding(self):
        with self.assertRaises(BreakerFailureProgramValidationError) as caught:
            compile_breaker_failure_program(
                card(),
                bindings=[],
                allow_incomplete_settings=True,
            )
        self.assertIn(
            "unbound_breaker_failure_functions",
            {item.code for item in caught.exception.issues},
        )

    def test_binding_must_target_breaker_failure_function(self):
        bad_binding = BreakerFailureBinding(
            function_id="function:kl-1:mtz",
            monitored_breaker_id=MONITORED,
            start_signal_id=START,
            breaker_open_signal_id=OPEN,
        )
        with self.assertRaises(BreakerFailureProgramValidationError) as caught:
            compile_breaker_failure_program(
                card(),
                bindings=[bad_binding],
                allow_incomplete_settings=True,
                allow_unbound_functions=True,
            )
        self.assertIn(
            "binding_function_concept_mismatch",
            {item.code for item in caught.exception.issues},
        )

    def test_current_supervision_is_not_silently_interpreted(self):
        data = raw_fixture()
        function = next(item for item in data["functions"] if item["id"] == BF)
        function["measurement_input_ids"] = [
            "measurement:kl-1:phase-current"
        ]
        with self.assertRaises(BreakerFailureProgramValidationError) as caught:
            compile_breaker_failure_program(
                setting_card_from_dict(data),
                bindings=[binding()],
                allow_incomplete_settings=True,
            )
        self.assertIn(
            "measurement_supervision_unsupported",
            {item.code for item in caught.exception.issues},
        )

    def test_extra_stage_parameter_is_not_silently_interpreted(self):
        data = raw_fixture()
        function = next(item for item in data["functions"] if item["id"] == BF)
        extra = copy.deepcopy(function["stages"][0]["parameters"][0])
        extra["id"] = "parameter:bf:extra"
        extra["semantic_key"] = "retrip_delay"
        extra["role"] = "other"
        function["stages"][0]["parameters"].append(extra)
        with self.assertRaises(BreakerFailureProgramValidationError) as caught:
            compile_breaker_failure_program(
                setting_card_from_dict(data),
                bindings=[binding()],
                allow_incomplete_settings=True,
            )
        self.assertIn(
            "unsupported_stage_parameter",
            {item.code for item in caught.exception.issues},
        )

    def test_output_is_declarative_and_setting_card_is_not_mutated(self):
        source_card = card()
        before = setting_card_fingerprint(source_card)
        compiled = compile_breaker_failure_program(
            source_card,
            bindings=[binding()],
            allow_incomplete_settings=True,
        )
        started = evaluate_breaker_failure_step(
            compiled,
            snapshot("0", start=True, breaker_open=False),
        )
        operated = evaluate_breaker_failure_step(
            compiled,
            snapshot("0.2", start=True, breaker_open=False),
            state=started.state,
        )
        self.assertEqual(setting_card_fingerprint(source_card), before)
        self.assertEqual(
            operated.requests[0].target_id,
            "breaker:section-coupler",
        )

    def test_request_and_result_are_deterministic(self):
        compiled = program()
        first_start = evaluate_breaker_failure_step(
            compiled,
            snapshot(
                "0",
                start=True,
                breaker_open=False,
                snapshot_id="bf:start",
            ),
        )
        second_start = evaluate_breaker_failure_step(
            compiled,
            snapshot(
                "0",
                start=True,
                breaker_open=False,
                snapshot_id="bf:start",
            ),
        )
        first = evaluate_breaker_failure_step(
            compiled,
            snapshot(
                "0.2",
                start=True,
                breaker_open=False,
                snapshot_id="bf:operate",
            ),
            state=first_start.state,
        )
        second = evaluate_breaker_failure_step(
            compiled,
            snapshot(
                "0.2",
                start=True,
                breaker_open=False,
                snapshot_id="bf:operate",
            ),
            state=second_start.state,
        )
        self.assertEqual(first.requests, second.requests)
        self.assertEqual(
            breaker_failure_step_fingerprint(first),
            breaker_failure_step_fingerprint(second),
        )

    def test_binary_signal_requires_real_bool(self):
        with self.assertRaises(BreakerFailureRuntimeInputError):
            make_binary_signal(START, 1)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
