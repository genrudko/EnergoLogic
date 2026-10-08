"""Strict read-verify-act-read projection to a live VTD/GOST Visio breaker.

This adapter has no dependency on MCP, COM, subprocesses or Windows runtime.
Its gateway must invoke only authorized Visio tools on a bound document. A live
Visio state change is NOT a physical electrical switching operation.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import PureWindowsPath
from typing import Any, Mapping, Protocol, Sequence

from energologic.core import fingerprint
from energologic.domain import read_switching_state
from energologic.operational import OperationalEventKind, SwitchingOperationStatus

from .protection_loop import IntegratedLoopResult, IntegratedLoopStatus


VTD_BREAKER_MASTER = "Выкатная тележка выключателя"
VTD_ACTION_NAME = "Row_1"


class LiveProjectionStatus(str, Enum):
    APPLIED = "applied"
    ALREADY_OPEN = "already_open"
    BLOCKED = "blocked"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True, slots=True)
class LiveVisioBinding:
    """Explicit, separately verified test-time mapping, NOT guessed from text."""

    element_id: str
    page_name: str
    shape_id: int
    document_name: str
    document_full_path: str
    expected_master_name: str
    source_ref: str


@dataclass(frozen=True, slots=True)
class LiveProjectionOutcome:
    status: LiveProjectionStatus
    code: str
    element_id: str | None = None
    shape_id: int | None = None
    before_state: str | None = None
    observed_after_state: str | None = None
    action_attempted: bool = False


class VtdVisioGateway(Protocol):
    """Decoded Visio MCP responses; methods must address exact document/page."""

    def list_open_documents(self) -> Sequence[Mapping[str, Any]]: ...

    def list_pages(self, document_name: str) -> Sequence[Mapping[str, Any]]: ...

    def inspect_shape_state_model(
        self, document_name: str, page_name: str, shape_id: int,
    ) -> Mapping[str, Any]: ...

    def get_vtd_state(
        self, document_name: str, page_name: str, shape_id: int,
    ) -> Mapping[str, Any]: ...

    def trigger_shape_action(
        self, document_name: str, page_name: str, shape_id: int,
        action_name: str,
    ) -> Any: ...


class _ProjectionRejected(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _windows_path(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _ProjectionRejected("invalid_visio_document_identity")
    path = PureWindowsPath(value)
    if not path.is_absolute() or path.suffix.casefold() != ".vsdm":
        raise _ProjectionRejected("invalid_visio_document_identity")
    return str(path).casefold()


def _shape_native_state(raw: Mapping[str, Any]) -> str:
    """The menu offers the *next action*; TRUE means CLOSED (ADR 0005)."""

    if not isinstance(raw, Mapping):
        raise _ProjectionRejected("unqualified_native_vtd_state")
    try:
        action = raw["main_action"]
        if action["name_u"] != VTD_ACTION_NAME:
            raise KeyError("action")
        current = action["action"]["result_str_u"]
        next_action = action["menu"]["result_str_u"]
        enabled = action["disabled"]["result_str_u"]
        hidden = action["invisible"]["result_str_u"]
        position = raw["cart_position"]
    except (KeyError, TypeError):
        raise _ProjectionRejected("unqualified_native_vtd_state") from None
    if enabled not in ("0", "FALSE") or hidden not in ("0", "FALSE"):
        raise _ProjectionRejected("native_action_not_available")
    if position != "рабочее":
        raise _ProjectionRejected("native_breaker_not_working_position")
    if current == "TRUE" and next_action == "Положение Отключено":
        return "closed"
    if current == "FALSE" and next_action == "Положение Включено":
        return "open"
    raise _ProjectionRejected("unqualified_native_vtd_state")


def _preflight(result: IntegratedLoopResult, binding: LiveVisioBinding) -> None:
    if (
        not isinstance(result, IntegratedLoopResult)
        or result.status is not IntegratedLoopStatus.COMPLETED
        or result.model_after is None
        or result.switching_result is None
        or result.switching_result.status is not SwitchingOperationStatus.SUCCESS
        or len(result.visio_updates) != 1
    ):
        raise _ProjectionRejected("no_completed_simulated_trip")
    intent = result.visio_updates[0]
    if (
        not isinstance(binding, LiveVisioBinding)
        or not binding.element_id
        or not binding.page_name
        or not binding.document_name
        or not isinstance(binding.shape_id, int)
        or isinstance(binding.shape_id, bool)
        or binding.shape_id <= 0
        or binding.expected_master_name != VTD_BREAKER_MASTER
        or not isinstance(binding.source_ref, str)
        or not binding.source_ref.strip()
        or intent.element_id != binding.element_id
        or intent.page_name != binding.page_name
        or intent.shape_id != binding.shape_id
        or intent.switch_state != "open"
    ):
        raise _ProjectionRejected("visio_binding_mismatch")
    expected_fingerprint = fingerprint(result.model_after)
    switching = result.switching_result
    if (
        intent.canonical_model_fingerprint != expected_fingerprint
        or switching.model_after_fingerprint != expected_fingerprint
        or switching.model_after is None
        or fingerprint(switching.model_after) != expected_fingerprint
        or switching.model_before_fingerprint != result.model_before_fingerprint
    ):
        raise _ProjectionRejected("stale_visio_projection")
    if (
        not switching.operation_id.startswith("protection:")
        or len([
            event for event in switching.events
            if event.kind is OperationalEventKind.SWITCH_STATE_CHANGED
            and event.element_id == binding.element_id
            and event.before_value == "closed"
            and event.after_value == "open"
            and event.operation_id == switching.operation_id
        ]) != 1
    ):
        raise _ProjectionRejected("unqualified_switch_transition")
    breaker = next((e for e in result.model_after.elements if e.id == binding.element_id), None)
    if breaker is None or breaker.kind != "circuit_breaker":
        raise _ProjectionRejected("invalid_projected_breaker")
    try:
        if read_switching_state(breaker).switch_state != "open":
            raise _ProjectionRejected("invalid_projected_breaker")
    except ValueError:
        raise _ProjectionRejected("invalid_projected_breaker") from None
    _windows_path(binding.document_full_path)


def _confirm_identity(gateway: VtdVisioGateway, binding: LiveVisioBinding) -> None:
    documents = [
        doc for doc in gateway.list_open_documents()
        if isinstance(doc, Mapping) and doc.get("name") == binding.document_name
    ]
    if len(documents) != 1 or _windows_path(documents[0].get("full_name")) != _windows_path(binding.document_full_path):
        raise _ProjectionRejected("visio_document_mismatch")
    pages = [
        page for page in gateway.list_pages(binding.document_name)
        if isinstance(page, Mapping) and page.get("name") == binding.page_name
    ]
    if len(pages) != 1:
        raise _ProjectionRejected("visio_page_mismatch")
    shape = gateway.inspect_shape_state_model(
        binding.document_name, binding.page_name, binding.shape_id,
    )
    if (
        not isinstance(shape, Mapping)
        or shape.get("shape_id") != binding.shape_id
        or shape.get("master_name") != binding.expected_master_name
    ):
        raise _ProjectionRejected("visio_master_or_shape_mismatch")


def apply_live_visio_projection(
    result: IntegratedLoopResult,
    binding: LiveVisioBinding,
    gateway: VtdVisioGateway,
    *,
    execute: bool = False,
) -> LiveProjectionOutcome:
    """Fail-closed action: explicit dry run unless execute=True.

    If a transport error happens after the one action attempt, return
    INDETERMINATE and NEVER automatically retry: the toggle may have executed.
    """

    def blocked(code: str, before: str | None = None) -> LiveProjectionOutcome:
        return LiveProjectionOutcome(
            LiveProjectionStatus.BLOCKED, code,
            element_id=getattr(binding, "element_id", None),
            shape_id=getattr(binding, "shape_id", None),
            before_state=before,
        )

    try:
        _preflight(result, binding)
        _confirm_identity(gateway, binding)
        before = _shape_native_state(
            gateway.get_vtd_state(binding.document_name, binding.page_name, binding.shape_id)
        )
    except _ProjectionRejected as exc:
        return blocked(exc.code)
    except Exception:
        return blocked("visio_read_before_failed")

    if before == "open":
        return LiveProjectionOutcome(
            LiveProjectionStatus.ALREADY_OPEN, "native_breaker_already_open",
            binding.element_id, binding.shape_id, before, before, False,
        )
    if not execute:
        return blocked("dry_run_no_mutation", before)

    # Re-check the exact addressed document, page and master immediately
    # before acting. This narrows the TOCTOU window but is not an atomic COM tx.
    try:
        _confirm_identity(gateway, binding)
        if _shape_native_state(gateway.get_vtd_state(
            binding.document_name, binding.page_name, binding.shape_id,
        )) != "closed":
            return blocked("native_state_changed_before_action", before)
    except _ProjectionRejected as exc:
        return blocked(exc.code, before)
    except Exception:
        return blocked("visio_recheck_failed", before)

    try:
        gateway.trigger_shape_action(
            binding.document_name, binding.page_name, binding.shape_id, VTD_ACTION_NAME,
        )
    except Exception:
        return LiveProjectionOutcome(
            LiveProjectionStatus.INDETERMINATE, "native_action_outcome_unknown",
            binding.element_id, binding.shape_id, before, None, True,
        )
    try:
        _confirm_identity(gateway, binding)
        after = _shape_native_state(
            gateway.get_vtd_state(binding.document_name, binding.page_name, binding.shape_id)
        )
    except Exception:
        return LiveProjectionOutcome(
            LiveProjectionStatus.INDETERMINATE, "visio_readback_failed",
            binding.element_id, binding.shape_id, before, None, True,
        )
    return LiveProjectionOutcome(
        LiveProjectionStatus.APPLIED if after == "open" else LiveProjectionStatus.INDETERMINATE,
        "native_open_confirmed" if after == "open" else "native_transition_not_confirmed",
        binding.element_id, binding.shape_id, before, after, True,
    )
