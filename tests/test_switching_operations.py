from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from energologic.core import CanonicalModel, load_model
from energologic.operational import (
    OperationBlock,
    OperationalEventKind,
    SourceRef,
    SwitchStateOperation,
    SwitchingOperationStatus,
    WithdrawablePositionOperation,
    execute_switching_operation,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "ws6-operational-two-source.json"
SOURCE_A = SourceRef("source:a", "node")
SOURCE_B = SourceRef("source:b", "node")


def load_fixture() -> CanonicalModel:
    return load_model(FIXTURE)


def element(model: CanonicalModel, element_id: str):
    return next(item for item in model.elements if item.id == element_id)


class SwitchingOperationsTests(unittest.TestCase):
    def test_close_bus_coupler_updates_model_and_records_source_changes(self):
        model = load_fixture()
        result = execute_switching_operation(
            model,
            (SOURCE_A, SOURCE_B),
            SwitchStateOperation(
                "op:close-coupler",
                "breaker:coupler",
                "closed",
            ),
        )

        self.assertEqual(result.status, SwitchingOperationStatus.SUCCESS)
        self.assertIsNotNone(result.model_after)
        self.assertEqual(
            element(model, "breaker:coupler").attributes["switch_state"],
            "open",
        )
        self.assertEqual(
            element(result.model_after, "breaker:coupler")
            .attributes["switch_state"],
            "closed",
        )
        self.assertNotEqual(
            result.model_before_fingerprint,
            result.model_after_fingerprint,
        )
        self.assertTrue(result.operational_delta.topology_changed)

        self.assertEqual(
            result.events[0].kind,
            OperationalEventKind.SWITCH_STATE_CHANGED,
        )
        self.assertEqual(result.events[0].before_value, "open")
        self.assertEqual(result.events[0].after_value, "closed")

        source_change_events = [
            event
            for event in result.events
            if event.kind
            is OperationalEventKind.TERMINAL_SOURCE_ATTRIBUTION_CHANGED
        ]
        self.assertTrue(source_change_events)
        self.assertTrue(
            any(
                event.element_id == "bus:a"
                and event.before_sources == (SOURCE_A,)
                and event.after_sources == (SOURCE_A, SOURCE_B)
                for event in source_change_events
            )
        )
        self.assertEqual(
            tuple(event.sequence for event in result.events),
            tuple(range(1, len(result.events) + 1)),
        )

    def test_open_source_b_disconnector_records_deenergization_sequence(self):
        result = execute_switching_operation(
            load_fixture(),
            (SOURCE_A, SOURCE_B),
            SwitchStateOperation(
                "op:open-source-b",
                "disconnector:source-b",
                "open",
            ),
        )
        self.assertEqual(result.status, SwitchingOperationStatus.SUCCESS)

        deenergized = [
            event
            for event in result.events
            if (
                event.kind
                is OperationalEventKind.TERMINAL_ENERGIZATION_CHANGED
                and event.before_value is True
                and event.after_value is False
            )
        ]
        self.assertTrue(deenergized)
        self.assertTrue(
            any(
                event.element_id == "bus:b"
                and event.terminal_id == "node"
                for event in deenergized
            )
        )
        self.assertTrue(
            any(
                event.element_id == "external:lv"
                and event.terminal_id == "node"
                for event in deenergized
            )
        )

    def test_withdrawable_position_change_is_represented_without_invented_block(self):
        result = execute_switching_operation(
            load_fixture(),
            (SOURCE_B,),
            WithdrawablePositionOperation(
                "op:withdraw-transformer-breaker",
                "breaker:transformer",
                "repair",
            ),
        )
        self.assertEqual(result.status, SwitchingOperationStatus.SUCCESS)
        self.assertEqual(
            result.events[0].kind,
            OperationalEventKind.WITHDRAWABLE_POSITION_CHANGED,
        )
        self.assertEqual(result.events[0].before_value, "working")
        self.assertEqual(result.events[0].after_value, "repair")
        self.assertTrue(
            any(
                event.kind
                is OperationalEventKind.TERMINAL_ENERGIZATION_CHANGED
                and event.element_id == "transformer:t1"
                for event in result.events
            )
        )

    def test_validator_can_block_before_model_mutation(self):
        def site_validator(model, operation, before):
            self.assertEqual(operation.element_id, "breaker:coupler")
            return (
                OperationBlock(
                    "site_block",
                    "operation is blocked by site configuration",
                    "test-site-validator",
                ),
            )

        model = load_fixture()
        result = execute_switching_operation(
            model,
            (SOURCE_A, SOURCE_B),
            SwitchStateOperation(
                "op:blocked-close",
                "breaker:coupler",
                "closed",
            ),
            validators=(site_validator,),
        )
        self.assertEqual(result.status, SwitchingOperationStatus.BLOCKED)
        self.assertEqual(result.events, ())
        self.assertEqual(result.model_after_fingerprint, result.model_before_fingerprint)
        self.assertEqual(result.model_after, model)
        self.assertEqual(result.blocks[0].code, "site_block")
        self.assertEqual(
            element(result.model_after, "breaker:coupler")
            .attributes["switch_state"],
            "open",
        )

    def test_validator_exception_fails_closed_without_leaking_exception_text(self):
        def broken_validator(model, operation, before):
            raise RuntimeError("SECRET_INTERNAL_DETAIL")

        result = execute_switching_operation(
            load_fixture(),
            (SOURCE_A,),
            SwitchStateOperation(
                "op:validator-failure",
                "breaker:coupler",
                "closed",
            ),
            validators=(broken_validator,),
        )
        self.assertEqual(result.status, SwitchingOperationStatus.BLOCKED)
        self.assertEqual(result.blocks[0].code, "validator_failure")
        self.assertNotIn("SECRET_INTERNAL_DETAIL", result.blocks[0].message)

    def test_same_target_state_is_explicit_no_change(self):
        model = load_fixture()
        result = execute_switching_operation(
            model,
            (SOURCE_A, SOURCE_B),
            SwitchStateOperation(
                "op:no-change",
                "breaker:coupler",
                "open",
            ),
        )
        self.assertEqual(result.status, SwitchingOperationStatus.NO_CHANGE)
        self.assertEqual(result.events, ())
        self.assertEqual(result.model_after, model)
        self.assertFalse(result.operational_delta.topology_changed)
        self.assertEqual(result.operational_delta.terminal_changes, ())

    def test_fixed_switchgear_rejects_withdrawable_position_operation(self):
        result = execute_switching_operation(
            load_fixture(),
            (SOURCE_A,),
            WithdrawablePositionOperation(
                "op:bad-position",
                "breaker:coupler",
                "repair",
            ),
        )
        self.assertEqual(
            result.status,
            SwitchingOperationStatus.INVALID_OPERATION,
        )
        self.assertEqual(
            result.messages[0].code,
            "operation_requires_withdrawable_switchgear",
        )

    def test_unknown_target_fails_closed(self):
        result = execute_switching_operation(
            load_fixture(),
            (SOURCE_A,),
            SwitchStateOperation(
                "op:missing",
                "breaker:missing",
                "open",
            ),
        )
        self.assertEqual(
            result.status,
            SwitchingOperationStatus.INVALID_OPERATION,
        )
        self.assertEqual(result.messages[0].code, "operation_target_not_found")

    def test_non_switching_target_fails_closed(self):
        result = execute_switching_operation(
            load_fixture(),
            (SOURCE_A,),
            SwitchStateOperation(
                "op:not-switch",
                "bus:a",
                "open",
            ),
        )
        self.assertEqual(
            result.status,
            SwitchingOperationStatus.INVALID_OPERATION,
        )
        self.assertEqual(
            result.messages[0].code,
            "unsupported_operation_target",
        )

    def test_invalid_target_state_fails_closed(self):
        result = execute_switching_operation(
            load_fixture(),
            (SOURCE_A,),
            SwitchStateOperation(
                "op:bad-state",
                "breaker:coupler",
                "tripped-ish",
            ),
        )
        self.assertEqual(
            result.status,
            SwitchingOperationStatus.INVALID_OPERATION,
        )
        self.assertEqual(
            result.messages[0].code,
            "invalid_target_switch_state",
        )

    def test_invalid_operation_id_fails_closed(self):
        result = execute_switching_operation(
            load_fixture(),
            (SOURCE_A,),
            SwitchStateOperation(
                "",
                "breaker:coupler",
                "closed",
            ),
        )
        self.assertEqual(
            result.status,
            SwitchingOperationStatus.INVALID_OPERATION,
        )
        self.assertEqual(result.messages[0].code, "invalid_operation_id")

    def test_invalid_source_is_not_misreported_as_invalid_model(self):
        result = execute_switching_operation(
            load_fixture(),
            (SourceRef("source:missing", "node"),),
            SwitchStateOperation(
                "op:invalid-source",
                "breaker:coupler",
                "closed",
            ),
        )
        self.assertEqual(
            result.status,
            SwitchingOperationStatus.INVALID_SOURCE,
        )
        self.assertEqual(result.messages[0].code, "invalid_source_endpoint")

    def test_invalid_initial_model_is_normalized(self):
        model = load_fixture()
        elements = []
        for item in model.elements:
            if item.id == "breaker:coupler":
                attrs = dict(item.attributes)
                attrs["switch_state"] = "bad"
                item = replace(item, attributes=attrs)
            elements.append(item)
        invalid = replace(model, elements=tuple(elements))

        result = execute_switching_operation(
            invalid,
            (SOURCE_A,),
            SwitchStateOperation(
                "op:on-invalid-model",
                "breaker:coupler",
                "closed",
            ),
        )
        self.assertEqual(result.status, SwitchingOperationStatus.INVALID_MODEL)
        self.assertIn(
            "invalid_switch_state",
            {message.code for message in result.messages},
        )

    def test_event_sequence_is_input_order_independent(self):
        model = load_fixture()
        reordered = replace(
            model,
            elements=tuple(reversed(model.elements)),
            connections=tuple(reversed(model.connections)),
        )
        operation = SwitchStateOperation(
            "op:deterministic",
            "breaker:coupler",
            "closed",
        )
        first = execute_switching_operation(
            model,
            (SOURCE_B, SOURCE_A),
            operation,
        )
        second = execute_switching_operation(
            reordered,
            (SOURCE_A, SOURCE_B, SOURCE_A),
            operation,
        )
        self.assertEqual(first.status, SwitchingOperationStatus.SUCCESS)
        self.assertEqual(second.status, SwitchingOperationStatus.SUCCESS)
        self.assertEqual(first.model_after_fingerprint, second.model_after_fingerprint)
        self.assertEqual(first.events, second.events)
        self.assertEqual(first.operational_delta, second.operational_delta)


if __name__ == "__main__":
    unittest.main()
