"""Fail-closed, source-attributed permission evidence for simulated switching.

This contract only validates supplied *claims*. It does not infer interlock
compliance, approve physical switching, or replace qualified site rules.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from energologic.core import CanonicalModel, fingerprint

from .contracts import OperationalResult, OperationalStatus
from .operations import (
    OperationBlock,
    OperationValidator,
    SwitchStateOperation,
    SwitchingOperation,
    WithdrawablePositionOperation,
)


class PermissionDecision(str, Enum):
    PERMITTED = "permitted"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class PermissionAssertionOutcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class PermissionAssertion:
    """One explicit external policy/interlock claim with a provenance pointer."""

    requirement_id: str
    outcome: str
    source_ref: str


@dataclass(frozen=True, slots=True)
class OperationPermissionEvidence:
    """Evidence bound to one exact canonical model and switching operation."""

    policy_id: str
    model_fingerprint: str
    operation_id: str
    element_id: str
    operation_type: str
    target_value: str
    assertions: tuple[PermissionAssertion, ...] = ()


@dataclass(frozen=True, slots=True)
class OperationPermissionResult:
    decision: PermissionDecision
    blocks: tuple[OperationBlock, ...]
    evaluated_requirements: tuple[str, ...] = ()


def _block(code: str, message: str, policy_id: str | None = None) -> OperationBlock:
    return OperationBlock(code=code, message=message, validator_id=policy_id)


def _identity(operation: SwitchingOperation) -> tuple[str, str] | None:
    if isinstance(operation, SwitchStateOperation):
        return ("switch_state", operation.target_state)
    if isinstance(operation, WithdrawablePositionOperation):
        return ("withdrawable_position", operation.target_position)
    return None


def evaluate_operation_permission(
    model: CanonicalModel,
    operation: SwitchingOperation,
    before: OperationalResult,
    evidence: OperationPermissionEvidence | None,
) -> OperationPermissionResult:
    """Check evidence deterministically; absence, conflicts and errors deny mutation.

    "PERMITTED" is a structurally valid *supplied* decision, not proof that
    a real-world electrical safety interlock or regulation has been met.
    """
    if not isinstance(evidence, OperationPermissionEvidence):
        return OperationPermissionResult(
            PermissionDecision.UNKNOWN,
            (_block("permission_evidence_missing", "permission evidence is missing"),),
        )
    policy_id = evidence.policy_id if isinstance(evidence.policy_id, str) and evidence.policy_id.strip() else None
    if policy_id is None:
        return OperationPermissionResult(
            PermissionDecision.UNKNOWN,
            (_block("permission_invalid_policy", "permission policy identifier is missing"),),
        )

    identity = _identity(operation)
    if (
        before.status is not OperationalStatus.SUCCESS
        or identity is None
        or not isinstance(evidence.model_fingerprint, str)
        or evidence.model_fingerprint != fingerprint(model)
        or before.model_fingerprint != evidence.model_fingerprint
        or evidence.operation_id != operation.operation_id
        or evidence.element_id != operation.element_id
        or evidence.operation_type != identity[0]
        or evidence.target_value != identity[1]
    ):
        return OperationPermissionResult(
            PermissionDecision.UNKNOWN,
            (_block("permission_binding_mismatch", "permission evidence does not match model and operation", policy_id),),
        )

    if not isinstance(evidence.assertions, tuple) or not evidence.assertions:
        return OperationPermissionResult(
            PermissionDecision.UNKNOWN,
            (_block("permission_requirements_missing", "no permission requirements were evaluated", policy_id),),
        )

    seen: set[str] = set()
    blocks: list[OperationBlock] = []
    outcomes: list[tuple[str, str]] = []
    for assertion in evidence.assertions:
        if (
            not isinstance(assertion, PermissionAssertion)
            or not isinstance(assertion.requirement_id, str)
            or not assertion.requirement_id.strip()
            or not isinstance(assertion.source_ref, str)
            or not assertion.source_ref.strip()
            or not isinstance(assertion.outcome, str)
            or assertion.outcome not in {member.value for member in PermissionAssertionOutcome}
        ):
            return OperationPermissionResult(
                PermissionDecision.UNKNOWN,
                (_block("permission_invalid_assertion", "permission assertion or provenance is invalid", policy_id),),
            )
        if assertion.requirement_id in seen:
            return OperationPermissionResult(
                PermissionDecision.UNKNOWN,
                (_block("permission_duplicate_requirement", "permission requirement was evaluated more than once", policy_id),),
            )
        seen.add(assertion.requirement_id)
        outcomes.append((assertion.requirement_id, assertion.outcome))

    for requirement_id, outcome in sorted(outcomes):
        if outcome == PermissionAssertionOutcome.FAIL.value:
            blocks.append(_block("permission_requirement_failed", f"permission requirement {requirement_id!r} failed", policy_id))
        elif outcome == PermissionAssertionOutcome.UNKNOWN.value:
            blocks.append(_block("permission_requirement_unknown", f"permission requirement {requirement_id!r} is unknown", policy_id))

    if blocks:
        decision = (
            PermissionDecision.BLOCKED
            if any(block.code == "permission_requirement_failed" for block in blocks)
            else PermissionDecision.UNKNOWN
        )
        return OperationPermissionResult(decision, tuple(blocks), tuple(sorted(seen)))
    return OperationPermissionResult(PermissionDecision.PERMITTED, (), tuple(sorted(seen)))


def permission_evidence_validator(
    evidence: OperationPermissionEvidence | None,
) -> OperationValidator:
    """Adapt a specific evidence snapshot to the existing pre-mutation gate."""

    def validate(
        model: CanonicalModel,
        operation: SwitchingOperation,
        before: OperationalResult,
    ) -> tuple[OperationBlock, ...]:
        return evaluate_operation_permission(model, operation, before, evidence).blocks

    validate.__name__ = "permission_evidence_validator"
    return validate
