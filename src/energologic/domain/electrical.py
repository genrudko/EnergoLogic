from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from energologic.core.model import CanonicalModel, Endpoint
from energologic.core.validation import ValidationIssue, validate_model


ELECTRICAL_V1_NAME = "electrical-v1"


@dataclass(frozen=True, slots=True)
class ElectricalElementSpec:
    kind: str
    terminals: tuple[str, ...]
    max_terminal_degree: Mapping[str, int | None]


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
        }
    ),
)


def _path_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _element_path(element_id: str) -> str:
    return f"/elements[id='{_path_value(element_id)}']"


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
    valid_voltage_by_id: dict[str, int] = {}

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
        voltage = _nominal_voltage_v(raw_voltage)
        if voltage is None:
            issues.append(
                ValidationIssue(
                    "invalid_nominal_voltage",
                    f"{path}/attributes/nominal_voltage_v",
                    "nominal_voltage_v must be a positive integer number of volts",
                )
            )
            continue
        valid_voltage_by_id[element.id] = voltage

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

        left_voltage = valid_voltage_by_id.get(left.element_id)
        right_voltage = valid_voltage_by_id.get(right.element_id)
        if (
            left_voltage is not None
            and right_voltage is not None
            and left_voltage != right_voltage
        ):
            issues.append(
                ValidationIssue(
                    "nominal_voltage_mismatch",
                    path,
                    (
                        f"{left.element_id}={left_voltage} V and "
                        f"{right.element_id}={right_voltage} V"
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
                    (
                        f"{_element_path(endpoint.element_id)}"
                        f"/terminals[id='{_path_value(endpoint.terminal_id)}']"
                    ),
                    (
                        f"terminal degree {degree} exceeds electrical-v1 limit "
                        f"{limit} for kind '{element.kind}'"
                    ),
                )
            )

    return tuple(sorted(set(issues)))
