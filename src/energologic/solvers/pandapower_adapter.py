from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import warnings as python_warnings
from typing import Any, Iterable

from energologic.core import CanonicalModel, Element, Endpoint, validate_model
from energologic.domain import SwitchingStateError, switch_allows_primary_conduction

from .contracts import (
    BranchPowerFlowResult,
    BusPowerFlowResult,
    ExternalGridParameters,
    FaultType,
    LineParameters,
    LoadParameters,
    PowerFlowRequest,
    PowerFlowResult,
    ShortCircuitBranchResult,
    ShortCircuitNodeResult,
    ShortCircuitRequest,
    ShortCircuitResult,
    SolverMessage,
    SolverStatus,
    SolverStudyInput,
    Transformer2WParameters,
)
from .units import (
    amperes_to_kiloamperes,
    farad_per_metre_to_nanofarad_per_kilometre,
    kiloamperes_to_amperes,
    kilovolts_to_volts,
    megavars_to_vars,
    megawatts_to_watts,
    metres_to_kilometres,
    ohm_per_metre_to_ohm_per_kilometre,
    vars_to_megavars,
    volts_to_kilovolts,
    watts_to_kilowatts,
    watts_to_megawatts,
)


_SOLVER_NAME = "pandapower"

_TERMINAL_CONTRACTS: dict[str, tuple[str, ...]] = {
    "bus": ("node",),
    "external_grid": ("node",),
    "line": ("from", "to"),
    "load": ("node",),
    "transformer_2w": ("hv", "lv"),
    "circuit_breaker": ("a", "b"),
    "disconnector": ("a", "b"),
}

_PARAMETERIZED_KINDS = frozenset(
    {"external_grid", "line", "load", "transformer_2w"}
)


class _AdapterInputError(Exception):
    def __init__(
        self,
        status: SolverStatus,
        code: str,
        message: str,
        canonical_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.canonical_id = canonical_id


@dataclass(slots=True)
class _NetworkMaps:
    bus: dict[str, int]
    line: dict[str, int]
    transformer_2w: dict[str, int]


@dataclass(slots=True)
class _BuiltNetwork:
    pp: Any
    sc: Any
    net: Any
    maps: _NetworkMaps
    topology_signature: str


def _message_from_input_error(exc: _AdapterInputError) -> SolverMessage:
    return SolverMessage(exc.code, str(exc), exc.canonical_id)


def _clean_exception_message(exc: BaseException) -> str:
    message = str(exc).strip()
    return message or exc.__class__.__name__


def _finite_or_none(value: object) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _scaled(value: object, scale: float) -> float | None:
    numeric = _finite_or_none(value)
    return None if numeric is None else numeric * scale


def _row_value(row: Any, name: str) -> object | None:
    try:
        return row[name]
    except (KeyError, TypeError, IndexError):
        return None


def _table_row(table: Any, index: int) -> Any | None:
    try:
        if index in table.index:
            row = table.loc[index]
            if getattr(row, "ndim", 1) > 1:
                return row.iloc[0]
            return row
    except (KeyError, TypeError, AttributeError):
        pass

    try:
        if getattr(table.index, "nlevels", 1) > 1:
            rows = table.xs(index, level=0)
            if len(rows):
                return rows.iloc[0]
    except (KeyError, TypeError, AttributeError):
        pass
    return None


def _parameter_map(
    parameters: Iterable[
        ExternalGridParameters
        | LineParameters
        | LoadParameters
        | Transformer2WParameters
    ],
    *,
    kind: str,
) -> dict[str, object]:
    result: dict[str, object] = {}
    for item in parameters:
        if item.canonical_id in result:
            raise _AdapterInputError(
                SolverStatus.INVALID_MODEL,
                "duplicate_solver_parameters",
                f"duplicate {kind} parameters for {item.canonical_id!r}",
                item.canonical_id,
            )
        result[item.canonical_id] = item
    return result


def _positive(value: float, field: str, canonical_id: str) -> None:
    if not math.isfinite(value) or value <= 0:
        raise _AdapterInputError(
            SolverStatus.MISSING_PARAMETERS,
            "invalid_electrical_parameter",
            f"{field} must be finite and > 0; got {value!r}",
            canonical_id,
        )


def _non_negative(value: float, field: str, canonical_id: str) -> None:
    if not math.isfinite(value) or value < 0:
        raise _AdapterInputError(
            SolverStatus.MISSING_PARAMETERS,
            "invalid_electrical_parameter",
            f"{field} must be finite and >= 0; got {value!r}",
            canonical_id,
        )


def _validate_parameter_values(
    external: ExternalGridParameters
    | LineParameters
    | LoadParameters
    | Transformer2WParameters,
) -> None:
    cid = external.canonical_id
    if isinstance(external, ExternalGridParameters):
        _positive(external.voltage_pu, "voltage_pu", cid)
        _positive(
            external.short_circuit_power_max_va,
            "short_circuit_power_max_va",
            cid,
        )
        _non_negative(external.rx_max, "rx_max", cid)
        return

    if isinstance(external, LineParameters):
        _positive(external.length_m, "length_m", cid)
        _non_negative(
            external.resistance_ohm_per_m,
            "resistance_ohm_per_m",
            cid,
        )
        _non_negative(
            external.reactance_ohm_per_m,
            "reactance_ohm_per_m",
            cid,
        )
        _non_negative(
            external.capacitance_f_per_m,
            "capacitance_f_per_m",
            cid,
        )
        _positive(external.max_current_a, "max_current_a", cid)
        if external.line_type not in {"line", "cable"}:
            raise _AdapterInputError(
                SolverStatus.UNSUPPORTED_CONFIGURATION,
                "unsupported_line_type",
                "line_type must be 'line' or 'cable'",
                cid,
            )
        return

    if isinstance(external, Transformer2WParameters):
        _positive(external.rated_power_va, "rated_power_va", cid)
        _positive(external.hv_voltage_v, "hv_voltage_v", cid)
        _positive(external.lv_voltage_v, "lv_voltage_v", cid)
        _positive(
            external.short_circuit_voltage_percent,
            "short_circuit_voltage_percent",
            cid,
        )
        _non_negative(
            external.short_circuit_resistance_percent,
            "short_circuit_resistance_percent",
            cid,
        )
        _non_negative(external.iron_loss_w, "iron_loss_w", cid)
        _non_negative(
            external.no_load_current_percent,
            "no_load_current_percent",
            cid,
        )
        return

    if isinstance(external, LoadParameters):
        if not math.isfinite(external.active_power_w):
            raise _AdapterInputError(
                SolverStatus.MISSING_PARAMETERS,
                "invalid_electrical_parameter",
                "active_power_w must be finite",
                cid,
            )
        if not math.isfinite(external.reactive_power_var):
            raise _AdapterInputError(
                SolverStatus.MISSING_PARAMETERS,
                "invalid_electrical_parameter",
                "reactive_power_var must be finite",
                cid,
            )


def _element_map(model: CanonicalModel) -> dict[str, Element]:
    structural_issues = validate_model(model)
    if structural_issues:
        first = structural_issues[0]
        raise _AdapterInputError(
            SolverStatus.INVALID_MODEL,
            f"canonical_{first.code}",
            f"{first.path}: {first.message}",
        )

    elements: dict[str, Element] = {}
    for element in model.elements:
        if element.id in elements:
            raise _AdapterInputError(
                SolverStatus.INVALID_MODEL,
                "duplicate_element_id",
                f"duplicate canonical element id {element.id!r}",
                element.id,
            )
        elements[element.id] = element
    return elements


def _validate_terminal_contract(element: Element) -> None:
    expected = _TERMINAL_CONTRACTS.get(element.kind)
    if expected is None:
        raise _AdapterInputError(
            SolverStatus.UNSUPPORTED_CONFIGURATION,
            "unsupported_solver_element_kind",
            f"solver spike does not support canonical kind {element.kind!r}",
            element.id,
        )
    actual = tuple(terminal.id for terminal in element.terminals)
    if len(actual) != len(expected) or set(actual) != set(expected):
        raise _AdapterInputError(
            SolverStatus.INVALID_MODEL,
            "invalid_solver_terminal_contract",
            (
                f"kind {element.kind!r} requires terminals {sorted(expected)!r}; "
                f"got {sorted(actual)!r}"
            ),
            element.id,
        )


def _endpoint_bus_map(
    model: CanonicalModel,
    elements: dict[str, Element],
) -> dict[Endpoint, str]:
    endpoint_to_bus: dict[Endpoint, str] = {}

    for connection in model.connections:
        left, right = connection.endpoints
        left_element = elements[left.element_id]
        right_element = elements[right.element_id]
        left_is_bus = left_element.kind == "bus"
        right_is_bus = right_element.kind == "bus"

        if left_is_bus == right_is_bus:
            raise _AdapterInputError(
                SolverStatus.UNSUPPORTED_CONFIGURATION,
                "solver_requires_direct_bus_terminal_connection",
                (
                    f"connection {connection.id!r} must connect exactly one bus "
                    "terminal to one equipment terminal"
                ),
            )

        bus_endpoint = left if left_is_bus else right
        equipment_endpoint = right if left_is_bus else left
        if bus_endpoint.terminal_id != "node":
            raise _AdapterInputError(
                SolverStatus.INVALID_MODEL,
                "invalid_bus_terminal",
                "solver bus endpoint must use terminal 'node'",
                bus_endpoint.element_id,
            )
        if equipment_endpoint in endpoint_to_bus:
            raise _AdapterInputError(
                SolverStatus.INVALID_MODEL,
                "solver_terminal_degree_exceeded",
                "solver equipment terminal is connected to more than one bus",
                equipment_endpoint.element_id,
            )
        endpoint_to_bus[equipment_endpoint] = bus_endpoint.element_id

    for element in elements.values():
        if element.kind == "bus":
            continue
        for terminal in element.terminals:
            endpoint = Endpoint(element.id, terminal.id)
            if endpoint not in endpoint_to_bus:
                raise _AdapterInputError(
                    SolverStatus.INVALID_MODEL,
                    "unconnected_solver_terminal",
                    f"terminal {terminal.id!r} is not connected to a canonical bus",
                    element.id,
                )
    return endpoint_to_bus


def _nominal_voltage_v(element: Element) -> float:
    raw = element.attributes.get("nominal_voltage_v")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise _AdapterInputError(
            SolverStatus.MISSING_PARAMETERS,
            "missing_nominal_voltage",
            "bus requires numeric canonical nominal_voltage_v",
            element.id,
        )
    value = float(raw)
    _positive(value, "nominal_voltage_v", element.id)
    return value


def _required_parameters(
    elements: dict[str, Element],
    study: SolverStudyInput,
) -> tuple[
    dict[str, ExternalGridParameters],
    dict[str, LineParameters],
    dict[str, Transformer2WParameters],
    dict[str, LoadParameters],
]:
    external = _parameter_map(study.external_grids, kind="external_grid")
    lines = _parameter_map(study.lines, kind="line")
    transformers = _parameter_map(study.transformers_2w, kind="transformer_2w")
    loads = _parameter_map(study.loads, kind="load")

    typed_maps: tuple[tuple[str, dict[str, object]], ...] = (
        ("external_grid", external),
        ("line", lines),
        ("transformer_2w", transformers),
        ("load", loads),
    )
    for kind, mapping in typed_maps:
        expected = {element.id for element in elements.values() if element.kind == kind}
        supplied = set(mapping)
        missing = sorted(expected - supplied)
        extra = sorted(supplied - expected)
        if missing:
            raise _AdapterInputError(
                SolverStatus.MISSING_PARAMETERS,
                "missing_solver_parameters",
                f"missing {kind} solver parameters for {missing!r}",
                missing[0],
            )
        if extra:
            raise _AdapterInputError(
                SolverStatus.INVALID_MODEL,
                "orphan_solver_parameters",
                f"{kind} solver parameters reference unknown/non-{kind} ids {extra!r}",
                extra[0],
            )
        for item in mapping.values():
            _validate_parameter_values(item)  # type: ignore[arg-type]

    known_ids = set(elements)
    unknown_inactive = sorted(study.inactive_equipment_ids - known_ids)
    if unknown_inactive:
        raise _AdapterInputError(
            SolverStatus.INVALID_MODEL,
            "unknown_inactive_equipment",
            f"inactive equipment ids are absent from canonical model: {unknown_inactive!r}",
            unknown_inactive[0],
        )

    inactive_buses = sorted(
        item
        for item in study.inactive_equipment_ids
        if elements[item].kind == "bus"
    )
    if inactive_buses:
        raise _AdapterInputError(
            SolverStatus.UNSUPPORTED_CONFIGURATION,
            "inactive_bus_not_supported",
            "WS-8 spike supports active/inactive equipment but not inactive canonical buses",
            inactive_buses[0],
        )

    return (
        external,  # type: ignore[return-value]
        lines,  # type: ignore[return-value]
        transformers,  # type: ignore[return-value]
        loads,  # type: ignore[return-value]
    )


def _topology_signature(
    elements: dict[str, Element],
    inactive_equipment_ids: frozenset[str],
) -> str:
    facts: list[str] = []
    for element_id in sorted(elements):
        element = elements[element_id]
        active = element_id not in inactive_equipment_ids
        if element.kind in {"circuit_breaker", "disconnector"}:
            try:
                conductive = active and switch_allows_primary_conduction(element)
            except SwitchingStateError as exc:
                raise _AdapterInputError(
                    SolverStatus.INVALID_MODEL,
                    exc.code,
                    str(exc),
                    element.id,
                ) from exc
            facts.append(f"{element_id}:{'closed' if conductive else 'open'}")
        elif element.kind in _PARAMETERIZED_KINDS:
            facts.append(f"{element_id}:{'active' if active else 'inactive'}")
    payload = "\n".join(facts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _import_backend() -> tuple[Any, Any]:
    try:
        import pandapower as pp
        import pandapower.shortcircuit as sc
    except Exception as exc:  # pragma: no cover - exercised in dependency-free CI
        raise _AdapterInputError(
            SolverStatus.SOLVER_FAILURE,
            "solver_unavailable",
            "pandapower backend is not installed or failed to import",
        ) from exc
    return pp, sc


def _validate_one_phase_parameters(
    external: dict[str, ExternalGridParameters],
    lines: dict[str, LineParameters],
    transformers: dict[str, Transformer2WParameters],
) -> None:
    for item in external.values():
        if (
            item.zero_sequence_r_over_x_max is None
            or item.zero_sequence_x_over_x_max is None
        ):
            raise _AdapterInputError(
                SolverStatus.MISSING_PARAMETERS,
                "missing_zero_sequence_parameters",
                "single-phase-to-earth fault requires external-grid zero-sequence parameters",
                item.canonical_id,
            )
    for item in lines.values():
        if (
            item.zero_sequence_resistance_ohm_per_m is None
            or item.zero_sequence_reactance_ohm_per_m is None
            or item.zero_sequence_capacitance_f_per_m is None
        ):
            raise _AdapterInputError(
                SolverStatus.MISSING_PARAMETERS,
                "missing_zero_sequence_parameters",
                "single-phase-to-earth fault requires line zero-sequence parameters",
                item.canonical_id,
            )
    for item in transformers.values():
        if (
            item.vector_group is None
            or item.zero_sequence_short_circuit_voltage_percent is None
            or item.zero_sequence_short_circuit_resistance_percent is None
            or item.zero_sequence_magnetizing_percent is None
            or item.zero_sequence_magnetizing_r_over_x is None
            or item.zero_sequence_hv_partition is None
        ):
            raise _AdapterInputError(
                SolverStatus.MISSING_PARAMETERS,
                "missing_zero_sequence_parameters",
                "single-phase-to-earth fault requires transformer zero-sequence parameters",
                item.canonical_id,
            )


def _build_network(
    study: SolverStudyInput,
    *,
    fault_type: FaultType | None = None,
) -> _BuiltNetwork:
    elements = _element_map(study.model)
    for element in elements.values():
        _validate_terminal_contract(element)

    endpoint_bus = _endpoint_bus_map(study.model, elements)
    external, lines, transformers, loads = _required_parameters(elements, study)

    if fault_type is FaultType.SINGLE_PHASE_TO_EARTH:
        _validate_one_phase_parameters(external, lines, transformers)

    topology_signature = _topology_signature(
        elements,
        study.inactive_equipment_ids,
    )
    pp, sc = _import_backend()
    net = pp.create_empty_network(sn_mva=100.0, f_hz=50.0)

    bus_map: dict[str, int] = {}
    line_map: dict[str, int] = {}
    transformer_map: dict[str, int] = {}

    for element in sorted(elements.values(), key=lambda item: item.id):
        if element.kind != "bus":
            continue
        bus_map[element.id] = int(
            pp.create_bus(
                net,
                vn_kv=volts_to_kilovolts(_nominal_voltage_v(element)),
                name=element.id,
            )
        )

    for element in sorted(elements.values(), key=lambda item: item.id):
        active = element.id not in study.inactive_equipment_ids

        if element.kind == "external_grid":
            p = external[element.id]
            bus_id = endpoint_bus[Endpoint(element.id, "node")]
            kwargs: dict[str, object] = {
                "vm_pu": p.voltage_pu,
                "va_degree": p.angle_deg,
                "s_sc_max_mva": watts_to_megawatts(p.short_circuit_power_max_va),
                "rx_max": p.rx_max,
                "in_service": active,
                "name": element.id,
            }
            if p.zero_sequence_r_over_x_max is not None:
                kwargs["r0x0_max"] = p.zero_sequence_r_over_x_max
            if p.zero_sequence_x_over_x_max is not None:
                kwargs["x0x_max"] = p.zero_sequence_x_over_x_max
            pp.create_ext_grid(net, bus_map[bus_id], **kwargs)
            continue

        if element.kind == "line":
            p = lines[element.id]
            from_bus = endpoint_bus[Endpoint(element.id, "from")]
            to_bus = endpoint_bus[Endpoint(element.id, "to")]
            kwargs = {
                "length_km": metres_to_kilometres(p.length_m),
                "r_ohm_per_km": ohm_per_metre_to_ohm_per_kilometre(
                    p.resistance_ohm_per_m
                ),
                "x_ohm_per_km": ohm_per_metre_to_ohm_per_kilometre(
                    p.reactance_ohm_per_m
                ),
                "c_nf_per_km": farad_per_metre_to_nanofarad_per_kilometre(
                    p.capacitance_f_per_m
                ),
                "max_i_ka": amperes_to_kiloamperes(p.max_current_a),
                "type": "cs" if p.line_type == "cable" else "ol",
                "endtemp_degree": p.end_temperature_c,
                "in_service": active,
                "name": element.id,
            }
            if p.zero_sequence_resistance_ohm_per_m is not None:
                kwargs["r0_ohm_per_km"] = ohm_per_metre_to_ohm_per_kilometre(
                    p.zero_sequence_resistance_ohm_per_m
                )
            if p.zero_sequence_reactance_ohm_per_m is not None:
                kwargs["x0_ohm_per_km"] = ohm_per_metre_to_ohm_per_kilometre(
                    p.zero_sequence_reactance_ohm_per_m
                )
            if p.zero_sequence_capacitance_f_per_m is not None:
                kwargs["c0_nf_per_km"] = farad_per_metre_to_nanofarad_per_kilometre(
                    p.zero_sequence_capacitance_f_per_m
                )
            line_map[element.id] = int(
                pp.create_line_from_parameters(
                    net,
                    bus_map[from_bus],
                    bus_map[to_bus],
                    **kwargs,
                )
            )
            continue

        if element.kind == "transformer_2w":
            p = transformers[element.id]
            hv_bus = endpoint_bus[Endpoint(element.id, "hv")]
            lv_bus = endpoint_bus[Endpoint(element.id, "lv")]
            kwargs = {
                "sn_mva": watts_to_megawatts(p.rated_power_va),
                "vn_hv_kv": volts_to_kilovolts(p.hv_voltage_v),
                "vn_lv_kv": volts_to_kilovolts(p.lv_voltage_v),
                "vkr_percent": p.short_circuit_resistance_percent,
                "vk_percent": p.short_circuit_voltage_percent,
                "pfe_kw": watts_to_kilowatts(p.iron_loss_w),
                "i0_percent": p.no_load_current_percent,
                "shift_degree": p.phase_shift_deg,
                "in_service": active,
                "name": element.id,
            }
            if p.vector_group is not None:
                kwargs["vector_group"] = p.vector_group
            if p.zero_sequence_short_circuit_voltage_percent is not None:
                kwargs["vk0_percent"] = (
                    p.zero_sequence_short_circuit_voltage_percent
                )
            if p.zero_sequence_short_circuit_resistance_percent is not None:
                kwargs["vkr0_percent"] = (
                    p.zero_sequence_short_circuit_resistance_percent
                )
            if p.zero_sequence_magnetizing_percent is not None:
                kwargs["mag0_percent"] = p.zero_sequence_magnetizing_percent
            if p.zero_sequence_magnetizing_r_over_x is not None:
                kwargs["mag0_rx"] = p.zero_sequence_magnetizing_r_over_x
            if p.zero_sequence_hv_partition is not None:
                kwargs["si0_hv_partial"] = p.zero_sequence_hv_partition
            transformer_map[element.id] = int(
                pp.create_transformer_from_parameters(
                    net,
                    bus_map[hv_bus],
                    bus_map[lv_bus],
                    **kwargs,
                )
            )
            continue

        if element.kind == "load":
            p = loads[element.id]
            bus_id = endpoint_bus[Endpoint(element.id, "node")]
            pp.create_load(
                net,
                bus_map[bus_id],
                p_mw=watts_to_megawatts(p.active_power_w),
                q_mvar=vars_to_megavars(p.reactive_power_var),
                in_service=active,
                name=element.id,
            )
            continue

        if element.kind in {"circuit_breaker", "disconnector"}:
            try:
                closed = active and switch_allows_primary_conduction(element)
            except SwitchingStateError as exc:
                raise _AdapterInputError(
                    SolverStatus.INVALID_MODEL,
                    exc.code,
                    str(exc),
                    element.id,
                ) from exc
            a_bus = endpoint_bus[Endpoint(element.id, "a")]
            b_bus = endpoint_bus[Endpoint(element.id, "b")]
            pp.create_switch(
                net,
                bus=bus_map[a_bus],
                element=bus_map[b_bus],
                et="b",
                closed=closed,
                type="CB" if element.kind == "circuit_breaker" else "DS",
                name=element.id,
            )

    return _BuiltNetwork(
        pp=pp,
        sc=sc,
        net=net,
        maps=_NetworkMaps(
            bus=bus_map,
            line=line_map,
            transformer_2w=transformer_map,
        ),
        topology_signature=topology_signature,
    )


def _captured_warnings(captured: list[python_warnings.WarningMessage]) -> tuple[SolverMessage, ...]:
    messages = {
        (item.category.__name__, str(item.message))
        for item in captured
    }
    return tuple(
        SolverMessage(
            code=f"pandapower_warning.{category}",
            message=message,
        )
        for category, message in sorted(messages)
    )


def _solver_version(pp: Any) -> str | None:
    raw = getattr(pp, "__version__", None)
    return str(raw) if raw is not None else None


def _power_flow_buses(built: _BuiltNetwork) -> tuple[BusPowerFlowResult, ...]:
    rows: list[BusPowerFlowResult] = []
    for canonical_id in sorted(built.maps.bus):
        index = built.maps.bus[canonical_id]
        row = built.net.res_bus.loc[index]
        vm_pu = _finite_or_none(_row_value(row, "vm_pu"))
        nominal_kv = _finite_or_none(built.net.bus.at[index, "vn_kv"])
        voltage_v = (
            None
            if vm_pu is None or nominal_kv is None
            else kilovolts_to_volts(vm_pu * nominal_kv)
        )
        rows.append(
            BusPowerFlowResult(
                canonical_id=canonical_id,
                voltage_v=voltage_v,
                voltage_pu=vm_pu,
                voltage_angle_deg=_finite_or_none(
                    _row_value(row, "va_degree")
                ),
                net_active_power_w=_scaled(
                    _row_value(row, "p_mw"), 1_000_000.0
                ),
                net_reactive_power_var=_scaled(
                    _row_value(row, "q_mvar"), 1_000_000.0
                ),
            )
        )
    return tuple(rows)


def _power_flow_branches(
    built: _BuiltNetwork,
) -> tuple[BranchPowerFlowResult, ...]:
    rows: list[BranchPowerFlowResult] = []

    for canonical_id in sorted(built.maps.line):
        index = built.maps.line[canonical_id]
        row = built.net.res_line.loc[index]
        currents = [
            _finite_or_none(_row_value(row, "i_from_ka")),
            _finite_or_none(_row_value(row, "i_to_ka")),
        ]
        finite_currents = [item for item in currents if item is not None]
        rows.append(
            BranchPowerFlowResult(
                canonical_id=canonical_id,
                element_kind="line",
                current_a=(
                    kiloamperes_to_amperes(max(finite_currents))
                    if finite_currents
                    else None
                ),
                active_power_from_w=_scaled(
                    _row_value(row, "p_from_mw"), 1_000_000.0
                ),
                reactive_power_from_var=_scaled(
                    _row_value(row, "q_from_mvar"), 1_000_000.0
                ),
                active_power_to_w=_scaled(
                    _row_value(row, "p_to_mw"), 1_000_000.0
                ),
                reactive_power_to_var=_scaled(
                    _row_value(row, "q_to_mvar"), 1_000_000.0
                ),
                active_loss_w=_scaled(
                    _row_value(row, "pl_mw"), 1_000_000.0
                ),
                reactive_loss_var=_scaled(
                    _row_value(row, "ql_mvar"), 1_000_000.0
                ),
                loading_percent=_finite_or_none(
                    _row_value(row, "loading_percent")
                ),
            )
        )

    for canonical_id in sorted(built.maps.transformer_2w):
        index = built.maps.transformer_2w[canonical_id]
        row = built.net.res_trafo.loc[index]
        currents = [
            _finite_or_none(_row_value(row, "i_hv_ka")),
            _finite_or_none(_row_value(row, "i_lv_ka")),
        ]
        finite_currents = [item for item in currents if item is not None]
        rows.append(
            BranchPowerFlowResult(
                canonical_id=canonical_id,
                element_kind="transformer_2w",
                current_a=(
                    kiloamperes_to_amperes(max(finite_currents))
                    if finite_currents
                    else None
                ),
                active_power_from_w=_scaled(
                    _row_value(row, "p_hv_mw"), 1_000_000.0
                ),
                reactive_power_from_var=_scaled(
                    _row_value(row, "q_hv_mvar"), 1_000_000.0
                ),
                active_power_to_w=_scaled(
                    _row_value(row, "p_lv_mw"), 1_000_000.0
                ),
                reactive_power_to_var=_scaled(
                    _row_value(row, "q_lv_mvar"), 1_000_000.0
                ),
                active_loss_w=_scaled(
                    _row_value(row, "pl_mw"), 1_000_000.0
                ),
                reactive_loss_var=_scaled(
                    _row_value(row, "ql_mvar"), 1_000_000.0
                ),
                loading_percent=_finite_or_none(
                    _row_value(row, "loading_percent")
                ),
            )
        )

    return tuple(sorted(rows, key=lambda item: item.canonical_id))


def _short_circuit_node(
    built: _BuiltNetwork,
    canonical_bus_id: str,
) -> ShortCircuitNodeResult:
    index = built.maps.bus[canonical_bus_id]
    row = built.net.res_bus_sc.loc[index]
    return ShortCircuitNodeResult(
        canonical_id=canonical_bus_id,
        initial_symmetrical_current_a=_scaled(
            _row_value(row, "ikss_ka"), 1_000.0
        ),
        peak_current_a=_scaled(_row_value(row, "ip_ka"), 1_000.0),
        thermal_current_a=_scaled(_row_value(row, "ith_ka"), 1_000.0),
        short_circuit_power_va=_scaled(
            _row_value(row, "skss_mw"), 1_000_000.0
        ),
        equivalent_resistance_ohm=_finite_or_none(
            _row_value(row, "rk_ohm")
        ),
        equivalent_reactance_ohm=_finite_or_none(
            _row_value(row, "xk_ohm")
        ),
    )


def _short_circuit_branches(
    built: _BuiltNetwork,
) -> tuple[ShortCircuitBranchResult, ...]:
    rows: list[ShortCircuitBranchResult] = []

    line_table = getattr(built.net, "res_line_sc", None)
    if line_table is not None:
        for canonical_id in sorted(built.maps.line):
            row = _table_row(line_table, built.maps.line[canonical_id])
            if row is None:
                continue
            from_a = _scaled(_row_value(row, "ikss_from_ka"), 1_000.0)
            to_a = _scaled(_row_value(row, "ikss_to_ka"), 1_000.0)
            direct_a = _scaled(_row_value(row, "ikss_ka"), 1_000.0)
            currents = [
                item for item in (from_a, to_a, direct_a) if item is not None
            ]
            rows.append(
                ShortCircuitBranchResult(
                    canonical_id=canonical_id,
                    element_kind="line",
                    initial_current_a=max(currents) if currents else None,
                    from_current_a=from_a,
                    to_current_a=to_a,
                    peak_current_a=_scaled(
                        _row_value(row, "ip_ka"), 1_000.0
                    ),
                    thermal_current_a=_scaled(
                        _row_value(row, "ith_ka"), 1_000.0
                    ),
                )
            )

    trafo_table = getattr(built.net, "res_trafo_sc", None)
    if trafo_table is not None:
        for canonical_id in sorted(built.maps.transformer_2w):
            row = _table_row(
                trafo_table,
                built.maps.transformer_2w[canonical_id],
            )
            if row is None:
                continue
            from_a = _scaled(_row_value(row, "ikss_hv_ka"), 1_000.0)
            to_a = _scaled(_row_value(row, "ikss_lv_ka"), 1_000.0)
            direct_a = _scaled(_row_value(row, "ikss_ka"), 1_000.0)
            currents = [
                item for item in (from_a, to_a, direct_a) if item is not None
            ]
            rows.append(
                ShortCircuitBranchResult(
                    canonical_id=canonical_id,
                    element_kind="transformer_2w",
                    initial_current_a=max(currents) if currents else None,
                    from_current_a=from_a,
                    to_current_a=to_a,
                    peak_current_a=_scaled(
                        _row_value(row, "ip_ka"), 1_000.0
                    ),
                    thermal_current_a=_scaled(
                        _row_value(row, "ith_ka"), 1_000.0
                    ),
                )
            )

    return tuple(sorted(rows, key=lambda item: item.canonical_id))


class PandapowerAdapter:
    """Headless pandapower adapter with no pandapower objects in its public contract."""

    solver_name = _SOLVER_NAME

    def power_flow(
        self,
        study: SolverStudyInput,
        request: PowerFlowRequest | None = None,
    ) -> PowerFlowResult:
        request = request or PowerFlowRequest()
        try:
            built = _build_network(study)
        except _AdapterInputError as exc:
            return PowerFlowResult(
                status=exc.status,
                solver_name=self.solver_name,
                errors=(_message_from_input_error(exc),),
            )

        try:
            with python_warnings.catch_warnings(record=True) as captured:
                python_warnings.simplefilter("always")
                built.pp.runpp(
                    built.net,
                    calculate_voltage_angles=request.calculate_voltage_angles,
                )
            warning_messages = _captured_warnings(captured)
        except Exception as exc:
            status = (
                SolverStatus.NON_CONVERGED
                if exc.__class__.__name__ == "LoadflowNotConverged"
                else SolverStatus.SOLVER_FAILURE
            )
            return PowerFlowResult(
                status=status,
                solver_name=self.solver_name,
                solver_version=_solver_version(built.pp),
                topology_signature=built.topology_signature,
                errors=(
                    SolverMessage(
                        "power_flow_failed",
                        _clean_exception_message(exc),
                    ),
                ),
            )

        if not bool(getattr(built.net, "converged", False)):
            return PowerFlowResult(
                status=SolverStatus.NON_CONVERGED,
                solver_name=self.solver_name,
                solver_version=_solver_version(built.pp),
                topology_signature=built.topology_signature,
                errors=(
                    SolverMessage(
                        "power_flow_non_converged",
                        "pandapower did not converge",
                    ),
                ),
            )

        return PowerFlowResult(
            status=SolverStatus.SUCCESS,
            solver_name=self.solver_name,
            solver_version=_solver_version(built.pp),
            topology_signature=built.topology_signature,
            buses=_power_flow_buses(built),
            branches=_power_flow_branches(built),
            warnings=warning_messages,
        )

    def short_circuit(
        self,
        study: SolverStudyInput,
        request: ShortCircuitRequest,
    ) -> ShortCircuitResult:
        try:
            built = _build_network(study, fault_type=request.fault_type)
        except _AdapterInputError as exc:
            return ShortCircuitResult(
                status=exc.status,
                solver_name=self.solver_name,
                fault_type=request.fault_type,
                fault_canonical_bus_id=request.canonical_bus_id,
                errors=(_message_from_input_error(exc),),
            )

        if request.canonical_bus_id not in built.maps.bus:
            return ShortCircuitResult(
                status=SolverStatus.INVALID_MODEL,
                solver_name=self.solver_name,
                solver_version=_solver_version(built.pp),
                fault_type=request.fault_type,
                fault_canonical_bus_id=request.canonical_bus_id,
                errors=(
                    SolverMessage(
                        "fault_bus_not_found",
                        "short-circuit target must be a canonical bus id",
                        request.canonical_bus_id,
                    ),
                ),
            )
        if request.case not in {"max", "min"}:
            return ShortCircuitResult(
                status=SolverStatus.UNSUPPORTED_CONFIGURATION,
                solver_name=self.solver_name,
                solver_version=_solver_version(built.pp),
                fault_type=request.fault_type,
                fault_canonical_bus_id=request.canonical_bus_id,
                errors=(
                    SolverMessage(
                        "unsupported_short_circuit_case",
                        "short-circuit case must be 'max' or 'min'",
                    ),
                ),
            )

        try:
            with python_warnings.catch_warnings(record=True) as captured:
                python_warnings.simplefilter("always")
                built.sc.calc_sc(
                    built.net,
                    bus=built.maps.bus[request.canonical_bus_id],
                    fault=request.fault_type.value,
                    case=request.case,
                    ip=request.calculate_peak,
                    ith=request.calculate_thermal,
                    tk_s=request.clearing_time_s,
                    branch_results=request.branch_results,
                    return_all_currents=False,
                )
            warning_messages = _captured_warnings(captured)
        except Exception as exc:
            return ShortCircuitResult(
                status=SolverStatus.SOLVER_FAILURE,
                solver_name=self.solver_name,
                solver_version=_solver_version(built.pp),
                fault_type=request.fault_type,
                fault_canonical_bus_id=request.canonical_bus_id,
                errors=(
                    SolverMessage(
                        "short_circuit_failed",
                        _clean_exception_message(exc),
                        request.canonical_bus_id,
                    ),
                ),
            )

        return ShortCircuitResult(
            status=SolverStatus.SUCCESS,
            solver_name=self.solver_name,
            solver_version=_solver_version(built.pp),
            fault_type=request.fault_type,
            fault_canonical_bus_id=request.canonical_bus_id,
            node=_short_circuit_node(built, request.canonical_bus_id),
            branch_contributions=(
                _short_circuit_branches(built)
                if request.branch_results
                else ()
            ),
            warnings=warning_messages,
        )
