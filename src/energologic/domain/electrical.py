from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from energologic.core.model import CanonicalModel, Element, Endpoint, Terminal
from energologic.core.validation import ValidationIssue, validate_model


ELECTRICAL_V1_NAME = "electrical-v1"

VOLTAGE_CLASS_BELOW_3000_V = "below_3000_v"
VOLTAGE_CLASSES: Mapping[str, tuple[int | None, int | None]] = MappingProxyType(
    {
        # Half-open interval: 0 < U < 3000 V.
        VOLTAGE_CLASS_BELOW_3000_V: (0, 3000),
    }
)

TRANSFORMER_2W_KIND = "transformer_2w"
TRANSFORMER_WINDING_CONNECTIONS = frozenset(
    {
        "delta",
        "open_delta",
        "three_single_phase",
        "star",
        "star_with_neutral",
        "star_grounded_neutral",
        "zigzag",
        "zigzag_with_neutral",
    }
)


@dataclass(frozen=True, slots=True)
class VoltageSpec:
    nominal_voltage_v: int | None = None
    voltage_class: str | None = None

    def describe(self) -> str:
        if self.nominal_voltage_v is not None:
            return f"{self.nominal_voltage_v} V"
        return f"class {self.voltage_class}"


@dataclass(frozen=True, slots=True)
class ElectricalElementSpec:
    kind: str
    terminals: tuple[str, ...]
    max_terminal_degree: Mapping[str, int | None]
    voltage_scope: str = "element"


@dataclass(frozen=True, slots=True)
class ElectricalProfile:
    name: str
    specs: Mapping[str, ElectricalElementSpec]


ELECTRICAL_V1 = ElectricalProfile(
    name=ELECTRICAL_V1_NAME,
    specs=MappingProxyType(
        {
            "bus": ElectricalElementSpec(
                kind="bus",
                terminals=("node",),
                max_terminal_degree=MappingProxyType({"node": None}),
            ),
            "circuit_breaker": ElectricalElementSpec(
                kind="circuit_breaker",
                terminals=("a", "b"),
                max_terminal_degree=MappingProxyType({"a": 1, "b": 1}),
            ),
            "disconnector": ElectricalElementSpec(
                kind="disconnector",
                terminals=("a", "b"),
                max_terminal_degree=MappingProxyType({"a": 1, "b": 1}),
            ),
            "current_transformer": ElectricalElementSpec(
                kind="current_transformer",
                terminals=("a", "b"),
                max_terminal_degree=MappingProxyType({"a": 1, "b": 1}),
            ),
            "external_link": ElectricalElementSpec(
                kind="external_link",
                terminals=("node",),
                max_terminal_degree=MappingProxyType({"node": 1}),
            ),
            TRANSFORMER_2W_KIND: ElectricalElementSpec(
                kind=TRANSFORMER_2W_KIND,
                terminals=("hv", "lv"),
                max_terminal_degree=MappingProxyType({"hv": 1, "lv": 1}),
                voltage_scope="terminal",
            ),
        }
    ),
)

# An explicit additive profile for solver-driven headless operational studies.
# The original ELECTRICAL_V1 is intentionally unchanged: these three kinds
# inherit an unambiguous voltage from a directly connected canonical bus,
# never from shape text, solver output or assumed electrical parameters.
ELECTRICAL_OPERATIONAL_SOLVER_V1_NAME = "electrical-operational-solver-v1"
ELECTRICAL_OPERATIONAL_SOLVER_V1 = ElectricalProfile(
    name=ELECTRICAL_OPERATIONAL_SOLVER_V1_NAME,
    specs=MappingProxyType({
        **ELECTRICAL_V1.specs,
        "external_grid": ElectricalElementSpec(
            "external_grid", ("node",),
            MappingProxyType({"node": 1}), voltage_scope="connected_bus",
        ),
        "line": ElectricalElementSpec(
            "line", ("from", "to"),
            MappingProxyType({"from": 1, "to": 1}), voltage_scope="connected_bus",
        ),
        "load": ElectricalElementSpec(
            "load", ("node",),
            MappingProxyType({"node": 1}), voltage_scope="connected_bus",
        ),
    }),
)


def _path_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _element_path(element_id: str) -> str:
    return f"/elements[id='{_path_value(element_id)}']"


def _terminal_path(element_id: str, terminal_id: str) -> str:
    return (
        f"{_element_path(element_id)}"
        f"/terminals[id='{_path_value(terminal_id)}']"
    )


def _connection_path(connection_id: str) -> str:
    return f"/connections[id='{_path_value(connection_id)}']"


def _endpoint_text(endpoint: Endpoint) -> str:
    return f"{endpoint.element_id}:{endpoint.terminal_id}"


def _nominal_voltage_v(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value <= 0:
        return None
    return value


def _read_voltage_spec(
    attributes: Mapping[str, object],
    *,
    path: str,
    missing_code: str,
    invalid_voltage_code: str,
    invalid_class_code: str,
    ambiguous_code: str,
    missing_message: str,
) -> tuple[VoltageSpec | None, tuple[ValidationIssue, ...]]:
    has_exact = "nominal_voltage_v" in attributes
    has_class = "voltage_class" in attributes
    issues: list[ValidationIssue] = []

    if has_exact and has_class:
        issues.append(
            ValidationIssue(
                ambiguous_code,
                path,
                "voltage specification must use either nominal_voltage_v or voltage_class, not both",
            )
        )
        return None, tuple(issues)

    if has_exact:
        raw_voltage = attributes["nominal_voltage_v"]
        voltage = _nominal_voltage_v(raw_voltage)
        if voltage is None:
            issues.append(
                ValidationIssue(
                    invalid_voltage_code,
                    f"{path}/nominal_voltage_v",
                    "nominal_voltage_v must be a positive integer number of volts",
                )
            )
            return None, tuple(issues)
        return VoltageSpec(nominal_voltage_v=voltage), ()

    if has_class:
        raw_class = attributes["voltage_class"]
        if not isinstance(raw_class, str) or raw_class not in VOLTAGE_CLASSES:
            issues.append(
                ValidationIssue(
                    invalid_class_code,
                    f"{path}/voltage_class",
                    (
                        f"voltage_class must be one of {sorted(VOLTAGE_CLASSES)!r}; "
                        f"got {raw_class!r}"
                    ),
                )
            )
            return None, tuple(issues)
        return VoltageSpec(voltage_class=raw_class), ()

    issues.append(ValidationIssue(missing_code, path, missing_message))
    return None, tuple(issues)


def _class_contains(voltage_class: str, voltage_v: int) -> bool:
    lower_exclusive, upper_exclusive = VOLTAGE_CLASSES[voltage_class]
    if lower_exclusive is not None and voltage_v <= lower_exclusive:
        return False
    if upper_exclusive is not None and voltage_v >= upper_exclusive:
        return False
    return True


def voltage_specs_compatible(left: VoltageSpec, right: VoltageSpec) -> bool:
    if left.nominal_voltage_v is not None and right.nominal_voltage_v is not None:
        return left.nominal_voltage_v == right.nominal_voltage_v

    if left.nominal_voltage_v is not None and right.voltage_class is not None:
        return _class_contains(right.voltage_class, left.nominal_voltage_v)

    if right.nominal_voltage_v is not None and left.voltage_class is not None:
        return _class_contains(left.voltage_class, right.nominal_voltage_v)

    if left.voltage_class is not None and right.voltage_class is not None:
        return left.voltage_class == right.voltage_class

    return False


def _voltage_definitely_lower(left: VoltageSpec, right: VoltageSpec) -> bool:
    if left.nominal_voltage_v is not None and right.nominal_voltage_v is not None:
        return left.nominal_voltage_v < right.nominal_voltage_v

    if left.voltage_class == VOLTAGE_CLASS_BELOW_3000_V:
        if right.nominal_voltage_v is not None:
            return right.nominal_voltage_v >= 3000

    return False


def voltage_spec_for_terminal(
    element: Element,
    terminal_id: str,
    *,
    profile: ElectricalProfile = ELECTRICAL_V1,
) -> VoltageSpec:
    spec = profile.specs.get(element.kind)
    if spec is None:
        raise ValueError(f"unsupported element kind: {element.kind}")

    if spec.voltage_scope == "element":
        raw_voltage = element.attributes.get("nominal_voltage_v")
        voltage_v = _nominal_voltage_v(raw_voltage)
        if voltage_v is None:
            raise ValueError(
                "element-scoped electrical equipment requires a positive integer "
                "nominal_voltage_v"
            )
        voltage = VoltageSpec(nominal_voltage_v=voltage_v)
        issues: tuple[ValidationIssue, ...] = ()
    elif spec.voltage_scope == "terminal":
        terminal = next(
            (item for item in element.terminals if item.id == terminal_id),
            None,
        )
        if terminal is None:
            raise ValueError(
                f"element {element.id} has no terminal {terminal_id!r}"
            )
        voltage, issues = _read_voltage_spec(
            terminal.attributes,
            path=f"{_terminal_path(element.id, terminal_id)}/attributes",
            missing_code="missing_terminal_voltage",
            invalid_voltage_code="invalid_terminal_voltage",
            invalid_class_code="invalid_terminal_voltage_class",
            ambiguous_code="ambiguous_terminal_voltage_spec",
            missing_message=(
                "terminal requires canonical nominal_voltage_v or voltage_class"
            ),
        )
    else:
        raise ValueError(
            f"unsupported voltage scope {spec.voltage_scope!r} for {element.kind}"
        )

    if issues or voltage is None:
        first = issues[0] if issues else None
        raise ValueError(first.message if first else "invalid voltage specification")
    return voltage


def _validate_transformer_terminal(
    element: Element,
    terminal: Terminal,
) -> tuple[ValidationIssue, ...]:
    path = f"{_terminal_path(element.id, terminal.id)}/attributes"
    issues: list[ValidationIssue] = []

    raw_connection = terminal.attributes.get("winding_connection")
    if (
        not isinstance(raw_connection, str)
        or raw_connection not in TRANSFORMER_WINDING_CONNECTIONS
    ):
        issues.append(
            ValidationIssue(
                "invalid_winding_connection",
                f"{path}/winding_connection",
                (
                    "transformer terminal requires winding_connection in "
                    f"{sorted(TRANSFORMER_WINDING_CONNECTIONS)!r}; "
                    f"got {raw_connection!r}"
                ),
            )
        )
    return tuple(issues)


def validate_electrical_model(
    model: CanonicalModel,
    *,
    profile: ElectricalProfile = ELECTRICAL_V1,
) -> tuple[ValidationIssue, ...]:
    """Validate deterministic electrical semantics in addition to structural rules."""

    issues: list[ValidationIssue] = list(validate_model(model))

    counts: dict[str, int] = {}
    for element in model.elements:
        counts[element.id] = counts.get(element.id, 0) + 1

    unique_elements = {
        element.id: element
        for element in model.elements
        if counts.get(element.id) == 1
    }
    voltage_by_endpoint: dict[Endpoint, VoltageSpec] = {}
    connected_bus_endpoints: list[Endpoint] = []

    for element in model.elements:
        path = _element_path(element.id)
        spec = profile.specs.get(element.kind)
        if spec is None:
            issues.append(
                ValidationIssue(
                    "unsupported_element_kind",
                    f"{path}/kind",
                    (
                        f"element kind '{element.kind}' is not supported by "
                        f"profile '{profile.name}'"
                    ),
                )
            )
            continue

        actual_terminals = tuple(terminal.id for terminal in element.terminals)
        if (
            len(actual_terminals) != len(spec.terminals)
            or set(actual_terminals) != set(spec.terminals)
        ):
            issues.append(
                ValidationIssue(
                    "invalid_terminal_contract",
                    f"{path}/terminals",
                    (
                        f"kind '{element.kind}' requires terminals "
                        f"{sorted(spec.terminals)!r}; got {sorted(actual_terminals)!r}"
                    ),
                )
            )

        if spec.voltage_scope == "connected_bus":
            if "nominal_voltage_v" in element.attributes or "voltage_class" in element.attributes:
                issues.append(ValidationIssue(
                    "unexpected_inferred_voltage_spec",
                    f"{path}/attributes",
                    "this solver-operational kind inherits exact voltage only from an adjacent canonical bus",
                ))
            connected_bus_endpoints.extend(
                Endpoint(element.id, terminal.id) for terminal in element.terminals
            )
            continue

        if spec.voltage_scope == "element":
            if "voltage_class" in element.attributes:
                issues.append(
                    ValidationIssue(
                        "unexpected_element_voltage_class",
                        f"{path}/attributes/voltage_class",
                        (
                            f"kind '{element.kind}' requires exact "
                            "nominal_voltage_v; voltage_class is reserved for "
                            "qualified terminal-scoped semantics"
                        ),
                    )
                )

            if "nominal_voltage_v" not in element.attributes:
                issues.append(
                    ValidationIssue(
                        "missing_nominal_voltage",
                        f"{path}/attributes/nominal_voltage_v",
                        "electrical-v1 requires canonical nominal_voltage_v",
                    )
                )
                continue

            raw_voltage = element.attributes["nominal_voltage_v"]
            voltage_v = _nominal_voltage_v(raw_voltage)
            if voltage_v is None:
                issues.append(
                    ValidationIssue(
                        "invalid_nominal_voltage",
                        f"{path}/attributes/nominal_voltage_v",
                        (
                            "nominal_voltage_v must be a positive integer "
                            "number of volts"
                        ),
                    )
                )
                continue

            voltage = VoltageSpec(nominal_voltage_v=voltage_v)
            for terminal in element.terminals:
                voltage_by_endpoint[Endpoint(element.id, terminal.id)] = voltage
            continue

        if spec.voltage_scope != "terminal":
            issues.append(
                ValidationIssue(
                    "invalid_voltage_scope",
                    f"{path}/kind",
                    f"unsupported voltage scope {spec.voltage_scope!r}",
                )
            )
            continue

        if (
            "nominal_voltage_v" in element.attributes
            or "voltage_class" in element.attributes
        ):
            issues.append(
                ValidationIssue(
                    "unexpected_element_voltage_spec",
                    f"{path}/attributes",
                    (
                        f"kind '{element.kind}' requires voltage specification "
                        "on each terminal, not on the whole element"
                    ),
                )
            )

        for terminal in element.terminals:
            terminal_path = _terminal_path(element.id, terminal.id)
            voltage, voltage_issues = _read_voltage_spec(
                terminal.attributes,
                path=f"{terminal_path}/attributes",
                missing_code="missing_terminal_voltage",
                invalid_voltage_code="invalid_terminal_voltage",
                invalid_class_code="invalid_terminal_voltage_class",
                ambiguous_code="ambiguous_terminal_voltage_spec",
                missing_message=(
                    "terminal requires canonical nominal_voltage_v or voltage_class"
                ),
            )
            issues.extend(voltage_issues)
            if voltage is not None:
                voltage_by_endpoint[Endpoint(element.id, terminal.id)] = voltage

            if element.kind == TRANSFORMER_2W_KIND:
                issues.extend(_validate_transformer_terminal(element, terminal))

        if element.kind == TRANSFORMER_2W_KIND:
            hv = voltage_by_endpoint.get(Endpoint(element.id, "hv"))
            lv = voltage_by_endpoint.get(Endpoint(element.id, "lv"))
            if (
                hv is not None
                and lv is not None
                and _voltage_definitely_lower(hv, lv)
            ):
                issues.append(
                    ValidationIssue(
                        "invalid_transformer_voltage_order",
                        f"{path}/terminals",
                        (
                            f"transformer hv side {hv.describe()} is definitely "
                            f"below lv side {lv.describe()}"
                        ),
                    )
                )

    # Solver-neutral line/load/grid kinds can omit voltage at their own
    # terminals only when each is connected DIRECTLY to one qualified bus.
    # This is an explicit modeled topology rule, never a speculative inference.
    for endpoint in connected_bus_endpoints:
        neighbors = [
            right if left == endpoint else left
            for connection in model.connections
            for left, right in (connection.endpoints,)
            if endpoint == left or endpoint == right
        ]
        valid = (
            len(neighbors) == 1
            and neighbors[0].terminal_id == "node"
            and neighbors[0].element_id in unique_elements
            and unique_elements[neighbors[0].element_id].kind == "bus"
            and neighbors[0] in voltage_by_endpoint
        )
        if not valid:
            issues.append(ValidationIssue(
                "unresolved_connected_bus_voltage",
                _terminal_path(endpoint.element_id, endpoint.terminal_id),
                "terminal requires one directly connected canonical bus with known voltage",
            ))
            continue
        voltage_by_endpoint[endpoint] = voltage_by_endpoint[neighbors[0]]

    for element in model.elements:
        if element.kind != "line" or element.kind not in profile.specs:
            continue
        left = voltage_by_endpoint.get(Endpoint(element.id, "from"))
        right = voltage_by_endpoint.get(Endpoint(element.id, "to"))
        if left is not None and right is not None and not voltage_specs_compatible(left, right):
            issues.append(ValidationIssue(
                "line_terminal_voltage_mismatch",
                f"{_element_path(element.id)}/terminals",
                f"line connects incompatible bus voltages: {left.describe()} and {right.describe()}",
            ))

    pair_to_connection_ids: dict[tuple[Endpoint, Endpoint], list[str]] = {}
    terminal_degree: dict[Endpoint, int] = {}

    for connection in model.connections:
        left, right = connection.endpoints
        path = _connection_path(connection.id)
        pair = tuple(sorted((left, right)))
        pair_to_connection_ids.setdefault(pair, []).append(connection.id)

        for endpoint in connection.endpoints:
            terminal_degree[endpoint] = terminal_degree.get(endpoint, 0) + 1

        if left.element_id == right.element_id:
            issues.append(
                ValidationIssue(
                    "intra_element_connection",
                    path,
                    (
                        "external topology must not connect two terminals of the "
                        f"same element '{left.element_id}'"
                    ),
                )
            )

        left_element = unique_elements.get(left.element_id)
        right_element = unique_elements.get(right.element_id)
        if left_element is None or right_element is None:
            continue
        if (
            left_element.kind not in profile.specs
            or right_element.kind not in profile.specs
        ):
            continue

        left_voltage = voltage_by_endpoint.get(left)
        right_voltage = voltage_by_endpoint.get(right)
        if (
            left_voltage is not None
            and right_voltage is not None
            and not voltage_specs_compatible(left_voltage, right_voltage)
        ):
            issues.append(
                ValidationIssue(
                    "nominal_voltage_mismatch",
                    path,
                    (
                        f"{_endpoint_text(left)}={left_voltage.describe()} and "
                        f"{_endpoint_text(right)}={right_voltage.describe()}"
                    ),
                )
            )

    for pair, connection_ids in pair_to_connection_ids.items():
        if len(connection_ids) <= 1:
            continue
        left, right = pair
        issues.append(
            ValidationIssue(
                "duplicate_electrical_connection",
                (
                    "/connections"
                    f"[pair='{_path_value(_endpoint_text(left))}"
                    f"<->{_path_value(_endpoint_text(right))}']"
                ),
                (
                    "multiple connection records describe the same electrical edge: "
                    + ", ".join(sorted(connection_ids))
                ),
            )
        )

    for endpoint, degree in terminal_degree.items():
        element = unique_elements.get(endpoint.element_id)
        if element is None:
            continue
        spec = profile.specs.get(element.kind)
        if spec is None:
            continue
        limit = spec.max_terminal_degree.get(endpoint.terminal_id)
        if limit is not None and degree > limit:
            issues.append(
                ValidationIssue(
                    "terminal_degree_exceeded",
                    _terminal_path(endpoint.element_id, endpoint.terminal_id),
                    (
                        f"terminal degree {degree} exceeds electrical-v1 limit "
                        f"{limit} for kind '{element.kind}'"
                    ),
                )
            )

    return tuple(sorted(set(issues)))
