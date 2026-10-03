from __future__ import annotations

from dataclasses import dataclass

from .model import CanonicalModel, Endpoint


@dataclass(frozen=True, slots=True, order=True)
class ValidationIssue:
    code: str
    path: str
    message: str


def _path_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _endpoint_path(connection_id: str, endpoint: Endpoint) -> str:
    cid = _path_value(connection_id)
    eid = _path_value(endpoint.element_id)
    tid = _path_value(endpoint.terminal_id)
    return (
        f"/connections[id='{cid}']"
        f"/endpoints[element_id='{eid}',terminal_id='{tid}']"
    )


def validate_model(model: CanonicalModel) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []

    element_counts: dict[str, int] = {}
    terminal_sets: dict[str, set[str]] = {}

    for element in model.elements:
        element_counts[element.id] = element_counts.get(element.id, 0) + 1
        seen_terminals: set[str] = set()
        for terminal in element.terminals:
            if terminal.id in seen_terminals:
                issues.append(
                    ValidationIssue(
                        "duplicate_terminal_id",
                        (
                            f"/elements[id='{_path_value(element.id)}']"
                            f"/terminals[id='{_path_value(terminal.id)}']"
                        ),
                        "terminal id must be unique within an element",
                    )
                )
            seen_terminals.add(terminal.id)
        terminal_sets.setdefault(element.id, set()).update(seen_terminals)

    for element_id, count in element_counts.items():
        if count > 1:
            issues.append(
                ValidationIssue(
                    "duplicate_element_id",
                    f"/elements[id='{_path_value(element_id)}']",
                    "element id must be globally unique",
                )
            )

    connection_counts: dict[str, int] = {}
    for connection in model.connections:
        connection_counts[connection.id] = connection_counts.get(connection.id, 0) + 1

        if connection.endpoints[0] == connection.endpoints[1]:
            issues.append(
                ValidationIssue(
                    "degenerate_connection",
                    f"/connections[id='{_path_value(connection.id)}']",
                    "connection endpoints must be distinct",
                )
            )

        for endpoint in connection.endpoints:
            path = _endpoint_path(connection.id, endpoint)
            if element_counts.get(endpoint.element_id, 0) == 0:
                issues.append(
                    ValidationIssue(
                        "unknown_element",
                        path,
                        f"unknown element id: {endpoint.element_id}",
                    )
                )
                continue
            if element_counts.get(endpoint.element_id, 0) > 1:
                continue
            if endpoint.terminal_id not in terminal_sets.get(endpoint.element_id, set()):
                issues.append(
                    ValidationIssue(
                        "unknown_terminal",
                        path,
                        (
                            f"unknown terminal id '{endpoint.terminal_id}' "
                            f"on element '{endpoint.element_id}'"
                        ),
                    )
                )

    for connection_id, count in connection_counts.items():
        if count > 1:
            issues.append(
                ValidationIssue(
                    "duplicate_connection_id",
                    f"/connections[id='{_path_value(connection_id)}']",
                    "connection id must be globally unique",
                )
            )

    return tuple(sorted(set(issues)))
