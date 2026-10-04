from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Sequence

from .model import (
    ProtectionFunctionSettings,
    ProtectionSettingCard,
    ProtectionStage,
    SettingAction,
    SettingParameter,
    setting_card_fingerprint,
    validate_setting_card,
)
from .runtime import ProtectionOutputRequest
from .units import UnitNormalizationError, canonical_decimal, parse_decimal_source


BREAKER_FAILURE_CONCEPT_ID = "protection.breaker_failure"
BREAKER_FAILURE_STATUSES = frozenset(
    {"idle", "timing", "operated", "waiting_start_clear"}
)
BREAKER_FAILURE_EVENT_TYPES = frozenset({"start", "reset", "operate"})


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
    function_id: str
    monitored_breaker_id: str
    start_signal_id: str
    breaker_open_signal_id: str


@dataclass(frozen=True, slots=True)
class BinarySignal:
    signal_id: str
    value: bool


@dataclass(frozen=True, slots=True)
class BreakerFailureSnapshot:
    snapshot_id: str
    time_s: str
    signals: tuple[BinarySignal, ...]


@dataclass(frozen=True, slots=True)
class BreakerFailureDefinition:
    function_id: str
    stage_id: str
    monitored_breaker_id: str
    start_signal_id: str
    breaker_open_signal_id: str
    delay_s: str
    actions: tuple[SettingAction, ...]


@dataclass(frozen=True, slots=True)
class BreakerFailureProgram:
    card_fingerprint: str
    program_fingerprint: str
    settings_scope: str
    lifecycle_status: str
    definitions: tuple[BreakerFailureDefinition, ...]


@dataclass(frozen=True, slots=True)
class BreakerFailureStageState:
    function_id: str
    stage_id: str
    status: str
    timing_started_at_s: str = ""
    operated_at_s: str = ""


@dataclass(frozen=True, slots=True)
class BreakerFailureRuntimeState:
    program_fingerprint: str
    last_time_s: str
    stages: tuple[BreakerFailureStageState, ...]


@dataclass(frozen=True, order=True, slots=True)
class BreakerFailureEvent:
    event_type: str
    function_id: str
    stage_id: str
    monitored_breaker_id: str
    time_s: str
    cause: str


@dataclass(frozen=True, slots=True)
class BreakerFailureStepResult:
    snapshot_id: str
    time_s: str
    state: BreakerFailureRuntimeState
    events: tuple[BreakerFailureEvent, ...]
    requests: tuple[ProtectionOutputRequest, ...]


def _issue(code: str, path: str, message: str) -> BreakerFailureIssue:
    return BreakerFailureIssue(code, path, message)


def _canonical_number(value: str, *, path: str) -> str:
    try:
        parsed = parse_decimal_source(value)
    except UnitNormalizationError as exc:
        raise BreakerFailureRuntimeInputError(
            _issue("invalid_decimal", path, str(exc))
        ) from exc
    return canonical_decimal(parsed)


def make_binary_signal(signal_id: str, value: bool) -> BinarySignal:
    if not isinstance(signal_id, str) or not signal_id.strip():
        raise BreakerFailureRuntimeInputError(
            _issue("missing_signal_id", "/signal_id", "signal ID is required")
        )
    if not isinstance(value, bool):
        raise BreakerFailureRuntimeInputError(
            _issue(
                "invalid_signal_value",
                f"/signals/{signal_id}",
                "binary signal value must be bool",
            )
        )
    return BinarySignal(signal_id=signal_id, value=value)


def make_breaker_failure_snapshot(
    *,
    snapshot_id: str,
    time_s: str,
    signals: Sequence[BinarySignal],
) -> BreakerFailureSnapshot:
    if not isinstance(snapshot_id, str) or not snapshot_id.strip():
        raise BreakerFailureRuntimeInputError(
            _issue(
                "missing_snapshot_id",
                "/snapshot_id",
                "snapshot ID is required",
            )
        )
    canonical_time = _canonical_number(time_s, path="/time_s")
    if Decimal(canonical_time) < 0:
        raise BreakerFailureRuntimeInputError(
            _issue(
                "negative_logical_time",
                "/time_s",
                "logical time must be >= 0",
            )
        )
    return BreakerFailureSnapshot(
        snapshot_id=snapshot_id,
        time_s=canonical_time,
        signals=tuple(signals),
    )


def _delay_parameter(
    stage: ProtectionStage,
    *,
    path: str,
    issues: list[BreakerFailureIssue],
) -> SettingParameter | None:
    matches = [item for item in stage.parameters if item.role == "delay"]
    if len(matches) != 1:
        issues.append(
            _issue(
                "invalid_delay_parameter_count",
                path,
                f"expected exactly one delay parameter, found {len(matches)}",
            )
        )
        return None
    parameter = matches[0]
    if parameter.semantic_key != "breaker_failure_delay":
        issues.append(
            _issue(
                "delay_semantic_mismatch",
                f"{path}/{parameter.id}/semantic_key",
                "expected semantic_key='breaker_failure_delay'",
            )
        )
    if parameter.value.kind != "quantity":
        issues.append(
            _issue(
                "invalid_delay_value_kind",
                f"{path}/{parameter.id}/value",
                "breaker-failure delay must be a quantity",
            )
        )
        return None
    return parameter


def _program_fingerprint(
    card_fingerprint: str,
    definitions: Sequence[BreakerFailureDefinition],
) -> str:
    payload = {
        "card_fingerprint": card_fingerprint,
        "definitions": [
            {
                "function_id": item.function_id,
                "stage_id": item.stage_id,
                "monitored_breaker_id": item.monitored_breaker_id,
                "start_signal_id": item.start_signal_id,
                "breaker_open_signal_id": item.breaker_open_signal_id,
                "delay_s": item.delay_s,
                "action_ids": [action.id for action in item.actions],
            }
            for item in definitions
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


def compile_breaker_failure_program(
    card: ProtectionSettingCard,
    *,
    bindings: Sequence[BreakerFailureBinding],
    allow_incomplete_settings: bool = False,
    allow_non_authoritative_settings: bool = False,
    allow_unbound_functions: bool = False,
) -> BreakerFailureProgram:
    base_issues = validate_setting_card(card)
    if base_issues:
        raise BreakerFailureProgramValidationError(
            _issue(
                "invalid_setting_card",
                item.path,
                f"{item.code}: {item.message}",
            )
            for item in base_issues
        )

    issues: list[BreakerFailureIssue] = []

    if (
        card.settings_scope != "full_configuration"
        and not allow_incomplete_settings
    ):
        issues.append(
            _issue(
                "incomplete_settings_scope",
                "/settings_scope",
                (
                    "production execution requires full_configuration; "
                    "override only for explicit bounded engineering use"
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
                "production execution requires approved or implemented settings",
            )
        )

    function_by_id = {item.id: item for item in card.functions}
    enabled_bf_ids = {
        item.id
        for item in card.functions
        if item.concept_id == BREAKER_FAILURE_CONCEPT_ID
        and item.enabled is not False
    }

    binding_by_function: dict[str, BreakerFailureBinding] = {}
    for index, binding in enumerate(bindings):
        path = f"/bindings/{index}"
        for field_name, value in (
            ("function_id", binding.function_id),
            ("monitored_breaker_id", binding.monitored_breaker_id),
            ("start_signal_id", binding.start_signal_id),
            ("breaker_open_signal_id", binding.breaker_open_signal_id),
        ):
            if not isinstance(value, str) or not value.strip():
                issues.append(
                    _issue(
                        f"missing_{field_name}",
                        f"{path}/{field_name}",
                        "stable ID is required",
                    )
                )
        if binding.function_id in binding_by_function:
            issues.append(
                _issue(
                    "duplicate_function_binding",
                    f"{path}/function_id",
                    binding.function_id,
                )
            )
        else:
            binding_by_function[binding.function_id] = binding
        if (
            binding.start_signal_id
            and binding.start_signal_id == binding.breaker_open_signal_id
        ):
            issues.append(
                _issue(
                    "signal_identity_collision",
                    path,
                    "start and breaker-open feedback must use different IDs",
                )
            )

        function = function_by_id.get(binding.function_id)
        if function is None:
            issues.append(
                _issue(
                    "unknown_bound_function",
                    f"{path}/function_id",
                    binding.function_id,
                )
            )
        elif function.concept_id != BREAKER_FAILURE_CONCEPT_ID:
            issues.append(
                _issue(
                    "binding_function_concept_mismatch",
                    f"{path}/function_id",
                    (
                        f"{binding.function_id!r} is "
                        f"{function.concept_id!r}, not breaker failure"
                    ),
                )
            )

    unbound = sorted(enabled_bf_ids - set(binding_by_function))
    if unbound and not allow_unbound_functions:
        issues.append(
            _issue(
                "unbound_breaker_failure_functions",
                "/bindings",
                f"missing bindings for enabled/indeterminate functions: {unbound!r}",
            )
        )

    definitions: list[BreakerFailureDefinition] = []

    for function_id in sorted(binding_by_function):
        binding = binding_by_function[function_id]
        function: ProtectionFunctionSettings | None = function_by_id.get(function_id)
        if function is None or function.concept_id != BREAKER_FAILURE_CONCEPT_ID:
            continue

        path = f"/functions/{function.id}"
        if function.enabled is None:
            issues.append(
                _issue(
                    "indeterminate_function_enabled",
                    f"{path}/enabled",
                    "breaker-failure function enabled state must be explicit",
                )
            )
            continue
        if function.enabled is False:
            continue

        if function.measurement_input_ids:
            issues.append(
                _issue(
                    "measurement_supervision_unsupported",
                    f"{path}/measurement_input_ids",
                    (
                        "binary-feedback foundation does not infer "
                        "current-supervised breaker-failure logic"
                    ),
                )
            )
        if function.parameters:
            issues.append(
                _issue(
                    "function_parameters_unsupported",
                    f"{path}/parameters",
                    "breaker-failure delay must be stage-scoped",
                )
            )
        if function.actions:
            issues.append(
                _issue(
                    "function_actions_unsupported",
                    f"{path}/actions",
                    "breaker-failure outputs must be stage-scoped in this contract",
                )
            )

        if len(function.stages) != 1:
            issues.append(
                _issue(
                    "invalid_stage_count",
                    f"{path}/stages",
                    (
                        "binary-feedback foundation requires exactly one "
                        "breaker-failure stage"
                    ),
                )
            )
            continue

        stage = function.stages[0]
        stage_path = f"{path}/stages/{stage.id}"
        if stage.enabled is None:
            issues.append(
                _issue(
                    "indeterminate_stage_enabled",
                    f"{stage_path}/enabled",
                    "breaker-failure stage enabled state must be explicit",
                )
            )
            continue
        if stage.enabled is False:
            continue

        extra_parameters = [
            item for item in stage.parameters if item.role != "delay"
        ]
        if extra_parameters:
            issues.append(
                _issue(
                    "unsupported_stage_parameter",
                    f"{stage_path}/parameters",
                    (
                        "binary-feedback foundation supports only the "
                        "explicit breaker-failure delay"
                    ),
                )
            )

        delay = _delay_parameter(
            stage,
            path=f"{stage_path}/parameters",
            issues=issues,
        )
        if delay is None:
            continue

        value = delay.value
        if value.quantity_kind != "time" or value.normalized_unit != "s":
            issues.append(
                _issue(
                    "invalid_delay_quantity",
                    f"{stage_path}/parameters/{delay.id}",
                    "breaker-failure delay must be normalized time in seconds",
                )
            )
        if value.basis != "not_applicable":
            issues.append(
                _issue(
                    "delay_basis_mismatch",
                    f"{stage_path}/parameters/{delay.id}",
                    "breaker-failure delay basis must be not_applicable",
                )
            )
        try:
            delay_decimal = parse_decimal_source(value.normalized_value)
        except UnitNormalizationError as exc:
            issues.append(
                _issue(
                    "invalid_delay_value",
                    f"{stage_path}/parameters/{delay.id}",
                    str(exc),
                )
            )
        else:
            if delay_decimal < 0:
                issues.append(
                    _issue(
                        "negative_delay",
                        f"{stage_path}/parameters/{delay.id}",
                        "breaker-failure delay must be >= 0",
                    )
                )

        definitions.append(
            BreakerFailureDefinition(
                function_id=function.id,
                stage_id=stage.id,
                monitored_breaker_id=binding.monitored_breaker_id,
                start_signal_id=binding.start_signal_id,
                breaker_open_signal_id=binding.breaker_open_signal_id,
                delay_s=value.normalized_value,
                actions=tuple(sorted(stage.actions, key=lambda item: item.id)),
            )
        )

    if issues:
        raise BreakerFailureProgramValidationError(issues)

    definitions_tuple = tuple(
        sorted(definitions, key=lambda item: (item.function_id, item.stage_id))
    )
    card_fp = setting_card_fingerprint(card)
    return BreakerFailureProgram(
        card_fingerprint=card_fp,
        program_fingerprint=_program_fingerprint(card_fp, definitions_tuple),
        settings_scope=card.settings_scope,
        lifecycle_status=card.lifecycle_status,
        definitions=definitions_tuple,
    )


def initial_breaker_failure_state(
    program: BreakerFailureProgram,
) -> BreakerFailureRuntimeState:
    return BreakerFailureRuntimeState(
        program_fingerprint=program.program_fingerprint,
        last_time_s="",
        stages=tuple(
            BreakerFailureStageState(
                function_id=item.function_id,
                stage_id=item.stage_id,
                status="idle",
            )
            for item in program.definitions
        ),
    )


def _validate_time(
    value: str,
    *,
    path: str,
    allow_empty: bool,
) -> Decimal | None:
    if allow_empty and value == "":
        return None
    canonical = _canonical_number(value, path=path)
    if canonical != value:
        raise BreakerFailureRuntimeInputError(
            _issue(
                "noncanonical_time",
                path,
                f"expected canonical decimal {canonical!r}",
            )
        )
    parsed = Decimal(canonical)
    if parsed < 0:
        raise BreakerFailureRuntimeInputError(
            _issue("negative_logical_time", path, "logical time must be >= 0")
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
                "runtime state belongs to a different breaker-failure program",
            )
        )

    expected = {(item.function_id, item.stage_id) for item in program.definitions}
    actual = {(item.function_id, item.stage_id) for item in state.stages}
    if expected != actual or len(actual) != len(state.stages):
        raise BreakerFailureRuntimeInputError(
            _issue(
                "state_stage_set_mismatch",
                "/state/stages",
                "runtime state stage set does not match compiled program",
            )
        )

    last_time = _validate_time(
        state.last_time_s,
        path="/state/last_time_s",
        allow_empty=True,
    )
    if last_time is None and any(item.status != "idle" for item in state.stages):
        raise BreakerFailureRuntimeInputError(
            _issue(
                "missing_last_time_for_active_state",
                "/state/last_time_s",
                "non-idle breaker-failure state requires last_time_s",
            )
        )

    for index, item in enumerate(state.stages):
        path = f"/state/stages/{index}"
        if item.status not in BREAKER_FAILURE_STATUSES:
            raise BreakerFailureRuntimeInputError(
                _issue("invalid_stage_status", f"{path}/status", item.status)
            )

        started = _validate_time(
            item.timing_started_at_s,
            path=f"{path}/timing_started_at_s",
            allow_empty=True,
        )
        operated = _validate_time(
            item.operated_at_s,
            path=f"{path}/operated_at_s",
            allow_empty=True,
        )

        if item.status in {"idle", "waiting_start_clear"}:
            if started is not None or operated is not None:
                raise BreakerFailureRuntimeInputError(
                    _issue(
                        "invalid_non_timing_state",
                        path,
                        "idle/waiting state must not retain timing timestamps",
                    )
                )
        elif item.status == "timing":
            if started is None or operated is not None:
                raise BreakerFailureRuntimeInputError(
                    _issue(
                        "invalid_timing_state",
                        path,
                        "timing state requires start timestamp only",
                    )
                )
        elif item.status == "operated":
            if started is None or operated is None:
                raise BreakerFailureRuntimeInputError(
                    _issue(
                        "invalid_operated_state",
                        path,
                        "operated state requires timing and operate timestamps",
                    )
                )
            if operated < started:
                raise BreakerFailureRuntimeInputError(
                    _issue(
                        "invalid_operated_time_order",
                        path,
                        "operate timestamp precedes timing start",
                    )
                )

        for timestamp_name, timestamp in (
            ("timing_started_at_s", started),
            ("operated_at_s", operated),
        ):
            if timestamp is not None and last_time is not None and timestamp > last_time:
                raise BreakerFailureRuntimeInputError(
                    _issue(
                        "state_timestamp_after_last_time",
                        f"{path}/{timestamp_name}",
                        "stage timestamp is after state.last_time_s",
                    )
                )


def _signal_map(
    program: BreakerFailureProgram,
    snapshot: BreakerFailureSnapshot,
) -> dict[str, bool]:
    canonical_time = _canonical_number(snapshot.time_s, path="/snapshot/time_s")
    if canonical_time != snapshot.time_s:
        raise BreakerFailureRuntimeInputError(
            _issue(
                "noncanonical_snapshot_time",
                "/snapshot/time_s",
                f"expected canonical decimal {canonical_time!r}",
            )
        )
    if Decimal(canonical_time) < 0:
        raise BreakerFailureRuntimeInputError(
            _issue(
                "negative_logical_time",
                "/snapshot/time_s",
                "logical time must be >= 0",
            )
        )

    required = {
        signal_id
        for item in program.definitions
        for signal_id in (item.start_signal_id, item.breaker_open_signal_id)
    }
    result: dict[str, bool] = {}
    for index, signal in enumerate(snapshot.signals):
        path = f"/snapshot/signals/{index}"
        if signal.signal_id in result:
            raise BreakerFailureRuntimeInputError(
                _issue(
                    "duplicate_signal",
                    f"{path}/signal_id",
                    signal.signal_id,
                )
            )
        if signal.signal_id not in required:
            raise BreakerFailureRuntimeInputError(
                _issue(
                    "unknown_signal",
                    f"{path}/signal_id",
                    signal.signal_id,
                )
            )
        if not isinstance(signal.value, bool):
            raise BreakerFailureRuntimeInputError(
                _issue(
                    "invalid_signal_value",
                    f"{path}/value",
                    "binary signal value must be bool",
                )
            )
        result[signal.signal_id] = signal.value

    missing = sorted(required - set(result))
    if missing:
        raise BreakerFailureRuntimeInputError(
            _issue(
                "missing_signals",
                "/snapshot/signals",
                f"missing required signals: {missing!r}",
            )
        )
    return result


def _request_id(
    *,
    program: BreakerFailureProgram,
    snapshot: BreakerFailureSnapshot,
    definition: BreakerFailureDefinition,
    action: SettingAction,
) -> str:
    payload = {
        "program_fingerprint": program.program_fingerprint,
        "snapshot_id": snapshot.snapshot_id,
        "time_s": snapshot.time_s,
        "function_id": definition.function_id,
        "stage_id": definition.stage_id,
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
    return f"protection-request:{digest[:32]}"


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

    if state is None:
        state = initial_breaker_failure_state(program)
    _validate_state(program, state)
    signals = _signal_map(program, snapshot)

    now = parse_decimal_source(snapshot.time_s)
    if state.last_time_s:
        previous = parse_decimal_source(state.last_time_s)
        if now < previous:
            raise BreakerFailureRuntimeInputError(
                _issue(
                    "logical_time_reversal",
                    "/snapshot/time_s",
                    f"{snapshot.time_s} < prior {state.last_time_s}",
                )
            )

    prior_by_key = {
        (item.function_id, item.stage_id): item for item in state.stages
    }
    next_states: list[BreakerFailureStageState] = []
    events: list[BreakerFailureEvent] = []
    requests: list[ProtectionOutputRequest] = []

    for definition in program.definitions:
        prior = prior_by_key[(definition.function_id, definition.stage_id)]
        start_active = signals[definition.start_signal_id]
        breaker_open = signals[definition.breaker_open_signal_id]
        delay = parse_decimal_source(definition.delay_s)

        def add_event(event_type: str, cause: str) -> None:
            events.append(
                BreakerFailureEvent(
                    event_type=event_type,
                    function_id=definition.function_id,
                    stage_id=definition.stage_id,
                    monitored_breaker_id=definition.monitored_breaker_id,
                    time_s=snapshot.time_s,
                    cause=cause,
                )
            )

        def operate(started_at_s: str) -> BreakerFailureStageState:
            add_event("operate", "delay_elapsed_breaker_not_open")
            for action in definition.actions:
                requests.append(
                    ProtectionOutputRequest(
                        request_id=_request_id(
                            program=program,
                            snapshot=snapshot,
                            definition=definition,
                            action=action,
                        ),
                        function_id=definition.function_id,
                        stage_id=definition.stage_id,
                        action_id=action.id,
                        action_type=action.action_type,
                        target_kind=action.target_kind,
                        target_id=action.target_id,
                        time_s=snapshot.time_s,
                        cause="breaker_failure_operated",
                    )
                )
            return BreakerFailureStageState(
                function_id=definition.function_id,
                stage_id=definition.stage_id,
                status="operated",
                timing_started_at_s=started_at_s,
                operated_at_s=snapshot.time_s,
            )

        if prior.status == "idle":
            if not start_active:
                next_state = prior
            elif breaker_open:
                next_state = BreakerFailureStageState(
                    function_id=definition.function_id,
                    stage_id=definition.stage_id,
                    status="waiting_start_clear",
                )
            else:
                add_event("start", "start_active_breaker_not_open")
                if delay == 0:
                    next_state = operate(snapshot.time_s)
                else:
                    next_state = BreakerFailureStageState(
                        function_id=definition.function_id,
                        stage_id=definition.stage_id,
                        status="timing",
                        timing_started_at_s=snapshot.time_s,
                    )

        elif prior.status == "timing":
            if not start_active:
                add_event("reset", "start_removed")
                next_state = BreakerFailureStageState(
                    function_id=definition.function_id,
                    stage_id=definition.stage_id,
                    status="idle",
                )
            elif breaker_open:
                add_event("reset", "breaker_open")
                next_state = BreakerFailureStageState(
                    function_id=definition.function_id,
                    stage_id=definition.stage_id,
                    status="waiting_start_clear",
                )
            else:
                started = parse_decimal_source(prior.timing_started_at_s)
                if now - started >= delay:
                    next_state = operate(prior.timing_started_at_s)
                else:
                    next_state = prior

        elif prior.status == "operated":
            if not start_active:
                add_event("reset", "start_removed")
                next_state = BreakerFailureStageState(
                    function_id=definition.function_id,
                    stage_id=definition.stage_id,
                    status="idle",
                )
            elif breaker_open:
                add_event("reset", "breaker_open")
                next_state = BreakerFailureStageState(
                    function_id=definition.function_id,
                    stage_id=definition.stage_id,
                    status="waiting_start_clear",
                )
            else:
                next_state = prior

        elif prior.status == "waiting_start_clear":
            if start_active:
                next_state = prior
            else:
                next_state = BreakerFailureStageState(
                    function_id=definition.function_id,
                    stage_id=definition.stage_id,
                    status="idle",
                )

        else:
            raise AssertionError(prior.status)

        next_states.append(next_state)

    next_runtime_state = BreakerFailureRuntimeState(
        program_fingerprint=program.program_fingerprint,
        last_time_s=snapshot.time_s,
        stages=tuple(next_states),
    )
    return BreakerFailureStepResult(
        snapshot_id=snapshot.snapshot_id,
        time_s=snapshot.time_s,
        state=next_runtime_state,
        events=tuple(events),
        requests=tuple(sorted(requests)),
    )


def breaker_failure_step_fingerprint(result: BreakerFailureStepResult) -> str:
    payload = {
        "snapshot_id": result.snapshot_id,
        "time_s": result.time_s,
        "state": {
            "program_fingerprint": result.state.program_fingerprint,
            "last_time_s": result.state.last_time_s,
            "stages": [
                {
                    "function_id": item.function_id,
                    "stage_id": item.stage_id,
                    "status": item.status,
                    "timing_started_at_s": item.timing_started_at_s,
                    "operated_at_s": item.operated_at_s,
                }
                for item in sorted(
                    result.state.stages,
                    key=lambda value: (value.function_id, value.stage_id),
                )
            ],
        },
        "events": [
            {
                "event_type": item.event_type,
                "function_id": item.function_id,
                "stage_id": item.stage_id,
                "monitored_breaker_id": item.monitored_breaker_id,
                "time_s": item.time_s,
                "cause": item.cause,
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
