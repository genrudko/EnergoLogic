from __future__ import annotations

from dataclasses import replace
import unittest

from energologic.core import Endpoint, load_model
from energologic.domain import (
    ELECTRICAL_OPERATIONAL_SOLVER_V1,
    validate_electrical_model,
    validate_switching_state_model,
)
from energologic.operational import (
    SourceRef, SwitchStateOperation, SwitchingOperationStatus,
    execute_switching_operation, simulate_operational_state,
    OperationalStatus,
)

from solver_spike_fixture import ROOT


MODEL = ROOT / "examples" / "ws8-synthetic-network.json"
PROFILE = ELECTRICAL_OPERATIONAL_SOLVER_V1
SOURCE = (SourceRef("source:grid", "node"),)


def changed_element(model, element_id, **attrs):
    elements = []
    for element in model.elements:
        if element.id == element_id:
            elements.append(replace(element, attributes={**element.attributes, **attrs}))
        else:
            elements.append(element)
    return replace(model, elements=tuple(elements))


class OperationalSolverCompatibleProfileTests(unittest.TestCase):
    def setUp(self):
        self.model = load_model(MODEL)

    def test_base_electrical_v1_remains_restrictive(self):
        errors = validate_electrical_model(self.model)
        self.assertIn("unsupported_element_kind", {item.code for item in errors})

    def test_opt_in_profile_accepts_validated_solver_topology(self):
        self.assertEqual(validate_electrical_model(self.model, profile=PROFILE), ())
        self.assertEqual(
            validate_switching_state_model(self.model, electrical_profile=PROFILE), (),
        )
        result = simulate_operational_state(
            self.model, SOURCE, electrical_profile=PROFILE,
        )
        self.assertEqual(result.status, OperationalStatus.SUCCESS)
        states={(x.element_id,x.terminal_id):x for x in result.terminal_states}
        self.assertTrue(states[("line:feed-a","from")].energized)
        self.assertTrue(states[("line:feed-a","to")].energized)
        self.assertTrue(states[("bus:section-a-35kv","node")].energized)

    def test_open_breaker_recalculates_solver_network_deenergization(self):
        changed = execute_switching_operation(
            self.model, SOURCE,
            SwitchStateOperation("op:protect-incomer-a", "breaker:incomer-a", "open"),
            electrical_profile=PROFILE,
        )
        self.assertEqual(changed.status, SwitchingOperationStatus.SUCCESS)
        self.assertTrue(changed.operational_delta.topology_changed)
        self.assertTrue(
            any(row.element_id=="bus:section-a-35kv"
                and row.before_energized and not row.after_energized
                for row in changed.operational_delta.terminal_changes)
        )
        # Opening incomer A does not deenergize the other feeder.
        other = {
            (x.element_id,x.terminal_id):x
            for x in changed.operational_after.terminal_states
        }
        self.assertTrue(other[("bus:section-b-35kv","node")].energized)

    def test_direct_bus_voltage_mismatch_on_line_is_rejected(self):
        changed = changed_element(self.model,"bus:feeder-a-35kv",nominal_voltage_v=10000)
        issues = validate_electrical_model(changed, profile=PROFILE)
        self.assertIn("line_terminal_voltage_mismatch", {item.code for item in issues})
        result = simulate_operational_state(changed,SOURCE,electrical_profile=PROFILE)
        self.assertEqual(result.status, OperationalStatus.INVALID_MODEL)

    def test_line_cannot_infer_voltage_from_non_bus_neighbor(self):
        cs=[]
        for c in self.model.connections:
            if c.id == "connection:line-a-feeder":
                cs.append(replace(c,endpoints=(
                    Endpoint("line:feed-a","to"),
                    Endpoint("breaker:incomer-a","b"),
                )))
            else:
                cs.append(c)
        changed=replace(self.model,connections=tuple(cs))
        issues = validate_electrical_model(changed,profile=PROFILE)
        self.assertIn("unresolved_connected_bus_voltage",{x.code for x in issues})
        result=simulate_operational_state(changed,SOURCE,electrical_profile=PROFILE)
        self.assertEqual(result.status,OperationalStatus.INVALID_MODEL)

    def test_inherited_bus_voltage_and_explicit_voltage_cannot_conflict(self):
        changed = changed_element(self.model,"load:section-a",nominal_voltage_v=400)
        self.assertIn(
            "unexpected_inferred_voltage_spec",
            {x.code for x in validate_electrical_model(changed,profile=PROFILE)}
        )


if __name__ == "__main__":
    unittest.main()
