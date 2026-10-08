"""Materialize versioned engineering facts into the existing solver-neutral Gate-D DTO."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib
import json
from energologic.core import CanonicalModel
from energologic.core.codec import model_to_data
from energologic.domain.calculation import (
    CalculationValidationError, ElectricalCalculationProfile,
    EquipmentCalculation, calculation_profile_to_data, validate_calculation,
)
from .contracts import (
    ExternalGridParameters, LineParameters, LoadParameters,
    SolverStudyInput, Transformer2WParameters,
)

@dataclass(frozen=True, slots=True)
class MaterializedStudy:
    solver_input: SolverStudyInput
    normalized_json: str
    fingerprint: str

def _get(e: EquipmentCalculation, key: str):
    fact = e.parameters.get(key)
    return fact.value if fact is not None and fact.state == "known" else None

def _num(e: EquipmentCalculation, key: str) -> float:
    value = _get(e, key)
    assert isinstance(value, (int, float)) and not isinstance(value, bool)
    return float(value)

def _opt(e: EquipmentCalculation, key: str) -> float | None:
    return None if _get(e, key) is None else _num(e, key)

def materialize_study(model: CanonicalModel, profile: ElectricalCalculationProfile,
                      *, study_type: str = "power_flow") -> MaterializedStudy:
    issues = validate_calculation(model, profile, study_type=study_type)
    if issues:
        raise CalculationValidationError(issues)
    grids, lines, transformers, loads = [], [], [], []
    for e in sorted(profile.equipment, key=lambda x: x.canonical_id):
        if e.kind == "external_grid":
            grids.append(ExternalGridParameters(
                e.canonical_id, _num(e, "voltage_pu"), _num(e, "angle_deg"),
                _num(e, "short_circuit_power_max_va"), _num(e, "rx_max"),
                _opt(e, "zero_sequence_r_over_x_max"),
                _opt(e, "zero_sequence_x_over_x_max")))
        elif e.kind == "line":
            construction = _get(e, "construction")
            assert construction in ("overhead", "cable")
            lines.append(LineParameters(
                e.canonical_id, _num(e, "length_m"), _num(e, "resistance_ohm_per_m"),
                _num(e, "reactance_ohm_per_m"), _num(e, "capacitance_f_per_m"),
                _num(e, "max_current_a"),
                "cable" if construction == "cable" else "line",
                _opt(e, "zero_sequence_resistance_ohm_per_m"),
                _opt(e, "zero_sequence_reactance_ohm_per_m"),
                _opt(e, "zero_sequence_capacitance_f_per_m"),
                _num(e, "end_temperature_c")))
        elif e.kind == "transformer_2w":
            item = next(x for x in model.elements if x.id == e.canonical_id)
            voltages = {t.id: float(t.attributes["nominal_voltage_v"]) for t in item.terminals}
            group = _get(e, "vector_group")
            transformers.append(Transformer2WParameters(
                e.canonical_id, _num(e, "rated_power_va"), voltages["hv"], voltages["lv"],
                _num(e, "short_circuit_voltage_percent"),
                _num(e, "short_circuit_resistance_percent"),
                _num(e, "iron_loss_w"), _num(e, "no_load_current_percent"),
                _num(e, "phase_shift_deg"), group if isinstance(group, str) else None,
                _opt(e, "zero_sequence_short_circuit_voltage_percent"),
                _opt(e, "zero_sequence_short_circuit_resistance_percent"),
                _opt(e, "zero_sequence_magnetizing_percent"),
                _opt(e, "zero_sequence_magnetizing_r_over_x"),
                _opt(e, "zero_sequence_hv_partition")))
        elif e.kind == "load":
            loads.append(LoadParameters(
                e.canonical_id, _num(e, "active_power_w"), _num(e, "reactive_power_var")))
    result = SolverStudyInput(
        model=model, external_grids=tuple(grids), lines=tuple(lines),
        transformers_2w=tuple(transformers), loads=tuple(loads),
        inactive_equipment_ids=profile.inactive_equipment_ids)
    manifest = {
        "profile_version": profile.version,
        "study_type": study_type,
        "solver_study_input": {
            "model": model_to_data(model),
            "external_grids": [asdict(x) for x in result.external_grids],
            "lines": [asdict(x) for x in result.lines],
            "transformers_2w": [asdict(x) for x in result.transformers_2w],
            "loads": [asdict(x) for x in result.loads],
            "inactive_equipment_ids": sorted(result.inactive_equipment_ids),
        },
        "calculation_facts": calculation_profile_to_data(profile),
    }
    raw = json.dumps(manifest, sort_keys=True, ensure_ascii=False,
                     allow_nan=False, separators=(",", ":"))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    normalized = json.dumps(
        {**manifest, "fingerprint_sha256": digest},
        sort_keys=True, ensure_ascii=False, allow_nan=False,
        separators=(",", ":")) + "\n"
    return MaterializedStudy(result, normalized, digest)
