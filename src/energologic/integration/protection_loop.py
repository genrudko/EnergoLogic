"""Qualified synthetic fault → protection → breaker-operation integration (headless).

This module deliberately never sends commands to physical switchgear or writes Visio.
A 'VisioStateUpdate' is an intent that requires a separately accepted live adapter.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from math import isfinite
from typing import Iterable, Protocol

from energologic.core import CanonicalModel, fingerprint
from energologic.domain import ELECTRICAL_OPERATIONAL_SOLVER_V1, read_switching_state
from energologic.frontends.visio.contracts import VisioShapeBinding
from energologic.operational import (
    OperationValidator,
    OperationalStatus,
    SourceRef,
    SwitchStateOperation,
    SwitchingOperationResult,
    SwitchingOperationStatus,
    execute_switching_operation,
    simulate_operational_state,
)
from energologic.protection.runtime import (
    ProtectionProgram,
    ProtectionRuntimeInputError,
    ProtectionStepResult,
    evaluate_protection_step,
    make_measured_quantity,
    make_snapshot,
)
from energologic.solvers.contracts import (
    FaultType,
    ShortCircuitRequest,
    ShortCircuitResult,
    SolverStatus,
    SolverStudyInput,
)


class ShortCircuitSolver(Protocol):
    def short_circuit(
        self, study: SolverStudyInput, request: ShortCircuitRequest,
    ) -> ShortCircuitResult: ...


class IntegratedLoopStatus(str, Enum):
    COMPLETED = "completed"
    NO_TRIP = "no_trip"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class BranchCurrentBinding:
    """An *explicit* engineering assignment, never inferred from the topology."""

    measurement_input_id: str
    canonical_branch_id: str
    element_kind: str
    branch_side: str
    source_ref: str


@dataclass(frozen=True, slots=True)
class IntegratedLoopEvent:
    sequence: int
    kind: str
    reference_id: str
    logical_time_s: str = ""


@dataclass(frozen=True, slots=True)
class VisioStateUpdate:
    """Dry-run projection; NOT a Visio COM operation or proof of visual update."""

    element_id: str
    page_name: str
    shape_id: int
    switch_state: str
    canonical_model_fingerprint: str


@dataclass(frozen=True, slots=True)
class IntegratedLoopResult:
    status: IntegratedLoopStatus
    code: str
    model_before_fingerprint: str
    model_after: CanonicalModel | None
    solver_result: ShortCircuitResult | None = None
    protection_steps: tuple[ProtectionStepResult, ...] = ()
    switching_result: SwitchingOperationResult | None = None
    visio_updates: tuple[VisioStateUpdate, ...] = ()
    trace: tuple[IntegratedLoopEvent, ...] = ()


class _GateError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _time_pair(times: tuple[str, str]) -> tuple[str, str]:
    if not isinstance(times, tuple) or len(times) != 2:
        raise _GateError("invalid_logical_times")
    try:
        a, b = (Decimal(value) for value in times)
    except (ValueError, InvalidOperation, TypeError):
        raise _GateError("invalid_logical_times") from None
    if not a.is_finite() or not b.is_finite() or a < 0 or b <= a:
        raise _GateError("invalid_logical_times")
    return (str(a), str(b))


def _preflight(
    model: CanonicalModel,
    study: SolverStudyInput,
    sources: tuple[SourceRef, ...],
    program: ProtectionProgram,
    request: ShortCircuitRequest,
    binding: BranchCurrentBinding,
    shapes: tuple[VisioShapeBinding, ...],
    times: tuple[str, str],
) -> tuple[tuple[str, str], str, VisioShapeBinding]:
    logical_times = _time_pair(times)
    if not sources:
        raise _GateError("missing_explicit_sources")
    elements_by_id = {element.id: element for element in model.elements}
    if any(
        source.element_id not in elements_by_id
        or elements_by_id[source.element_id].kind not in {"external_grid", "external_link"}
        for source in sources
    ):
        raise _GateError("unqualified_source_kind")
    if not isinstance(study, SolverStudyInput) or fingerprint(study.model) != fingerprint(model):
        raise _GateError("study_model_mismatch")
    operational = simulate_operational_state(
        model, sources, electrical_profile=ELECTRICAL_OPERATIONAL_SOLVER_V1,
    )
    if operational.status is not OperationalStatus.SUCCESS:
        raise _GateError("invalid_operational_initial_state")
    if request.fault_type is not FaultType.THREE_PHASE or not request.branch_results:
        raise _GateError("unsupported_fault_study")
    if not any(e.id == request.canonical_bus_id and e.kind == "bus" for e in model.elements):
        raise _GateError("invalid_fault_bus")
    if (
        program.settings_scope != "full_configuration"
        or program.lifecycle_status not in {"implemented", "approved"}
        or program.unsupported_function_ids
        or len(program.stages) != 1
    ):
        raise _GateError("unqualified_protection_program")
    stage = program.stages[0]
    matches = [spec for spec in program.measurement_specs if spec.id == stage.measurement_input_id]
    if len(matches) != 1:
        raise _GateError("unsupported_protection_measurement_or_action")
    spec = matches[0]
    if (
        spec.semantic_key != "phase_current"
        or stage.concept_id not in {"protection.overcurrent", "protection.instantaneous_overcurrent"}
        or spec.quantity_kind != "current"
        or spec.basis != "primary"
        or stage.measurement_input_id != spec.id
        or len(stage.actions) != 1
    ):
        raise _GateError("unsupported_protection_measurement_or_action")
    action = stage.actions[0]
    if action.action_type != "trip" or action.target_kind != "equipment":
        raise _GateError("unsupported_protection_measurement_or_action")
    breaker = next((e for e in model.elements if e.id == action.target_id), None)
    if breaker is None or breaker.kind != "circuit_breaker":
        raise _GateError("invalid_trip_target")
    if read_switching_state(breaker).switch_state != "closed":
        raise _GateError("breaker_not_closed")
    matched = [s for s in shapes if s.element_id == action.target_id]
    if len(matched) != 1 or not matched[0].page_name.strip() or matched[0].shape_id <= 0:
        raise _GateError("unqualified_visio_binding")
    if (
        binding.measurement_input_id != spec.id
        or binding.branch_side not in {"from", "to"}
        or binding.element_kind not in {"line", "transformer_2w"}
        or not isinstance(binding.source_ref, str)
        or not binding.source_ref.strip()
    ):
        raise _GateError("invalid_measurement_binding")
    branch = next((e for e in model.elements if e.id == binding.canonical_branch_id), None)
    if branch is None or branch.kind != binding.element_kind:
        raise _GateError("invalid_measurement_branch")
    return logical_times, action.target_id, matched[0]


def _qualified_current(
    result: ShortCircuitResult,
    request: ShortCircuitRequest,
    binding: BranchCurrentBinding,
) -> str:
    if not isinstance(result, ShortCircuitResult):
        raise _GateError("invalid_solver_result")
    if (
        result.status is not SolverStatus.SUCCESS
        or result.fault_type is not FaultType.THREE_PHASE
        or result.fault_canonical_bus_id != request.canonical_bus_id
        or not isinstance(result.solver_name, str)
        or not result.solver_name.strip()
    ):
        raise _GateError("unqualified_solver_result")
    node = result.node
    if node is None or node.canonical_id != request.canonical_bus_id:
        raise _GateError("missing_fault_node_evidence")
    node_current = node.initial_symmetrical_current_a
    if (
        isinstance(node_current, bool) or not isinstance(node_current, (float, int))
        or not isfinite(node_current) or node_current < 0
    ):
        raise _GateError("unqualified_fault_node_current")
    rows = [r for r in result.branch_contributions if r.canonical_id == binding.canonical_branch_id]
    if len(rows) != 1 or rows[0].element_kind != binding.element_kind:
        raise _GateError("missing_branch_current")
    value = rows[0].from_current_a if binding.branch_side == "from" else rows[0].to_current_a
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not isfinite(value) or value < 0:
        raise _GateError("unqualified_branch_current")
    return str(Decimal(str(value)))


def run_integrated_protection_loop(
    model: CanonicalModel,
    study: SolverStudyInput,
    sources: Iterable[SourceRef],
    solver: ShortCircuitSolver,
    request: ShortCircuitRequest,
    program: ProtectionProgram,
    binding: BranchCurrentBinding,
    visio_bindings: Iterable[VisioShapeBinding],
    *,
    logical_times_s: tuple[str, str] = ("0", "0.8"),
    validators: Iterable[OperationValidator] = (),
) -> IntegratedLoopResult:
    """Run a bounded *simulation*, with no physical breaker or Visio side effects.

    Only one known three-phase branch-current measurement and one trip action
    are accepted in v1; every ambiguous gate fails closed before model mutation.
    """
    before_fp = fingerprint(model)
    source_refs = tuple(sources)
    def denied(code: str, *, solver_result=None, steps=(), trace=(), switch=None) -> IntegratedLoopResult:
        return IntegratedLoopResult(
            IntegratedLoopStatus.BLOCKED, code, before_fp, None,
            solver_result=solver_result, protection_steps=tuple(steps),
            switching_result=switch, trace=tuple(trace),
        )
    try:
        times, breaker_id, shape = _preflight(
            model, study, source_refs, program, request,
            binding, tuple(visio_bindings), logical_times_s,
        )
    except (ValueError, TypeError, AttributeError, _GateError) as exc:
        return denied(exc.code if isinstance(exc, _GateError) else "invalid_integration_input")

    try:
        sc_result = solver.short_circuit(study, request)
    except Exception:
        return denied("solver_execution_failed")
    try:
        current = _qualified_current(sc_result, request, binding)
    except _GateError as exc:
        return denied(exc.code, solver_result=sc_result)
    try:
        measured = make_measured_quantity(
            measurement_input_id=binding.measurement_input_id,
            source_value=current, source_unit="A",
            quantity_kind="current", basis="primary",
        )
        initial_snapshot = make_snapshot(
            snapshot_id="fault:pickup", time_s=times[0], measurements=(measured,),
        )
        subsequent_snapshot = make_snapshot(
            snapshot_id="fault:operate", time_s=times[1], measurements=(measured,),
        )
        first = evaluate_protection_step(program, initial_snapshot)
        second = evaluate_protection_step(program, subsequent_snapshot, state=first.state)
    except Exception:
        return denied("protection_step_failed", solver_result=sc_result)

    trace: list[IntegratedLoopEvent] = []
    def event(kind: str, ref: str, at: str = "") -> None:
        trace.append(IntegratedLoopEvent(len(trace) + 1, kind, ref, at))
    event("fault_studied", request.canonical_bus_id)
    event("branch_current_qualified", binding.measurement_input_id)
    for step in (first, second):
        for item in step.events:
            event(item.event_type, f"{item.function_id}/{item.stage_id}", item.time_s)
    requests = (*first.requests, *second.requests)
    if not requests:
        return IntegratedLoopResult(
            IntegratedLoopStatus.NO_TRIP, "protection_did_not_operate",
            before_fp, model, solver_result=sc_result,
            protection_steps=(first, second), trace=tuple(trace),
        )
    if (
        len(requests) != 1
        or requests[0].action_type != "trip"
        or requests[0].target_kind != "equipment"
        or requests[0].target_id != breaker_id
    ):
        return denied("invalid_trip_request", solver_result=sc_result, steps=(first, second), trace=trace)
    trip = requests[0]
    event("trip_requested", trip.request_id, trip.time_s)
    operation = SwitchStateOperation(
        operation_id=f"protection:{trip.request_id}",
        element_id=breaker_id,
        target_state="open",
    )
    try:
        switched = execute_switching_operation(
            model, source_refs, operation, validators=tuple(validators),
            electrical_profile=ELECTRICAL_OPERATIONAL_SOLVER_V1,
        )
    except Exception:
        return denied("switching_adapter_failed", solver_result=sc_result, steps=(first, second), trace=trace)
    if (
        switched.status is not SwitchingOperationStatus.SUCCESS
        or switched.model_after is None
        or switched.operational_after is None
        or switched.operational_delta is None
        or switched.operational_after.status is not OperationalStatus.SUCCESS
    ):
        return denied("switching_not_completed", solver_result=sc_result, steps=(first, second), trace=trace, switch=switched)

    event("breaker_opened", breaker_id, trip.time_s)
    event("topology_recalculated", breaker_id, trip.time_s)
    projection = VisioStateUpdate(
        element_id=breaker_id,
        page_name=shape.page_name,
        shape_id=shape.shape_id,
        switch_state="open",
        canonical_model_fingerprint=fingerprint(switched.model_after),
    )
    event("visio_update_prepared", breaker_id, trip.time_s)
    return IntegratedLoopResult(
        IntegratedLoopStatus.COMPLETED, "simulated_cycle_completed",
        before_fp, switched.model_after,
        solver_result=sc_result,
        protection_steps=(first, second),
        switching_result=switched,
        visio_updates=(projection,),
        trace=tuple(trace),
    )
