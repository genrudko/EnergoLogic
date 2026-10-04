from __future__ import annotations

import unittest

from energologic.protection import (
    CsvColumnMap,
    CsvDeviceSpec,
    CsvImportSpec,
    CsvSettingCardAdapter,
    JsonSettingCardAdapter,
    ProtectionSettingImportError,
)


COLUMNS = CsvColumnMap(
    function_id="function_id",
    function_concept_id="concept",
    function_name="function_name",
    device_id="device_id",
    function_enabled="function_enabled",
    stage_id="stage_id",
    stage_name="stage_name",
    stage_enabled="stage_enabled",
    parameter_id="parameter_id",
    semantic_key="semantic_key",
    role="role",
    value_kind="value_kind",
    value="value",
    unit="unit",
    quantity_kind="quantity_kind",
    basis="basis",
)


def spec() -> CsvImportSpec:
    return CsvImportSpec(
        card_id="setting-card:test:csv",
        card_revision="r1",
        site_id="site:test",
        settings_scope="partial_configuration",
        lifecycle_status="approved",
        protected_object_ids=("line:test",),
        source_id="source:test:csv",
        source_document_type="setting_card",
        source_title="Synthetic CSV setting card",
        source_revision="r1",
        devices=(
            CsvDeviceSpec(
                id="ied:test",
                technology="microprocessor",
                dispatch_name="РЗА тест",
                manufacturer="Synthetic",
                model="RZA-CSV",
                software_version="1.0",
            ),
        ),
        columns=COLUMNS,
        delimiter=";",
        decimal_separator=",",
        true_tokens=("Вкл",),
        false_tokens=("Откл",),
    )


CSV_TEXT = """function_id;concept;function_name;device_id;function_enabled;stage_id;stage_name;stage_enabled;parameter_id;semantic_key;role;value_kind;value;unit;quantity_kind;basis
function:test:mtz;protection.overcurrent;МТЗ;ied:test;Вкл;stage:test:mtz-1;МТЗ I;Вкл;parameter:test:pickup;pickup_current;pickup;quantity;0,600;кА;current;primary
function:test:mtz;protection.overcurrent;МТЗ;ied:test;Вкл;stage:test:mtz-1;МТЗ I;Вкл;parameter:test:delay;operate_delay;delay;quantity;0,80;с;time;not_applicable
"""


class ProtectionSettingImportTests(unittest.TestCase):
    def test_csv_import_requires_explicit_mapping_and_preserves_basis(self):
        card = CsvSettingCardAdapter(spec()).import_text(CSV_TEXT)
        self.assertEqual(card.card_id, "setting-card:test:csv")
        function = card.functions[0]
        self.assertEqual(function.concept_id, "protection.overcurrent")
        self.assertTrue(function.enabled)
        stage = function.stages[0]
        self.assertTrue(stage.enabled)

        pickup = next(
            item for item in stage.parameters
            if item.semantic_key == "pickup_current"
        )
        self.assertEqual(pickup.value.raw_text, "0,600")
        self.assertEqual(pickup.value.normalized_value, "600")
        self.assertEqual(pickup.value.normalized_unit, "A")
        self.assertEqual(pickup.value.basis, "primary")

        delay = next(
            item for item in stage.parameters
            if item.semantic_key == "operate_delay"
        )
        self.assertEqual(delay.value.normalized_value, "0.8")
        self.assertEqual(delay.value.normalized_unit, "s")

    def test_csv_source_hash_is_from_exact_input_text(self):
        card_a = CsvSettingCardAdapter(spec()).import_text(CSV_TEXT)
        card_b = CsvSettingCardAdapter(spec()).import_text(CSV_TEXT + "\n")
        self.assertNotEqual(card_a.sources[0].sha256, card_b.sources[0].sha256)

    def test_missing_explicit_csv_header_is_rejected(self):
        broken = CSV_TEXT.replace(";basis\n", "\n", 1)
        with self.assertRaises(ProtectionSettingImportError) as caught:
            CsvSettingCardAdapter(spec()).import_text(broken)
        self.assertEqual(caught.exception.code, "missing_csv_headers")

    def test_repeated_function_identity_must_be_consistent(self):
        broken = CSV_TEXT.replace(
            "function:test:mtz;protection.overcurrent;МТЗ;ied:test;Вкл;stage:test:mtz-1;МТЗ I;Вкл;parameter:test:delay",
            "function:test:mtz;protection.earth_fault;МТЗ;ied:test;Вкл;stage:test:mtz-1;МТЗ I;Вкл;parameter:test:delay",
        )
        with self.assertRaises(ProtectionSettingImportError) as caught:
            CsvSettingCardAdapter(spec()).import_text(broken)
        self.assertEqual(
            caught.exception.code,
            "inconsistent_function_identity",
        )

    def test_boolean_tokens_are_explicit_not_guessed(self):
        broken = CSV_TEXT.replace(";Вкл;stage:test:mtz-1", ";ON;stage:test:mtz-1", 1)
        with self.assertRaises(ProtectionSettingImportError) as caught:
            CsvSettingCardAdapter(spec()).import_text(broken)
        self.assertEqual(caught.exception.code, "invalid_boolean_value")

    def test_json_duplicate_keys_are_rejected_before_model_decode(self):
        with self.assertRaises(ProtectionSettingImportError) as caught:
            JsonSettingCardAdapter().import_text('{"a":1,"a":2}')
        self.assertEqual(caught.exception.code, "duplicate_json_key")


if __name__ == "__main__":
    unittest.main()
