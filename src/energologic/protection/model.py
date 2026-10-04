from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable, Mapping, Sequence

from .units import (
    QUANTITY_KINDS,
    UnitNormalizationError,
    normalize_quantity,
    parse_decimal_source,
)


SCHEMA_VERSION = "protection-settings-v1"

DOCUMENT_TYPES = frozenset(
    {
        "setting_card",
        "dispatcher_setting_task",
        "owner_setting_task",
        "vendor_setting_template",
        "parameter_file",
        "commissioning_record",
        "other",
    }
)
SETTINGS_SCOPES = frozenset(
    {
        "operational_summary",
        "partial_configuration",
        "full_configuration",
    }
)
LIFECYCLE_STATUSES = frozenset(
    {"draft", "approved", "implemented", "superseded", "unknown"}
)
DEVICE_TECHNOLOGIES = frozenset(
    {"electromechanical", "static", "microprocessor", "unknown"}
)
VALUE_KINDS = frozenset({"quantity", "boolean", "enum", "text"})
SETTING_BASES = frozenset(
    {"primary", "secondary", "relative", "device_native", "not_applicable"}
)
PARAMETER_ROLES = frozenset(
    {
        "pickup",
        "delay",
        "reset",
        "measurement",
        "direction",
        "characteristic",
        "enable",
        "logic",
        "coordination",
        "other",
    }
)
ACTION_TYPES = frozenset(
    {
        "trip",
        "signal",
        "start",
        "block",
        "unblock",
        "initiate_breaker_failure",
        "other",
    }
)
TARGET_KINDS = frozenset(
    {
        "equipment",
        "protection_function",
        "protection_device",
        "binary_output",
        "other",
    }
)
LOCATOR_KINDS = frozenset(
    {
        "json_pointer",
        "csv_row",
        "csv_cell",
        "sheet_cell",
        "sheet_range",
        "page",
        "vendor_path",
        "document",
        "other",
    }
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CONCEPT_RE = re.compile(r"^protection\.[a-z0-9._-]+$")


@dataclass(frozen=True, order=True, slots=True)
class ProtectionSettingIssue:
    code: str
    path: str
    message: str


class ProtectionSettingError(ValueError):
    pass


class ProtectionSettingDecodeError(ProtectionSettingError):
    pass


class ProtectionSettingValidationError(ProtectionSettingError):
    def __init__(self, issues: Iterable[ProtectionSettingIssue]):
        self.issues = tuple(sorted(set(issues)))
        super().__init__(
            "invalid protection setting card: "
            + "; ".join(f"{item.code}@{item.path}" for item in self.issues)
        )


@dataclass(frozen=True, slots=True)
class SourceReference:
    source_id: str
    locator_kind: str
    locator: str


@dataclass(frozen=True, slots=True)
class SourceDocument:
    id: str
    document_type: str
    title: str
    revision: str
    sha256: str
    issue_date: str = ""
    source_uri: str = ""
    notes: str = ""


@dataclass(frozen=True, slots=True)
class ProtectionDevice:
    id: str
    technology: str
    dispatch_name: str = ""
    manufacturer: str = ""
    model: str = ""
    software_version: str = ""
    parameter_file_source_ids: tuple[str, ...] = ()
    provenance: tuple[SourceReference, ...] = ()


@dataclass(frozen=True, slots=True)
class MeasurementInput:
    id: str
    semantic_key: str
    quantity_kind: str
    basis: str
    source_label: str
    provenance: tuple[SourceReference, ...]
    source_object_id: str = ""
    terminal_id: str = ""
    notes: str = ""


@dataclass(frozen=True, slots=True)
class SettingValue:
    kind: str
    raw_text: str
    source_value: str = ""
    source_unit: str = ""
    quantity_kind: str = ""
    basis: str = ""
    normalized_value: str = ""
    normalized_unit: str = ""
    boolean_value: bool | None = None
    enum_value: str = ""
    text_value: str = ""


@dataclass(frozen=True, slots=True)
class SettingParameter:
    id: str
    semantic_key: str
    role: str
    value: SettingValue
    provenance: tuple[SourceReference, ...]
    notes: str = ""


@dataclass(frozen=True, slots=True)
class SettingAction:
    id: str
    action_type: str
    target_kind: str
    target_id: str
    provenance: tuple[SourceReference, ...]
    source_label: str = ""
    notes: str = ""


@dataclass(frozen=True, slots=True)
class ProtectionStage:
    id: str
    source_name: str
    enabled: bool | None
    parameters: tuple[SettingParameter, ...]
    actions: tuple[SettingAction, ...]
    provenance: tuple[SourceReference, ...]


@dataclass(frozen=True, slots=True)
class ProtectionFunctionSettings:
    id: str
    concept_id: str
    source_name: str
    device_id: str
    enabled: bool | None
    measurement_input_ids: tuple[str, ...]
    parameters: tuple[SettingParameter, ...]
    stages: tuple[ProtectionStage, ...]
    actions: tuple[SettingAction, ...]
    provenance: tuple[SourceReference, ...]


@dataclass(frozen=True, slots=True)
class ProtectionSettingCard:
    schema_version: str
    card_id: str
    card_revision: str
    site_id: str
    settings_scope: str
    lifecycle_status: str
    primary_source_id: str
    protected_object_ids: tuple[str, ...]
    sources: tuple[SourceDocument, ...]
    measurement_inputs: tuple[MeasurementInput, ...]
    devices: tuple[ProtectionDevice, ...]
    functions: tuple[ProtectionFunctionSettings, ...]
    notes: str = ""


def make_quantity_value(
    *,
    raw_text: str,
    source_value: str,
    source_unit: str,
    quantity_kind: str,
    basis: str,
    decimal_separator: str = ".",
) -> SettingValue:
    canonical_source, normalized_value, normalized_unit = normalize_quantity(
        source_value,
        source_unit,
        quantity_kind,
        decimal_separator=decimal_separator,
    )
    return SettingValue(
        kind="quantity",
        raw_text=raw_text,
        source_value=canonical_source,
        source_unit=source_unit,
        quantity_kind=quantity_kind,
        basis=basis,
        normalized_value=normalized_value,
        normalized_unit=normalized_unit,
    )


def _issue(
    issues: list[ProtectionSettingIssue],
    code: str,
    path: str,
    message: str,
) -> None:
    issues.append(ProtectionSettingIssue(code, path, message))


def _check_text(
    value: object,
    *,
    issues: list[ProtectionSettingIssue],
    path: str,
    code: str,
) -> bool:
    if not isinstance(value, str) or not value.strip():
        _issue(issues, code, path, "expected non-empty text")
        return False
    return True


def _validate_source_reference(
    ref: SourceReference,
    *,
    known_source_ids: set[str],
    issues: list[ProtectionSettingIssue],
    path: str,
) -> None:
    if ref.source_id not in known_source_ids:
        _issue(
            issues,
            "unknown_provenance_source",
            f"{path}/source_id",
            f"unknown source document {ref.source_id!r}",
        )
    if ref.locator_kind not in LOCATOR_KINDS:
        _issue(
            issues,
            "invalid_locator_kind",
            f"{path}/locator_kind",
            repr(ref.locator_kind),
        )
    _check_text(
        ref.locator,
        issues=issues,
        path=f"{path}/locator",
        code="missing_source_locator",
    )


def _validate_value(
    value: SettingValue,
    *,
    role: str,
    issues: list[ProtectionSettingIssue],
    path: str,
) -> None:
    if value.kind not in VALUE_KINDS:
        _issue(issues, "invalid_value_kind", f"{path}/kind", repr(value.kind))
        return

    _check_text(
        value.raw_text,
        issues=issues,
        path=f"{path}/raw_text",
        code="missing_raw_text",
    )

    if value.kind == "quantity":
        if value.basis not in SETTING_BASES:
            _issue(
                issues,
                "invalid_setting_basis",
                f"{path}/basis",
                repr(value.basis),
            )
        try:
            canonical_source, normalized_value, normalized_unit = normalize_quantity(
                value.source_value,
                value.source_unit,
                value.quantity_kind,
            )
        except UnitNormalizationError as exc:
            _issue(
                issues,
                "invalid_quantity",
                path,
                str(exc),
            )
            return

        if canonical_source != value.source_value:
            _issue(
                issues,
                "noncanonical_source_value",
                f"{path}/source_value",
                f"expected canonical decimal {canonical_source!r}",
            )
        if normalized_value != value.normalized_value:
            _issue(
                issues,
                "normalized_value_mismatch",
                f"{path}/normalized_value",
                f"expected {normalized_value!r}",
            )
        if normalized_unit != value.normalized_unit:
            _issue(
                issues,
                "normalized_unit_mismatch",
                f"{path}/normalized_unit",
                f"expected {normalized_unit!r}",
            )

        if role == "delay":
            if value.quantity_kind != "time":
                _issue(
                    issues,
                    "delay_quantity_kind_mismatch",
                    path,
                    "numeric delay must use quantity_kind='time'",
                )
            try:
                delay = parse_decimal_source(value.normalized_value)
            except UnitNormalizationError:
                delay = None
            if delay is not None and delay < 0:
                _issue(
                    issues,
                    "negative_delay",
                    f"{path}/normalized_value",
                    "time delay must not be negative",
                )

    elif value.kind == "boolean":
        if value.boolean_value is None:
            _issue(
                issues,
                "missing_boolean_value",
                f"{path}/boolean_value",
                "boolean setting requires boolean_value",
            )

    elif value.kind == "enum":
        _check_text(
            value.enum_value,
            issues=issues,
            path=f"{path}/enum_value",
            code="missing_enum_value",
        )

    elif value.kind == "text":
        _check_text(
            value.text_value,
            issues=issues,
            path=f"{path}/text_value",
            code="missing_text_value",
        )


def validate_setting_card(
    card: ProtectionSettingCard,
) -> tuple[ProtectionSettingIssue, ...]:
    issues: list[ProtectionSettingIssue] = []

    if card.schema_version != SCHEMA_VERSION:
        _issue(
            issues,
            "unsupported_schema_version",
            "/schema_version",
            f"expected {SCHEMA_VERSION!r}",
        )

    for field_name, value in (
        ("card_id", card.card_id),
        ("card_revision", card.card_revision),
        ("site_id", card.site_id),
        ("primary_source_id", card.primary_source_id),
    ):
        _check_text(
            value,
            issues=issues,
            path=f"/{field_name}",
            code=f"missing_{field_name}",
        )

    if card.settings_scope not in SETTINGS_SCOPES:
        _issue(
            issues,
            "invalid_settings_scope",
            "/settings_scope",
            repr(card.settings_scope),
        )
    if card.lifecycle_status not in LIFECYCLE_STATUSES:
        _issue(
            issues,
            "invalid_lifecycle_status",
            "/lifecycle_status",
            repr(card.lifecycle_status),
        )
    if not card.protected_object_ids:
        _issue(
            issues,
            "missing_protected_objects",
            "/protected_object_ids",
            "at least one protected object stable ID is required",
        )
    if len(set(card.protected_object_ids)) != len(card.protected_object_ids):
        _issue(
            issues,
            "duplicate_protected_object_id",
            "/protected_object_ids",
            "protected object stable IDs must be unique",
        )

    source_ids: set[str] = set()
    source_types: dict[str, str] = {}
    for index, source in enumerate(card.sources):
        path = f"/sources/{index}"
        if source.id in source_ids:
            _issue(
                issues,
                "duplicate_source_id",
                f"{path}/id",
                source.id,
            )
        source_ids.add(source.id)
        source_types[source.id] = source.document_type
        if source.document_type not in DOCUMENT_TYPES:
            _issue(
                issues,
                "invalid_document_type",
                f"{path}/document_type",
                repr(source.document_type),
            )
        for field_name, value in (
            ("id", source.id),
            ("title", source.title),
            ("revision", source.revision),
        ):
            _check_text(
                value,
                issues=issues,
                path=f"{path}/{field_name}",
                code=f"missing_source_{field_name}",
            )
        if not _SHA256_RE.fullmatch(source.sha256):
            _issue(
                issues,
                "invalid_source_sha256",
                f"{path}/sha256",
                "expected lowercase 64-character SHA-256",
            )
        if source.issue_date:
            try:
                date.fromisoformat(source.issue_date)
            except ValueError:
                _issue(
                    issues,
                    "invalid_source_issue_date",
                    f"{path}/issue_date",
                    "expected ISO date YYYY-MM-DD",
                )

    if not card.sources:
        _issue(
            issues,
            "missing_sources",
            "/sources",
            "at least one source document is required",
        )
    if card.primary_source_id not in source_ids:
        _issue(
            issues,
            "unknown_primary_source",
            "/primary_source_id",
            card.primary_source_id,
        )

    device_ids: set[str] = set()
    for index, device in enumerate(card.devices):
        path = f"/devices/{index}"
        if device.id in device_ids:
            _issue(issues, "duplicate_device_id", f"{path}/id", device.id)
        device_ids.add(device.id)
        _check_text(
            device.id,
            issues=issues,
            path=f"{path}/id",
            code="missing_device_id",
        )
        if device.technology not in DEVICE_TECHNOLOGIES:
            _issue(
                issues,
                "invalid_device_technology",
                f"{path}/technology",
                repr(device.technology),
            )
        if (
            card.settings_scope == "full_configuration"
            and device.technology == "microprocessor"
            and not device.software_version.strip()
        ):
            _issue(
                issues,
                "missing_software_version",
                f"{path}/software_version",
                (
                    "full configuration of a microprocessor protection device "
                    "requires software_version"
                ),
            )
        for ref_index, ref in enumerate(device.provenance):
            _validate_source_reference(
                ref,
                known_source_ids=source_ids,
                issues=issues,
                path=f"{path}/provenance/{ref_index}",
            )
        if not device.provenance:
            _issue(
                issues,
                "missing_device_provenance",
                f"{path}/provenance",
                "device identity requires provenance",
            )
        seen_parameter_files: set[str] = set()
        for source_id in device.parameter_file_source_ids:
            if source_id in seen_parameter_files:
                _issue(
                    issues,
                    "duplicate_parameter_file_ref",
                    f"{path}/parameter_file_source_ids",
                    source_id,
                )
            seen_parameter_files.add(source_id)
            if source_id not in source_ids:
                _issue(
                    issues,
                    "unknown_parameter_file_source",
                    f"{path}/parameter_file_source_ids",
                    source_id,
                )
            elif source_types.get(source_id) != "parameter_file":
                _issue(
                    issues,
                    "invalid_parameter_file_source_type",
                    f"{path}/parameter_file_source_ids",
                    (
                        f"source {source_id!r} is "
                        f"{source_types.get(source_id)!r}, not 'parameter_file'"
                    ),
                )

    if not card.devices:
        _issue(
            issues,
            "missing_devices",
            "/devices",
            "at least one protection device is required",
        )

    measurement_input_ids: set[str] = set()
    for index, measurement in enumerate(card.measurement_inputs):
        path = f"/measurement_inputs/{index}"
        if measurement.id in measurement_input_ids:
            _issue(
                issues,
                "duplicate_measurement_input_id",
                f"{path}/id",
                measurement.id,
            )
        measurement_input_ids.add(measurement.id)
        for field_name, value in (
            ("id", measurement.id),
            ("semantic_key", measurement.semantic_key),
            ("source_label", measurement.source_label),
        ):
            _check_text(
                value,
                issues=issues,
                path=f"{path}/{field_name}",
                code=f"missing_measurement_{field_name}",
            )
        if measurement.quantity_kind not in QUANTITY_KINDS:
            _issue(
                issues,
                "invalid_measurement_quantity_kind",
                f"{path}/quantity_kind",
                repr(measurement.quantity_kind),
            )
        if measurement.basis not in SETTING_BASES:
            _issue(
                issues,
                "invalid_measurement_basis",
                f"{path}/basis",
                repr(measurement.basis),
            )
        if not measurement.provenance:
            _issue(
                issues,
                "missing_measurement_provenance",
                f"{path}/provenance",
                "measurement input requires source provenance",
            )
        for ref_index, ref in enumerate(measurement.provenance):
            _validate_source_reference(
                ref,
                known_source_ids=source_ids,
                issues=issues,
                path=f"{path}/provenance/{ref_index}",
            )

    function_ids: set[str] = set()
    stage_ids: set[str] = set()
    parameter_ids: set[str] = set()
    action_ids: set[str] = set()

    def validate_parameter(
        parameter: SettingParameter,
        *,
        path: str,
    ) -> None:
        if parameter.id in parameter_ids:
            _issue(
                issues,
                "duplicate_parameter_id",
                f"{path}/id",
                parameter.id,
            )
        parameter_ids.add(parameter.id)
        _check_text(
            parameter.id,
            issues=issues,
            path=f"{path}/id",
            code="missing_parameter_id",
        )
        _check_text(
            parameter.semantic_key,
            issues=issues,
            path=f"{path}/semantic_key",
            code="missing_parameter_semantic_key",
        )
        if parameter.role not in PARAMETER_ROLES:
            _issue(
                issues,
                "invalid_parameter_role",
                f"{path}/role",
                repr(parameter.role),
            )
        _validate_value(
            parameter.value,
            role=parameter.role,
            issues=issues,
            path=f"{path}/value",
        )
        if not parameter.provenance:
            _issue(
                issues,
                "missing_parameter_provenance",
                f"{path}/provenance",
                "setting parameter requires source provenance",
            )
        for ref_index, ref in enumerate(parameter.provenance):
            _validate_source_reference(
                ref,
                known_source_ids=source_ids,
                issues=issues,
                path=f"{path}/provenance/{ref_index}",
            )

    def validate_action(
        action: SettingAction,
        *,
        path: str,
    ) -> None:
        if action.id in action_ids:
            _issue(issues, "duplicate_action_id", f"{path}/id", action.id)
        action_ids.add(action.id)
        _check_text(
            action.id,
            issues=issues,
            path=f"{path}/id",
            code="missing_action_id",
        )
        if action.action_type not in ACTION_TYPES:
            _issue(
                issues,
                "invalid_action_type",
                f"{path}/action_type",
                repr(action.action_type),
            )
        if action.target_kind not in TARGET_KINDS:
            _issue(
                issues,
                "invalid_target_kind",
                f"{path}/target_kind",
                repr(action.target_kind),
            )
        _check_text(
            action.target_id,
            issues=issues,
            path=f"{path}/target_id",
            code="missing_action_target_id",
        )
        if not action.provenance:
            _issue(
                issues,
                "missing_action_provenance",
                f"{path}/provenance",
                "action association requires source provenance",
            )
        for ref_index, ref in enumerate(action.provenance):
            _validate_source_reference(
                ref,
                known_source_ids=source_ids,
                issues=issues,
                path=f"{path}/provenance/{ref_index}",
            )

    for function_index, function in enumerate(card.functions):
        path = f"/functions/{function_index}"
        if function.id in function_ids:
            _issue(
                issues,
                "duplicate_function_id",
                f"{path}/id",
                function.id,
            )
        function_ids.add(function.id)
        _check_text(
            function.id,
            issues=issues,
            path=f"{path}/id",
            code="missing_function_id",
        )
        if not _CONCEPT_RE.fullmatch(function.concept_id):
            _issue(
                issues,
                "invalid_protection_concept_id",
                f"{path}/concept_id",
                function.concept_id,
            )
        _check_text(
            function.source_name,
            issues=issues,
            path=f"{path}/source_name",
            code="missing_function_source_name",
        )
        if function.device_id not in device_ids:
            _issue(
                issues,
                "unknown_function_device",
                f"{path}/device_id",
                function.device_id,
            )
        seen_measurement_refs: set[str] = set()
        for ref_index, measurement_id in enumerate(
            function.measurement_input_ids
        ):
            ref_path = f"{path}/measurement_input_ids/{ref_index}"
            if measurement_id in seen_measurement_refs:
                _issue(
                    issues,
                    "duplicate_function_measurement_ref",
                    ref_path,
                    measurement_id,
                )
            seen_measurement_refs.add(measurement_id)
            if measurement_id not in measurement_input_ids:
                _issue(
                    issues,
                    "unknown_function_measurement_input",
                    ref_path,
                    measurement_id,
                )
        if not function.provenance:
            _issue(
                issues,
                "missing_function_provenance",
                f"{path}/provenance",
                "protection function requires source provenance",
            )
        for ref_index, ref in enumerate(function.provenance):
            _validate_source_reference(
                ref,
                known_source_ids=source_ids,
                issues=issues,
                path=f"{path}/provenance/{ref_index}",
            )
        for parameter_index, parameter in enumerate(function.parameters):
            validate_parameter(
                parameter,
                path=f"{path}/parameters/{parameter_index}",
            )
        for action_index, action in enumerate(function.actions):
            validate_action(
                action,
                path=f"{path}/actions/{action_index}",
            )
        for stage_index, stage in enumerate(function.stages):
            stage_path = f"{path}/stages/{stage_index}"
            if stage.id in stage_ids:
                _issue(
                    issues,
                    "duplicate_stage_id",
                    f"{stage_path}/id",
                    stage.id,
                )
            stage_ids.add(stage.id)
            _check_text(
                stage.id,
                issues=issues,
                path=f"{stage_path}/id",
                code="missing_stage_id",
            )
            _check_text(
                stage.source_name,
                issues=issues,
                path=f"{stage_path}/source_name",
                code="missing_stage_source_name",
            )
            if not stage.provenance:
                _issue(
                    issues,
                    "missing_stage_provenance",
                    f"{stage_path}/provenance",
                    "stage requires source provenance",
                )
            for ref_index, ref in enumerate(stage.provenance):
                _validate_source_reference(
                    ref,
                    known_source_ids=source_ids,
                    issues=issues,
                    path=f"{stage_path}/provenance/{ref_index}",
                )
            for parameter_index, parameter in enumerate(stage.parameters):
                validate_parameter(
                    parameter,
                    path=f"{stage_path}/parameters/{parameter_index}",
                )
            for action_index, action in enumerate(stage.actions):
                validate_action(
                    action,
                    path=f"{stage_path}/actions/{action_index}",
                )

    if not card.functions:
        _issue(
            issues,
            "missing_functions",
            "/functions",
            "at least one protection function setting is required",
        )

    for function_index, function in enumerate(card.functions):
        for action_index, action in enumerate(function.actions):
            path = f"/functions/{function_index}/actions/{action_index}"
            if (
                action.target_kind == "protection_device"
                and action.target_id not in device_ids
            ):
                _issue(
                    issues,
                    "unknown_action_device_target",
                    f"{path}/target_id",
                    action.target_id,
                )
            if (
                action.target_kind == "protection_function"
                and action.target_id not in function_ids
            ):
                _issue(
                    issues,
                    "unknown_action_function_target",
                    f"{path}/target_id",
                    action.target_id,
                )
        for stage_index, stage in enumerate(function.stages):
            for action_index, action in enumerate(stage.actions):
                path = (
                    f"/functions/{function_index}/stages/{stage_index}"
                    f"/actions/{action_index}"
                )
                if (
                    action.target_kind == "protection_device"
                    and action.target_id not in device_ids
                ):
                    _issue(
                        issues,
                        "unknown_action_device_target",
                        f"{path}/target_id",
                        action.target_id,
                    )
                if (
                    action.target_kind == "protection_function"
                    and action.target_id not in function_ids
                ):
                    _issue(
                        issues,
                        "unknown_action_function_target",
                        f"{path}/target_id",
                        action.target_id,
                    )

    return tuple(sorted(set(issues)))


def _ref_to_dict(ref: SourceReference) -> dict[str, object]:
    return {
        "source_id": ref.source_id,
        "locator_kind": ref.locator_kind,
        "locator": ref.locator,
    }


def _value_to_dict(value: SettingValue) -> dict[str, object]:
    result: dict[str, object] = {
        "kind": value.kind,
        "raw_text": value.raw_text,
    }
    if value.kind == "quantity":
        result.update(
            {
                "source_value": value.source_value,
                "source_unit": value.source_unit,
                "quantity_kind": value.quantity_kind,
                "basis": value.basis,
                "normalized_value": value.normalized_value,
                "normalized_unit": value.normalized_unit,
            }
        )
    elif value.kind == "boolean":
        result["boolean_value"] = value.boolean_value
    elif value.kind == "enum":
        result["enum_value"] = value.enum_value
    elif value.kind == "text":
        result["text_value"] = value.text_value
    return result


def setting_card_to_dict(card: ProtectionSettingCard) -> dict[str, object]:
    def refs(items: Sequence[SourceReference]) -> list[dict[str, object]]:
        return [
            _ref_to_dict(item)
            for item in sorted(
                items,
                key=lambda item: (
                    item.source_id,
                    item.locator_kind,
                    item.locator,
                ),
            )
        ]

    def parameter(item: SettingParameter) -> dict[str, object]:
        return {
            "id": item.id,
            "semantic_key": item.semantic_key,
            "role": item.role,
            "value": _value_to_dict(item.value),
            "provenance": refs(item.provenance),
            "notes": item.notes,
        }

    def action(item: SettingAction) -> dict[str, object]:
        return {
            "id": item.id,
            "action_type": item.action_type,
            "target_kind": item.target_kind,
            "target_id": item.target_id,
            "source_label": item.source_label,
            "provenance": refs(item.provenance),
            "notes": item.notes,
        }

    def stage(item: ProtectionStage) -> dict[str, object]:
        return {
            "id": item.id,
            "source_name": item.source_name,
            "enabled": item.enabled,
            "measurement_input_ids": sorted(item.measurement_input_ids),
            "parameters": [
                parameter(value)
                for value in sorted(item.parameters, key=lambda value: value.id)
            ],
            "actions": [
                action(value)
                for value in sorted(item.actions, key=lambda value: value.id)
            ],
            "provenance": refs(item.provenance),
        }

    def function(item: ProtectionFunctionSettings) -> dict[str, object]:
        return {
            "id": item.id,
            "concept_id": item.concept_id,
            "source_name": item.source_name,
            "device_id": item.device_id,
            "enabled": item.enabled,
            "parameters": [
                parameter(value)
                for value in sorted(item.parameters, key=lambda value: value.id)
            ],
            "stages": [
                stage(value)
                for value in sorted(item.stages, key=lambda value: value.id)
            ],
            "actions": [
                action(value)
                for value in sorted(item.actions, key=lambda value: value.id)
            ],
            "provenance": refs(item.provenance),
        }

    return {
        "schema_version": card.schema_version,
        "card_id": card.card_id,
        "card_revision": card.card_revision,
        "site_id": card.site_id,
        "settings_scope": card.settings_scope,
        "lifecycle_status": card.lifecycle_status,
        "primary_source_id": card.primary_source_id,
        "protected_object_ids": sorted(card.protected_object_ids),
        "sources": [
            {
                "id": item.id,
                "document_type": item.document_type,
                "title": item.title,
                "revision": item.revision,
                "sha256": item.sha256,
                "issue_date": item.issue_date,
                "source_uri": item.source_uri,
                "notes": item.notes,
            }
            for item in sorted(card.sources, key=lambda item: item.id)
        ],
        "measurement_inputs": [
            {
                "id": item.id,
                "semantic_key": item.semantic_key,
                "quantity_kind": item.quantity_kind,
                "basis": item.basis,
                "source_label": item.source_label,
                "source_object_id": item.source_object_id,
                "terminal_id": item.terminal_id,
                "provenance": refs(item.provenance),
                "notes": item.notes,
            }
            for item in sorted(
                card.measurement_inputs,
                key=lambda item: item.id,
            )
        ],
        "devices": [
            {
                "id": item.id,
                "technology": item.technology,
                "dispatch_name": item.dispatch_name,
                "manufacturer": item.manufacturer,
                "model": item.model,
                "software_version": item.software_version,
                "parameter_file_source_ids": sorted(
                    item.parameter_file_source_ids
                ),
                "provenance": refs(item.provenance),
            }
            for item in sorted(card.devices, key=lambda item: item.id)
        ],
        "functions": [
            function(item)
            for item in sorted(card.functions, key=lambda item: item.id)
        ],
        "notes": card.notes,
    }


def canonical_setting_card_bytes(card: ProtectionSettingCard) -> bytes:
    return (
        json.dumps(
            setting_card_to_dict(card),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def setting_card_fingerprint(card: ProtectionSettingCard) -> str:
    return hashlib.sha256(canonical_setting_card_bytes(card)).hexdigest()


def _display_path(path: str) -> str:
    return path or "/"


def _expect_mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ProtectionSettingDecodeError(
            f"{_display_path(path)}: expected object"
        )
    return value


def _expect_exact_mapping(
    value: object,
    path: str,
    *,
    allowed: frozenset[str],
) -> Mapping[str, object]:
    data = _expect_mapping(value, path)
    extra = sorted(set(data) - allowed)
    if extra:
        raise ProtectionSettingDecodeError(
            f"{_display_path(path)}: unexpected fields {extra!r}"
        )
    return data


def _expect_list(value: object, path: str) -> list[object]:
    if not isinstance(value, list):
        raise ProtectionSettingDecodeError(
            f"{_display_path(path)}: expected array"
        )
    return value


def _text(
    mapping: Mapping[str, object],
    key: str,
    path: str,
) -> str:
    if key not in mapping:
        raise ProtectionSettingDecodeError(f"{path}/{key}: missing")
    value = mapping[key]
    if not isinstance(value, str):
        raise ProtectionSettingDecodeError(
            f"{path}/{key}: expected string"
        )
    return value


def _optional_bool(
    mapping: Mapping[str, object],
    key: str,
    path: str,
) -> bool | None:
    if key not in mapping:
        raise ProtectionSettingDecodeError(f"{path}/{key}: missing")
    value = mapping[key]
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ProtectionSettingDecodeError(
            f"{path}/{key}: expected boolean or null"
        )
    return value


_ROOT_FIELDS = frozenset(
    {
        "schema_version",
        "card_id",
        "card_revision",
        "site_id",
        "settings_scope",
        "lifecycle_status",
        "primary_source_id",
        "protected_object_ids",
        "sources",
        "measurement_inputs",
        "devices",
        "functions",
        "notes",
    }
)
_SOURCE_FIELDS = frozenset(
    {
        "id",
        "document_type",
        "title",
        "revision",
        "sha256",
        "issue_date",
        "source_uri",
        "notes",
    }
)
_DEVICE_FIELDS = frozenset(
    {
        "id",
        "technology",
        "dispatch_name",
        "manufacturer",
        "model",
        "software_version",
        "parameter_file_source_ids",
        "provenance",
    }
)
_REFERENCE_FIELDS = frozenset({"source_id", "locator_kind", "locator"})
_MEASUREMENT_FIELDS = frozenset(
    {
        "id",
        "semantic_key",
        "quantity_kind",
        "basis",
        "source_label",
        "source_object_id",
        "terminal_id",
        "provenance",
        "notes",
    }
)
_PARAMETER_FIELDS = frozenset(
    {"id", "semantic_key", "role", "value", "provenance", "notes"}
)
_ACTION_FIELDS = frozenset(
    {
        "id",
        "action_type",
        "target_kind",
        "target_id",
        "source_label",
        "provenance",
        "notes",
    }
)
_STAGE_FIELDS = frozenset(
    {"id", "source_name", "enabled", "parameters", "actions", "provenance"}
)
_FUNCTION_FIELDS = frozenset(
    {
        "id",
        "concept_id",
        "source_name",
        "device_id",
        "enabled",
        "measurement_input_ids",
        "parameters",
        "stages",
        "actions",
        "provenance",
    }
)
_VALUE_FIELDS_BY_KIND = {
    "quantity": frozenset(
        {
            "kind",
            "raw_text",
            "source_value",
            "source_unit",
            "quantity_kind",
            "basis",
            "normalized_value",
            "normalized_unit",
        }
    ),
    "boolean": frozenset({"kind", "raw_text", "boolean_value"}),
    "enum": frozenset({"kind", "raw_text", "enum_value"}),
    "text": frozenset({"kind", "raw_text", "text_value"}),
}
_ALL_VALUE_FIELDS = frozenset().union(*_VALUE_FIELDS_BY_KIND.values())


def _string_array(value: object, path: str) -> tuple[str, ...]:
    items = _expect_list(value, path)
    result: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, str):
            raise ProtectionSettingDecodeError(
                f"{path}/{index}: expected string"
            )
        result.append(item)
    return tuple(result)


def _refs(value: object, path: str) -> tuple[SourceReference, ...]:
    items = _expect_list(value, path)
    result: list[SourceReference] = []
    for index, raw in enumerate(items):
        item_path = f"{path}/{index}"
        data = _expect_exact_mapping(
            raw,
            item_path,
            allowed=_REFERENCE_FIELDS,
        )
        result.append(
            SourceReference(
                source_id=_text(data, "source_id", item_path),
                locator_kind=_text(data, "locator_kind", item_path),
                locator=_text(data, "locator", item_path),
            )
        )
    return tuple(result)


def _setting_value(value: object, path: str) -> SettingValue:
    base = _expect_mapping(value, path)
    kind = _text(base, "kind", path)
    allowed = _VALUE_FIELDS_BY_KIND.get(kind, _ALL_VALUE_FIELDS)
    data = _expect_exact_mapping(value, path, allowed=allowed)

    if kind == "quantity":
        return SettingValue(
            kind=kind,
            raw_text=_text(data, "raw_text", path),
            source_value=_text(data, "source_value", path),
            source_unit=_text(data, "source_unit", path),
            quantity_kind=_text(data, "quantity_kind", path),
            basis=_text(data, "basis", path),
            normalized_value=_text(data, "normalized_value", path),
            normalized_unit=_text(data, "normalized_unit", path),
        )
    if kind == "boolean":
        boolean_value = data.get("boolean_value")
        if not isinstance(boolean_value, bool):
            raise ProtectionSettingDecodeError(
                f"{path}/boolean_value: expected boolean"
            )
        return SettingValue(
            kind=kind,
            raw_text=_text(data, "raw_text", path),
            boolean_value=boolean_value,
        )
    if kind == "enum":
        return SettingValue(
            kind=kind,
            raw_text=_text(data, "raw_text", path),
            enum_value=_text(data, "enum_value", path),
        )
    if kind == "text":
        return SettingValue(
            kind=kind,
            raw_text=_text(data, "raw_text", path),
            text_value=_text(data, "text_value", path),
        )

    # Preserve deterministic validation of an unknown kind while still rejecting
    # arbitrary fields not part of any versioned setting-value shape.
    return SettingValue(
        kind=kind,
        raw_text=_text(data, "raw_text", path),
    )


def _parameter(value: object, path: str) -> SettingParameter:
    data = _expect_exact_mapping(
        value,
        path,
        allowed=_PARAMETER_FIELDS,
    )
    return SettingParameter(
        id=_text(data, "id", path),
        semantic_key=_text(data, "semantic_key", path),
        role=_text(data, "role", path),
        value=_setting_value(data.get("value"), f"{path}/value"),
        provenance=_refs(data.get("provenance"), f"{path}/provenance"),
        notes=_text(data, "notes", path),
    )


def _action(value: object, path: str) -> SettingAction:
    data = _expect_exact_mapping(
        value,
        path,
        allowed=_ACTION_FIELDS,
    )
    return SettingAction(
        id=_text(data, "id", path),
        action_type=_text(data, "action_type", path),
        target_kind=_text(data, "target_kind", path),
        target_id=_text(data, "target_id", path),
        source_label=_text(data, "source_label", path),
        provenance=_refs(data.get("provenance"), f"{path}/provenance"),
        notes=_text(data, "notes", path),
    )


def _stage(value: object, path: str) -> ProtectionStage:
    data = _expect_exact_mapping(
        value,
        path,
        allowed=_STAGE_FIELDS,
    )
    return ProtectionStage(
        id=_text(data, "id", path),
        source_name=_text(data, "source_name", path),
        enabled=_optional_bool(data, "enabled", path),
        measurement_input_ids=_string_array(
            data.get("measurement_input_ids"),
            f"{path}/measurement_input_ids",
        ),
        parameters=tuple(
            _parameter(item, f"{path}/parameters/{index}")
            for index, item in enumerate(
                _expect_list(data.get("parameters"), f"{path}/parameters")
            )
        ),
        actions=tuple(
            _action(item, f"{path}/actions/{index}")
            for index, item in enumerate(
                _expect_list(data.get("actions"), f"{path}/actions")
            )
        ),
        provenance=_refs(data.get("provenance"), f"{path}/provenance"),
    )


def _function(value: object, path: str) -> ProtectionFunctionSettings:
    data = _expect_exact_mapping(
        value,
        path,
        allowed=_FUNCTION_FIELDS,
    )
    return ProtectionFunctionSettings(
        id=_text(data, "id", path),
        concept_id=_text(data, "concept_id", path),
        source_name=_text(data, "source_name", path),
        device_id=_text(data, "device_id", path),
        enabled=_optional_bool(data, "enabled", path),
        parameters=tuple(
            _parameter(item, f"{path}/parameters/{index}")
            for index, item in enumerate(
                _expect_list(data.get("parameters"), f"{path}/parameters")
            )
        ),
        stages=tuple(
            _stage(item, f"{path}/stages/{index}")
            for index, item in enumerate(
                _expect_list(data.get("stages"), f"{path}/stages")
            )
        ),
        actions=tuple(
            _action(item, f"{path}/actions/{index}")
            for index, item in enumerate(
                _expect_list(data.get("actions"), f"{path}/actions")
            )
        ),
        provenance=_refs(data.get("provenance"), f"{path}/provenance"),
    )


def _source_document(value: object, path: str) -> SourceDocument:
    data = _expect_exact_mapping(
        value,
        path,
        allowed=_SOURCE_FIELDS,
    )
    return SourceDocument(
        id=_text(data, "id", path),
        document_type=_text(data, "document_type", path),
        title=_text(data, "title", path),
        revision=_text(data, "revision", path),
        sha256=_text(data, "sha256", path),
        issue_date=_text(data, "issue_date", path),
        source_uri=_text(data, "source_uri", path),
        notes=_text(data, "notes", path),
    )


def _measurement_input(value: object, path: str) -> MeasurementInput:
    data = _expect_exact_mapping(
        value,
        path,
        allowed=_MEASUREMENT_FIELDS,
    )
    return MeasurementInput(
        id=_text(data, "id", path),
        semantic_key=_text(data, "semantic_key", path),
        quantity_kind=_text(data, "quantity_kind", path),
        basis=_text(data, "basis", path),
        source_label=_text(data, "source_label", path),
        source_object_id=_text(data, "source_object_id", path),
        terminal_id=_text(data, "terminal_id", path),
        provenance=_refs(data.get("provenance"), f"{path}/provenance"),
        notes=_text(data, "notes", path),
    )


def _device(value: object, path: str) -> ProtectionDevice:
    data = _expect_exact_mapping(
        value,
        path,
        allowed=_DEVICE_FIELDS,
    )
    return ProtectionDevice(
        id=_text(data, "id", path),
        technology=_text(data, "technology", path),
        dispatch_name=_text(data, "dispatch_name", path),
        manufacturer=_text(data, "manufacturer", path),
        model=_text(data, "model", path),
        software_version=_text(data, "software_version", path),
        parameter_file_source_ids=_string_array(
            data.get("parameter_file_source_ids"),
            f"{path}/parameter_file_source_ids",
        ),
        provenance=_refs(data.get("provenance"), f"{path}/provenance"),
    )


def setting_card_from_dict(
    value: object,
    *,
    require_valid: bool = True,
) -> ProtectionSettingCard:
    data = _expect_exact_mapping(
        value,
        "",
        allowed=_ROOT_FIELDS,
    )
    card = ProtectionSettingCard(
        schema_version=_text(data, "schema_version", ""),
        card_id=_text(data, "card_id", ""),
        card_revision=_text(data, "card_revision", ""),
        site_id=_text(data, "site_id", ""),
        settings_scope=_text(data, "settings_scope", ""),
        lifecycle_status=_text(data, "lifecycle_status", ""),
        primary_source_id=_text(data, "primary_source_id", ""),
        protected_object_ids=_string_array(
            data.get("protected_object_ids"),
            "/protected_object_ids",
        ),
        sources=tuple(
            _source_document(item, f"/sources/{index}")
            for index, item in enumerate(
                _expect_list(data.get("sources"), "/sources")
            )
        ),
        measurement_inputs=tuple(
            _measurement_input(item, f"/measurement_inputs/{index}")
            for index, item in enumerate(
                _expect_list(
                    data.get("measurement_inputs"),
                    "/measurement_inputs",
                )
            )
        ),
        devices=tuple(
            _device(item, f"/devices/{index}")
            for index, item in enumerate(
                _expect_list(data.get("devices"), "/devices")
            )
        ),
        functions=tuple(
            _function(item, f"/functions/{index}")
            for index, item in enumerate(
                _expect_list(data.get("functions"), "/functions")
            )
        ),
        notes=_text(data, "notes", ""),
    )

    if require_valid:
        issues = validate_setting_card(card)
        if issues:
            raise ProtectionSettingValidationError(issues)
    return card
