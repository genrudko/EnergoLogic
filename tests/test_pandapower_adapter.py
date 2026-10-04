from __future__ import annotations

import importlib.util
import json
import math
import unittest

from energologic.solvers.contracts import (
    FaultType,
    ShortCircuitRequest,
    SolverStatus,
)
from energologic.solvers.pandapower_adapter import PandapowerAdapter

from solver_spike_fixture import ROOT, state_a_model, state_b_model, study


PANDAPOWER_AVAILABLE = importlib.util.find_spec("pandapower") is not None


@unittest.skipUnless(PANDAPOWER_AVAILABLE, "requires solver-pandapower extra")
class PandapowerAdapterIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.adapter = PandapowerAdapter()

    def test_power_flow_state_a_and_b_change_topology_and_results(self):
        result_a = self.adapter.power_flow(study(state_a_model()))
        result_b = self.adapter.power_flow(study(state_b_model()))

        self.assertEqual(result_a.status, SolverStatus.SUCCESS, result_a.errors)
        self.assertEqual(result_b.status, SolverStatus.SUCCESS, result_b.errors)
        self.assertEqual(result_a.solver_version, "3.5.5")
        self.assertEqual(result_b.solver_version, "3.5.5")
        self.assertNotEqual(result_a.topology_signature, result_b.topology_signature)

        expected_bus_ids = {
            element.id
            for element in state_a_model().elements
            if element.kind == "bus"
        }
        self.assertEqual(
            {item.canonical_id for item in result_a.buses},
            expected_bus_ids,
        )
        self.assertEqual(
            {item.canonical_id for item in result_b.buses},
            expected_bus_ids,
        )

        expected_branch_ids = {
            "line:feed-a",
            "line:feed-b",
            "transformer:t1",
        }
        self.assertEqual(
            {item.canonical_id for item in result_a.branches},
            expected_branch_ids,
        )

        current_deltas = [
            abs(
                (result_a.branch(branch_id).current_a or 0.0)
                - (result_b.branch(branch_id).current_a or 0.0)
            )
            for branch_id in ("line:feed-a", "line:feed-b")
        ]
        self.assertGreater(max(current_deltas), 1.0)

        open_difference = abs(
            (result_a.bus("bus:section-a-35kv").voltage_v or 0.0)
            - (result_a.bus("bus:section-b-35kv").voltage_v or 0.0)
        )
        closed_difference = abs(
            (result_b.bus("bus:section-a-35kv").voltage_v or 0.0)
            - (result_b.bus("bus:section-b-35kv").voltage_v or 0.0)
        )
        self.assertGreater(open_difference, 0.01)
        self.assertLess(closed_difference, open_difference)

        summary = {
            "state_a": {
                "section_a_v": result_a.bus("bus:section-a-35kv").voltage_v,
                "section_b_v": result_a.bus("bus:section-b-35kv").voltage_v,
                "line_a_current_a": result_a.branch("line:feed-a").current_a,
                "line_b_current_a": result_a.branch("line:feed-b").current_a,
                "trafo_loading_percent": result_a.branch(
                    "transformer:t1"
                ).loading_percent,
            },
            "state_b": {
                "section_a_v": result_b.bus("bus:section-a-35kv").voltage_v,
                "section_b_v": result_b.bus("bus:section-b-35kv").voltage_v,
                "line_a_current_a": result_b.branch("line:feed-a").current_a,
                "line_b_current_a": result_b.branch("line:feed-b").current_a,
                "trafo_loading_percent": result_b.branch(
                    "transformer:t1"
                ).loading_percent,
            },
        }
        print("WS8_POWER_FLOW_JSON=" + json.dumps(summary, sort_keys=True))

    def test_three_phase_short_circuit_exposes_normalized_currents_and_branch_contribution(self):
        result = self.adapter.short_circuit(
            study(),
            ShortCircuitRequest(
                canonical_bus_id="bus:section-a-35kv",
                fault_type=FaultType.THREE_PHASE,
                calculate_peak=True,
                calculate_thermal=True,
                branch_results=True,
            ),
        )
        self.assertEqual(result.status, SolverStatus.SUCCESS, result.errors)
        self.assertIsNotNone(result.node)
        assert result.node is not None
        self.assertEqual(result.node.canonical_id, "bus:section-a-35kv")
        self.assertGreater(result.node.initial_symmetrical_current_a or 0.0, 0.0)
        self.assertGreater(result.node.peak_current_a or 0.0, 0.0)
        self.assertGreater(result.node.thermal_current_a or 0.0, 0.0)

        contributions = {
            item.canonical_id: item
            for item in result.branch_contributions
        }
        self.assertIn("line:feed-a", contributions)
        self.assertGreater(
            contributions["line:feed-a"].initial_current_a or 0.0,
            0.0,
        )

        print(
            "WS8_SC_3PH_JSON="
            + json.dumps(
                {
                    "ikss_a": result.node.initial_symmetrical_current_a,
                    "ip_a": result.node.peak_current_a,
                    "ith_a": result.node.thermal_current_a,
                    "skss_va": result.node.short_circuit_power_va,
                    "line_a_ikss_a": contributions[
                        "line:feed-a"
                    ].initial_current_a,
                },
                sort_keys=True,
            )
        )

    def test_external_grid_short_circuit_matches_independent_hand_calculation(self):
        result = self.adapter.short_circuit(
            study(),
            ShortCircuitRequest(
                canonical_bus_id="bus:grid-35kv",
                fault_type=FaultType.THREE_PHASE,
                calculate_peak=False,
                calculate_thermal=False,
                branch_results=False,
            ),
        )
        self.assertEqual(result.status, SolverStatus.SUCCESS, result.errors)
        assert result.node is not None
        actual = result.node.initial_symmetrical_current_a
        self.assertIsNotNone(actual)

        expected = 500_000_000.0 / (math.sqrt(3.0) * 35_000.0)
        self.assertAlmostEqual(actual or 0.0, expected, delta=expected * 0.005)

    def test_two_phase_fault_is_supported(self):
        result = self.adapter.short_circuit(
            study(),
            ShortCircuitRequest(
                canonical_bus_id="bus:section-a-35kv",
                fault_type=FaultType.PHASE_TO_PHASE,
                calculate_peak=False,
                calculate_thermal=False,
                branch_results=True,
            ),
        )
        self.assertEqual(result.status, SolverStatus.SUCCESS, result.errors)
        assert result.node is not None
        self.assertGreater(result.node.initial_symmetrical_current_a or 0.0, 0.0)

    def test_single_phase_to_earth_fault_is_supported_with_zero_sequence_data(self):
        result = self.adapter.short_circuit(
            study(),
            ShortCircuitRequest(
                canonical_bus_id="bus:section-a-35kv",
                fault_type=FaultType.SINGLE_PHASE_TO_EARTH,
                calculate_peak=False,
                calculate_thermal=False,
                branch_results=True,
            ),
        )
        self.assertEqual(result.status, SolverStatus.SUCCESS, result.errors)
        assert result.node is not None
        self.assertGreater(result.node.initial_symmetrical_current_a or 0.0, 0.0)
        self.assertEqual(result.node.canonical_id, "bus:section-a-35kv")


    def test_pandapower_355_matches_committed_numerical_golden(self):
        golden = json.loads(
            (
                ROOT
                / "tests"
                / "fixtures"
                / "ws8-pandapower-3.5.5-golden.json"
            ).read_text(encoding="utf-8")
        )
        tol = golden["tolerances"]

        result_a = self.adapter.power_flow(study(state_a_model()))
        result_b = self.adapter.power_flow(study(state_b_model()))
        self.assertEqual(result_a.status, SolverStatus.SUCCESS, result_a.errors)
        self.assertEqual(result_b.status, SolverStatus.SUCCESS, result_b.errors)

        for label, result in (("state_a", result_a), ("state_b", result_b)):
            expected = golden["power_flow"][label]
            self.assertAlmostEqual(
                result.bus("bus:section-a-35kv").voltage_v or 0.0,
                expected["section_a_voltage_v"],
                delta=tol["voltage_v"],
            )
            self.assertAlmostEqual(
                result.bus("bus:section-b-35kv").voltage_v or 0.0,
                expected["section_b_voltage_v"],
                delta=tol["voltage_v"],
            )
            self.assertAlmostEqual(
                result.branch("line:feed-a").current_a or 0.0,
                expected["line_a_current_a"],
                delta=tol["current_a"],
            )
            self.assertAlmostEqual(
                result.branch("line:feed-b").current_a or 0.0,
                expected["line_b_current_a"],
                delta=tol["current_a"],
            )
            self.assertAlmostEqual(
                result.branch("transformer:t1").loading_percent or 0.0,
                expected["transformer_loading_percent"],
                delta=tol["loading_percent"],
            )

        requests = (
            ("section_a_3ph", FaultType.THREE_PHASE, True, True),
            ("section_a_2ph", FaultType.PHASE_TO_PHASE, False, False),
            (
                "section_a_1ph",
                FaultType.SINGLE_PHASE_TO_EARTH,
                False,
                False,
            ),
        )
        for key, fault_type, peak, thermal in requests:
            with self.subTest(fault=fault_type.value):
                result = self.adapter.short_circuit(
                    study(),
                    ShortCircuitRequest(
                        canonical_bus_id="bus:section-a-35kv",
                        fault_type=fault_type,
                        calculate_peak=peak,
                        calculate_thermal=thermal,
                        branch_results=True,
                    ),
                )
                self.assertEqual(
                    result.status,
                    SolverStatus.SUCCESS,
                    result.errors,
                )
                assert result.node is not None
                expected = golden["short_circuit"][key]
                self.assertAlmostEqual(
                    result.node.initial_symmetrical_current_a or 0.0,
                    expected["ikss_a"],
                    delta=tol["short_circuit_current_a"],
                )
                contributions = {
                    item.canonical_id: item
                    for item in result.branch_contributions
                }
                self.assertAlmostEqual(
                    contributions["line:feed-a"].initial_current_a or 0.0,
                    expected["line_a_ikss_a"],
                    delta=tol["short_circuit_current_a"],
                )
                if "ip_a" in expected:
                    self.assertAlmostEqual(
                        result.node.peak_current_a or 0.0,
                        expected["ip_a"],
                        delta=tol["short_circuit_current_a"],
                    )
                if "ith_a" in expected:
                    self.assertAlmostEqual(
                        result.node.thermal_current_a or 0.0,
                        expected["ith_a"],
                        delta=tol["short_circuit_current_a"],
                    )
                if "skss_va" in expected:
                    self.assertAlmostEqual(
                        result.node.short_circuit_power_va or 0.0,
                        expected["skss_va"],
                        delta=tol["short_circuit_power_va"],
                    )


if __name__ == "__main__":
    unittest.main()
