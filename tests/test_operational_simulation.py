from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from energologic.core import CanonicalModel, Element, Terminal, load_model
from energologic.operational import (
    OperationalStatus,
    SourceRef,
    compare_operational_results,
    simulate_operational_state,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "ws6-operational-two-source.json"
SOURCE_A = SourceRef("source:a", "node")
SOURCE_B = SourceRef("source:b", "node")


def load_fixture() -> CanonicalModel:
    return load_model(FIXTURE)


def replace_element_attributes(
    model: CanonicalModel,
    element_id: str,
    **changes: object,
) -> CanonicalModel:
    elements: list[Element] = []
    for element in model.elements:
        if element.id != element_id:
            elements.append(element)
            continue
        attributes = dict(element.attributes)
        attributes.update(changes)
        elements.append(replace(element, attributes=attributes))
    return replace(model, elements=tuple(elements))


def terminal_state(result, element_id: str, terminal_id: str):
    return next(
        state
        for state in result.terminal_states
        if state.element_id == element_id and state.terminal_id == terminal_id
    )


def element_state(result, element_id: str):
    return next(
        state
        for state in result.element_states
        if state.element_id == element_id
    )


class OperationalSimulationTests(unittest.TestCase):
    def test_fixture_is_valid_and_two_open_coupler_sides_trace_different_sources(self):
        result = simulate_operational_state(
            load_fixture(),
            (SOURCE_B, SOURCE_A),
        )
        self.assertEqual(result.status, OperationalStatus.SUCCESS)

        left = terminal_state(result, "breaker:coupler", "a")
        right = terminal_state(result, "breaker:coupler", "b")

        self.assertTrue(left.energized)
        self.assertTrue(right.energized)
        self.assertEqual(left.sources, (SOURCE_A,))
        self.assertEqual(right.sources, (SOURCE_B,))

        coupler = element_state(result, "breaker:coupler")
        self.assertTrue(coupler.energized)
        self.assertTrue(coupler.fully_energized)
        self.assertEqual(coupler.sources, (SOURCE_A, SOURCE_B))

    def test_closing_bus_coupler_merges_source_attribution(self):
        before_model = load_fixture()
        after_model = replace_element_attributes(
            before_model,
            "breaker:coupler",
            switch_state="closed",
        )

        before = simulate_operational_state(before_model, (SOURCE_A, SOURCE_B))
        after = simulate_operational_state(after_model, (SOURCE_A, SOURCE_B))

        self.assertEqual(before.status, OperationalStatus.SUCCESS)
        self.assertEqual(after.status, OperationalStatus.SUCCESS)
        self.assertNotEqual(
            before.conductive_topology_fingerprint,
            after.conductive_topology_fingerprint,
        )

        self.assertEqual(
            terminal_state(after, "bus:a", "node").sources,
            (SOURCE_A, SOURCE_B),
        )
        self.assertEqual(
            terminal_state(after, "bus:b", "node").sources,
            (SOURCE_A, SOURCE_B),
        )
        self.assertEqual(
            terminal_state(after, "external:lv", "node").sources,
            (SOURCE_A, SOURCE_B),
        )

        delta = compare_operational_results(before, after)
        self.assertEqual(delta.status, OperationalStatus.SUCCESS)
        self.assertTrue(delta.topology_changed)
        self.assertTrue(delta.terminal_changes)
        self.assertTrue(
            any(
                change.element_id == "bus:a"
                and change.before_sources == (SOURCE_A,)
                and change.after_sources == (SOURCE_A, SOURCE_B)
                for change in delta.terminal_changes
            )
        )

    def test_open_source_b_disconnector_deenergizes_section_b_and_transformer(self):
        model = replace_element_attributes(
            load_fixture(),
            "disconnector:source-b",
            switch_state="open",
        )
        result = simulate_operational_state(model, (SOURCE_A, SOURCE_B))
        self.assertEqual(result.status, OperationalStatus.SUCCESS)

        self.assertTrue(
            terminal_state(result, "disconnector:source-b", "a").energized
        )
        self.assertEqual(
            terminal_state(result, "disconnector:source-b", "a").sources,
            (SOURCE_B,),
        )
        self.assertFalse(
            terminal_state(result, "disconnector:source-b", "b").energized
        )
        self.assertFalse(terminal_state(result, "bus:b", "node").energized)
        self.assertFalse(
            terminal_state(result, "transformer:t1", "hv").energized
        )
        self.assertFalse(
            terminal_state(result, "transformer:t1", "lv").energized
        )
        self.assertFalse(
            terminal_state(result, "external:lv", "node").energized
        )

    def test_withdrawable_transformer_breaker_repair_position_blocks_primary_path(self):
        model = replace_element_attributes(
            load_fixture(),
            "breaker:transformer",
            withdrawable_position="repair",
        )
        result = simulate_operational_state(model, (SOURCE_A, SOURCE_B))
        self.assertEqual(result.status, OperationalStatus.SUCCESS)

        self.assertTrue(
            terminal_state(result, "breaker:transformer", "a").energized
        )
        self.assertFalse(
            terminal_state(result, "breaker:transformer", "b").energized
        )
        self.assertFalse(
            terminal_state(result, "transformer:t1", "hv").energized
        )
        self.assertFalse(
            terminal_state(result, "external:lv", "node").energized
        )

    def test_withdrawable_transformer_breaker_control_position_also_blocks(self):
        model = replace_element_attributes(
            load_fixture(),
            "breaker:transformer",
            withdrawable_position="control",
        )
        result = simulate_operational_state(model, (SOURCE_B,))
        self.assertEqual(result.status, OperationalStatus.SUCCESS)
        self.assertFalse(
            terminal_state(result, "breaker:transformer", "b").energized
        )

    def test_transformer_propagates_topological_energization_across_voltage_levels(self):
        result = simulate_operational_state(load_fixture(), (SOURCE_B,))
        self.assertEqual(result.status, OperationalStatus.SUCCESS)
        self.assertTrue(
            terminal_state(result, "transformer:t1", "hv").energized
        )
        self.assertTrue(
            terminal_state(result, "transformer:t1", "lv").energized
        )
        self.assertEqual(
            terminal_state(result, "external:lv", "node").sources,
            (SOURCE_B,),
        )

    def test_current_transformer_is_topologically_conductive(self):
        result = simulate_operational_state(load_fixture(), (SOURCE_A,))
        self.assertEqual(result.status, OperationalStatus.SUCCESS)
        self.assertEqual(
            terminal_state(result, "ct:source-a", "a").sources,
            (SOURCE_A,),
        )
        self.assertEqual(
            terminal_state(result, "ct:source-a", "b").sources,
            (SOURCE_A,),
        )
        self.assertEqual(
            terminal_state(result, "bus:a", "node").sources,
            (SOURCE_A,),
        )

    def test_no_active_sources_is_valid_all_deenergized_state(self):
        result = simulate_operational_state(load_fixture(), ())
        self.assertEqual(result.status, OperationalStatus.SUCCESS)
        self.assertTrue(result.terminal_states)
        self.assertTrue(
            all(not state.energized for state in result.terminal_states)
        )
        self.assertTrue(
            all(not state.energized for state in result.element_states)
        )

    def test_missing_source_endpoint_fails_closed(self):
        result = simulate_operational_state(
            load_fixture(),
            (SourceRef("source:missing", "node"),),
        )
        self.assertEqual(result.status, OperationalStatus.INVALID_SOURCE)
        self.assertEqual(result.terminal_states, ())
        self.assertEqual(
            tuple(message.code for message in result.messages),
            ("invalid_source_endpoint",),
        )

    def test_invalid_switching_model_returns_normalized_invalid_model(self):
        model = load_fixture()
        invalid = replace_element_attributes(
            model,
            "breaker:coupler",
            switch_state="unknown",
        )
        result = simulate_operational_state(invalid, (SOURCE_A,))
        self.assertEqual(result.status, OperationalStatus.INVALID_MODEL)
        self.assertEqual(result.terminal_states, ())
        self.assertIn(
            "invalid_switch_state",
            {message.code for message in result.messages},
        )

    def test_results_are_independent_of_model_and_source_input_order(self):
        model = load_fixture()
        reversed_model = replace(
            model,
            elements=tuple(reversed(model.elements)),
            connections=tuple(reversed(model.connections)),
        )
        first = simulate_operational_state(model, (SOURCE_B, SOURCE_A))
        second = simulate_operational_state(
            reversed_model,
            (SOURCE_A, SOURCE_B, SOURCE_A),
        )
        self.assertEqual(first.status, OperationalStatus.SUCCESS)
        self.assertEqual(second.status, OperationalStatus.SUCCESS)
        self.assertEqual(
            first.conductive_topology_fingerprint,
            second.conductive_topology_fingerprint,
        )
        self.assertEqual(first.terminal_states, second.terminal_states)
        self.assertEqual(first.element_states, second.element_states)

    def test_delta_rejects_changed_terminal_set(self):
        before = simulate_operational_state(load_fixture(), (SOURCE_A,))
        model = load_fixture()
        extra = Element(
            id="bus:extra",
            kind="bus",
            terminals=(Terminal("node"),),
            attributes={"nominal_voltage_v": 35000},
        )
        changed_model = replace(model, elements=(*model.elements, extra))
        after = simulate_operational_state(changed_model, (SOURCE_A,))
        self.assertEqual(after.status, OperationalStatus.SUCCESS)

        delta = compare_operational_results(before, after)
        self.assertEqual(delta.status, OperationalStatus.INCOMPATIBLE_MODELS)
        self.assertEqual(
            tuple(message.code for message in delta.messages),
            ("terminal_set_changed",),
        )

    def test_delta_rejects_non_success_results(self):
        good = simulate_operational_state(load_fixture(), (SOURCE_A,))
        bad = simulate_operational_state(
            load_fixture(),
            (SourceRef("missing", "node"),),
        )
        delta = compare_operational_results(good, bad)
        self.assertEqual(delta.status, OperationalStatus.INCOMPATIBLE_MODELS)
        self.assertEqual(
            tuple(message.code for message in delta.messages),
            ("non_success_result",),
        )


if __name__ == "__main__":
    unittest.main()
