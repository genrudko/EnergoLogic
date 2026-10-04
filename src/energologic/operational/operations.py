from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Callable, Iterable, TypeAlias

from energologic.core import CanonicalModel, Element, fingerprint
from energologic.domain import (
    SWITCHING_KINDS,
    SWITCH_STATES,
    WITHDRAWABLE_POSITIONS,
    read_switching_state,
)

from .contracts import (
    OperationalDelta,
    OperationalMessage,
    OperationalResult,
    OperationalStatus,
    SourceRef,
)
from .runtime import compare_operational_results, simulate_operational_state


class SwitchingOperationStatus(str, Enum):
    SUCCESS = "success"
    NO_CHANGE = "no_change"
    BLOCKED = "blocked"
    INVALID_MODEL = "invalid_model"
    INVALID_SOURCE = "invalid_source"
    INVALID_OPERATION = "invalid_operation"


class OperationalEventKind(str, Enum):
    SWITCH_STATE_CHANGED = "switch_state_changed"
    WITHDRAWABLE_POSITION_CHANGED = "withdrawable_position_changed"
    TERMINAL_ENERGIZATION_CHANGED = "terminal_energization_changed"
    TERMINAL_SOURCE_ATTRIBUTION_CHANGED = "terminal_source_attribution_changed"


@dataclass(frozen=True, slots=True)
class SwitchStateOperation:
    operation_id: str
    element_id: str
    target_state: str


@dataclass(frozen=True, slots=True)
class WithdrawablePositionOperation:
    operation_id: str
    element_id: str
    target_position: str


SwitchingOperation: TypeAlias = (
    SwitchStateOperation | WithdrawablePositionOperation
)


@dataclass(frozen=True, slots=True)
class OperationBlock:
    code: str
    message: str
    validator_id: str | None = None


@dataclass(frozen=True, slots=True)
class OperationalEvent:
    sequence: int
    operation_id: str
    kind: OperationalEventKind
    element_id: str
    terminal_id: str | None = None
    before_value: str | bool | None = None
    after_value: str | bool | None = None
    before_sources: tuple[SourceRef, ...] = ()
    after_sources: tuple[SourceRef, ...] = ()


@dataclass(frozen=True, slots=True)
class SwitchingOperationResult:
    status: SwitchingOperationStatus
    operation_id: str
    model_before_fingerprint: str | None
    model_after_fingerprint: str | None
    model_after: CanonicalModel | None
    operational_before: OperationalResult | None
    operational_after: OperationalResult | None
    operational_delta: OperationalDelta | None
    events: tuple[OperationalEvent, ...] = ()
    blocks: tuple[OperationBlock, ...] = ()
    messages: tuple[OperationalMessage, ...] = ()


OperationValidator: TypeAlias = Callable[
    [CanonicalModel, SwitchingOperation, OperationalResult],
    Iterable[OperationBlock],
]


def _operation_identity(
    operation: object,
) -> tuple[object, object]:
    return (
        getattr(operation, "operation_id", ""),
        getattr(operation, "element_id", ""),
    )


def _find_element(model: CanonicalModel, element_id: str) -> Element | None:
    return next(
        (element for element in model.elements if element.id == element_id),
        None,
    )


def _replace_element(
    model: CanonicalModel,
    replacement: Element,
) -> CanonicalModel:
    return replace(
        model,
        elements=tuple(
            replacement if element.id == replacement.id else element
            for element in model.elements
        ),
    )


def _invalid_operation_result(
    *,
    operation: SwitchingOperation,
    model: CanonicalModel,
    before: OperationalResult | None,
    code: str,
    message: str,
) -> SwitchingOperationResult:
    return SwitchingOperationResult(
        status=SwitchingOperationStatus.INVALID_OPERATION,
        operation_id=getattr(operation, "operation_id", ""),
        model_before_fingerprint=fingerprint(model),
        model_after_fingerprint=None,
        model_after=None,
        operational_before=before,
        operational_after=None,
        operational_delta=None,
        messages=(OperationalMessage(code, message, operation.element_id),),
    )


def _validate_operation_shape(
    model: CanonicalModel,
    operation: SwitchingOperation,
    before: OperationalResult,
) -> tuple[Element | None, SwitchingOperationResult | None]:
    operation_id, element_id = _operation_identity(operation)
    if not isinstance(operation_id, str) or not operation_id.strip():
        return None, _invalid_operation_result(
            operation=operation,
            model=model,
            before=before,
            code="invalid_operation_id",
            message="operation_id must be a non-empty string",
        )

    if not isinstance(element_id, str) or not element_id:
        return None, _invalid_operation_result(
            operation=operation,
            model=model,
            before=before,
            code="invalid_operation_element_id",
            message="element_id must be a non-empty string",
        )

    element = _find_element(model, element_id)
    if element is None:
        return None, _invalid_operation_result(
            operation=operation,
            model=model,
            before=before,
            code="operation_target_not_found",
            message=f"operation target does not exist: {element_id}",
        )

    if element.kind not in SWITCHING_KINDS:
        return None, _invalid_operation_result(
            operation=operation,
            model=model,
            before=before,
            code="unsupported_operation_target",
            message=(
                f"element {element_id} kind {element.kind!r} is not supported "
                "switching-state-v1 switchgear"
            ),
        )

    if isinstance(operation, SwitchStateOperation):
        if (
            not isinstance(operation.target_state, str)
            or operation.target_state not in SWITCH_STATES
        ):
            return None, _invalid_operation_result(
                operation=operation,
                model=model,
                before=before,
                code="invalid_target_switch_state",
                message=(
                    "target_state must be one of "
                    f"{sorted(SWITCH_STATES)!r}; got {operation.target_state!r}"
                ),
            )
        return element, None

    if isinstance(operation, WithdrawablePositionOperation):
        state = read_switching_state(element)
        if state.mounting_type != "withdrawable":
            return None, _invalid_operation_result(
                operation=operation,
                model=model,
                before=before,
                code="operation_requires_withdrawable_switchgear",
                message=(
                    f"element {element_id} mounting_type is "
                    f"{state.mounting_type!r}, not 'withdrawable'"
                ),
            )
        if (
            not isinstance(operation.target_position, str)
            or operation.target_position not in WITHDRAWABLE_POSITIONS
        ):
            return None, _invalid_operation_result(
                operation=operation,
                model=model,
                before=before,
                code="invalid_target_withdrawable_position",
                message=(
                    "target_position must be one of "
                    f"{sorted(WITHDRAWABLE_POSITIONS)!r}; "
                    f"got {operation.target_position!r}"
                ),
            )
        return element, None

    return None, _invalid_operation_result(
        operation=operation,
        model=model,
        before=before,
        code="unsupported_operation_type",
        message=f"unsupported operation type: {type(operation).__name__}",
    )


def _operation_is_no_change(
    element: Element,
    operation: SwitchingOperation,
) -> bool:
    state = read_switching_state(element)
    if isinstance(operation, SwitchStateOperation):
        return state.switch_state == operation.target_state
    if isinstance(operation, WithdrawablePositionOperation):
        return state.withdrawable_position == operation.target_position
    return False


def _apply_operation(
    model: CanonicalModel,
    element: Element,
    operation: SwitchingOperation,
) -> tuple[CanonicalModel, OperationalEvent]:
    attributes = dict(element.attributes)

    if isinstance(operation, SwitchStateOperation):
        before_value = attributes["switch_state"]
        attributes["switch_state"] = operation.target_state
        event_kind = OperationalEventKind.SWITCH_STATE_CHANGED
        after_value: str = operation.target_state
    elif isinstance(operation, WithdrawablePositionOperation):
        before_value = attributes["withdrawable_position"]
        attributes["withdrawable_position"] = operation.target_position
        event_kind = OperationalEventKind.WITHDRAWABLE_POSITION_CHANGED
        after_value = operation.target_position
    else:
        raise TypeError(f"unsupported operation type: {type(operation).__name__}")

    changed = replace(element, attributes=attributes)
    changed_model = _replace_element(model, changed)

    event = OperationalEvent(
        sequence=1,
        operation_id=operation.operation_id,
        kind=event_kind,
        element_id=element.id,
        before_value=before_value,
        after_value=after_value,
    )
    return changed_model, event


def _state_events(
    operation_id: str,
    delta: OperationalDelta,
    *,
    start_sequence: int,
) -> tuple[OperationalEvent, ...]:
    events: list[OperationalEvent] = []
    sequence = start_sequence

    for change in delta.terminal_changes:
        if change.before_energized != change.after_energized:
            events.append(
                OperationalEvent(
                    sequence=sequence,
                    operation_id=operation_id,
                    kind=OperationalEventKind.TERMINAL_ENERGIZATION_CHANGED,
                    element_id=change.element_id,
                    terminal_id=change.terminal_id,
                    before_value=change.before_energized,
                    after_value=change.after_energized,
                    before_sources=change.before_sources,
                    after_sources=change.after_sources,
                )
            )
            sequence += 1

        if change.before_sources != change.after_sources:
            events.append(
                OperationalEvent(
                    sequence=sequence,
                    operation_id=operation_id,
                    kind=(
                        OperationalEventKind
                        .TERMINAL_SOURCE_ATTRIBUTION_CHANGED
                    ),
                    element_id=change.element_id,
                    terminal_id=change.terminal_id,
                    before_sources=change.before_sources,
                    after_sources=change.after_sources,
                )
            )
            sequence += 1

    return tuple(events)


def _run_validators(
    model: CanonicalModel,
    operation: SwitchingOperation,
    before: OperationalResult,
    validators: Iterable[OperationValidator],
) -> tuple[OperationBlock, ...]:
    blocks: list[OperationBlock] = []

    for validator in validators:
        try:
            produced = tuple(validator(model, operation, before))
        except Exception:
            # Validation is a safety gate. A failed validator must fail closed,
            # and raw exception details are not part of the public contract.
            blocks.append(
                OperationBlock(
                    code="validator_failure",
                    message="operation validator failed closed",
                    validator_id=getattr(validator, "__name__", None),
                )
            )
            continue

        for block in produced:
            if not isinstance(block, OperationBlock):
                blocks.append(
                    OperationBlock(
                        code="invalid_validator_result",
                        message="operation validator returned an invalid result",
                        validator_id=getattr(validator, "__name__", None),
                    )
                )
                continue
            blocks.append(block)

    return tuple(blocks)


def execute_switching_operation(
    model: CanonicalModel,
    sources: Iterable[SourceRef],
    operation: SwitchingOperation,
    *,
    validators: Iterable[OperationValidator] = (),
) -> SwitchingOperationResult:
    """Apply one deterministic commutation operation.

    This function provides a validation hook but intentionally contains no
    site-specific, normative or equipment-blocking rules in this work item.
    """

    before = simulate_operational_state(model, sources)
    if before.status is not OperationalStatus.SUCCESS:
        status = (
            SwitchingOperationStatus.INVALID_SOURCE
            if before.status is OperationalStatus.INVALID_SOURCE
            else SwitchingOperationStatus.INVALID_MODEL
        )
        return SwitchingOperationResult(
            status=status,
            operation_id=getattr(operation, "operation_id", ""),
            model_before_fingerprint=before.model_fingerprint,
            model_after_fingerprint=None,
            model_after=None,
            operational_before=before,
            operational_after=None,
            operational_delta=None,
            messages=before.messages,
        )

    element, invalid = _validate_operation_shape(model, operation, before)
    if invalid is not None:
        return invalid
    assert element is not None

    if _operation_is_no_change(element, operation):
        delta = compare_operational_results(before, before)
        return SwitchingOperationResult(
            status=SwitchingOperationStatus.NO_CHANGE,
            operation_id=operation.operation_id,
            model_before_fingerprint=before.model_fingerprint,
            model_after_fingerprint=before.model_fingerprint,
            model_after=model,
            operational_before=before,
            operational_after=before,
            operational_delta=delta,
        )

    blocks = _run_validators(model, operation, before, validators)
    if blocks:
        return SwitchingOperationResult(
            status=SwitchingOperationStatus.BLOCKED,
            operation_id=operation.operation_id,
            model_before_fingerprint=before.model_fingerprint,
            model_after_fingerprint=before.model_fingerprint,
            model_after=model,
            operational_before=before,
            operational_after=before,
            operational_delta=compare_operational_results(before, before),
            blocks=blocks,
        )

    changed_model, operation_event = _apply_operation(
        model,
        element,
        operation,
    )
    after = simulate_operational_state(changed_model, sources)
    if after.status is not OperationalStatus.SUCCESS:
        return SwitchingOperationResult(
            status=SwitchingOperationStatus.INVALID_MODEL,
            operation_id=operation.operation_id,
            model_before_fingerprint=before.model_fingerprint,
            model_after_fingerprint=after.model_fingerprint,
            model_after=None,
            operational_before=before,
            operational_after=after,
            operational_delta=None,
            messages=after.messages,
        )

    delta = compare_operational_results(before, after)
    if delta.status is not OperationalStatus.SUCCESS:
        return SwitchingOperationResult(
            status=SwitchingOperationStatus.INVALID_OPERATION,
            operation_id=operation.operation_id,
            model_before_fingerprint=before.model_fingerprint,
            model_after_fingerprint=after.model_fingerprint,
            model_after=None,
            operational_before=before,
            operational_after=after,
            operational_delta=delta,
            messages=delta.messages,
        )

    state_events = _state_events(
        operation.operation_id,
        delta,
        start_sequence=2,
    )
    events = (operation_event, *state_events)

    return SwitchingOperationResult(
        status=SwitchingOperationStatus.SUCCESS,
        operation_id=operation.operation_id,
        model_before_fingerprint=before.model_fingerprint,
        model_after_fingerprint=after.model_fingerprint,
        model_after=changed_model,
        operational_before=before,
        operational_after=after,
        operational_delta=delta,
        events=events,
    )
