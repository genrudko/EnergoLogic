from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from energologic.core import CanonicalModel


class SolverStatus(str, Enum):
    SUCCESS = "success"
    NON_CONVERGED = "non-converged"
    INVALID_MODEL = "invalid_model"
    UNSUPPORTED_CONFIGURATION = "unsupported_configuration"
    MISSING_PARAMETERS = "missing_parameters"
    SOLVER_FAILURE = "solver_failure"


class FaultType(str, Enum):
    THREE_PHASE = "3ph"
    PHASE_TO_PHASE = "2ph"
    SINGLE_PHASE_TO_EARTH = "1ph"


@dataclass(frozen=True, slots=True)
class SolverMessage:
    code: str
    message: str
    canonical_id: str | None = None


@dataclass(frozen=True, slots=True)
class ExternalGridParameters:
    canonical_id: str
    voltage_pu: float = 1.0
    angle_deg: float = 0.0
    short_circuit_power_max_va: float = 0.0
    rx_max: float = 0.1
    zero_sequence_r_over_x_max: float | None = None
    zero_sequence_x_over_x_max: float | None = None


@dataclass(frozen=True, slots=True)
class LineParameters:
    canonical_id: str
    length_m: float
    resistance_ohm_per_m: float
    reactance_ohm_per_m: float
    capacitance_f_per_m: float
    max_current_a: float
    line_type: str = "cable"
    zero_sequence_resistance_ohm_per_m: float | None = None
    zero_sequence_reactance_ohm_per_m: float | None = None
    zero_sequence_capacitance_f_per_m: float | None = None
    end_temperature_c: float = 20.0


@dataclass(frozen=True, slots=True)
class Transformer2WParameters:
    canonical_id: str
    rated_power_va: float
    hv_voltage_v: float
    lv_voltage_v: float
    short_circuit_voltage_percent: float
    short_circuit_resistance_percent: float
    iron_loss_w: float
    no_load_current_percent: float
    phase_shift_deg: float = 0.0
    vector_group: str | None = None
    zero_sequence_short_circuit_voltage_percent: float | None = None
    zero_sequence_short_circuit_resistance_percent: float | None = None
    zero_sequence_magnetizing_percent: float | None = None
    zero_sequence_magnetizing_r_over_x: float | None = None
    zero_sequence_hv_partition: float | None = None


@dataclass(frozen=True, slots=True)
class LoadParameters:
    canonical_id: str
    active_power_w: float
    reactive_power_var: float = 0.0


@dataclass(frozen=True, slots=True)
class SolverStudyInput:
    model: CanonicalModel
    external_grids: tuple[ExternalGridParameters, ...] = ()
    lines: tuple[LineParameters, ...] = ()
    transformers_2w: tuple[Transformer2WParameters, ...] = ()
    loads: tuple[LoadParameters, ...] = ()
    inactive_equipment_ids: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True, slots=True)
class PowerFlowRequest:
    calculate_voltage_angles: bool = True


@dataclass(frozen=True, slots=True)
class ShortCircuitRequest:
    canonical_bus_id: str
    fault_type: FaultType = FaultType.THREE_PHASE
    case: str = "max"
    calculate_peak: bool = True
    calculate_thermal: bool = True
    clearing_time_s: float = 1.0
    branch_results: bool = True


@dataclass(frozen=True, slots=True)
class BusPowerFlowResult:
    canonical_id: str
    voltage_v: float | None
    voltage_pu: float | None
    voltage_angle_deg: float | None
    net_active_power_w: float | None
    net_reactive_power_var: float | None


@dataclass(frozen=True, slots=True)
class BranchPowerFlowResult:
    canonical_id: str
    element_kind: str
    current_a: float | None
    from_current_a: float | None
    to_current_a: float | None
    active_power_from_w: float | None
    reactive_power_from_var: float | None
    active_power_to_w: float | None
    reactive_power_to_var: float | None
    active_loss_w: float | None
    reactive_loss_var: float | None
    loading_percent: float | None


@dataclass(frozen=True, slots=True)
class PowerFlowResult:
    status: SolverStatus
    solver_name: str
    solver_version: str | None = None
    topology_signature: str | None = None
    buses: tuple[BusPowerFlowResult, ...] = ()
    branches: tuple[BranchPowerFlowResult, ...] = ()
    warnings: tuple[SolverMessage, ...] = ()
    errors: tuple[SolverMessage, ...] = ()

    @property
    def succeeded(self) -> bool:
        return self.status is SolverStatus.SUCCESS

    def bus(self, canonical_id: str) -> BusPowerFlowResult:
        return next(item for item in self.buses if item.canonical_id == canonical_id)

    def branch(self, canonical_id: str) -> BranchPowerFlowResult:
        return next(item for item in self.branches if item.canonical_id == canonical_id)


@dataclass(frozen=True, slots=True)
class ShortCircuitNodeResult:
    canonical_id: str
    initial_symmetrical_current_a: float | None
    peak_current_a: float | None
    thermal_current_a: float | None
    short_circuit_power_va: float | None
    equivalent_resistance_ohm: float | None
    equivalent_reactance_ohm: float | None


@dataclass(frozen=True, slots=True)
class ShortCircuitBranchResult:
    canonical_id: str
    element_kind: str
    initial_current_a: float | None
    from_current_a: float | None
    to_current_a: float | None
    peak_current_a: float | None
    thermal_current_a: float | None


@dataclass(frozen=True, slots=True)
class ShortCircuitResult:
    status: SolverStatus
    solver_name: str
    fault_type: FaultType
    fault_canonical_bus_id: str
    solver_version: str | None = None
    node: ShortCircuitNodeResult | None = None
    branch_contributions: tuple[ShortCircuitBranchResult, ...] = ()
    warnings: tuple[SolverMessage, ...] = ()
    errors: tuple[SolverMessage, ...] = ()

    @property
    def succeeded(self) -> bool:
        return self.status is SolverStatus.SUCCESS
