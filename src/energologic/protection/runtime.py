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
from .units import (
    UnitNormalizationError,
    canonical_decimal,
    normalize_quantity,
    parse_decimal_source,
)


SUPPORTED_CONCEPT_IDS = frozenset(
    {
        "protection.overcurrent",
        "protection.instantaneous_overcurrent",
        "protection.earth_fault",
    }
)
STAGE_STATUSES = frozenset({"inactive", "picked_up", "operated"})
EVENT_TYPES = frozenset({"pickup", "reset", "operate"})

_FUNCTION_CONTRACTS = {
    "protection.overcurrent": ("phase_current", "pickup_current"),
    "protection.instantaneous_overcurrent": (
        "phase_current",
        "pickup_current",
    ),
    "protection.earth_fault": (
        "residual_current",
        "pickup_residual_current",
    ),
}

_CANONICAL_UNIT_BY_KIND = {
    "current": "A",
    "voltage": "V",
    "time": "s",
    "frequency": "Hz",
    "impedance": "ohm",
    "power_active": "W",
    "power_reactive": "var",
    "angle": "deg",
    "ratio": "pu",
    "scalar": "1",
}


@dataclass(frozen=True, order=True, slots=True)
class ProtectionEngineIssue:
    code: str
    path: str
    message: str


class ProtectionEngineError(ValueError):
    pass


class ProtectionProgramValidationError(ProtectionEngineError):
    def __init__(self, issues: Iterable[ProtectionEngineIssue]):
        self.issues = tuple(sorted(set(issues)))
        super().__init__(
            "invalid protection program: "
            + "; ".join(f"{item.code}@{item.path}" for item in self.issues)
        )


class ProtectionRuntimeInputError(ProtectionEngineError):
    def __init__(self, issue: ProtectionEngineIssue):
        self.issue = issue
        super().__init__(f"{issue.code}@{issue.path}: {issue.message}")


@dataclass(frozen=True, slots=True)
class MeasurementSpec:
    id: str
    semantic_key: str
    quantity_kind: str
    basis: str
    canonical_unit: str


@dataclass(frozen=True, slots=True)
class StageDefinition:
    function_id: str
    concept_id: str
    stage_id: str
    measurement_input_id: str
    pickup_value: str
    pickup_unit: str
    pickup_quantity_kind: str
    pickup_basis: str
    delay_s: str
    actions: tuple[SettingAction, ...]


@dataclass(frozen=True, slots=True)
class ProtectionProgram:
    card_fingerprint: str
    settings_scope: str
    lifecycle_status: str
    selected_function_ids: tuple[str, ...]
    unsupported_function_ids: tuple[str, ...]
    measurement_specs: tuple[MeasurementSpec, ...]
    stages: tuple[StageDefinition, ...]


@dataclass(frozen=True, slots=True)
class MeasuredQuantity:
    measurement_input_id: str
    quantity_kind: str
    basis: str
    normalized_value: str
    normalized_unit: str


@dataclass(frozen=True, slots=True)
class ProtectionSnapshot:
    snapshot_id: str
    time_s: str
    measurements: tuple[MeasuredQuantity, ...]


@dataclass(frozen=True, slots=True)
class StageRuntimeState:
    function_id: str
    stage_id: str
    status: str
    pickup_started_at_s: str = ""
    operated_at_s: str = ""


@dataclass(frozen=True, slots=True)
class ProtectionRuntimeState:
    card_fingerprint: str
    last_time_s: str
    stages: tuple[StageRuntimeState, ...]


@dataclass(frozen=True, order=True, slots=True)
class ProtectionEngineEvent:
    event_type: str
    function_id: str
    stage_id: str
    time_s: str
    measurement_input_id: str
    measured_value: str
    pickup_value: str


@dataclass(frozen=True, order=True, slots=True)
class ProtectionOutputRequest:
    request_id: str
    function_id: str
    stage_id: str
    action_id: str
    action_type: str
    target_kind: str
    target_id: str
    time_s: str
    cause: str


@dataclass(frozen=True, slots=True)
class ProtectionStepResult:
    snapshot_id: str
    time_s: str
    state: ProtectionRuntimeState
    events: tuple[ProtectionEngineEvent, ...]
    requests: tuple[ProtectionOutputRequest, ...]


def _issue(code: str, path: str, message: str) -> ProtectionEngineIssue:
    return ProtectionEngineIssue(code, path, message)


def _canonical_number(value: str, *, path: str) -> str:
    try:
        parsed = parse_decimal_source(value)
    except UnitNormalizationError as exc:
        raise ProtectionRuntimeInputError(
            _issue("invalid_decimal", path, str(exc))
        ) from exc
    return canonical_decimal(parsed)


def make_measured_quantity(
    *,
    measurement_input_id: str,
    source_value: str,
    source_unit: str,
    quantity_kind: str,
    basis: str,
    decimal_separator: str = ".",
) -> MeasuredQuantity:
    try:
        _, normalized_value, normalized_unit = normalize_quantity(
            source_value,
            source_unit,
            quantity_kind,
            decimal_separator=decimal_separator,
        )
    except UnitNormalizationError as exc:
        raise ProtectionRuntimeInputError(
            _issue(
                "invalid_measured_quantity",
                f"/measurements/{measurement_input_id}",
                str(exc),
            )
        ) from exc
    return MeasuredQuantity(
        measurement_input_id=measurement_input_id,
        quantity_kind=quantity_kind,
        basis=basis,
        normalized_value=normalized_value,
        normalized_unit=normalized_unit,
    )


def make_snapshot(
    *,
    snapshot_id: str,
    time_s: str,
    measurements: Sequence[MeasuredQuantity],
) -> ProtectionSnapshot:
    if not isinstance(snapshot_id, str) or not snapshot_id.strip():
        raise ProtectionRuntimeInputError(
            _issue(
                "missing_snapshot_id",
                "/snapshot_id",
                "snapshot ID is required",
            )
        )
    canonical_time = _canonical_number(time_s, path="/time_s")
    if Decimal(canonical_time) < 0:
        raise ProtectionRuntimeInputError(
            _issue(
                "negative_logical_time",
                "/time_s",
                "logical time must be >= 0",
            )
        )
    return ProtectionSnapshot(
        snapshot_id=snapshot_id,
        time_s=canonical_time,
        measurements=tuple(measurements),
    )


def _quantity_parameter(
    stage: ProtectionStage,
    *,
    role: str,
    path: str,
    issues: list[ProtectionEngineIssue],
) -> SettingParameter | None:
    matches = [item for item in stage.parameters if item.role == role]
    if len(matches) != 1:
        issues.append(
            _issue(
                f"invalid_{role}_parameter_count",
                path,
                f"expected exactly one {role!r} stage parameter, found {len(matches)}",
            )
        )
        return None
    parameter = matches[0]
    if parameter.value.kind != "quantity":
        issues.append(
            _issue(
                f"invalid_{role}_value_kind",
                path,
                f"{role!r} parameter must be a quantity",
            )
        )
        return None
    return parameter


def _canonical_unit_for_quantity(quantity_kind: str) -> str:
    source_unit = _CANONICAL_UNIT_BY_KIND.get(quantity_kind)
    if source_unit is None:
        raise ValueError(quantity_kind)
    try:
        _, _, unit = normalize_quantity("0", source_unit, quantity_kind)
    except UnitNormalizationError as exc:
        raise ValueError(quantity_kind) from exc
    return unit


def compile_protection_program(
    card: ProtectionSettingCard,
    *,
    function_ids: Iterable[str] | None = None,
    allow_incomplete_settings: bool = False,
    allow_non_authoritative_settings: bool = False,
) -> ProtectionProgram:
    base_issues = validate_setting_card(card)
    if base_issues:
        raise ProtectionProgramValidationError(
            _issue(
                "invalid_setting_card",
                item.path,
                f"{item.code}: {item.message}",
            )
            for item in base_issues
        )

    issues: list[ProtectionEngineIssue] = []
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
                    "set allow_incomplete_settings=True only for explicit "
                    "bounded engineering/synthetic evaluation"
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
                    "production execution requires approved or implemented "
                    "settings; override only for explicit engineering use"
                ),
            )
        )

    by_function_id = {item.id: item for item in card.functions}
    if function_ids is None:
        requested_ids = tuple(sorted(by_function_id))
    else:
        requested_ids = tuple(sorted(set(function_ids)))
        missing = [item for item in requested_ids if item not in by_function_id]
        if missing:
            raise ProtectionProgramValidationError(
                [
                    _issue(
                        "unknown_function_id",
                        "/function_ids",
                        f"unknown function IDs: {missing!r}",
                    )
                ]
            )

    measurement_by_id = {item.id: item for item in card.measurement_inputs}
    measurement_specs: dict[str, MeasurementSpec] = {}
    for measurement in card.measurement_inputs:
        try:
            canonical_unit = _canonical_unit_for_quantity(
                measurement.quantity_kind
            )
        except ValueError:
            continue
        measurement_specs[measurement.id] = MeasurementSpec(
            id=measurement.id,
            semantic_key=measurement.semantic_key,
            quantity_kind=measurement.quantity_kind,
            basis=measurement.basis,
            canonical_unit=canonical_unit,
        )

    stage_defs: list[StageDefinition] = []
    unsupported: list[str] = []
    selected_supported: list[str] = []

    for function_id in requested_ids:
        function: ProtectionFunctionSettings = by_function_id[function_id]
        function_path = f"/functions/{function.id}"

        if function.concept_id not in SUPPORTED_CONCEPT_IDS:
            unsupported.append(function.id)
            continue

        selected_supported.append(function.id)

        if function.enabled is None:
            issues.append(
                _issue(
                    "indeterminate_function_enabled",
                    f"{function_path}/enabled",
                    "supported function enabled state must be explicit",
                )
            )
            continue
        if function.enabled is False:
            continue

        if function.parameters:
            issues.append(
                _issue(
                    "function_parameters_unsupported",
                    f"{function_path}/parameters",
                    (
                        "foundation requires algorithm settings on stages, "
                        "not inherited function parameters"
                    ),
                )
            )
        if function.actions:
            issues.append(
                _issue(
                    "function_actions_unsupported",
                    f"{function_path}/actions",
                    (
                        "foundation does not guess whether function-level "
                        "actions apply to every stage; actions must be "
                        "stage-scoped"
                    ),
                )
            )

        if len(function.measurement_input_ids) != 1:
            issues.append(
                _issue(
                    "invalid_measurement_input_count",
                    f"{function_path}/measurement_input_ids",
                    (
                        "supported current function requires exactly one "
                        "measurement input"
                    ),
                )
            )
            continue

        measurement_id = function.measurement_input_ids[0]
        measurement = measurement_by_id[measurement_id]
        expected_measurement_key, expected_pickup_key = _FUNCTION_CONTRACTS[
            function.concept_id
        ]
        if measurement.semantic_key != expected_measurement_key:
            issues.append(
                _issue(
                    "measurement_semantic_mismatch",
                    f"{function_path}/measurement_input_ids",
                    (
                        f"{function.concept_id!r} requires measurement "
                        f"semantic_key={expected_measurement_key!r}, got "
                        f"{measurement.semantic_key!r}"
                    ),
                )
            )
        if measurement.quantity_kind != "current":
            issues.append(
                _issue(
                    "unsupported_operating_quantity",
                    f"{function_path}/measurement_input_ids",
                    (
                        "foundation overcurrent functions require a "
                        "current magnitude input"
                    ),
                )
            )
        try:
            canonical_unit = _canonical_unit_for_quantity(
                measurement.quantity_kind
            )
        except ValueError:
            issues.append(
                _issue(
                    "unsupported_measurement_quantity",
                    f"{function_path}/measurement_input_ids",
                    measurement.quantity_kind,
                )
            )
            continue

        if not function.stages:
            issues.append(
                _issue(
                    "missing_stages",
                    f"{function_path}/stages",
                    "supported function requires at least one explicit stage",
                )
            )
            continue

        for stage in function.stages:
            stage_path = f"{function_path}/stages/{stage.id}"

            if stage.enabled is None:
                issues.append(
                    _issue(
                        "indeterminate_stage_enabled",
                        f"{stage_path}/enabled",
                        "supported stage enabled state must be explicit",
                    )
                )
                continue
            if stage.enabled is False:
                continue

            unsupported_parameters = [
                item
                for item in stage.parameters
                if item.role not in {"pickup", "delay"}
            ]
            if unsupported_parameters:
                issues.append(
                    _issue(
                        "unsupported_stage_parameter",
                        f"{stage_path}/parameters",
                        (
                            "foundation supports only explicit pickup and "
                            "delay parameters"
                        ),
                    )
                )

            pickup = _quantity_parameter(
                stage,
                role="pickup",
                path=f"{stage_path}/parameters",
                issues=issues,
            )
            delay = _quantity_parameter(
                stage,
                role="delay",
                path=f"{stage_path}/parameters",
                issues=issues,
            )
            if pickup is None or delay is None:
                continue

            pickup_value = pickup.value
            delay_value = delay.value

            if pickup.semantic_key != expected_pickup_key:
                issues.append(
                    _issue(
                        "pickup_semantic_mismatch",
                        f"{stage_path}/parameters/{pickup.id}/semantic_key",
                        (
                            f"expected {expected_pickup_key!r}, got "
                            f"{pickup.semantic_key!r}"
                        ),
                    )
                )
            if delay.semantic_key != "operate_delay":
                issues.append(
                    _issue(
                        "delay_semantic_mismatch",
                        f"{stage_path}/parameters/{delay.id}/semantic_key",
                        (
                            "definite-time foundation requires "
                            "semantic_key='operate_delay'"
                        ),
                    )
                )

            if pickup_value.quantity_kind != measurement.quantity_kind:
                issues.append(
                    _issue(
                        "pickup_quantity_mismatch",
                        f"{stage_path}/parameters/{pickup.id}",
                        (
                            f"pickup quantity {pickup_value.quantity_kind!r} "
                            "does not match measurement "
                            f"{measurement.quantity_kind!r}"
                        ),
                    )
                )
            if pickup_value.basis != measurement.basis:
                issues.append(
                    _issue(
                        "pickup_basis_mismatch",
                        f"{stage_path}/parameters/{pickup.id}",
                        (
                            f"pickup basis {pickup_value.basis!r} does not "
                            f"match measurement basis {measurement.basis!r}"
                        ),
                    )
                )
            if pickup_value.normalized_unit != canonical_unit:
                issues.append(
                    _issue(
                        "pickup_unit_mismatch",
                        f"{stage_path}/parameters/{pickup.id}",
                        (
                            f"pickup unit {pickup_value.normalized_unit!r} "
                            "does not match canonical measurement unit "
                            f"{canonical_unit!r}"
                        ),
                    )
                )

            if delay_value.basis != "not_applicable":
                issues.append(
                    _issue(
                        "delay_basis_mismatch",
                        f"{stage_path}/parameters/{delay.id}",
                        (
                            "operate delay basis must be "
                            "'not_applicable'"
                        ),
                    )
                )
            if (
                delay_value.quantity_kind != "time"
                or delay_value.normalized_unit != "s"
            ):
                issues.append(
                    _issue(
                        "invalid_delay_quantity",
                        f"{stage_path}/parameters/{delay.id}",
                        "operate delay must be normalized time in seconds",
                    )
                )
            else:
                try:
                    delay_decimal = parse_decimal_source(
                        delay_value.normalized_value
                    )
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
                                "operate delay must be >= 0",
                            )
                        )

            try:
                pickup_decimal = parse_decimal_source(
                    pickup_value.normalized_value
                )
            except UnitNormalizationError as exc:
                issues.append(
                    _issue(
                        "invalid_pickup_value",
                        f"{stage_path}/parameters/{pickup.id}",
                        str(exc),
                    )
                )
            else:
                if pickup_decimal < 0:
                    issues.append(
                        _issue(
                            "negative_pickup",
                            f"{stage_path}/parameters/{pickup.id}",
                            "pickup threshold must be >= 0",
                        )
                    )

            actions = tuple(
                sorted(
                    stage.actions,
                    key=lambda item: item.id,
                )
            )
            stage_defs.append(
                StageDefinition(
                    function_id=function.id,
                    concept_id=function.concept_id,
                    stage_id=stage.id,
                    measurement_input_id=measurement_id,
                    pickup_value=pickup_value.normalized_value,
                    pickup_unit=pickup_value.normalized_unit,
                    pickup_quantity_kind=pickup_value.quantity_kind,
                    pickup_basis=pickup_value.basis,
                    delay_s=delay_value.normalized_value,
                    actions=actions,
                )
            )

    if issues:
        raise ProtectionProgramValidationError(issues)

    return ProtectionProgram(
        card_fingerprint=setting_card_fingerprint(card),
        settings_scope=card.settings_scope,
        lifecycle_status=card.lifecycle_status,
        selected_function_ids=tuple(sorted(selected_supported)),
        unsupported_function_ids=tuple(sorted(unsupported)),
        measurement_specs=tuple(
            measurement_specs[key] for key in sorted(measurement_specs)
        ),
        stages=tuple(
            sorted(
                stage_defs,
                key=lambda item: (item.function_id, item.stage_id),
            )
        ),
    )


def initial_runtime_state(program: ProtectionProgram) -> ProtectionRuntimeState:
    return ProtectionRuntimeState(
        card_fingerprint=program.card_fingerprint,
        last_time_s="",
        stages=tuple(
            StageRuntimeState(
                function_id=stage.function_id,
                stage_id=stage.stage_id,
                status="inactive",
            )
            for stage in program.stages
        ),
    )


def _validate_state_time(
    value: str,
    *,
    path: str,
    allow_empty: bool,
) -> Decimal | None:
    if allow_empty and value == "":
        return None
    canonical = _canonical_number(value, path=path)
    if canonical != value:
        raise ProtectionRuntimeInputError(
            _issue(
                "noncanonical_state_time",
                path,
                f"expected canonical decimal {canonical!r}",
            )
        )
    parsed = Decimal(canonical)
    if parsed < 0:
        raise ProtectionRuntimeInputError(
            _issue(
                "negative_state_time",
                path,
                "state logical time must be >= 0",
            )
        )
    return parsed


def _validate_runtime_state(
    program: ProtectionProgram,
    state: ProtectionRuntimeState,
) -> None:
    if state.card_fingerprint != program.card_fingerprint:
        raise ProtectionRuntimeInputError(
            _issue(
                "state_card_mismatch",
                "/state/card_fingerprint",
                "runtime state belongs to a different setting card",
            )
        )

    expected = {(item.function_id, item.stage_id) for item in program.stages}
    actual = {(item.function_id, item.stage_id) for item in state.stages}
    if expected != actual or len(actual) != len(state.stages):
        raise ProtectionRuntimeInputError(
            _issue(
                "state_stage_set_mismatch",
                "/state/stages",
                "runtime state stage set does not match compiled program",
            )
        )

    last_time = _validate_state_time(
        state.last_time_s,
        path="/state/last_time_s",
        allow_empty=True,
    )

    if last_time is None and any(
        item.status != "inactive" for item in state.stages
    ):
        raise ProtectionRuntimeInputError(
            _issue(
                "missing_last_time_for_active_state",
                "/state/last_time_s",
                (
                    "picked-up/operated runtime state requires "
                    "last_time_s"
                ),
            )
        )

    for index, item in enumerate(state.stages):
        path = f"/state/stages/{index}"
        if item.status not in STAGE_STATUSES:
            raise ProtectionRuntimeInputError(
                _issue(
                    "invalid_stage_status",
                    f"{path}/status",
                    repr(item.status),
                )
            )

        pickup_time = _validate_state_time(
            item.pickup_started_at_s,
            path=f"{path}/pickup_started_at_s",
            allow_empty=True,
        )
        operated_time = _validate_state_time(
            item.operated_at_s,
            path=f"{path}/operated_at_s",
            allow_empty=True,
        )

        if item.status == "inactive":
            if pickup_time is not None or operated_time is not None:
                raise ProtectionRuntimeInputError(
                    _issue(
                        "invalid_inactive_stage_state",
                        path,
                        (
                            "inactive stage must not retain pickup/operate "
                            "timestamps"
                        ),
                    )
                )
        elif item.status == "picked_up":
            if pickup_time is None or operated_time is not None:
                raise ProtectionRuntimeInputError(
                    _issue(
                        "invalid_picked_up_stage_state",
                        path,
                        (
                            "picked-up stage requires pickup timestamp and "
                            "no operate timestamp"
                        ),
                    )
                )
        elif item.status == "operated":
            if pickup_time is None or operated_time is None:
                raise ProtectionRuntimeInputError(
                    _issue(
                        "invalid_operated_stage_state",
                        path,
                        (
                            "operated stage requires pickup and operate "
                            "timestamps"
                        ),
                    )
                )
            if operated_time < pickup_time:
                raise ProtectionRuntimeInputError(
                    _issue(
                        "invalid_operated_time_order",
                        path,
                        "operate timestamp precedes pickup timestamp",
                    )
                )

        for timestamp_name, timestamp in (
            ("pickup_started_at_s", pickup_time),
            ("operated_at_s", operated_time),
        ):
            if (
                timestamp is not None
                and last_time is not None
                and timestamp > last_time
            ):
                raise ProtectionRuntimeInputError(
                    _issue(
                        "state_timestamp_after_last_time",
                        f"{path}/{timestamp_name}",
                        "stage timestamp is after state.last_time_s",
                    )
                )


def _measurement_map(
    program: ProtectionProgram,
    snapshot: ProtectionSnapshot,
) -> dict[str, MeasuredQuantity]:
    known_specs = {item.id: item for item in program.measurement_specs}
    result: dict[str, MeasuredQuantity] = {}

    canonical_time = _canonical_number(
        snapshot.time_s,
        path="/snapshot/time_s",
    )
    if canonical_time != snapshot.time_s:
        raise ProtectionRuntimeInputError(
            _issue(
                "noncanonical_snapshot_time",
                "/snapshot/time_s",
                f"expected canonical decimal {canonical_time!r}",
            )
        )
    if Decimal(canonical_time) < 0:
        raise ProtectionRuntimeInputError(
            _issue(
                "negative_logical_time",
                "/snapshot/time_s",
                "logical time must be >= 0",
            )
        )

    for index, measured in enumerate(snapshot.measurements):
        path = f"/snapshot/measurements/{index}"
        if measured.measurement_input_id in result:
            raise ProtectionRuntimeInputError(
                _issue(
                    "duplicate_measurement_input",
                    f"{path}/measurement_input_id",
                    measured.measurement_input_id,
                )
            )

        spec = known_specs.get(measured.measurement_input_id)
        if spec is None:
            raise ProtectionRuntimeInputError(
                _issue(
                    "unknown_measurement_input",
                    f"{path}/measurement_input_id",
                    measured.measurement_input_id,
                )
            )

        if measured.quantity_kind != spec.quantity_kind:
            raise ProtectionRuntimeInputError(
                _issue(
                    "measurement_quantity_mismatch",
                    f"{path}/quantity_kind",
                    f"expected {spec.quantity_kind!r}",
                )
            )
        if measured.basis != spec.basis:
            raise ProtectionRuntimeInputError(
                _issue(
                    "measurement_basis_mismatch",
                    f"{path}/basis",
                    f"expected {spec.basis!r}",
                )
            )

        try:
            _, normalized_value, normalized_unit = normalize_quantity(
                measured.normalized_value,
                measured.normalized_unit,
                measured.quantity_kind,
            )
        except UnitNormalizationError as exc:
            raise ProtectionRuntimeInputError(
                _issue("invalid_measurement", path, str(exc))
            ) from exc

        if normalized_unit != spec.canonical_unit:
            raise ProtectionRuntimeInputError(
                _issue(
                    "measurement_unit_mismatch",
                    f"{path}/normalized_unit",
                    f"expected canonical unit {spec.canonical_unit!r}",
                )
            )
        if normalized_unit != measured.normalized_unit:
            raise ProtectionRuntimeInputError(
                _issue(
                    "measurement_not_normalized",
                    f"{path}/normalized_unit",
                    f"expected {normalized_unit!r}",
                )
            )
        if normalized_value != measured.normalized_value:
            raise ProtectionRuntimeInputError(
                _issue(
                    "measurement_value_not_canonical",
                    f"{path}/normalized_value",
                    (
                        "expected canonical normalized value "
                        f"{normalized_value!r}"
                    ),
                )
            )
        if Decimal(normalized_value) < 0:
            raise ProtectionRuntimeInputError(
                _issue(
                    "negative_operating_quantity",
                    f"{path}/normalized_value",
                    (
                        "foundation current algorithms require "
                        "non-negative scalar magnitude"
                    ),
                )
            )

        result[measured.measurement_input_id] = measured

    required = {item.measurement_input_id for item in program.stages}
    missing = sorted(required - set(result))
    if missing:
        raise ProtectionRuntimeInputError(
            _issue(
                "missing_measurement_inputs",
                "/snapshot/measurements",
                f"missing required measurement inputs: {missing!r}",
            )
        )
    return result


def _request_id(
    *,
    program: ProtectionProgram,
    snapshot: ProtectionSnapshot,
    stage: StageDefinition,
    action: SettingAction,
) -> str:
    payload = {
        "card_fingerprint": program.card_fingerprint,
        "snapshot_id": snapshot.snapshot_id,
        "time_s": snapshot.time_s,
        "function_id": stage.function_id,
        "stage_id": stage.stage_id,
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


def evaluate_protection_step(
    program: ProtectionProgram,
    snapshot: ProtectionSnapshot,
    *,
    state: ProtectionRuntimeState | None = None,
) -> ProtectionStepResult:
    if not isinstance(snapshot.snapshot_id, str) or not snapshot.snapshot_id.strip():
        raise ProtectionRuntimeInputError(
            _issue(
                "missing_snapshot_id",
                "/snapshot/snapshot_id",
                "snapshot ID is required",
            )
        )

    if state is None:
        state = initial_runtime_state(program)
    _validate_runtime_state(program, state)

    measurement_map = _measurement_map(program, snapshot)
    now = parse_decimal_source(snapshot.time_s)

    if state.last_time_s:
        previous_time = parse_decimal_source(state.last_time_s)
        if now < previous_time:
            raise ProtectionRuntimeInputError(
                _issue(
                    "logical_time_reversal",
                    "/snapshot/time_s",
                    f"{snapshot.time_s} < prior {state.last_time_s}",
                )
            )

    prior_by_key = {
        (item.function_id, item.stage_id): item for item in state.stages
    }
    next_states: list[StageRuntimeState] = []
    events: list[ProtectionEngineEvent] = []
    requests: list[ProtectionOutputRequest] = []

    for stage in program.stages:
        prior = prior_by_key[(stage.function_id, stage.stage_id)]
        measured = measurement_map[stage.measurement_input_id]
        measured_value = parse_decimal_source(measured.normalized_value)
        pickup_value = parse_decimal_source(stage.pickup_value)
        delay = parse_decimal_source(stage.delay_s)
        criterion = measured_value >= pickup_value

        def add_event(event_type: str) -> None:
            events.append(
                ProtectionEngineEvent(
                    event_type=event_type,
                    function_id=stage.function_id,
                    stage_id=stage.stage_id,
                    time_s=snapshot.time_s,
                    measurement_input_id=stage.measurement_input_id,
                    measured_value=measured.normalized_value,
                    pickup_value=stage.pickup_value,
                )
            )

        def operate(pickup_started_at_s: str) -> StageRuntimeState:
            add_event("operate")
            for action in stage.actions:
                requests.append(
                    ProtectionOutputRequest(
                        request_id=_request_id(
                            program=program,
                            snapshot=snapshot,
                            stage=stage,
                            action=action,
                        ),
                        function_id=stage.function_id,
                        stage_id=stage.stage_id,
                        action_id=action.id,
                        action_type=action.action_type,
                        target_kind=action.target_kind,
                        target_id=action.target_id,
                        time_s=snapshot.time_s,
                        cause="stage_operated",
                    )
                )
            return StageRuntimeState(
                function_id=stage.function_id,
                stage_id=stage.stage_id,
                status="operated",
                pickup_started_at_s=pickup_started_at_s,
                operated_at_s=snapshot.time_s,
            )

        if prior.status == "inactive":
            if not criterion:
                next_state = prior
            else:
                add_event("pickup")
                if delay == 0:
                    next_state = operate(snapshot.time_s)
                else:
                    next_state = StageRuntimeState(
                        function_id=stage.function_id,
                        stage_id=stage.stage_id,
                        status="picked_up",
                        pickup_started_at_s=snapshot.time_s,
                    )

        elif prior.status == "picked_up":
            if not criterion:
                add_event("reset")
                next_state = StageRuntimeState(
                    function_id=stage.function_id,
                    stage_id=stage.stage_id,
                    status="inactive",
                )
            else:
                pickup_started = parse_decimal_source(
                    prior.pickup_started_at_s
                )
                if now - pickup_started >= delay:
                    next_state = operate(prior.pickup_started_at_s)
                else:
                    next_state = prior

        elif prior.status == "operated":
            if criterion:
                next_state = prior
            else:
                add_event("reset")
                next_state = StageRuntimeState(
                    function_id=stage.function_id,
                    stage_id=stage.stage_id,
                    status="inactive",
                )

        else:
            raise AssertionError(prior.status)

        next_states.append(next_state)

    next_state = ProtectionRuntimeState(
        card_fingerprint=program.card_fingerprint,
        last_time_s=snapshot.time_s,
        stages=tuple(next_states),
    )
    return ProtectionStepResult(
        snapshot_id=snapshot.snapshot_id,
        time_s=snapshot.time_s,
        state=next_state,
        events=tuple(events),
        requests=tuple(sorted(requests)),
    )


def protection_step_fingerprint(result: ProtectionStepResult) -> str:
    payload = {
        "snapshot_id": result.snapshot_id,
        "time_s": result.time_s,
        "state": {
            "card_fingerprint": result.state.card_fingerprint,
            "last_time_s": result.state.last_time_s,
            "stages": [
                {
                    "function_id": item.function_id,
                    "stage_id": item.stage_id,
                    "status": item.status,
                    "pickup_started_at_s": item.pickup_started_at_s,
                    "operated_at_s": item.operated_at_s,
                }
                for item in sorted(
                    result.state.stages,
                    key=lambda value: (
                        value.function_id,
                        value.stage_id,
                    ),
                )
            ],
        },
        "events": [
            {
                "event_type": item.event_type,
                "function_id": item.function_id,
                "stage_id": item.stage_id,
                "time_s": item.time_s,
                "measurement_input_id": item.measurement_input_id,
                "measured_value": item.measured_value,
                "pickup_value": item.pickup_value,
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
