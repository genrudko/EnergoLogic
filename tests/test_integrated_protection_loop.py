from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import unittest

from energologic.core import load_model
from energologic.frontends.visio import VisioShapeBinding
from energologic.integration import (
    BranchCurrentBinding, IntegratedLoopStatus, run_integrated_protection_loop,
)
from energologic.operational import OperationBlock, SourceRef
from energologic.protection import setting_card_from_dict
from energologic.protection.runtime import compile_protection_program
from energologic.solvers import (
    FaultType, ShortCircuitBranchResult, ShortCircuitNodeResult,
    ShortCircuitRequest, ShortCircuitResult, SolverStatus, SolverStudyInput,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (SourceRef("source:b", "node"),)
FAULT = ShortCircuitRequest(canonical_bus_id="bus:b")
TARGET = "breaker:transformer"
BRANCH = "transformer:t1"
MEASUREMENT = "measurement:kl-1:phase-current"


def card_program(target=TARGET):
    data = json.loads((ROOT / "examples" / "protection-settings.synthetic.json").read_text(encoding="utf-8"))
    data["settings_scope"] = "full_configuration"
    for function in data["functions"]:
        if function["id"] == "function:kl-1:mtz":
            function["stages"][0]["actions"][0]["target_id"] = target
    return compile_protection_program(
        setting_card_from_dict(data), function_ids=("function:kl-1:mtz",),
    )


def qualified_fault(current_a=850.0, *, status=SolverStatus.SUCCESS, bus="bus:b"):
    return ShortCircuitResult(
        status=status,
        solver_name="qualified-fixture-solver",
        fault_type=FaultType.THREE_PHASE,
        fault_canonical_bus_id=bus,
        node=ShortCircuitNodeResult(
            canonical_id=bus,
            initial_symmetrical_current_a=current_a,
            peak_current_a=None, thermal_current_a=None,
            short_circuit_power_va=None,
            equivalent_resistance_ohm=None, equivalent_reactance_ohm=None,
        ),
        branch_contributions=(ShortCircuitBranchResult(
            canonical_id=BRANCH, element_kind="transformer_2w",
            initial_current_a=current_a,
            from_current_a=current_a,
            to_current_a=current_a,
            peak_current_a=None, thermal_current_a=None,
        ),),
    )


class FakeFaultSolver:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def short_circuit(self, study, request):
        self.calls += 1
        return self.result


class IntegratedProtectionLoopTests(unittest.TestCase):
    def setUp(self):
        self.model = load_model(ROOT / "examples" / "ws6-operational-two-source.json")
        self.study = SolverStudyInput(model=self.model)
        self.program = card_program()
        self.binding = BranchCurrentBinding(
            MEASUREMENT, BRANCH, "transformer_2w", "from", "synthetic:branch-current-hv",
        )
        self.shape = (VisioShapeBinding(TARGET, "Synthetic 35 kV", 107),)
        self.solver = FakeFaultSolver(qualified_fault())

    def run_loop(self, **overrides):
        values = dict(model=self.model, study=self.study, sources=SOURCE,
                      solver=self.solver, request=FAULT, program=self.program,
                      binding=self.binding, visio_bindings=self.shape)
        values.update(overrides)
        return run_integrated_protection_loop(**values)

    def test_trip_cycle_updates_topology_then_prepares_visio_projection(self):
        result = self.run_loop()
        self.assertEqual(result.status, IntegratedLoopStatus.COMPLETED)
        self.assertEqual(self.solver.calls, 1)
        self.assertEqual([item.event_type for item in result.protection_steps[0].events], ["pickup"])
        self.assertEqual([item.event_type for item in result.protection_steps[1].events], ["operate"])
        self.assertEqual(len(result.protection_steps[1].requests), 1)
        self.assertEqual(result.protection_steps[1].requests[0].action_type, "trip")
        self.assertEqual(result.switching_result.operation_id,
                         "protection:" + result.protection_steps[1].requests[0].request_id)
        self.assertEqual(result.switching_result.status.value, "success")
        self.assertEqual(
            next(e for e in result.model_after.elements if e.id == TARGET).attributes["switch_state"],
            "open",
        )
        self.assertNotEqual(result.model_before_fingerprint, result.visio_updates[0].canonical_model_fingerprint)
        delta = result.switching_result.operational_delta
        self.assertTrue(delta.topology_changed)
        self.assertTrue(any(c.before_energized and not c.after_energized
                            for c in delta.terminal_changes))
        self.assertEqual(result.visio_updates[0].shape_id, 107)
        self.assertEqual(result.visio_updates[0].page_name, "Synthetic 35 kV")
        self.assertEqual(
            [item.kind for item in result.trace],
            ["fault_studied", "branch_current_qualified", "pickup", "operate",
             "trip_requested", "breaker_opened", "topology_recalculated",
             "visio_update_prepared"],
        )
        self.assertEqual(
            [item.sequence for item in result.trace],
            list(range(1, len(result.trace)+1)),
        )

    def test_repeat_is_deterministic_and_sources_generator_is_supported(self):
        first = self.run_loop(sources=iter(SOURCE))
        self.solver.calls = 0
        second = self.run_loop(sources=iter(SOURCE))
        self.assertEqual(first, second)

    def test_current_below_pickup_does_not_trip_or_render(self):
        self.solver = FakeFaultSolver(qualified_fault(300.0))
        r = self.run_loop()
        self.assertEqual(r.status, IntegratedLoopStatus.NO_TRIP)
        self.assertEqual(r.model_after, self.model)
        self.assertIsNone(r.switching_result)
        self.assertFalse(r.visio_updates)
        self.assertNotIn("trip_requested", [x.kind for x in r.trace])

    def test_solver_failure_is_fail_closed(self):
        self.solver = FakeFaultSolver(qualified_fault(status=SolverStatus.SOLVER_FAILURE))
        r = self.run_loop()
        self.assertEqual((r.status, r.code), (IntegratedLoopStatus.BLOCKED, "unqualified_solver_result"))
        self.assertIsNone(r.model_after)
        self.assertFalse(r.visio_updates)

    def test_solver_exception_fails_closed_without_exposing_details(self):
        class Broken:
            def short_circuit(self, study, request):
                raise RuntimeError("PRIVATE_BACKEND_TRACE")
        r = self.run_loop(solver=Broken())
        self.assertEqual(r.code, "solver_execution_failed")
        self.assertNotIn("PRIVATE_BACKEND_TRACE", repr(r))

    def test_solver_result_wrong_fault_bus(self):
        r = self.run_loop(solver=FakeFaultSolver(qualified_fault(bus="bus:fake")))
        self.assertEqual(r.code, "unqualified_solver_result")

    def test_missing_or_duplicate_or_wrong_kind_branch_denied(self):
        good = qualified_fault()
        tests = [
            (replace(good, branch_contributions=()), "missing_branch_current"),
            (replace(good, branch_contributions=good.branch_contributions*2), "missing_branch_current"),
            (replace(good, branch_contributions=(replace(good.branch_contributions[0], element_kind="line"),)),
             "missing_branch_current"),
        ]
        for sc, expected in tests:
            with self.subTest(expected=expected):
                r = self.run_loop(solver=FakeFaultSolver(sc))
                self.assertEqual(r.code, expected)
                self.assertIsNone(r.model_after)

    def test_invalid_currents_block_pre_protection(self):
        for value in (None, float("nan"), float("inf"), -1, True):
            with self.subTest(value=value):
                good=qualified_fault()
                sc=replace(good, branch_contributions=(replace(good.branch_contributions[0], from_current_a=value),))
                r=self.run_loop(solver=FakeFaultSolver(sc))
                self.assertEqual(r.code, "unqualified_branch_current")
                self.assertFalse(r.protection_steps)

    def test_missing_fault_node_denied(self):
        fault = replace(qualified_fault(), node=None)
        self.assertEqual(
            self.run_loop(solver=FakeFaultSolver(fault)).code,
            "missing_fault_node_evidence",
        )

    def test_nonfinite_fault_node_current_denied(self):
        fault = qualified_fault()
        fault = replace(fault, node=replace(fault.node, initial_symmetrical_current_a=float("nan")))
        self.assertEqual(
            self.run_loop(solver=FakeFaultSolver(fault)).code,
            "unqualified_fault_node_current",
        )

    def test_sources_must_be_explicit(self):
        self.assertEqual(self.run_loop(sources=()).code, "missing_explicit_sources")
        self.assertEqual(self.solver.calls, 0)

    def test_residual_current_cannot_be_fed_from_three_phase_branch(self):
        altered_spec = replace(self.program.measurement_specs[0], semantic_key="residual_current")
        specs = tuple(
            altered_spec if s.id == altered_spec.id else s
            for s in self.program.measurement_specs
        )
        program = replace(self.program, measurement_specs=specs)
        result = self.run_loop(program=program)
        self.assertEqual(result.code, "unsupported_protection_measurement_or_action")
        self.assertEqual(self.solver.calls, 0)

    def test_wrong_study_model_denies_without_solving(self):
        modified=replace(self.model, model_id="another-network")
        r=self.run_loop(study=replace(self.study, model=modified))
        self.assertEqual(r.code,"study_model_mismatch")
        self.assertEqual(self.solver.calls,0)

    def test_fault_type_requires_qualified_three_phase(self):
        r=self.run_loop(request=replace(FAULT, fault_type=FaultType.PHASE_TO_PHASE))
        self.assertEqual(r.code, "unsupported_fault_study")
        self.assertEqual(self.solver.calls,0)

    def test_invalid_measurement_binding_fails_before_solving(self):
        for b in (
            replace(self.binding, measurement_input_id="guess"),
            replace(self.binding, source_ref=""),
            replace(self.binding, branch_side="neutral"),
            replace(self.binding, canonical_branch_id="missing"),
        ):
            with self.subTest(b=b):
                r=self.run_loop(binding=b)
                self.assertTrue(r.code.startswith("invalid_"))
                self.assertEqual(self.solver.calls,0)

    def test_missing_or_ambiguous_shape_binding_fails_before_solver(self):
        for shapes in ((), self.shape*2, (VisioShapeBinding(TARGET,"",107),)):
            with self.subTest(shapes=shapes):
                r=self.run_loop(visio_bindings=shapes)
                self.assertEqual(r.code,"unqualified_visio_binding")
                self.assertEqual(self.solver.calls,0)

    def test_unqualified_protection_scope_denied(self):
        r=self.run_loop(program=replace(self.program, settings_scope="operational_summary"))
        self.assertEqual(r.code,"unqualified_protection_program")

    def test_no_trip_if_delayed_stage_has_not_elapsed(self):
        r=self.run_loop(logical_times_s=("0","0.5"))
        self.assertEqual(r.status,IntegratedLoopStatus.NO_TRIP)
        self.assertFalse(r.visio_updates)

    def test_validator_blocks_simulated_breaker_without_visio_update(self):
        def deny(model, operation, before):
            return (OperationBlock("test_interlock", "synthetic gate"),)
        r=self.run_loop(validators=(deny,))
        self.assertEqual(r.code,"switching_not_completed")
        self.assertIsNone(r.model_after)
        self.assertFalse(r.visio_updates)
        self.assertEqual(r.switching_result.blocks[0].code,"test_interlock")
        self.assertIn("trip_requested", [x.kind for x in r.trace])
        self.assertNotIn("breaker_opened", [x.kind for x in r.trace])

    def test_unsound_logical_times_denied(self):
        for times in (("0","0"),("2","1"),("-1","0"),("NaN","1")):
            with self.subTest(times=times):
                r=self.run_loop(logical_times_s=times)
                self.assertEqual(r.code,"invalid_logical_times")
                self.assertEqual(self.solver.calls,0)


if __name__ == "__main__":
    unittest.main()
