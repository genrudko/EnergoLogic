"""Optional real pandapower integration gate for the synthetic protection loop.

Skipped only when solver extra is absent; Linux/Windows pinned solver CI must run it.
"""
from __future__ import annotations

import importlib.util
import unittest

from energologic.frontends.visio import VisioShapeBinding
from energologic.integration import (
    BranchCurrentBinding, IntegratedLoopStatus, run_integrated_protection_loop,
)
from energologic.operational import SourceRef
from energologic.solvers import PandapowerAdapter, ShortCircuitRequest

from solver_spike_fixture import state_a_model, study
from test_integrated_protection_loop import card_program


PANDAPOWER_AVAILABLE = importlib.util.find_spec("pandapower") is not None


@unittest.skipUnless(PANDAPOWER_AVAILABLE, "requires pinned solver-pandapower extra")
class RealSolverIntegratedProtectionTests(unittest.TestCase):
    def test_pandapower_three_phase_fault_opens_feeder_breaker(self):
        model = state_a_model()
        result = run_integrated_protection_loop(
            model=model,
            study=study(model),
            sources=(SourceRef("source:grid", "node"),),
            solver=PandapowerAdapter(),
            request=ShortCircuitRequest(
                canonical_bus_id="bus:section-a-35kv", branch_results=True,
            ),
            program=card_program(target="breaker:incomer-a"),
            binding=BranchCurrentBinding(
                measurement_input_id="measurement:kl-1:phase-current",
                canonical_branch_id="line:feed-a",
                element_kind="line",
                branch_side="from",
                source_ref="synthetic:ws8-pandapower-3ph-branch",
            ),
            visio_bindings=(VisioShapeBinding(
                element_id="breaker:incomer-a",
                page_name="Synthetic 35 kV",
                shape_id=204,
            ),),
            logical_times_s=("0", "0.8"),
        )
        self.assertEqual(result.status, IntegratedLoopStatus.COMPLETED, result.code)
        self.assertEqual(result.solver_result.solver_version, "3.5.5")
        self.assertEqual(result.solver_result.fault_canonical_bus_id, "bus:section-a-35kv")
        self.assertEqual(
            next(e for e in result.model_after.elements if e.id=="breaker:incomer-a")
                .attributes["switch_state"], "open",
        )
        self.assertTrue(result.switching_result.operational_delta.topology_changed)
        self.assertEqual(result.visio_updates[0].shape_id, 204)
        self.assertEqual(result.trace[-1].kind, "visio_update_prepared")


if __name__ == "__main__":
    unittest.main()
