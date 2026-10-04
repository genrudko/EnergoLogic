from __future__ import annotations

from collections import defaultdict, deque
import hashlib
from typing import Iterable

from energologic.core import CanonicalModel, Endpoint, fingerprint
from energologic.domain import (
    SWITCHING_KINDS,
    switch_allows_primary_conduction,
    validate_switching_state_model,
)

from .contracts import (
    ElementOperationalState,
    OperationalDelta,
    OperationalMessage,
    OperationalResult,
    OperationalStatus,
    SourceRef,
    TerminalOperationalDelta,
    TerminalOperationalState,
)


def _endpoint_key(endpoint: Endpoint | SourceRef) -> tuple[str, str]:
    return (endpoint.element_id, endpoint.terminal_id)


def _validation_messages(model: CanonicalModel) -> tuple[OperationalMessage, ...]:
    return tuple(
        OperationalMessage(
            issue.code,
            issue.message,
            path=issue.path,
        )
        for issue in validate_switching_state_model(model)
    )


def _terminal_index(model: CanonicalModel) -> dict[tuple[str, str], Endpoint]:
    return {
        (element.id, terminal.id): Endpoint(element.id, terminal.id)
        for element in model.elements
        for terminal in element.terminals
    }


def _add_edge(
    adjacency: dict[Endpoint, set[Endpoint]],
    first: Endpoint,
    second: Endpoint,
) -> None:
    adjacency[first].add(second)
    adjacency[second].add(first)


def _internal_conduction_edges(model: CanonicalModel) -> tuple[tuple[Endpoint, Endpoint], ...]:
    edges: list[tuple[Endpoint, Endpoint]] = []

    for element in sorted(model.elements, key=lambda item: item.id):
        terminal_ids = {terminal.id for terminal in element.terminals}

        if element.kind in SWITCHING_KINDS:
            if not switch_allows_primary_conduction(element):
                continue
            first, second = "a", "b"
        elif element.kind == "current_transformer":
            first, second = "a", "b"
        elif element.kind == "transformer_2w":
            first, second = "hv", "lv"
        else:
            continue

        if first not in terminal_ids or second not in terminal_ids:
            # The domain validator reports the structural/domain error before
            # this function is reached. Keep this path fail-closed anyway.
            continue

        left = Endpoint(element.id, first)
        right = Endpoint(element.id, second)
        edges.append((left, right))

    return tuple(edges)


def _conductive_graph(
    model: CanonicalModel,
) -> dict[Endpoint, set[Endpoint]]:
    endpoints = tuple(
        Endpoint(element.id, terminal.id)
        for element in model.elements
        for terminal in element.terminals
    )
    adjacency: dict[Endpoint, set[Endpoint]] = {
        endpoint: set() for endpoint in endpoints
    }

    for connection in model.connections:
        first, second = connection.endpoints
        _add_edge(adjacency, first, second)

    for first, second in _internal_conduction_edges(model):
        _add_edge(adjacency, first, second)

    return adjacency


def _topology_fingerprint(
    adjacency: dict[Endpoint, set[Endpoint]],
) -> str:
    edge_keys: set[
        tuple[tuple[str, str], tuple[str, str]]
    ] = set()

    for endpoint, neighbors in adjacency.items():
        first = _endpoint_key(endpoint)
        for neighbor in neighbors:
            second = _endpoint_key(neighbor)
            edge_keys.add(tuple(sorted((first, second))))

    payload = "\n".join(
        f"{left[0]}:{left[1]}--{right[0]}:{right[1]}"
        for left, right in sorted(edge_keys)
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _reachable_from(
    adjacency: dict[Endpoint, set[Endpoint]],
    start: Endpoint,
) -> set[Endpoint]:
    visited: set[Endpoint] = {start}
    pending: deque[Endpoint] = deque((start,))

    while pending:
        current = pending.popleft()
        for neighbor in sorted(adjacency[current], key=_endpoint_key):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            pending.append(neighbor)

    return visited


def simulate_operational_state(
    model: CanonicalModel,
    sources: Iterable[SourceRef] = (),
) -> OperationalResult:
    """Resolve terminal energization and source reachability.

    Source status is an explicit runtime boundary condition. It is never
    inferred from element kind, text, voltage or geometry.
    """

    validation_messages = _validation_messages(model)
    if validation_messages:
        return OperationalResult(
            status=OperationalStatus.INVALID_MODEL,
            model_id=model.model_id,
            model_fingerprint=fingerprint(model),
            conductive_topology_fingerprint=None,
            messages=validation_messages,
        )

    terminal_index = _terminal_index(model)
    source_refs = tuple(sorted(set(sources)))

    invalid_sources = tuple(
        source
        for source in source_refs
        if _endpoint_key(source) not in terminal_index
    )
    if invalid_sources:
        messages = tuple(
            OperationalMessage(
                "invalid_source_endpoint",
                (
                    "source endpoint does not exist in canonical model: "
                    f"{source.element_id}:{source.terminal_id}"
                ),
                source.element_id,
                source.terminal_id,
            )
            for source in invalid_sources
        )
        return OperationalResult(
            status=OperationalStatus.INVALID_SOURCE,
            model_id=model.model_id,
            model_fingerprint=fingerprint(model),
            conductive_topology_fingerprint=None,
            messages=messages,
        )

    adjacency = _conductive_graph(model)
    reached_by: dict[Endpoint, set[SourceRef]] = defaultdict(set)

    for source in source_refs:
        start = terminal_index[_endpoint_key(source)]
        for endpoint in _reachable_from(adjacency, start):
            reached_by[endpoint].add(source)

    terminal_states = tuple(
        TerminalOperationalState(
            element_id=endpoint.element_id,
            terminal_id=endpoint.terminal_id,
            energized=bool(reached_by[endpoint]),
            sources=tuple(sorted(reached_by[endpoint])),
        )
        for endpoint in sorted(adjacency, key=_endpoint_key)
    )

    terminal_state_by_key = {
        (state.element_id, state.terminal_id): state
        for state in terminal_states
    }

    element_states: list[ElementOperationalState] = []
    for element in sorted(model.elements, key=lambda item: item.id):
        states = tuple(
            terminal_state_by_key[(element.id, terminal.id)]
            for terminal in sorted(element.terminals, key=lambda item: item.id)
        )
        energized_ids = tuple(
            state.terminal_id for state in states if state.energized
        )
        deenergized_ids = tuple(
            state.terminal_id for state in states if not state.energized
        )
        source_union = tuple(
            sorted(
                {
                    source
                    for state in states
                    for source in state.sources
                }
            )
        )
        element_states.append(
            ElementOperationalState(
                element_id=element.id,
                energized=bool(energized_ids),
                fully_energized=bool(states) and not deenergized_ids,
                energized_terminal_ids=energized_ids,
                deenergized_terminal_ids=deenergized_ids,
                sources=source_union,
            )
        )

    return OperationalResult(
        status=OperationalStatus.SUCCESS,
        model_id=model.model_id,
        model_fingerprint=fingerprint(model),
        conductive_topology_fingerprint=_topology_fingerprint(adjacency),
        terminal_states=terminal_states,
        element_states=tuple(element_states),
    )


def compare_operational_results(
    before: OperationalResult,
    after: OperationalResult,
) -> OperationalDelta:
    """Compare two successful states with the same canonical terminal set."""

    if (
        before.status is not OperationalStatus.SUCCESS
        or after.status is not OperationalStatus.SUCCESS
    ):
        return OperationalDelta(
            status=OperationalStatus.INCOMPATIBLE_MODELS,
            before_model_id=before.model_id,
            after_model_id=after.model_id,
            topology_changed=False,
            messages=(
                OperationalMessage(
                    "non_success_result",
                    "operational delta requires two successful results",
                ),
            ),
        )

    before_by_key = {
        (state.element_id, state.terminal_id): state
        for state in before.terminal_states
    }
    after_by_key = {
        (state.element_id, state.terminal_id): state
        for state in after.terminal_states
    }

    if set(before_by_key) != set(after_by_key):
        return OperationalDelta(
            status=OperationalStatus.INCOMPATIBLE_MODELS,
            before_model_id=before.model_id,
            after_model_id=after.model_id,
            topology_changed=(
                before.conductive_topology_fingerprint
                != after.conductive_topology_fingerprint
            ),
            messages=(
                OperationalMessage(
                    "terminal_set_changed",
                    "operational delta v1 requires identical canonical terminal sets",
                ),
            ),
        )

    changes: list[TerminalOperationalDelta] = []
    for element_id, terminal_id in sorted(before_by_key):
        old = before_by_key[(element_id, terminal_id)]
        new = after_by_key[(element_id, terminal_id)]
        if old.energized == new.energized and old.sources == new.sources:
            continue
        changes.append(
            TerminalOperationalDelta(
                element_id=element_id,
                terminal_id=terminal_id,
                before_energized=old.energized,
                after_energized=new.energized,
                before_sources=old.sources,
                after_sources=new.sources,
            )
        )

    return OperationalDelta(
        status=OperationalStatus.SUCCESS,
        before_model_id=before.model_id,
        after_model_id=after.model_id,
        topology_changed=(
            before.conductive_topology_fingerprint
            != after.conductive_topology_fingerprint
        ),
        terminal_changes=tuple(changes),
    )
