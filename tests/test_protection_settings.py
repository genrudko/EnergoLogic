from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from energologic.protection import (
    JsonSettingCardAdapter,
    ProtectionSettingValidationError,
    make_quantity_value,
    setting_card_fingerprint,
    setting_card_from_dict,
    setting_card_to_dict,
    validate_setting_card,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "protection-settings.synthetic.json"


def raw_fixture() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class ProtectionSettingModelTests(unittest.TestCase):
    def test_synthetic_fixture_is_valid_and_covers_initial_functions(self):
        card = JsonSettingCardAdapter().import_text(
            FIXTURE.read_text(encoding="utf-8")
        )
        self.assertEqual(validate_setting_card(card), ())
        self.assertEqual(card.settings_scope, "operational_summary")
        self.assertEqual(
            {item.concept_id for item in card.functions},
            {
                "protection.overcurrent",
                "protection.instantaneous_overcurrent",
                "protection.earth_fault",
                "protection.breaker_failure",
            },
        )

    def test_measurement_inputs_are_explicit_and_function_scoped(self):
        card = setting_card_from_dict(raw_fixture())
        self.assertEqual(
            {item.id for item in card.measurement_inputs},
            {
                "measurement:kl-1:phase-current",
                "measurement:kl-1:residual-current",
            },
        )
        mtz = next(
            item for item in card.functions
            if item.concept_id == "protection.overcurrent"
        )
        earth_fault = next(
            item for item in card.functions
            if item.concept_id == "protection.earth_fault"
        )
        self.assertEqual(
            mtz.measurement_input_ids,
            ("measurement:kl-1:phase-current",),
        )
        self.assertEqual(
            earth_fault.measurement_input_ids,
            ("measurement:kl-1:residual-current",),
        )

    def test_unknown_function_measurement_reference_is_rejected(self):
        data = raw_fixture()
        data["functions"][0]["measurement_input_ids"] = [
            "measurement:missing"
        ]
        card = setting_card_from_dict(data, require_valid=False)
        self.assertIn(
            "unknown_function_measurement_input",
            {issue.code for issue in validate_setting_card(card)},
        )

    def test_duplicate_measurement_input_id_is_rejected(self):
        data = raw_fixture()
        duplicate = copy.deepcopy(data["measurement_inputs"][0])
        data["measurement_inputs"].append(duplicate)
        card = setting_card_from_dict(data, require_valid=False)
        self.assertIn(
            "duplicate_measurement_input_id",
            {issue.code for issue in validate_setting_card(card)},
        )

    def test_quantity_normalization_preserves_raw_source_text(self):
        value = make_quantity_value(
            raw_text="1,250 кА",
            source_value="1,250",
            source_unit="кА",
            quantity_kind="current",
            basis="primary",
            decimal_separator=",",
        )
        self.assertEqual(value.raw_text, "1,250 кА")
        self.assertEqual(value.source_value, "1.25")
        self.assertEqual(value.normalized_value, "1250")
        self.assertEqual(value.normalized_unit, "A")
        self.assertEqual(value.basis, "primary")

    def test_secondary_value_is_not_promoted_to_primary(self):
        value = make_quantity_value(
            raw_text="5,00 А втор.",
            source_value="5,00",
            source_unit="А",
            quantity_kind="current",
            basis="secondary",
            decimal_separator=",",
        )
        self.assertEqual(value.normalized_value, "5")
        self.assertEqual(value.normalized_unit, "A")
        self.assertEqual(value.basis, "secondary")

    def test_relative_percent_normalizes_exactly_to_per_unit(self):
        value = make_quantity_value(
            raw_text="80 %",
            source_value="80",
            source_unit="%",
            quantity_kind="ratio",
            basis="relative",
        )
        self.assertEqual(value.normalized_value, "0.8")
        self.assertEqual(value.normalized_unit, "pu")

    def test_incompatible_quantity_unit_fails_closed(self):
        with self.assertRaises(ValueError):
            make_quantity_value(
                raw_text="5 s",
                source_value="5",
                source_unit="s",
                quantity_kind="current",
                basis="primary",
            )

    def test_unknown_json_field_is_rejected_fail_closed(self):
        data = raw_fixture()
        data["unexpected_typo"] = "must not be ignored"
        with self.assertRaises(Exception) as caught:
            setting_card_from_dict(data)
        self.assertIn("unexpected fields", str(caught.exception))

    def test_unknown_nested_value_field_is_rejected_fail_closed(self):
        data = raw_fixture()
        value = data["functions"][0]["stages"][0]["parameters"][0]["value"]
        value["basiss"] = "primary"
        with self.assertRaises(Exception) as caught:
            setting_card_from_dict(data)
        self.assertIn("basiss", str(caught.exception))

    def test_duplicate_protected_object_ids_are_rejected(self):
        data = raw_fixture()
        data["protected_object_ids"].append(data["protected_object_ids"][0])
        card = setting_card_from_dict(data, require_valid=False)
        self.assertIn(
            "duplicate_protected_object_id",
            {issue.code for issue in validate_setting_card(card)},
        )

    def test_negative_numeric_delay_is_rejected(self):
        data = raw_fixture()
        delay = data["functions"][0]["stages"][0]["parameters"][1]["value"]
        delay["raw_text"] = "-0.1 s"
        delay["source_value"] = "-0.1"
        delay["normalized_value"] = "-0.1"
        card = setting_card_from_dict(data, require_valid=False)
        self.assertIn(
            "negative_delay",
            {issue.code for issue in validate_setting_card(card)},
        )

    def test_normalized_value_tampering_is_rejected(self):
        data = raw_fixture()
        pickup = data["functions"][0]["stages"][0]["parameters"][0]["value"]
        pickup["normalized_value"] = "601"
        card = setting_card_from_dict(data, require_valid=False)
        self.assertIn(
            "normalized_value_mismatch",
            {issue.code for issue in validate_setting_card(card)},
        )

    def test_duplicate_parameter_ids_are_rejected_globally(self):
        data = raw_fixture()
        duplicate = copy.deepcopy(
            data["functions"][0]["stages"][0]["parameters"][0]
        )
        data["functions"][1]["stages"][0]["parameters"].append(duplicate)
        card = setting_card_from_dict(data, require_valid=False)
        self.assertIn(
            "duplicate_parameter_id",
            {issue.code for issue in validate_setting_card(card)},
        )

    def test_full_microprocessor_configuration_requires_software_version(self):
        data = raw_fixture()
        data["settings_scope"] = "full_configuration"
        data["devices"][0]["software_version"] = ""
        card = setting_card_from_dict(data, require_valid=False)
        self.assertIn(
            "missing_software_version",
            {issue.code for issue in validate_setting_card(card)},
        )

    def test_operational_summary_does_not_claim_full_configuration(self):
        data = raw_fixture()
        data["devices"][0]["software_version"] = ""
        card = setting_card_from_dict(data, require_valid=False)
        codes = {issue.code for issue in validate_setting_card(card)}
        self.assertNotIn("missing_software_version", codes)
        self.assertEqual(card.settings_scope, "operational_summary")

    def test_canonical_fingerprint_is_stable_under_identity_array_reordering(self):
        data = raw_fixture()
        card_a = setting_card_from_dict(data)
        data["functions"] = list(reversed(data["functions"]))
        data["protected_object_ids"] = list(
            reversed(data["protected_object_ids"])
        )
        card_b = setting_card_from_dict(data)
        self.assertEqual(
            setting_card_fingerprint(card_a),
            setting_card_fingerprint(card_b),
        )
        self.assertEqual(setting_card_to_dict(card_a), setting_card_to_dict(card_b))

    def test_action_is_data_only_and_target_identity_is_preserved(self):
        card = setting_card_from_dict(raw_fixture())
        mtz = next(item for item in card.functions if item.id == "function:kl-1:mtz")
        action = mtz.stages[0].actions[0]
        self.assertEqual(action.action_type, "trip")
        self.assertEqual(action.target_id, "breaker:v-1-35")


if __name__ == "__main__":
    unittest.main()
