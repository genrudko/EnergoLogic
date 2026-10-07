from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
import unicodedata
from typing import Mapping

from energologic.core.model import CanonicalModel, Connection, Element, Endpoint, Terminal
from energologic.domain import (
    SWITCHING_KINDS,
    TRANSFORMER_2W_KIND,
    VOLTAGE_CLASS_BELOW_3000_V,
    VoltageSpec,
    read_switching_state,
    validate_switching_state_model,
    voltage_spec_for_terminal,
)

from .contracts import VisioShapeBinding
from .identity import VisioIdentityError, projection_cell_id
from .snapshot import VisioPageSnapshot, VisioShapeSnapshot, VisioVtdStateSnapshot


_VTD_VOLTAGE_V_BY_INDEX: dict[int, int] = {
    0: 1_150_000,
    1: 800_000,
    2: 750_000,
    3: 500_000,
    4: 400_000,
    5: 330_000,
    6: 220_000,
    7: 150_000,
    8: 110_000,
    9: 60_000,
    10: 35_000,
    11: 20_000,
    12: 15_000,
    13: 10_000,
    14: 6_000,
    15: 3_000,
}
_VTD_INDEX_BY_VOLTAGE_V = {
    value: key for key, value in _VTD_VOLTAGE_V_BY_INDEX.items()
}
_VTD_VOLTAGE_CLASS_BY_INDEX = {
    16: VOLTAGE_CLASS_BELOW_3000_V,
}
_VTD_INDEX_BY_VOLTAGE_CLASS = {
    value: key for key, value in _VTD_VOLTAGE_CLASS_BY_INDEX.items()
}
_CONNECTION_ROW = re.compile(r"^Connections\.(\d+)\.X$", re.IGNORECASE)


class VisioMappingError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True, slots=True)
class _MasterRule:
    kind: str
    stencil_name: str
    terminals: tuple[str, ...]
    mounting_type: str | None = None


_MASTER_RULES: dict[str, _MasterRule] = {
    "Шина10": _MasterRule("bus", "Шины.vss", ("node",)),
    "Выкатная тележка выключателя": _MasterRule(
        "circuit_breaker",
        "Коммутационные аппараты.vss",
        ("a", "b"),
        "withdrawable",
    ),
    "Разъединитель выдвижной": _MasterRule(
        "disconnector",
        "Коммутационные аппараты.vss",
        ("a", "b"),
        "withdrawable",
    ),
    "ТТ": _MasterRule("current_transformer", "Трансформаторы.vss", ("a", "b")),
    "ТСН2": _MasterRule(
        TRANSFORMER_2W_KIND,
        "Трансформаторы.vss",
        ("hv", "lv"),
    ),
    "Связь с объектом2": _MasterRule("external_link", "Линии, заземление.vss", ("node",)),
}


@dataclass(frozen=True, slots=True)
class VisioCaptureResult:
    model: CanonicalModel
    bindings: tuple[VisioShapeBinding, ...]


@dataclass(frozen=True, slots=True)
class VisioRenderShape:
    element_id: str
    kind: str
    stencil_name: str
    master_name: str
    text: str
    shape_data: Mapping[str, str]
    x_mm: float
    y_mm: float
    vtd_state: VisioVtdStateSnapshot | None = None


@dataclass(frozen=True, slots=True)
class VisioRenderConnection:
    """Executable native-glue instruction for the supported Visio slice."""

    source: Endpoint
    target: Endpoint
    source_endpoint: str
    target_connection_row: int
    target_child_user_nt: int | None = None


@dataclass(frozen=True, slots=True)
class VisioRenderPlan:
    page_name: str
    shapes: tuple[VisioRenderShape, ...]
    connections: tuple[VisioRenderConnection, ...]


def _normalized_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).split())


def _element_id(kind: str, text: str, *, cell_id: str | None = None) -> str:
    normalized = _normalized_text(text)
    if not normalized:
        raise VisioMappingError("missing_identity_text", f"{kind} shape has empty text")
    material = f"{kind}\0{normalized}"
    if cell_id is not None:
        material += f"\0cell:{cell_id}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"{kind}:{digest}"


def _connection_id(first: Endpoint, second: Endpoint) -> str:
    left, right = sorted((first, second))
    material = (
        f"{left.element_id}\0{left.terminal_id}\0"
        f"{right.element_id}\0{right.terminal_id}"
    )
    return "connection:" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def _shape_data_index(
    shape: VisioShapeSnapshot, property_name: str
) -> int:
    formula = shape.shape_data.get(property_name)
    if formula is None:
        raise VisioMappingError(
            "missing_shape_data",
            (
                f"shape {shape.shape_id} ({shape.master_name}) has no "
                f"Prop.{property_name} snapshot"
            ),
        )
    pattern = re.compile(
        rf"^INDEX\((\d+),\s*Prop\.{re.escape(property_name)}\.Format\)$",
        re.IGNORECASE,
    )
    match = pattern.fullmatch(formula.strip())
    if match is None:
        raise VisioMappingError(
            "unsupported_shape_data_formula",
            (
                f"shape {shape.shape_id} has unsupported Prop.{property_name} "
                f"formula {formula!r}"
            ),
        )
    return int(match.group(1))


def _voltage_spec(
    shape: VisioShapeSnapshot, property_name: str
) -> VoltageSpec:
    index = _shape_data_index(shape, property_name)
    exact = _VTD_VOLTAGE_V_BY_INDEX.get(index)
    if exact is not None:
        return VoltageSpec(nominal_voltage_v=exact)
    voltage_class = _VTD_VOLTAGE_CLASS_BY_INDEX.get(index)
    if voltage_class is not None:
        return VoltageSpec(voltage_class=voltage_class)
    raise VisioMappingError(
        "unsupported_voltage_class",
        (
            f"shape {shape.shape_id} Prop.{property_name} uses unsupported "
            f"VTD voltage index {index}"
        ),
    )


def _voltage_v(shape: VisioShapeSnapshot) -> int:
    spec = _voltage_spec(shape, "u")
    if spec.nominal_voltage_v is None:
        raise VisioMappingError(
            "unsupported_voltage_class",
            (
                f"shape {shape.shape_id} requires exact Prop.u voltage for "
                "this element kind"
            ),
        )
    return spec.nominal_voltage_v


def _voltage_spec_attributes(spec: VoltageSpec) -> dict[str, object]:
    if spec.nominal_voltage_v is not None:
        return {"nominal_voltage_v": spec.nominal_voltage_v}
    if spec.voltage_class is not None:
        return {"voltage_class": spec.voltage_class}
    raise AssertionError("empty VoltageSpec")


_VTD_WINDING_BY_INDEX = {
    1: "delta",
    2: "open_delta",
    3: "three_single_phase",
    4: "star",
    5: "star_with_neutral",
    6: "star_grounded_neutral",
    7: "zigzag",
    8: "zigzag_with_neutral",
}
_CANONICAL_WINDING_TO_VTD = {
    value: key for key, value in _VTD_WINDING_BY_INDEX.items()
}


def _winding_connection(
    shape: VisioShapeSnapshot, property_name: str
) -> str:
    index = _shape_data_index(shape, property_name)
    try:
        return _VTD_WINDING_BY_INDEX[index]
    except KeyError as exc:
        raise VisioMappingError(
            "unsupported_winding_connection",
            (
                f"shape {shape.shape_id} Prop.{property_name} uses unsupported "
                f"winding index {index}"
            ),
        ) from exc


def _transformer_terminals(shape: VisioShapeSnapshot) -> tuple[Terminal, Terminal]:
    hv_attributes = {
        **_voltage_spec_attributes(_voltage_spec(shape, "u")),
        "winding_connection": _winding_connection(shape, "s1"),
    }
    lv_attributes = {
        **_voltage_spec_attributes(_voltage_spec(shape, "u2")),
        "winding_connection": _winding_connection(shape, "s2"),
    }
    return (
        Terminal(id="hv", attributes=hv_attributes),
        Terminal(id="lv", attributes=lv_attributes),
    )


_VTD_CART_TO_CANONICAL = {
    0: "working",
    1: "repair",
    2: "control",
}
_CANONICAL_CART_TO_VTD = {
    value: key for key, value in _VTD_CART_TO_CANONICAL.items()
}


def _switching_attributes(
    shape: VisioShapeSnapshot, rule: _MasterRule
) -> dict[str, str]:
    if rule.kind not in SWITCHING_KINDS:
        return {}
    if rule.mounting_type != "withdrawable":
        raise VisioMappingError(
            "unsupported_switching_master",
            (
                f"shape {shape.shape_id} master {shape.master_name!r} has "
                f"unsupported mounting type {rule.mounting_type!r}"
            ),
        )
    state = shape.vtd_state
    if state is None:
        raise VisioMappingError(
            "missing_vtd_state",
            f"shape {shape.shape_id} ({shape.master_name}) has no VTD state snapshot",
        )
    if not isinstance(state.main_action_active, bool):
        raise VisioMappingError(
            "invalid_vtd_switch_state",
            (
                f"shape {shape.shape_id} requires boolean native main action state; "
                f"got {state.main_action_active!r}"
            ),
        )
    try:
        position = _VTD_CART_TO_CANONICAL[state.cart_position_value]
    except KeyError as exc:
        raise VisioMappingError(
            "invalid_vtd_cart_position",
            (
                f"shape {shape.shape_id} requires native cart position 0/1/2; "
                f"got {state.cart_position_value!r}"
            ),
        ) from exc
    return {
        "switch_state": "closed" if state.main_action_active else "open",
        "mounting_type": "withdrawable",
        "withdrawable_position": position,
    }


def _shape_rule(shape: VisioShapeSnapshot) -> _MasterRule:
    try:
        return _MASTER_RULES[shape.master_name]
    except KeyError as exc:
        raise VisioMappingError(
            "unsupported_master",
            f"shape {shape.shape_id} uses unsupported master {shape.master_name!r}",
        ) from exc


def _element_for_shape(shape: VisioShapeSnapshot) -> Element:
    rule = _shape_rule(shape)
    name = _normalized_text(shape.text)
    try:
        cell_id = projection_cell_id(shape.user_cells)
    except VisioIdentityError as exc:
        raise VisioMappingError(exc.code, str(exc).split(": ", 1)[-1]) from exc
    element_id = _element_id(rule.kind, name, cell_id=cell_id)

    if rule.kind == TRANSFORMER_2W_KIND:
        return Element(
            id=element_id,
            kind=rule.kind,
            name=name,
            terminals=_transformer_terminals(shape),
            attributes={},
        )

    attributes = {"nominal_voltage_v": _voltage_v(shape)}
    attributes.update(_switching_attributes(shape, rule))
    return Element(
        id=element_id,
        kind=rule.kind,
        name=name,
        terminals=tuple(Terminal(id=terminal_id) for terminal_id in rule.terminals),
        attributes=attributes,
    )


def _endpoint_for_cell(
    shape: VisioShapeSnapshot,
    cell_name: str,
    elements_by_shape_id: Mapping[int, Element],
    shapes_by_id: Mapping[int, VisioShapeSnapshot],
) -> Endpoint:
    if shape.parent_shape_id is not None:
        try:
            parent = shapes_by_id[shape.parent_shape_id]
            parent_element = elements_by_shape_id[parent.shape_id]
        except KeyError as exc:
            raise VisioMappingError(
                "orphan_group_child",
                f"child shape {shape.shape_id} has unresolved parent {shape.parent_shape_id}",
            ) from exc
        if parent_element.kind != "bus":
            raise VisioMappingError(
                "unsupported_group_child",
                f"child shape {shape.shape_id} belongs to non-bus element {parent_element.id}",
            )
        return Endpoint(parent_element.id, "node")

    try:
        element = elements_by_shape_id[shape.shape_id]
    except KeyError as exc:
        raise VisioMappingError(
            "unmapped_shape",
            f"shape {shape.shape_id} participates in topology but is not an electrical element",
        ) from exc

    if len(element.terminals) == 1:
        return Endpoint(element.id, element.terminals[0].id)

    normalized = cell_name.strip()
    if element.kind == TRANSFORMER_2W_KIND:
        if normalized.casefold() == "beginx":
            return Endpoint(element.id, "hv")
        if normalized.casefold() == "endx":
            return Endpoint(element.id, "lv")
        match = _CONNECTION_ROW.fullmatch(normalized)
        if match:
            row = int(match.group(1))
            if row == 1:
                return Endpoint(element.id, "hv")
            if row == 2:
                return Endpoint(element.id, "lv")
    else:
        if normalized.casefold() == "beginx":
            return Endpoint(element.id, "a")
        if normalized.casefold() == "endx":
            return Endpoint(element.id, "b")
        match = _CONNECTION_ROW.fullmatch(normalized)
        if match:
            row = int(match.group(1))
            if row == 1:
                return Endpoint(element.id, "a")
            if row == 2:
                return Endpoint(element.id, "b")
    raise VisioMappingError(
        "unsupported_terminal_cell",
        f"cannot map {cell_name!r} on shape {shape.shape_id} to a supported terminal",
    )


def capture_page_snapshot(
    snapshot: VisioPageSnapshot, *, model_id: str
) -> VisioCaptureResult:
    shapes_by_id: dict[int, VisioShapeSnapshot] = {}
    for shape in snapshot.shapes:
        if shape.shape_id in shapes_by_id:
            raise VisioMappingError(
                "duplicate_shape_id", f"duplicate Visio shape id {shape.shape_id}"
            )
        shapes_by_id[shape.shape_id] = shape

    elements_by_shape_id: dict[int, Element] = {}
    elements_by_id: dict[str, Element] = {}
    bindings: list[VisioShapeBinding] = []

    for shape in snapshot.shapes:
        if shape.parent_shape_id is not None:
            continue
        element = _element_for_shape(shape)
        if element.id in elements_by_id:
            other = elements_by_id[element.id]
            raise VisioMappingError(
                "ambiguous_identity",
                (
                    f"multiple {element.kind} shapes normalize to the same identity "
                    f"{element.id}: {other.name!r}"
                ),
            )
        elements_by_shape_id[shape.shape_id] = element
        elements_by_id[element.id] = element
        bindings.append(
            VisioShapeBinding(
                element_id=element.id,
                page_name=snapshot.page_name,
                shape_id=shape.shape_id,
            )
        )

    for shape in snapshot.shapes:
        if shape.parent_shape_id is None:
            continue
        _endpoint_for_cell(shape, "", elements_by_shape_id, shapes_by_id)

    connections_by_pair: dict[tuple[Endpoint, Endpoint], Connection] = {}
    for glue in snapshot.connections:
        try:
            source_shape = shapes_by_id[glue.from_shape_id]
            target_shape = shapes_by_id[glue.to_shape_id]
        except KeyError as exc:
            raise VisioMappingError(
                "unknown_shape_reference",
                f"glue references shape id {exc.args[0]} outside the snapshot",
            ) from exc

        source = _endpoint_for_cell(
            source_shape, glue.from_cell, elements_by_shape_id, shapes_by_id
        )
        target = _endpoint_for_cell(
            target_shape, glue.to_cell, elements_by_shape_id, shapes_by_id
        )
        if source == target:
            raise VisioMappingError(
                "degenerate_connection",
                (
                    f"glue on shapes {glue.from_shape_id}->{glue.to_shape_id} "
                    "resolves to one endpoint"
                ),
            )
        pair = tuple(sorted((source, target)))
        if pair in connections_by_pair:
            continue
        connections_by_pair[pair] = Connection(
            id=_connection_id(source, target),
            endpoints=(source, target),
        )

    model = CanonicalModel(
        schema_version="0.1",
        model_id=model_id,
        elements=tuple(elements_by_id.values()),
        connections=tuple(connections_by_pair.values()),
    )
    return VisioCaptureResult(
        model=model,
        bindings=tuple(sorted(bindings, key=lambda item: item.element_id)),
    )


def _voltage_formula(element: Element) -> str:
    value = element.attributes.get("nominal_voltage_v")
    if not isinstance(value, int) or isinstance(value, bool):
        raise VisioMappingError(
            "missing_nominal_voltage",
            (
                f"element {element.id} needs integer nominal_voltage_v "
                "for Visio projection"
            ),
        )
    try:
        index = _VTD_INDEX_BY_VOLTAGE_V[value]
    except KeyError as exc:
        raise VisioMappingError(
            "unsupported_nominal_voltage",
            f"element {element.id} uses unsupported nominal voltage {value!r}",
        ) from exc
    return f"INDEX({index},Prop.u.Format)"


def _voltage_spec_formula(
    element: Element,
    terminal_id: str,
    property_name: str,
) -> str:
    spec = voltage_spec_for_terminal(element, terminal_id)
    if spec.nominal_voltage_v is not None:
        try:
            index = _VTD_INDEX_BY_VOLTAGE_V[spec.nominal_voltage_v]
        except KeyError as exc:
            raise VisioMappingError(
                "unsupported_exact_voltage_projection",
                (
                    f"element {element.id} terminal {terminal_id} exact voltage "
                    f"{spec.nominal_voltage_v} V cannot be represented losslessly "
                    "by the qualified VTD voltage list"
                ),
            ) from exc
    elif spec.voltage_class is not None:
        try:
            index = _VTD_INDEX_BY_VOLTAGE_CLASS[spec.voltage_class]
        except KeyError as exc:
            raise VisioMappingError(
                "unsupported_voltage_class_projection",
                (
                    f"element {element.id} terminal {terminal_id} voltage class "
                    f"{spec.voltage_class!r} has no qualified VTD mapping"
                ),
            ) from exc
    else:
        raise AssertionError("empty VoltageSpec")
    return f"INDEX({index},Prop.{property_name}.Format)"


def _winding_formula(
    element: Element,
    terminal_id: str,
    property_name: str,
) -> str:
    terminal = next(
        (item for item in element.terminals if item.id == terminal_id),
        None,
    )
    if terminal is None:
        raise VisioMappingError(
            "missing_transformer_terminal",
            f"element {element.id} has no terminal {terminal_id!r}",
        )
    value = terminal.attributes.get("winding_connection")
    try:
        index = _CANONICAL_WINDING_TO_VTD[value]
    except (KeyError, TypeError) as exc:
        raise VisioMappingError(
            "unsupported_winding_projection",
            (
                f"element {element.id} terminal {terminal_id} winding "
                f"{value!r} has no qualified VTD mapping"
            ),
        ) from exc
    return f"INDEX({index},Prop.{property_name}.Format)"


def _transformer_shape_data(element: Element) -> dict[str, str]:
    return {
        "u": _voltage_spec_formula(element, "hv", "u"),
        "u2": _voltage_spec_formula(element, "lv", "u2"),
        "s1": _winding_formula(element, "hv", "s1"),
        "s2": _winding_formula(element, "lv", "s2"),
        # Native projection defaults observed on qualified ТСН2.
        "p2": "INDEX(1,Prop.p2.Format)",
        "c": "INDEX(1,Prop.c.Format)",
    }


def _render_rule(element: Element) -> tuple[str, _MasterRule]:
    matches = [
        (master, rule)
        for master, rule in _MASTER_RULES.items()
        if rule.kind == element.kind
        and (
            rule.mounting_type is None
            or element.attributes.get("mounting_type") == rule.mounting_type
        )
    ]
    if len(matches) != 1:
        raise VisioMappingError(
            "unsupported_element_kind",
            f"element {element.id} kind {element.kind!r} has no unique Visio master",
        )
    return matches[0]


def _render_vtd_state(element: Element) -> VisioVtdStateSnapshot | None:
    if element.kind not in SWITCHING_KINDS:
        return None
    state = read_switching_state(element)
    if state.mounting_type != "withdrawable":
        raise VisioMappingError(
            "unsupported_switching_projection",
            (
                f"element {element.id} uses mounting_type={state.mounting_type!r}; "
                "qualified Visio masters are withdrawable"
            ),
        )
    try:
        cart_position = _CANONICAL_CART_TO_VTD[state.withdrawable_position]
    except KeyError as exc:
        raise VisioMappingError(
            "unsupported_withdrawable_position",
            (
                f"element {element.id} has unsupported withdrawable position "
                f"{state.withdrawable_position!r}"
            ),
        ) from exc
    return VisioVtdStateSnapshot(
        main_action_active=state.switch_state == "closed",
        cart_position_value=cart_position,
    )


def _path_order(model: CanonicalModel) -> tuple[str, ...]:
    elements = {element.id: element for element in model.elements}
    if len(elements) == 1 and not model.connections:
        return (next(iter(elements)),)
    buses = sorted(element.id for element in model.elements if element.kind == "bus")
    externals = sorted(
        element.id for element in model.elements if element.kind == "external_link"
    )
    if len(buses) != 1 or len(externals) != 1:
        raise VisioMappingError(
            "unsupported_slice_topology",
            "first Visio slice requires exactly one bus and one external_link",
        )

    adjacency: dict[str, set[str]] = {element_id: set() for element_id in elements}
    for connection in model.connections:
        left, right = connection.endpoints
        if left.element_id not in elements or right.element_id not in elements:
            raise VisioMappingError(
                "broken_model_reference", f"connection {connection.id} is broken"
            )
        adjacency[left.element_id].add(right.element_id)
        adjacency[right.element_id].add(left.element_id)

    start = buses[0]
    goal = externals[0]
    order: list[str] = []
    previous: str | None = None
    current = start
    while True:
        order.append(current)
        if current == goal:
            break
        candidates = sorted(
            adjacency[current] - ({previous} if previous else set())
        )
        if len(candidates) != 1:
            raise VisioMappingError(
                "unsupported_slice_topology",
                f"element {current} does not form a single deterministic path",
            )
        previous, current = current, candidates[0]
        if current in order:
            raise VisioMappingError(
                "unsupported_slice_topology", "cycle detected in first slice"
            )

    if set(order) != set(elements):
        raise VisioMappingError(
            "unsupported_slice_topology",
            "first Visio slice must be one connected path containing every element",
        )
    return tuple(order)


def _render_connections(
    model: CanonicalModel, order: tuple[str, ...]
) -> tuple[VisioRenderConnection, ...]:
    elements = {element.id: element for element in model.elements}
    connections_by_pair: dict[frozenset[str], list[Connection]] = {}
    for connection in model.connections:
        pair = frozenset(endpoint.element_id for endpoint in connection.endpoints)
        connections_by_pair.setdefault(pair, []).append(connection)

    result: list[VisioRenderConnection] = []
    for upper_id, lower_id in zip(order, order[1:]):
        matches = connections_by_pair.get(frozenset((upper_id, lower_id)), [])
        if len(matches) != 1:
            raise VisioMappingError(
                "unsupported_slice_topology",
                (
                    f"expected exactly one connection between {upper_id} and "
                    f"{lower_id}, found {len(matches)}"
                ),
            )
        connection = matches[0]
        endpoints = {endpoint.element_id: endpoint for endpoint in connection.endpoints}
        source = endpoints[lower_id]
        target = endpoints[upper_id]

        if source.terminal_id not in {"a", "node"}:
            raise VisioMappingError(
                "unsupported_terminal_orientation",
                (
                    f"lower element {lower_id} must expose terminal a/node to "
                    f"Visio BeginX, got {source.terminal_id!r}"
                ),
            )
        if target.terminal_id not in {"b", "node"}:
            raise VisioMappingError(
                "unsupported_terminal_orientation",
                (
                    f"upper element {upper_id} must expose terminal b/node at "
                    f"native connection row 2, got {target.terminal_id!r}"
                ),
            )

        result.append(
            VisioRenderConnection(
                source=source,
                target=target,
                source_endpoint="begin",
                target_connection_row=2,
                target_child_user_nt=(
                    1 if elements[upper_id].kind == "bus" else None
                ),
            )
        )
    return tuple(result)


def build_render_plan(model: CanonicalModel, *, page_name: str) -> VisioRenderPlan:
    switching_issues = validate_switching_state_model(model)
    if switching_issues:
        issue = switching_issues[0]
        raise VisioMappingError(
            "invalid_switching_state_model",
            f"{issue.code} at {issue.path}: {issue.message}",
        )

    elements = {element.id: element for element in model.elements}
    order = _path_order(model)
    x_mm = 110.0
    top_y_mm = 250.0
    step_mm = 25.0

    shapes: list[VisioRenderShape] = []
    for position, element_id in enumerate(order):
        element = elements[element_id]
        master_name, rule = _render_rule(element)
        expected_terminals = tuple(terminal.id for terminal in element.terminals)
        if tuple(sorted(expected_terminals)) != tuple(sorted(rule.terminals)):
            raise VisioMappingError(
                "unsupported_terminal_contract",
                (
                    f"element {element.id} terminals {expected_terminals!r} "
                    f"do not match {rule.terminals!r}"
                ),
            )
        if element.kind == TRANSFORMER_2W_KIND:
            shape_data = _transformer_shape_data(element)
        else:
            shape_data = {"u": _voltage_formula(element)}
        if element.kind == "bus":
            # Projection defaults only. They define a compact one-point native
            # Шина10 for the vertical-slice rebuild and never enter canonical data.
            shape_data = {
                **shape_data,
                "rt": "INDEX(7,Prop.rt.Format)",
                "tp": "INDEX(0,Prop.tp.Format)",
            }
        shapes.append(
            VisioRenderShape(
                element_id=element.id,
                kind=element.kind,
                stencil_name=rule.stencil_name,
                master_name=master_name,
                text=element.name,
                shape_data=shape_data,
                x_mm=x_mm,
                y_mm=top_y_mm - position * step_mm,
                vtd_state=_render_vtd_state(element),
            )
        )

    connections = _render_connections(model, order)
    return VisioRenderPlan(
        page_name=page_name,
        shapes=tuple(shapes),
        connections=connections,
    )
