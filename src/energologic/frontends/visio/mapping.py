from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
import unicodedata
from typing import Mapping

from energologic.core.model import CanonicalModel, Connection, Element, Endpoint, Terminal

from .contracts import VisioShapeBinding
from .snapshot import VisioPageSnapshot, VisioShapeSnapshot


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
_INDEX_FORMULA = re.compile(r"^INDEX\((\d+),\s*Prop\.u\.Format\)$", re.IGNORECASE)
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


_MASTER_RULES: dict[str, _MasterRule] = {
    "Шина10": _MasterRule("bus", "Шины.vss", ("node",)),
    "Выкатная тележка выключателя": _MasterRule(
        "circuit_breaker", "Коммутационные аппараты.vss", ("a", "b")
    ),
    "ТТ": _MasterRule("current_transformer", "Трансформаторы.vss", ("a", "b")),
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


def _element_id(kind: str, text: str) -> str:
    normalized = _normalized_text(text)
    if not normalized:
        raise VisioMappingError("missing_identity_text", f"{kind} shape has empty text")
    digest = hashlib.sha256(f"{kind}\0{normalized}".encode("utf-8")).hexdigest()[:16]
    return f"{kind}:{digest}"


def _connection_id(first: Endpoint, second: Endpoint) -> str:
    left, right = sorted((first, second))
    material = (
        f"{left.element_id}\0{left.terminal_id}\0"
        f"{right.element_id}\0{right.terminal_id}"
    )
    return "connection:" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def _voltage_v(shape: VisioShapeSnapshot) -> int:
    formula = shape.shape_data.get("u")
    if formula is None:
        raise VisioMappingError(
            "missing_voltage",
            f"shape {shape.shape_id} ({shape.master_name}) has no Prop.u snapshot",
        )
    match = _INDEX_FORMULA.fullmatch(formula.strip())
    if match is None:
        raise VisioMappingError(
            "unsupported_voltage_formula",
            f"shape {shape.shape_id} has unsupported Prop.u formula {formula!r}",
        )
    index = int(match.group(1))
    try:
        return _VTD_VOLTAGE_V_BY_INDEX[index]
    except KeyError as exc:
        raise VisioMappingError(
            "unsupported_voltage_class",
            f"shape {shape.shape_id} uses VTD voltage index {index}",
        ) from exc


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
    element_id = _element_id(rule.kind, name)
    return Element(
        id=element_id,
        kind=rule.kind,
        name=name,
        terminals=tuple(Terminal(id=terminal_id) for terminal_id in rule.terminals),
        attributes={"nominal_voltage_v": _voltage_v(shape)},
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


def _render_rule(element: Element) -> tuple[str, _MasterRule]:
    matches = [
        (master, rule)
        for master, rule in _MASTER_RULES.items()
        if rule.kind == element.kind
    ]
    if len(matches) != 1:
        raise VisioMappingError(
            "unsupported_element_kind",
            f"element {element.id} kind {element.kind!r} has no unique Visio master",
        )
    return matches[0]


def _path_order(model: CanonicalModel) -> tuple[str, ...]:
    elements = {element.id: element for element in model.elements}
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
            )
        )

    connections = _render_connections(model, order)
    return VisioRenderPlan(
        page_name=page_name,
        shapes=tuple(shapes),
        connections=connections,
    )
