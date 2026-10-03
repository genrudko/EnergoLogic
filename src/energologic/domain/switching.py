from __future__ import annotations

from dataclasses import dataclass

from energologic.core.model import CanonicalModel, Element
from energologic.core.validation import ValidationIssue

from .electrical import validate_electrical_model


SWITCHING_STATE_V1_NAME = "switching-state-v1"

SWITCHING_KINDS = frozenset({"circuit_breaker", "disconnector"})
SWITCH_STATES = frozenset({"open", "closed"})
MOUNTING_TYPES = frozenset({"fixed", "withdrawable"})
WITHDRAWABLE_POSITIONS = frozenset({"working", "repair", "control"})


class SwitchingStateError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True, slots=True)
class SwitchingState:
    switch_state: str
    mounting_type: str
    withdrawable_position: str | None


def _path_value(value: str) -> str:
    return value.replace("\", "\\").replace("'", "\'")


def _element_path(element_id: str) -> str:
    return f"/elements[id='{_path_value(element_id)}']"


def read_switching_state(element: Element) -> SwitchingState:
    if element.kind not in SWITCHING_KINDS:
        raise SwitchingStateError(
            "unsupported_switching_kind",
            f"element {element.id} kind {element.kind!r} is not switching-state-v1 switchgear",
        )

    raw_state = element.attributes.get("switch_state")
    if raw_state not in SWITCH_STATES:
        raise SwitchingStateError(
            "invalid_switch_state",
            (
                f"element {element.id} requires switch_state in "
                f"{sorted(SWITCH_STATES)!r}; got {raw_state!r}"
            ),
        )

    raw_mounting = element.attributes.get("mounting_type")
    if raw_mounting not in MOUNTING_TYPES:
        raise SwitchingStateError(
            "invalid_mounting_type",
            (
                f"element {element.id} requires mounting_type in "
                f"{sorted(MOUNTING_TYPES)!r}; got {raw_mounting!r}"
            ),
        )

    raw_position = element.attributes.get("withdrawable_position")
    if raw_mounting == "withdrawable":
        if raw_position not in WITHDRAWABLE_POSITIONS:
            raise SwitchingStateError(
                "invalid_withdrawable_position",
                (
                    f"withdrawable element {element.id} requires "
                    f"withdrawable_position in {sorted(WITHDRAWABLE_POSITIONS)!r}; "
                    f"got {raw_position!r}"
                ),
            )
        position: str | None = raw_position
    else:
        if raw_position is not None:
            raise SwitchingStateError(
                "unexpected_withdrawable_position",
                (
                    f"fixed element {element.id} must not define "
                    f"withdrawable_position={raw_position!r}"
                ),
            )
        position = None

    return SwitchingState(
        switch_state=raw_state,
        mounting_type=raw_mounting,
        withdrawable_position=position,
    )


def switch_allows_primary_conduction(element: Element) -> bool:
    """Return local main-circuit conduction for one validated switching device."""

    state = read_switching_state(element)
    if state.switch_state != "closed":
        return False
    if state.mounting_type == "fixed":
        return True
    return state.withdrawable_position == "working"


def validate_switching_state_model(
    model: CanonicalModel,
) -> tuple[ValidationIssue, ...]:
    """Validate switching-state-v1 on top of electrical-v1."""

    issues: list[ValidationIssue] = list(validate_electrical_model(model))
    switching_keys = {
        "switch_state",
        "mounting_type",
        "withdrawable_position",
    }

    for element in model.elements:
        path = _element_path(element.id)
        if element.kind in SWITCHING_KINDS:
            try:
                read_switching_state(element)
            except SwitchingStateError as exc:
                attribute_name = {
                    "invalid_switch_state": "switch_state",
                    "invalid_mounting_type": "mounting_type",
                    "invalid_withdrawable_position": "withdrawable_position",
                    "unexpected_withdrawable_position": "withdrawable_position",
                }.get(exc.code)
                issue_path = (
                    f"{path}/attributes/{attribute_name}"
                    if attribute_name is not None
                    else f"{path}/attributes"
                )
                issues.append(
                    ValidationIssue(
                        exc.code,
                        issue_path,
                        str(exc).split(": ", 1)[1],
                    )
                )
            continue

        for key in sorted(switching_keys & set(element.attributes)):
            issues.append(
                ValidationIssue(
                    "unexpected_switching_attribute",
                    f"{path}/attributes/{key}",
                    (
                        f"kind '{element.kind}' must not define switching-state-v1 "
                        f"attribute '{key}'"
                    ),
                )
            )

    return tuple(sorted(set(issues)))
