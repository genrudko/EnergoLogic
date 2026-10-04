from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from .model import (
    ProtectionSettingCard,
    SettingAction,
    setting_card_fingerprint,
    validate_setting_card,
)
from .runtime import ProtectionOutputRequest
from .units import UnitNormalizationError, canonical_decimal, parse_decimal_source


BREAKER_FAILURE_CONCEPT_ID = "protection.breaker_failure"
BREAKER_FAILURE_CRITERION_MODES = frozenset(
    {
        "breaker_closed",
        "current_flow",
        "breaker_closed_or_current_flow",
        "breaker_closed_and_current_flow",
    }
)
BREAKER_FAILURE_START_BEHAVIORS = frozenset({"maintained", "latched"})
BREAKER_FAILURE_STATUSES = frozenset({"inactive", "timing", "operated"})
BREAKER_FAILURE_EVENT_TYPES = frozenset({"pickup", "reset", "operate"})


@dataclass(frozen=True, order=True, slots=True)
class BreakerFailureIssue:
    code: str
    path: str
    message: str


class BreakerFailureError(ValueError):
    pass


class BreakerFailureProgramValidationError(BreakerFailureError):
    def __init__(self, issues: Iterable[BreakerFailureIssue]):
        self.issues = tuple(sorted(set(issues)))
        super().__init__(
            "invalid breaker-failure program: "
            + "; ".join(f"{item.code}@{item.path}" for item in self.issues)
        )


class BreakerFailureRuntimeInputError(BreakerFailureError):
    def __init__(self, issue: BreakerFailureIssue):
        self.issue = issue
        super().__init__(f"{issue.code}@{issue.path}: {issue.message}")


@dataclass(frozen=True, slots=True)
class BreakerFailureBinding:
    binding_id: str
    function_id: str
    monitored_breaker_id: str
    criterion_mode: str
    start_behavior: str
    provenance_ref: str


@dataclass(frozen=True, slots=True)
class BreakerFailureProgram:
    program_fingerprint: str
    card_fingerprint: str
    settings_scope: str
    lifecycle_status: str
    binding: BreakerFailureBinding
    stage_id: str
    delay_s: str
    actions: tuple[SettingAction, ...]
    enabled: bool


@dataclass(frozen=True, slots=True)
class BreakerFailureSnapshot:
    snapshot_id: str
    time_s: str
    start_active: bool
    breaker_closed: bool | None = None
    current_flow_present: bool | None = None


@dataclass(frozen=True, slots=True)
class BreakerFailureRuntimeState:
    program_fingerprint: str
    last_time_s: str
    status: str
    started_at_s: str = ""
    operated_at_s: str = ""


@dataclass(frozen=True, order=True, slots=True)
class BreakerFailureEvent:
    event_type: str
    function_id: str
    stage_id: str
    monitored_breaker_id: str
    time_s: str
    criterion_mode: str
    start_active: bool
    failure_detected: bool


@dataclass(frozen=True, slots=True)
class BreakerFailureStepResult:
    snapshot_id: str
    time_s: str
    state: BreakerFailureRuntimeState
    events: tuple[BreakerFailureEvent, ...]
    requests: tuple[ProtectionOutputRequest, ...]


def _issue(code: str, path: str, message: str) -> BreakerFailureIssue:
    return BreakerFailureIssue(code, path, message)


def _canonical_time(value: str, *, path: str) -> str:
    try:
        parsed = parse_decimal_source(value)
    except UnitNormalizationError as exc:
        raise BreakerFailureRuntimeInputError(
            _issue("invalid_decimal", path, str(exc))
        ) from exc
    if parsed < 0:
        raise BreakerFailureRuntimeInputError(
            _issue(
                "negative_logical_time",
                path,
                "logical time must be >= 0",
            )
        )
    return canonical_decimal(parsed)


def make_breaker_failure_snapshot(
    *,
    snapshot_id: str,
    time_s: str,
    start_active: bool,
    breaker_closed: bool | None = None,
    current_flow_present: bool | None = None,
) -> BreakerFailureSnapshot:
    if not isinstance(snapshot_id, str) or not snapshot_id.strip():
        raise BreakerFailureRuntimeInputError(
            _issue(
                "missing_snapshot_id",
                "/snapshot_id",
                "snapshot ID is required",
            )
        )
    if not isinstance(start_active, bool):
        raise BreakerFailureRuntimeInputError(
            _issue(
                "invalid_start_active",
                "/start_active",
                "start_active must be boolean",
            )
        )
    for name, value in (
        ("breaker_closed", breaker_closed),
        ("current_flow_present", current_flow_present),
    ):
        if value is not None and not isinstance(value, bool):
            raise BreakerFailureRuntimeInputError(
                _issue(
                    f"invalid_{name}",
                    f"/{name}",
                    f"{name} must be boolean or null",
                )
            )
    return BreakerFailureSnapshot(
        snapshot_id=snapshot_id,
        time_s=_canonical_time(time_s, path="/time_s"),
        start_active=start_active,
        breaker_closed=breaker_closed,
        current_flow_present=current_flow_present,
    )


def _validate_binding(
    binding: BreakerFailureBinding,
) -> tuple[BreakerFailureIssue, ...]:
    issues: list[BreakerFailureIssue] = []
    for field_name, value in (
        ("binding_id", binding.binding_id),
        ("function_id", binding.function_id),
        ("monitored_breaker_id", binding.monitored_breaker_id),
        ("provenance_ref", binding.provenance_ref),
    ):
        if not isinstance(value, str) or not value.strip():
            issues.append(
                _issue(
                    f"missing_{field_name}",
                    f"/binding/{field_name}",
                    "non-empty text is required",
                )
            )
    if binding.criterion_mode not in BREAKER_FAILURE_CRITERION_MODES:
        issues.append(
            _issue(
                "invalid_criterion_mode",
                "/binding/criterion_mode",
                repr(binding.criterion_mode),
            )
        )
    if binding.start_behavior not in BREAKER_FAILURE_START_BEHAVIORS:
        issues.append(
            _issue(
                "invalid_start_behavior",
                "/binding/start_behavior",
                repr(binding.start_behavior),
            )
        )
    return tuple(issues)


def _program_fingerprint_payload(
    *,
    card_fingerprint: str,
    binding: BreakerFailureBinding,
    stage_id: str,
    delay_s: str,
    actions: tuple[SettingAction, ...],
    enabled: bool,
) -> dict[str, object]:
    return {
        "card_fingerprint": card_fingerprint,
        "binding": {
            "binding_id": binding.binding_id,
            "function_id": binding.function_id,
            "monitored_breaker_id": binding.monitored_breaker_id,
            "criterion_mode": binding.criterion_mode,
            "start_behavior": binding.start_behavior,
            "provenance_ref": binding.provenance_ref,
        },
        "stage_id": stage_id,
        "delay_s": delay_s,
        "enabled": enabled,
        "actions": [
            {
                "id": item.id,
                "action_type": item.action_type,
                "target_kind": item.target_kind,
                "target_id": item.target_id,
            }
            for item in sorted(actions, key=lambda value: value.id)
        ],
    }


def _make_program_fingerprint(
    *,
    card_fingerprint: str,
    binding: BreakerFailureBinding,
    stage_id: str,
    delay_s: str,
    actions: tuple[SettingAction, ...],
    enabled: bool,
) -> str:
    payload = _program_fingerprint_payload(
        card_fingerprint=card_fingerprint,
        binding=binding,
        stage_id=stage_id,
        delay_s=delay_s,
        actions=actions,
        enabled=enabled,
    )
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def compile_breaker_failure_program(
    card: ProtectionSettingCard,
    binding: BreakerFailureBinding,
    *,
    allow_incomplete_settings: bool = False,
    allow_non_authoritative_settings: bool = False,
) -> BreakerFailureProgram:
    issues: list[BreakerFailureIssue] = list(_validate_binding(binding))

    base_issues = validate_setting_card(card)
    for item in base_issues:
        issues.append(
            _issue(
                "invalid_setting_card",
                item.path,
                f"{item.code}: {item.message}",
            )
        )

    if (
        card.settings_scope != "full_configuration"
        and not allow_incomplete_settings
    ):
        issues.append(
            _issue(
                "incomplete_settings_scope",
                "/settings_scope",
                (
                    "breaker-failure execution requires full_configuration; "
                    "override only for explicit engineering/synthetic work"
                ),
            )
        )

    if (
        card.lifecycle_status not in {"approved", "implemented"}
        and not allow_non_authoritative_settings
    ):
        issues.append(
            _issue(
                "non_authoritative_settings",
                "/lifecycle_status",
                (
                    "breaker-failure execution requires approved or "
                    "implemented settings"
                ),
            )
        )

    functions = [item for item in card.functions if item.id == binding.function_id]
    if len(functions) != 1:
        issues.append(
            _issue(
                "unknown_breaker_failure_function",
                "/binding/function_id",
                binding.function_id,
            )
        )
        if issues:
            raise BreakerFailureProgramValidationError(issues)
        raise AssertionError("unreachable")

    function = functions[0]
    function_path = f"/functions/{function.id}"

    if function.concept_id != BREAKER_FAILURE_CONCEPT_ID:
        issues.append(
            _issue(
                "wrong_function_concept",
                f"{function_path}/concept_id",
                (
                    f"expected {BREAKER_FAILURE_CONCEPT_ID!r}, got "
                    f"{function.concept_id!r}"
                ),
            )
        )

    if function.enabled is None:
        issues.append(
            _issue(
                "indeterminate_function_enabled",
                f"{function_path}/enabled",
                "breaker-failure enabled state must be explicit",
            )
        )

    if function.parameters:
        issues.append(
            _issue(
                "function_parameters_unsupported",
                f"{function_path}/parameters",
                "breaker-failure foundation requires stage-scoped settings",
            )
        )

    if function.measurement_input_ids:
        issues.append(
            _issue(
                "measurement_inputs_unsupported",
                f"{function_path}/measurement_input_ids",
                (
                    "foundation consumes qualified boolean current-flow "
                    "feedback rather than inventing a current threshold"
                ),
            )
        )

    if function.actions:
        issues.append(
            _issue(
                "function_actions_unsupported",
                f"{function_path}/actions",
                "backup actions must be stage-scoped in this foundation",
            )
        )

    if len(function.stages) != 1:
        issues.append(
            _issue(
                "unsupported_stage_count",
                f"{function_path}/stages",
                (
                    "foundation supports exactly one breaker-failure stage; "
                    "multi-stage vendor logic requires a later contract"
                ),
            )
        )
        stage = None
    else:
        stage = function.stages[0]

    enabled = bool(function.enabled)
    stage_id = ""
    delay_s = "0"
    actions: tuple[SettingAction, ...] = ()

    if stage is not None:
        stage_id = stage.id
        stage_path = f"{function_path}/stages/{stage.id}"

        if stage.enabled is None:
            issues.append(
                _issue(
                    "indeterminate_stage_enabled",
                    f"{stage_path}/enabled",
                    "breaker-failure stage enabled state must be explicit",
                )
            )
        enabled = enabled and bool(stage.enabled)

        delays = [item for item in stage.parameters if item.role == "delay"]
        unsupported_parameters = [
            item for item in stage.parameters if item.role != "delay"
        ]
        if unsupported_parameters:
            issues.append(
                _issue(
                    "unsupported_stage_parameter",
                    f"{stage_path}/parameters",
                    (
                        "foundation accepts only explicit breaker-failure "
                        "delay; current thresholds/vendor logic are deferred"
                    ),
                )
            )

        if len(delays) != 1:
            issues.append(
                _issue(
                    "invalid_delay_parameter_count",
                    f"{stage_path}/parameters",
                    f"expected one delay parameter, found {len(delays)}",
                )
            )
        else:
            delay = delays[0]
            value = delay.value
            if delay.semantic_key != "breaker_failure_delay":
                issues.append(
                    _issue(
                        "delay_semantic_mismatch",
                        f"{stage_path}/parameters/{delay.id}/semantic_key",
                        (
                            "expected semantic_key='breaker_failure_delay'"
                        ),
                    )
                )
            if value.kind != "quantity":
                issues.append(
                    _issue(
                        "invalid_delay_value_kind",
                        f"{stage_path}/parameters/{delay.id}/value",
                        "breaker-failure delay must be a quantity",
                    )
                )
            elif (
                value.quantity_kind != "time"
                or value.normalized_unit != "s"
                or value.basis != "not_applicable"
            ):
                issues.append(
                    _issue(
                        "invalid_delay_quantity",
                        f"{stage_path}/parameters/{delay.id}/value",
                        (
                            "breaker-failure delay must be normalized "
                            "time in seconds with basis not_applicable"
                        ),
                    )
                )
            else:
                try:
                    parsed_delay = parse_decimal_source(
                        value.normalized_value
                    )
                except UnitNormalizationError as exc:
                    issues.append(
                        _issue(
                            "invalid_delay_value",
                            f"{stage_path}/parameters/{delay.id}/value",
                            str(exc),
                        )
                    )
                else:
                    if parsed_delay < 0:
                        issues.append(
                            _issue(
                                "negative_delay",
                                f"{stage_path}/parameters/{delay.id}/value",
                                "breaker-failure delay must be >= 0",
                            )
                        )
                    delay_s = canonical_decimal(parsed_delay)

        actions = tuple(sorted(stage.actions, key=lambda item: item.id))
        if enabled and not actions:
            issues.append(
                _issue(
                    "missing_backup_actions",
                    f"{stage_path}/actions",
                    (
                        "enabled breaker-failure stage requires at least "
                        "one explicit backup trip action"
                    ),
                )
            )

        for index, action in enumerate(actions):
            path = f"{stage_path}/actions/{index}"
            if action.action_type != "trip":
                issues.append(
                    _issue(
                        "unsupported_backup_action_type",
                        f"{path}/action_type",
                        (
                            "foundation qualifies breaker-failure backup "
                            "tripping only"
                        ),
                    )
                )
            if action.target_kind != "equipment":
                issues.append(
                    _issue(
                        "unsupported_backup_target_kind",
                        f"{path}/target_kind",
                        "backup trip target must be equipment",
                    )
                )
            if action.target_id == binding.monitored_breaker_id:
                issues.append(
                    _issue(
                        "retrip_unsupported",
                        f"{path}/target_id",
                        (
                            "foundation models tripping other breakers; "
                            "retrip of the failed breaker is deferred"
                        ),
                    )
                )

    if issues:
        raise BreakerFailureProgramValidationError(issues)

    card_fp = setting_card_fingerprint(card)
    program_fp = _make_program_fingerprint(
        card_fingerprint=card_fp,
        binding=binding,
        stage_id=stage_id,
        delay_s=delay_s,
        actions=actions,
        enabled=enabled,
    )
    return BreakerFailureProgram(
        program_fingerprint=program_fp,
        card_fingerprint=card_fp,
        settings_scope=card.settings_scope,
        lifecycle_status=card.lifecycle_status,
        binding=binding,
        stage_id=stage_id,
        delay_s=delay_s,
        actions=actions,
        enabled=enabled,
    )


def initial_breaker_failure_state(
    program: BreakerFailureProgram,
) -> BreakerFailureRuntimeState:
    return BreakerFailureRuntimeState(
        program_fingerprint=program.program_fingerprint,
        last_time_s="",
        status="inactive",
    )


def _parse_state_time(
    value: str,
    *,
    path: str,
    allow_empty: bool,
) -> Decimal | None:
    if allow_empty and value == "":
        return None
    try:
        parsed = parse_decimal_source(value)
    except UnitNormalizationError as exc:
        raise BreakerFailureRuntimeInputError(
            _issue("invalid_state_time", path, str(exc))
        ) from exc
    if parsed < 0:
        raise BreakerFailureRuntimeInputError(
            _issue(
                "negative_state_time",
                path,
                "state logical time must be >= 0",
            )
        )
    if canonical_decimal(parsed) != value:
        raise BreakerFailureRuntimeInputError(
            _issue(
                "noncanonical_state_time",
                path,
                f"expected {canonical_decimal(parsed)!r}",
            )
        )
    return parsed


def _validate_state(
    program: BreakerFailureProgram,
    state: BreakerFailureRuntimeState,
) -> None:
    if state.program_fingerprint != program.program_fingerprint:
        raise BreakerFailureRuntimeInputError(
            _issue(
                "state_program_mismatch",
                "/state/program_fingerprint",
                "state belongs to a different breaker-failure program",
            )
        )
    if state.status not in BREAKER_FAILURE_STATUSES:
        raise BreakerFailureRuntimeInputError(
            _issue(
                "invalid_state_status",
                "/state/status",
                repr(state.status),
            )
        )

    last_time = _parse_state_time(
        state.last_time_s,
        path="/state/last_time_s",
        allow_empty=True,
    )
    started_at = _parse_state_time(
        state.started_at_s,
        path="/state/started_at_s",
        allow_empty=True,
    )
    operated_at = _parse_state_time(
        state.operated_at_s,
        path="/state/operated_at_s",
        allow_empty=True,
    )

    if state.status == "inactive":
        if started_at is not None or operated_at is not None:
            raise BreakerFailureRuntimeInputError(
                _issue(
                    "invalid_inactive_state",
                    "/state",
                    (
                        "inactive state must not retain start/operate "
                        "timestamps"
                    ),
                )
            )
    elif state.status == "timing":
        if started_at is None or operated_at is not None:
            raise BreakerFailureRuntimeInputError(
                _issue(
                    "invalid_timing_state",
                    "/state",
                    (
                        "timing state requires started_at_s and no "
                        "operated_at_s"
                    ),
                )
            )
        if last_time is None:
            raise BreakerFailureRuntimeInputError(
                _issue(
                    "missing_last_time",
                    "/state/last_time_s",
                    "active restored state requires last_time_s",
                )
            )
    elif state.status == "operated":
        if started_at is None or operated_at is None:
            raise BreakerFailureRuntimeInputError(
                _issue(
                    "invalid_operated_state",
                    "/state",
                    (
                        "operated state requires start and operate "
                        "timestamps"
                    ),
                )
            )
        if operated_at < started_at:
            raise BreakerFailureRuntimeInputError(
                _issue(
                    "invalid_operated_time_order",
                    "/state",
                    "operated_at_s precedes started_at_s",
                )
            )
        if last_time is None:
            raise BreakerFailureRuntimeInputError(
                _issue(
                    "missing_last_time",
                    "/state/last_time_s",
                    "active restored state requires last_time_s",
                )
            )

    if last_time is not None:
        for path, timestamp in (
            ("/state/started_at_s", started_at),
            ("/state/operated_at_s", operated_at),
        ):
            if timestamp is not None and timestamp > last_time:
                raise BreakerFailureRuntimeInputError(
                    _issue(
                        "state_timestamp_after_last_time",
                        path,
                        "state timestamp is after last_time_s",
                    )
                )


def _failure_criterion(
    binding: BreakerFailureBinding,
    snapshot: BreakerFailureSnapshot,
) -> bool:
    mode = binding.criterion_mode

    if mode in {
        "breaker_closed",
        "breaker_closed_or_current_flow",
        "breaker_closed_and_current_flow",
    } and snapshot.breaker_closed is None:
        raise BreakerFailureRuntimeInputError(
            _issue(
                "missing_breaker_closed_feedback",
                "/snapshot/breaker_closed",
                f"criterion mode {mode!r} requires breaker feedback",
            )
        )

    if mode in {
        "current_flow",
        "breaker_closed_or_current_flow",
        "breaker_closed_and_current_flow",
    } and snapshot.current_flow_present is None:
        raise BreakerFailureRuntimeInputError(
            _issue(
                "missing_current_flow_feedback",
                "/snapshot/current_flow_present",
                f"criterion mode {mode!r} requires current-flow feedback",
            )
        )

    if mode == "breaker_closed":
        return bool(snapshot.breaker_closed)
    if mode == "current_flow":
        return bool(snapshot.current_flow_present)
    if mode == "breaker_closed_or_current_flow":
        return bool(snapshot.breaker_closed) or bool(
            snapshot.current_flow_present
        )
    if mode == "breaker_closed_and_current_flow":
        return bool(snapshot.breaker_closed) and bool(
            snapshot.current_flow_present
        )
    raise AssertionError(mode)


def _request_id(
    *,
    program: BreakerFailureProgram,
    snapshot: BreakerFailureSnapshot,
    action: SettingAction,
) -> str:
    payload = {
        "program_fingerprint": program.program_fingerprint,
        "snapshot_id": snapshot.snapshot_id,
        "time_s": snapshot.time_s,
        "function_id": program.binding.function_id,
        "stage_id": program.stage_id,
        "action_id": action.id,
        "action_type": action.action_type,
        "target_kind": action.target_kind,
        "target_id": action.target_id,
    }
    digest = hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return f"breaker-failure-request:{digest[:32]}"


def evaluate_breaker_failure_step(
    program: BreakerFailureProgram,
    snapshot: BreakerFailureSnapshot,
    *,
    state: BreakerFailureRuntimeState | None = None,
) -> BreakerFailureStepResult:
    if not isinstance(snapshot.snapshot_id, str) or not snapshot.snapshot_id.strip():
        raise BreakerFailureRuntimeInputError(
            _issue(
                "missing_snapshot_id",
                "/snapshot/snapshot_id",
                "snapshot ID is required",
            )
        )

    canonical_time = _canonical_time(
        snapshot.time_s,
        path="/snapshot/time_s",
    )
    if canonical_time != snapshot.time_s:
        raise BreakerFailureRuntimeInputError(
            _issue(
                "noncanonical_snapshot_time",
                "/snapshot/time_s",
                f"expected {canonical_time!r}",
            )
        )

    if state is None:
        state = initial_breaker_failure_state(program)
    _validate_state(program, state)

    now = parse_decimal_source(snapshot.time_s)
    if state.last_time_s:
        prior_time = parse_decimal_source(state.last_time_s)
        if now < prior_time:
            raise BreakerFailureRuntimeInputError(
                _issue(
                    "logical_time_reversal",
                    "/snapshot/time_s",
                    f"{snapshot.time_s} < prior {state.last_time_s}",
                )
            )

    if not program.enabled:
        return BreakerFailureStepResult(
            snapshot_id=snapshot.snapshot_id,
            time_s=snapshot.time_s,
            state=BreakerFailureRuntimeState(
                program_fingerprint=program.program_fingerprint,
                last_time_s=snapshot.time_s,
                status="inactive",
            ),
            events=(),
            requests=(),
        )

    events: list[BreakerFailureEvent] = []
    requests: list[ProtectionOutputRequest] = []

    def add_event(event_type: str, failure_detected: bool) -> None:
        events.append(
            BreakerFailureEvent(
                event_type=event_type,
                function_id=program.binding.function_id,
                stage_id=program.stage_id,
                monitored_breaker_id=program.binding.monitored_breaker_id,
                time_s=snapshot.time_s,
                criterion_mode=program.binding.criterion_mode,
                start_active=snapshot.start_active,
                failure_detected=failure_detected,
            )
        )

    def operate(started_at_s: str) -> BreakerFailureRuntimeState:
        add_event("operate", True)
        for action in program.actions:
            requests.append(
                ProtectionOutputRequest(
                    request_id=_request_id(
                        program=program,
                        snapshot=snapshot,
                        action=action,
                    ),
                    function_id=program.binding.function_id,
                    stage_id=program.stage_id,
                    action_id=action.id,
                    action_type=action.action_type,
                    target_kind=action.target_kind,
                    target_id=action.target_id,
                    time_s=snapshot.time_s,
                    cause="breaker_failure_operated",
                )
            )
        return BreakerFailureRuntimeState(
            program_fingerprint=program.program_fingerprint,
            last_time_s=snapshot.time_s,
            status="operated",
            started_at_s=started_at_s,
            operated_at_s=snapshot.time_s,
        )

    delay = parse_decimal_source(program.delay_s)

    if state.status == "inactive":
        if not snapshot.start_active:
            next_state = BreakerFailureRuntimeState(
                program_fingerprint=program.program_fingerprint,
                last_time_s=snapshot.time_s,
                status="inactive",
            )
        else:
            failure_detected = _failure_criterion(
                program.binding,
                snapshot,
            )
            if not failure_detected:
                next_state = BreakerFailureRuntimeState(
                    program_fingerprint=program.program_fingerprint,
                    last_time_s=snapshot.time_s,
                    status="inactive",
                )
            else:
                add_event("pickup", True)
                if delay == 0:
                    next_state = operate(snapshot.time_s)
                else:
                    next_state = BreakerFailureRuntimeState(
                        program_fingerprint=program.program_fingerprint,
                        last_time_s=snapshot.time_s,
                        status="timing",
                        started_at_s=snapshot.time_s,
                    )

    elif state.status == "timing":
        if (
            program.binding.start_behavior == "maintained"
            and not snapshot.start_active
        ):
            add_event("reset", False)
            next_state = BreakerFailureRuntimeState(
                program_fingerprint=program.program_fingerprint,
                last_time_s=snapshot.time_s,
                status="inactive",
            )
        else:
            failure_detected = _failure_criterion(
                program.binding,
                snapshot,
            )
            if not failure_detected:
                add_event("reset", False)
                next_state = BreakerFailureRuntimeState(
                    program_fingerprint=program.program_fingerprint,
                    last_time_s=snapshot.time_s,
                    status="inactive",
                )
            else:
                started_at = parse_decimal_source(state.started_at_s)
                if now - started_at >= delay:
                    next_state = operate(state.started_at_s)
                else:
                    next_state = BreakerFailureRuntimeState(
                        program_fingerprint=program.program_fingerprint,
                        last_time_s=snapshot.time_s,
                        status="timing",
                        started_at_s=state.started_at_s,
                    )

    elif state.status == "operated":
        failure_detected = _failure_criterion(
            program.binding,
            snapshot,
        )
        if failure_detected:
            next_state = BreakerFailureRuntimeState(
                program_fingerprint=program.program_fingerprint,
                last_time_s=snapshot.time_s,
                status="operated",
                started_at_s=state.started_at_s,
                operated_at_s=state.operated_at_s,
            )
        else:
            add_event("reset", False)
            next_state = BreakerFailureRuntimeState(
                program_fingerprint=program.program_fingerprint,
                last_time_s=snapshot.time_s,
                status="inactive",
            )

    else:
        raise AssertionError(state.status)

    return BreakerFailureStepResult(
        snapshot_id=snapshot.snapshot_id,
        time_s=snapshot.time_s,
        state=next_state,
        events=tuple(events),
        requests=tuple(sorted(requests)),
    )


def breaker_failure_result_fingerprint(
    result: BreakerFailureStepResult,
) -> str:
    payload = {
        "snapshot_id": result.snapshot_id,
        "time_s": result.time_s,
        "state": {
            "program_fingerprint": result.state.program_fingerprint,
            "last_time_s": result.state.last_time_s,
            "status": result.state.status,
            "started_at_s": result.state.started_at_s,
            "operated_at_s": result.state.operated_at_s,
        },
        "events": [
            {
                "event_type": item.event_type,
                "function_id": item.function_id,
                "stage_id": item.stage_id,
                "monitored_breaker_id": item.monitored_breaker_id,
                "time_s": item.time_s,
                "criterion_mode": item.criterion_mode,
                "start_active": item.start_active,
                "failure_detected": item.failure_detected,
            }
            for item in result.events
        ],
        "requests": [
            {
                "request_id": item.request_id,
                "function_id": item.function_id,
                "stage_id": item.stage_id,
                "action_id": item.action_id,
                "action_type": item.action_type,
                "target_kind": item.target_kind,
                "target_id": item.target_id,
                "time_s": item.time_s,
                "cause": item.cause,
            }
            for item in result.requests
        ],
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
