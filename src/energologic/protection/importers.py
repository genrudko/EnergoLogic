from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from typing import Mapping, Protocol

from .model import (
    ProtectionDevice,
    ProtectionFunctionSettings,
    ProtectionSettingCard,
    ProtectionSettingDecodeError,
    ProtectionSettingValidationError,
    ProtectionStage,
    SettingAction,
    SettingParameter,
    SettingValue,
    SourceDocument,
    SourceReference,
    make_quantity_value,
    setting_card_from_dict,
    validate_setting_card,
)


class ProtectionSettingImportError(ValueError):
    def __init__(self, code: str, locator: str, message: str):
        self.code = code
        self.locator = locator
        self.message = message
        super().__init__(f"{code}@{locator}: {message}")


class ProtectionSettingsSourceAdapter(Protocol):
    def import_text(self, text: str) -> ProtectionSettingCard:
        ...


def _reject_duplicate_object_pairs(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ProtectionSettingImportError(
                "duplicate_json_key",
                "$",
                f"duplicate JSON object key {key!r}",
            )
        result[key] = value
    return result


class JsonSettingCardAdapter:
    def import_text(self, text: str) -> ProtectionSettingCard:
        try:
            data = json.loads(
                text,
                object_pairs_hook=_reject_duplicate_object_pairs,
            )
        except ProtectionSettingImportError:
            raise
        except json.JSONDecodeError as exc:
            raise ProtectionSettingImportError(
                "invalid_json",
                f"line {exc.lineno}, column {exc.colno}",
                exc.msg,
            ) from exc

        try:
            return setting_card_from_dict(data, require_valid=True)
        except (
            ProtectionSettingDecodeError,
            ProtectionSettingValidationError,
        ) as exc:
            raise ProtectionSettingImportError(
                "invalid_setting_card",
                "$",
                str(exc),
            ) from exc


@dataclass(frozen=True, slots=True)
class CsvColumnMap:
    function_id: str
    function_concept_id: str
    function_name: str
    device_id: str
    stage_id: str
    stage_name: str
    parameter_id: str
    semantic_key: str
    role: str
    value_kind: str
    value: str
    unit: str
    quantity_kind: str
    basis: str
    function_enabled: str | None = None
    stage_enabled: str | None = None


@dataclass(frozen=True, slots=True)
class CsvDeviceSpec:
    id: str
    technology: str
    dispatch_name: str = ""
    manufacturer: str = ""
    model: str = ""
    software_version: str = ""
    parameter_file_source_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CsvImportSpec:
    card_id: str
    card_revision: str
    site_id: str
    settings_scope: str
    lifecycle_status: str
    protected_object_ids: tuple[str, ...]
    source_id: str
    source_document_type: str
    source_title: str
    source_revision: str
    devices: tuple[CsvDeviceSpec, ...]
    columns: CsvColumnMap
    source_issue_date: str = ""
    source_uri: str = ""
    source_notes: str = ""
    card_notes: str = ""
    delimiter: str = ","
    decimal_separator: str = "."
    true_tokens: tuple[str, ...] = ("true", "1")
    false_tokens: tuple[str, ...] = ("false", "0")


@dataclass(slots=True)
class _MutableStage:
    id: str
    source_name: str
    enabled: bool | None
    provenance: SourceReference
    parameters: list[SettingParameter]


@dataclass(slots=True)
class _MutableFunction:
    id: str
    concept_id: str
    source_name: str
    device_id: str
    enabled: bool | None
    provenance: SourceReference
    parameters: list[SettingParameter]
    stages: dict[str, _MutableStage]


class CsvSettingCardAdapter:
    def __init__(self, spec: CsvImportSpec):
        self.spec = spec

    def _required_headers(self) -> tuple[str, ...]:
        columns = self.spec.columns
        required = [
            columns.function_id,
            columns.function_concept_id,
            columns.function_name,
            columns.device_id,
            columns.stage_id,
            columns.stage_name,
            columns.parameter_id,
            columns.semantic_key,
            columns.role,
            columns.value_kind,
            columns.value,
            columns.unit,
            columns.quantity_kind,
            columns.basis,
        ]
        if columns.function_enabled is not None:
            required.append(columns.function_enabled)
        if columns.stage_enabled is not None:
            required.append(columns.stage_enabled)
        return tuple(required)

    def _cell(
        self,
        row: Mapping[str, str | None],
        column: str,
        *,
        line_number: int,
    ) -> str:
        value = row.get(column)
        if value is None:
            raise ProtectionSettingImportError(
                "missing_csv_column_value",
                f"row {line_number}; column {column}",
                "mapped CSV column has no value",
            )
        return value

    def _required_text(
        self,
        row: Mapping[str, str | None],
        column: str,
        *,
        line_number: int,
    ) -> str:
        raw = self._cell(row, column, line_number=line_number)
        value = raw.strip()
        if not value:
            raise ProtectionSettingImportError(
                "missing_required_value",
                f"row {line_number}; column {column}",
                "required mapped CSV value is empty",
            )
        return value

    def _optional_bool(
        self,
        row: Mapping[str, str | None],
        column: str | None,
        *,
        line_number: int,
    ) -> bool | None:
        if column is None:
            return None
        raw = self._cell(row, column, line_number=line_number).strip()
        if not raw:
            return None

        key = raw.casefold()
        true_values = {item.casefold() for item in self.spec.true_tokens}
        false_values = {item.casefold() for item in self.spec.false_tokens}
        if true_values & false_values:
            raise ProtectionSettingImportError(
                "invalid_boolean_token_config",
                "csv spec",
                "true_tokens and false_tokens overlap",
            )
        if key in true_values:
            return True
        if key in false_values:
            return False
        raise ProtectionSettingImportError(
            "invalid_boolean_value",
            f"row {line_number}; column {column}",
            (
                f"value {raw!r} is not in explicitly configured "
                "true/false token sets"
            ),
        )

    def _setting_value(
        self,
        row: Mapping[str, str | None],
        *,
        line_number: int,
    ) -> SettingValue:
        columns = self.spec.columns
        kind = self._required_text(
            row,
            columns.value_kind,
            line_number=line_number,
        )
        raw_value = self._cell(
            row,
            columns.value,
            line_number=line_number,
        )
        stripped = raw_value.strip()

        if kind == "quantity":
            unit = self._required_text(
                row,
                columns.unit,
                line_number=line_number,
            )
            quantity_kind = self._required_text(
                row,
                columns.quantity_kind,
                line_number=line_number,
            )
            basis = self._required_text(
                row,
                columns.basis,
                line_number=line_number,
            )
            try:
                return make_quantity_value(
                    raw_text=raw_value,
                    source_value=stripped,
                    source_unit=unit,
                    quantity_kind=quantity_kind,
                    basis=basis,
                    decimal_separator=self.spec.decimal_separator,
                )
            except ValueError as exc:
                raise ProtectionSettingImportError(
                    "invalid_quantity",
                    f"row {line_number}; column {columns.value}",
                    str(exc),
                ) from exc

        if kind == "boolean":
            if not stripped:
                raise ProtectionSettingImportError(
                    "missing_boolean_value",
                    f"row {line_number}; column {columns.value}",
                    "boolean value is empty",
                )
            key = stripped.casefold()
            true_values = {item.casefold() for item in self.spec.true_tokens}
            false_values = {item.casefold() for item in self.spec.false_tokens}
            if true_values & false_values:
                raise ProtectionSettingImportError(
                    "invalid_boolean_token_config",
                    "csv spec",
                    "true_tokens and false_tokens overlap",
                )
            if key in true_values:
                normalized = True
            elif key in false_values:
                normalized = False
            else:
                raise ProtectionSettingImportError(
                    "invalid_boolean_value",
                    f"row {line_number}; column {columns.value}",
                    (
                        f"value {stripped!r} is not in explicitly configured "
                        "true/false token sets"
                    ),
                )
            return SettingValue(
                kind="boolean",
                raw_text=raw_value,
                boolean_value=normalized,
            )

        if kind == "enum":
            if not stripped:
                raise ProtectionSettingImportError(
                    "missing_enum_value",
                    f"row {line_number}; column {columns.value}",
                    "enum value is empty",
                )
            return SettingValue(
                kind="enum",
                raw_text=raw_value,
                enum_value=stripped,
            )

        if kind == "text":
            if not stripped:
                raise ProtectionSettingImportError(
                    "missing_text_value",
                    f"row {line_number}; column {columns.value}",
                    "text value is empty",
                )
            return SettingValue(
                kind="text",
                raw_text=raw_value,
                text_value=stripped,
            )

        raise ProtectionSettingImportError(
            "unsupported_value_kind",
            f"row {line_number}; column {columns.value_kind}",
            repr(kind),
        )

    def import_text(self, text: str) -> ProtectionSettingCard:
        if not isinstance(text, str) or not text:
            raise ProtectionSettingImportError(
                "empty_source",
                "csv",
                "CSV source text is empty",
            )
        if len(self.spec.delimiter) != 1:
            raise ProtectionSettingImportError(
                "invalid_delimiter",
                "csv spec",
                "CSV delimiter must be one character",
            )
        if self.spec.decimal_separator not in {".", ","}:
            raise ProtectionSettingImportError(
                "invalid_decimal_separator",
                "csv spec",
                "decimal_separator must be '.' or ','",
            )

        reader = csv.DictReader(
            io.StringIO(text),
            delimiter=self.spec.delimiter,
        )
        headers = tuple(reader.fieldnames or ())
        missing_headers = [
            name for name in self._required_headers() if name not in headers
        ]
        if missing_headers:
            raise ProtectionSettingImportError(
                "missing_csv_headers",
                "header",
                f"missing explicitly mapped headers: {missing_headers!r}",
            )

        source = SourceDocument(
            id=self.spec.source_id,
            document_type=self.spec.source_document_type,
            title=self.spec.source_title,
            revision=self.spec.source_revision,
            sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            issue_date=self.spec.source_issue_date,
            source_uri=self.spec.source_uri,
            notes=self.spec.source_notes,
        )
        document_ref = SourceReference(
            source_id=source.id,
            locator_kind="document",
            locator="CSV source document",
        )
        devices = tuple(
            ProtectionDevice(
                id=item.id,
                technology=item.technology,
                dispatch_name=item.dispatch_name,
                manufacturer=item.manufacturer,
                model=item.model,
                software_version=item.software_version,
                parameter_file_source_ids=item.parameter_file_source_ids,
                provenance=(document_ref,),
            )
            for item in self.spec.devices
        )

        functions: dict[str, _MutableFunction] = {}
        columns = self.spec.columns
        row_count = 0

        for line_number, row in enumerate(reader, start=2):
            row_count += 1
            function_id = self._required_text(
                row,
                columns.function_id,
                line_number=line_number,
            )
            concept_id = self._required_text(
                row,
                columns.function_concept_id,
                line_number=line_number,
            )
            function_name = self._required_text(
                row,
                columns.function_name,
                line_number=line_number,
            )
            device_id = self._required_text(
                row,
                columns.device_id,
                line_number=line_number,
            )
            function_enabled = self._optional_bool(
                row,
                columns.function_enabled,
                line_number=line_number,
            )
            function_ref = SourceReference(
                source_id=source.id,
                locator_kind="csv_row",
                locator=f"row {line_number}",
            )

            function = functions.get(function_id)
            if function is None:
                function = _MutableFunction(
                    id=function_id,
                    concept_id=concept_id,
                    source_name=function_name,
                    device_id=device_id,
                    enabled=function_enabled,
                    provenance=function_ref,
                    parameters=[],
                    stages={},
                )
                functions[function_id] = function
            elif (
                function.concept_id != concept_id
                or function.source_name != function_name
                or function.device_id != device_id
                or function.enabled != function_enabled
            ):
                raise ProtectionSettingImportError(
                    "inconsistent_function_identity",
                    f"row {line_number}",
                    (
                        f"repeated function_id {function_id!r} has "
                        "inconsistent concept/name/device/enabled fields"
                    ),
                )

            parameter_id = self._required_text(
                row,
                columns.parameter_id,
                line_number=line_number,
            )
            semantic_key = self._required_text(
                row,
                columns.semantic_key,
                line_number=line_number,
            )
            role = self._required_text(
                row,
                columns.role,
                line_number=line_number,
            )
            parameter = SettingParameter(
                id=parameter_id,
                semantic_key=semantic_key,
                role=role,
                value=self._setting_value(row, line_number=line_number),
                provenance=(
                    SourceReference(
                        source_id=source.id,
                        locator_kind="csv_cell",
                        locator=(
                            f"row {line_number}; column {columns.value}"
                        ),
                    ),
                ),
            )

            stage_id = self._cell(
                row,
                columns.stage_id,
                line_number=line_number,
            ).strip()
            if not stage_id:
                function.parameters.append(parameter)
                continue

            stage_name = self._required_text(
                row,
                columns.stage_name,
                line_number=line_number,
            )
            stage_enabled = self._optional_bool(
                row,
                columns.stage_enabled,
                line_number=line_number,
            )
            stage = function.stages.get(stage_id)
            if stage is None:
                stage = _MutableStage(
                    id=stage_id,
                    source_name=stage_name,
                    enabled=stage_enabled,
                    provenance=function_ref,
                    parameters=[],
                )
                function.stages[stage_id] = stage
            elif (
                stage.source_name != stage_name
                or stage.enabled != stage_enabled
            ):
                raise ProtectionSettingImportError(
                    "inconsistent_stage_identity",
                    f"row {line_number}",
                    (
                        f"repeated stage_id {stage_id!r} has inconsistent "
                        "name/enabled fields"
                    ),
                )
            stage.parameters.append(parameter)

        if row_count == 0:
            raise ProtectionSettingImportError(
                "empty_data_rows",
                "csv",
                "CSV contains a header but no setting rows",
            )

        frozen_functions: list[ProtectionFunctionSettings] = []
        for function_id in sorted(functions):
            item = functions[function_id]
            stages = tuple(
                ProtectionStage(
                    id=stage.id,
                    source_name=stage.source_name,
                    enabled=stage.enabled,
                    parameters=tuple(stage.parameters),
                    actions=(),
                    provenance=(stage.provenance,),
                )
                for stage in (
                    item.stages[key]
                    for key in sorted(item.stages)
                )
            )
            frozen_functions.append(
                ProtectionFunctionSettings(
                    id=item.id,
                    concept_id=item.concept_id,
                    source_name=item.source_name,
                    device_id=item.device_id,
                    enabled=item.enabled,
                    parameters=tuple(item.parameters),
                    stages=stages,
                    actions=(),
                    provenance=(item.provenance,),
                )
            )

        card = ProtectionSettingCard(
            schema_version="protection-settings-v1",
            card_id=self.spec.card_id,
            card_revision=self.spec.card_revision,
            site_id=self.spec.site_id,
            settings_scope=self.spec.settings_scope,
            lifecycle_status=self.spec.lifecycle_status,
            primary_source_id=source.id,
            protected_object_ids=self.spec.protected_object_ids,
            sources=(source,),
            devices=devices,
            functions=tuple(frozen_functions),
            notes=self.spec.card_notes,
        )

        issues = validate_setting_card(card)
        if issues:
            raise ProtectionSettingValidationError(issues)
        return card
