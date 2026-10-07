"""Versioned solver-neutral electrical calculation facts (not a solver schema)."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from pathlib import Path
from typing import Any, Mapping

from energologic.core.model import CanonicalModel, Element, Endpoint
from energologic.core.validation import ValidationIssue, validate_model
from energologic.domain.switching import SwitchingStateError, switch_allows_primary_conduction

PROFILE_VERSION = "electrical-calculation-v1"
PARAMETER_KINDS = frozenset({"external_grid", "line", "load", "transformer_2w"})
CALCULATION_KINDS = PARAMETER_KINDS | {"bus", "circuit_breaker", "disconnector"}
TERMINALS = {
    "bus": ("node",),
    "external_grid": ("node",),
    "line": ("from", "to"),
    "load": ("node",),
    "transformer_2w": ("hv", "lv"),
    "circuit_breaker": ("a", "b"),
    "disconnector": ("a", "b"),
}
REQUIRED = {
    "external_grid": ("voltage_pu", "angle_deg", "short_circuit_power_max_va", "rx_max"),
    "line": ("construction", "length_m", "resistance_ohm_per_m",
             "reactance_ohm_per_m", "capacitance_f_per_m", "max_current_a",
             "end_temperature_c"),
    "load": ("active_power_w", "reactive_power_var"),
    "transformer_2w": ("rated_power_va", "short_circuit_voltage_percent",
                       "short_circuit_resistance_percent", "iron_loss_w",
                       "no_load_current_percent", "phase_shift_deg"),
}
OPTIONAL = {
    "external_grid": ("zero_sequence_r_over_x_max", "zero_sequence_x_over_x_max"),
    "line": ("zero_sequence_resistance_ohm_per_m", "zero_sequence_reactance_ohm_per_m",
             "zero_sequence_capacitance_f_per_m"),
    "load": (),
    "transformer_2w": ("vector_group", "zero_sequence_short_circuit_voltage_percent",
                       "zero_sequence_short_circuit_resistance_percent",
                       "zero_sequence_magnetizing_percent",
                       "zero_sequence_magnetizing_r_over_x", "zero_sequence_hv_partition"),
}
TEXT_FIELDS = frozenset({"construction", "vector_group"})
POSITIVE = frozenset({
    "voltage_pu", "short_circuit_power_max_va", "length_m", "max_current_a",
    "rated_power_va", "short_circuit_voltage_percent",
    "zero_sequence_short_circuit_voltage_percent", "zero_sequence_magnetizing_percent"
})
NONNEGATIVE = frozenset({
    "rx_max", "resistance_ohm_per_m", "reactance_ohm_per_m", "capacitance_f_per_m",
    "iron_loss_w", "no_load_current_percent", "short_circuit_resistance_percent",
    "zero_sequence_r_over_x_max", "zero_sequence_x_over_x_max",
    "zero_sequence_resistance_ohm_per_m", "zero_sequence_reactance_ohm_per_m",
    "zero_sequence_capacitance_f_per_m",
    "zero_sequence_short_circuit_resistance_percent",
    "zero_sequence_magnetizing_r_over_x", "zero_sequence_hv_partition"
})
SEQUENCE = {
    "external_grid": OPTIONAL["external_grid"],
    "line": OPTIONAL["line"],
    "transformer_2w": tuple(k for k in OPTIONAL["transformer_2w"] if k.startswith("zero_sequence_"))
}


@dataclass(frozen=True, slots=True)
class SourceLocator:
    source_id: str
    locator: str
    revision: str | None = None


@dataclass(frozen=True, slots=True)
class ParameterFact:
    state: str
    value: float | str | None = None
    provenance: SourceLocator | None = None


@dataclass(frozen=True, slots=True)
class EquipmentCalculation:
    canonical_id: str
    kind: str
    parameters: Mapping[str, ParameterFact] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ElectricalCalculationProfile:
    version: str
    model_id: str
    equipment: tuple[EquipmentCalculation, ...] = ()
    inactive_equipment_ids: frozenset[str] = field(default_factory=frozenset)


class CalculationDecodeError(ValueError):
    pass


class CalculationValidationError(ValueError):
    def __init__(self, issues: tuple[ValidationIssue, ...]):
        self.issues = issues
        super().__init__("electrical calculation input is invalid: " + "; ".join(
            f"{i.code} at {i.path}" for i in issues
        ))


def _keys(obj: Mapping[str, Any], allowed: set[str], required: set[str], path: str) -> None:
    if not isinstance(obj, dict):
        raise CalculationDecodeError(f"{path}: expected object")
    if required - obj.keys() or obj.keys() - allowed:
        raise CalculationDecodeError(
            f"{path}: missing={sorted(required - obj.keys())}, "
            f"unexpected={sorted(obj.keys() - allowed)}"
        )


def decode_calculation_profile(data: Mapping[str, Any]) -> ElectricalCalculationProfile:
    _keys(data, {"version", "model_id", "equipment", "inactive_equipment_ids"},
          {"version", "model_id", "equipment"}, "/")
    if data["version"] != PROFILE_VERSION or not isinstance(data["model_id"], str) or not data["model_id"]:
        raise CalculationDecodeError("unsupported version or invalid model_id")
    if not isinstance(data["equipment"], list):
        raise CalculationDecodeError("/equipment: expected array")
    equipment: list[EquipmentCalculation] = []
    for i, item in enumerate(data["equipment"]):
        path = f"/equipment/{i}"
        _keys(item, {"canonical_id", "kind", "parameters"},
              {"canonical_id", "kind", "parameters"}, path)
        if not all(isinstance(item[k], str) and item[k] for k in ("canonical_id", "kind")):
            raise CalculationDecodeError(f"{path}: canonical_id/kind must be nonempty strings")
        raw = item["parameters"]
        if not isinstance(raw, dict):
            raise CalculationDecodeError(f"{path}/parameters: expected object")
        facts = {}
        for key, fact in raw.items():
            fact_path = f"{path}/parameters/{key}"
            if not isinstance(key, str):
                raise CalculationDecodeError(f"{fact_path}: invalid field name")
            _keys(fact, {"state", "value", "provenance"}, {"state"}, fact_path)
            state = fact["state"]
            if state not in {"known", "unknown", "not_applicable"}:
                raise CalculationDecodeError(f"{fact_path}: invalid parameter state")
            if state == "known" and "value" not in fact:
                raise CalculationDecodeError(f"{fact_path}: known parameter needs value")
            if state != "known" and "value" in fact:
                raise CalculationDecodeError(f"{fact_path}: non-known parameter must not contain value")
            provenance = None
            if "provenance" in fact:
                p = fact["provenance"]
                _keys(p, {"source_id", "locator", "revision"},
                      {"source_id", "locator"}, fact_path + "/provenance")
                if (not isinstance(p["source_id"], str) or not p["source_id"]
                        or not isinstance(p["locator"], str) or not p["locator"]
                        or ("revision" in p and not isinstance(p["revision"], str))):
                    raise CalculationDecodeError(f"{fact_path}: invalid source locator")
                provenance = SourceLocator(p["source_id"], p["locator"], p.get("revision"))
            if state == "known" and provenance is None:
                raise CalculationDecodeError(f"{fact_path}: known parameter requires provenance")
            value = fact.get("value")
            if state == "known" and (isinstance(value, bool) or not isinstance(value, (str, float, int))):
                raise CalculationDecodeError(f"{fact_path}: unsupported value")
            if isinstance(value, float) and not math.isfinite(value):
                raise CalculationDecodeError(f"{fact_path}: nonfinite parameter")
            facts[key] = ParameterFact(state, value, provenance)
        equipment.append(EquipmentCalculation(item["canonical_id"], item["kind"], facts))
    inactive = data.get("inactive_equipment_ids", [])
    if not isinstance(inactive, list) or any(not isinstance(x, str) or not x for x in inactive):
        raise CalculationDecodeError("/inactive_equipment_ids: expected nonempty strings")
    if len(inactive) != len(set(inactive)):
        raise CalculationDecodeError("/inactive_equipment_ids: duplicate ID")
    return ElectricalCalculationProfile(data["version"], data["model_id"],
                                        tuple(equipment), frozenset(inactive))


def load_calculation_profile(path: str | Path) -> ElectricalCalculationProfile:
    return decode_calculation_profile(json.loads(Path(path).read_text(encoding="utf-8")))


def calculation_profile_to_data(profile: ElectricalCalculationProfile) -> dict[str, Any]:
    def render(fact: ParameterFact) -> dict[str, Any]:
        data: dict[str, Any] = {"state": fact.state}
        if fact.state == "known":
            data["value"] = fact.value
        if fact.provenance:
            p = fact.provenance
            data["provenance"] = {"source_id": p.source_id, "locator": p.locator}
            if p.revision is not None:
                data["provenance"]["revision"] = p.revision
        return data

    return {"version": profile.version, "model_id": profile.model_id,
            "equipment": [
                {"canonical_id": e.canonical_id, "kind": e.kind,
                 "parameters": {k: render(v) for k, v in sorted(e.parameters.items())}}
                for e in sorted(profile.equipment, key=lambda x: x.canonical_id)
            ],
            "inactive_equipment_ids": sorted(profile.inactive_equipment_ids)}


def _issue(code: str, path: str, message: str) -> ValidationIssue:
    return ValidationIssue(code, path, message)


def _exact_voltage(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def validate_calculation(
    model: CanonicalModel,
    profile: ElectricalCalculationProfile,
    *,
    study_type: str = "power_flow",
) -> tuple[ValidationIssue, ...]:
    """Fail-closed topology, fact and study-capability validation without any solver imports."""
    issues = list(validate_model(model))
    if profile.version != PROFILE_VERSION:
        issues.append(_issue("unsupported_calculation_profile", "/version", profile.version))
    if model.model_id != profile.model_id:
        issues.append(_issue("calculation_model_id_mismatch", "/model_id", profile.model_id))
    if study_type not in {"power_flow", "short_circuit_3ph", "short_circuit_2ph", "short_circuit_1ph"}:
        issues.append(_issue("unsupported_study_type", "/study_type", study_type))

    elements: dict[str, Element] = {}
    for e in model.elements:
        if e.id in elements:
            continue
        elements[e.id] = e
    records: dict[str, EquipmentCalculation] = {}
    for e in profile.equipment:
        path = f"/equipment[id='{e.canonical_id}']"
        if e.canonical_id in records:
            issues.append(_issue("duplicate_calculation_equipment", path, "duplicate canonical id"))
        records[e.canonical_id] = e
        element = elements.get(e.canonical_id)
        if element is None or element.kind != e.kind or e.kind not in PARAMETER_KINDS:
            issues.append(_issue("orphan_calculation_equipment", path, "id/kind not a parameterized canonical element"))
            continue
        permitted = set(REQUIRED[e.kind] + OPTIONAL[e.kind])
        for key in sorted(e.parameters):
            fact = e.parameters[key]
            fpath = f"{path}/parameters/{key}"
            if key not in permitted:
                issues.append(_issue("unknown_calculation_parameter", fpath, "field not in v1 contract"))
                continue
            if fact.state not in {"known", "unknown", "not_applicable"}:
                issues.append(_issue("invalid_parameter_state", fpath, fact.state))
                continue
            if fact.state == "known":
                if fact.provenance is None or not fact.provenance.source_id or not fact.provenance.locator:
                    issues.append(_issue("missing_parameter_provenance", fpath, "known facts require a source locator"))
                value = fact.value
                if key in TEXT_FIELDS:
                    if not isinstance(value, str) or not value.strip():
                        issues.append(_issue("invalid_calculation_parameter", fpath, "nonempty text required"))
                    elif key == "construction" and value not in {"overhead", "cable"}:
                        issues.append(_issue("unsupported_construction", fpath, "expected overhead or cable"))
                elif isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    issues.append(_issue("invalid_calculation_parameter", fpath, "finite numeric value required"))
                elif (key in POSITIVE and value <= 0) or (key in NONNEGATIVE and value < 0):
                    issues.append(_issue("invalid_calculation_parameter", fpath, "value outside engineering domain"))
                elif key == "zero_sequence_hv_partition" and value > 1:
                    issues.append(_issue("invalid_calculation_parameter", fpath, "fraction must not exceed 1"))
            elif fact.value is not None:
                issues.append(_issue("unexpected_parameter_value", fpath, "non-known fact must not have a value"))
        for key in REQUIRED[e.kind]:
            fact = e.parameters.get(key)
            ppath = f"{path}/parameters/{key}"
            if fact is None:
                issues.append(_issue("missing_required_parameter", ppath, "parameter absent"))
            elif fact.state == "unknown":
                issues.append(_issue("unknown_required_parameter", ppath, "value explicitly unknown"))
            elif fact.state == "not_applicable":
                issues.append(_issue("not_applicable_required_parameter", ppath, "parameter required for this study"))
        known = {k: v.value for k, v in e.parameters.items() if v.state == "known"}
        if e.kind == "line" and all(k in known for k in ("resistance_ohm_per_m", "reactance_ohm_per_m")):
            if known["resistance_ohm_per_m"] == known["reactance_ohm_per_m"] == 0:
                issues.append(_issue("invalid_line_impedance", path, "positive-sequence series impedance is zero"))
        if e.kind == "transformer_2w" and all(k in known for k in (
                "short_circuit_voltage_percent", "short_circuit_resistance_percent")):
            if known["short_circuit_resistance_percent"] > known["short_circuit_voltage_percent"]:
                issues.append(_issue("invalid_transformer_impedance", path,
                                     "resistive short-circuit component exceeds magnitude"))
        if study_type == "short_circuit_1ph":
            for key in SEQUENCE.get(e.kind, ()):
                fact = e.parameters.get(key)
                if fact is None or fact.state != "known":
                    issues.append(_issue("missing_sequence_parameter",
                                         f"{path}/parameters/{key}",
                                         "single-phase earth-fault study requires independently sourced zero-sequence data"))
            if e.kind == "transformer_2w" and e.parameters.get("vector_group", ParameterFact("unknown")).state != "known":
                issues.append(_issue("missing_winding_vector_group", path, "required for earth-fault study"))

    for e in model.elements:
        path = f"/elements[id='{e.id}']"
        expected = TERMINALS.get(e.kind)
        if expected is None:
            issues.append(_issue("unsupported_calculation_kind", path, e.kind))
            continue
        actual = tuple(t.id for t in e.terminals)
        if len(actual) != len(expected) or set(actual) != set(expected):
            issues.append(_issue("invalid_calculation_terminal_contract", path, f"expected {expected}"))
        if e.kind in PARAMETER_KINDS and e.id not in records:
            issues.append(_issue("missing_equipment_calculation", path, "no calculation facts for canonical equipment"))
        if e.kind in {"bus", "circuit_breaker", "disconnector"}:
            if not _exact_voltage(e.attributes.get("nominal_voltage_v")):
                issues.append(_issue("missing_exact_nominal_voltage", path, "requires exact nominal_voltage_v in V"))
        if e.kind in {"circuit_breaker", "disconnector"}:
            try:
                switch_allows_primary_conduction(e)
            except SwitchingStateError as exc:
                issues.append(_issue(exc.code, path, str(exc)))
        if e.kind == "transformer_2w":
            for terminal in e.terminals:
                if not _exact_voltage(terminal.attributes.get("nominal_voltage_v")):
                    issues.append(_issue("missing_exact_nominal_voltage", f"{path}/terminals/{terminal.id}",
                                         "requires terminal-scoped exact voltage, not voltage class"))
                if terminal.attributes.get("winding_connection") not in {
                    "delta", "open_delta", "three_single_phase", "star", "star_with_neutral",
                    "star_grounded_neutral", "zigzag", "zigzag_with_neutral"}:
                    issues.append(_issue("invalid_winding_connection", f"{path}/terminals/{terminal.id}",
                                         "requires an explicit accepted winding connection"))
            h = next((t for t in e.terminals if t.id == "hv"), None)
            l = next((t for t in e.terminals if t.id == "lv"), None)
            if h and l and _exact_voltage(h.attributes.get("nominal_voltage_v")) and _exact_voltage(l.attributes.get("nominal_voltage_v")):
                if h.attributes["nominal_voltage_v"] < l.attributes["nominal_voltage_v"]:
                    issues.append(_issue("invalid_transformer_voltage_order", path, "hv < lv"))
    endpoint_bus: dict[Endpoint, str] = {}
    for c in model.connections:
        left, right = c.endpoints
        a, b = elements.get(left.element_id), elements.get(right.element_id)
        if not a or not b:
            continue
        if (a.kind == "bus") == (b.kind == "bus"):
            issues.append(_issue("unsupported_solver_topology", f"/connections[id='{c.id}']",
                                 "Gate-D v1 requires exactly one bus endpoint per connection"))
            continue
        bus, device = (left, right) if a.kind == "bus" else (right, left)
        if device in endpoint_bus:
            issues.append(_issue("calculation_terminal_degree_exceeded", f"/connections[id='{c.id}']",
                                 "equipment terminal has multiple bus connections"))
        endpoint_bus[device] = bus.element_id
        bus_volt = elements[bus.element_id].attributes.get("nominal_voltage_v")
        device_element = elements[device.element_id]
        if device_element.kind in {"circuit_breaker", "disconnector"}:
            dev_volt = device_element.attributes.get("nominal_voltage_v")
        elif device_element.kind == "transformer_2w":
            term = next((t for t in device_element.terminals if t.id == device.terminal_id), None)
            dev_volt = term.attributes.get("nominal_voltage_v") if term else None
        else:
            dev_volt = None  # source/load/line voltage is defined by directly connected canonical bus
        if (_exact_voltage(bus_volt) and _exact_voltage(dev_volt)
                and bus_volt != dev_volt):
            issues.append(_issue("incompatible_terminal_node_voltage", f"/connections[id='{c.id}']",
                                 f"terminal {dev_volt} V != bus {bus_volt} V"))
    for e in model.elements:
        if e.kind == "bus":
            continue
        for t in e.terminals:
            if Endpoint(e.id, t.id) not in endpoint_bus:
                issues.append(_issue("unconnected_calculation_terminal", f"/elements[id='{e.id}']/terminals/{t.id}",
                                     "missing direct canonical bus connection"))
        if e.kind in {"line", "circuit_breaker", "disconnector"}:
            terminal_ids = TERMINALS.get(e.kind, ())
            if len(terminal_ids) == 2 and all(Endpoint(e.id, t) in endpoint_bus for t in terminal_ids):
                a, b = (elements[endpoint_bus[Endpoint(e.id, t)]].attributes.get("nominal_voltage_v") for t in terminal_ids)
                if _exact_voltage(a) and _exact_voltage(b) and a != b:
                    issues.append(_issue("incompatible_terminal_node_voltage", f"/elements[id='{e.id}']",
                                         f"branch connects {a} V to {b} V without a transformer"))
    for inactive in profile.inactive_equipment_ids:
        element = elements.get(inactive)
        if element is None:
            issues.append(_issue("unknown_inactive_equipment", "/inactive_equipment_ids", inactive))
        elif element.kind == "bus":
            issues.append(_issue("unsupported_inactive_bus", "/inactive_equipment_ids", inactive))
    # Explicit limitation: present adapter does not ingest independent negative-sequence or
    # qualified earthing/neutral network; never claim unbalanced fault capability here.
    if study_type == "short_circuit_2ph":
        issues.append(_issue("unsupported_sequence_study", "/study_type",
                             "negative-sequence modeling is not qualified by calculation-v1"))
    if study_type == "short_circuit_1ph":
        issues.append(_issue("unsupported_phase_neutral_topology", "/study_type",
                             "earth-fault path/neutral grounding requires later qualification"))
    return tuple(sorted(set(issues)))

