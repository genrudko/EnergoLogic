from __future__ import annotations

import copy
import json
import unittest
from importlib.resources import files

from energologic.terminology import (
    AmbiguousTermError,
    RegistryValidationError,
    TerminologyRegistry,
    UnknownTermError,
    validate_registry_data,
)


def _raw_registry() -> dict[str, object]:
    resource = files("energologic.terminology").joinpath("registry-v1.json")
    return json.loads(resource.read_text(encoding="utf-8"))


class TerminologyRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = TerminologyRegistry.load_default()

    def test_default_registry_loads_and_has_expected_version(self):
        self.assertEqual(self.registry.version, "1.0")
        self.assertGreaterEqual(len(self.registry.concepts), 40)

    def test_lookup_by_id_and_code_identifier(self):
        concept = self.registry.by_id("switchgear.circuit_breaker")
        self.assertEqual(concept["canonical"]["ru"], "выключатель")
        self.assertEqual(
            self.registry.by_code_identifier("CircuitBreaker")["id"],
            "switchgear.circuit_breaker",
        )

    def test_alias_lookup_does_not_promote_alias_to_canonical(self):
        matches = self.registry.lookup("предохранитель", language="ru")
        self.assertEqual(
            {(item.concept_id, item.match_kind) for item in matches},
            {("switchgear.fuse", "alias")},
        )
        self.assertEqual(
            self.registry.canonical_term("switchgear.fuse", "ru"),
            "плавкий предохранитель",
        )

    def test_normative_homonym_is_ambiguous_without_domain(self):
        matches = self.registry.lookup("заземлитель", language="ru")
        self.assertEqual(
            {item.concept_id for item in matches},
            {"earthing.earth_electrode", "switchgear.earthing_switch"},
        )
        with self.assertRaises(AmbiguousTermError):
            self.registry.resolve_unique("заземлитель", language="ru")

    def test_normative_homonym_can_be_resolved_by_domain(self):
        electrode = self.registry.resolve_unique(
            "заземлитель",
            language="ru",
            domain="electrical.earthing",
        )
        self.assertEqual(electrode["id"], "earthing.earth_electrode")

        earthing_switch = self.registry.resolve_unique(
            "заземлитель",
            language="ru",
            domain="power.switchgear",
        )
        self.assertEqual(earthing_switch["id"], "switchgear.earthing_switch")

    def test_open_is_ambiguous_between_state_and_operation_without_domain(self):
        with self.assertRaises(AmbiguousTermError):
            self.registry.resolve_unique("open", language="en")

        state = self.registry.resolve_unique(
            "open",
            language="en",
            domain="power.switchgear.state",
        )
        self.assertEqual(state["id"], "state.switch.open")

    def test_unknown_term_fails_closed(self):
        with self.assertRaises(UnknownTermError):
            self.registry.resolve_unique("definitely-not-a-term", language="en")

    def test_duplicate_concept_id_and_code_identifier_are_rejected(self):
        data = _raw_registry()
        duplicate = copy.deepcopy(data["concepts"][0])
        data["concepts"].append(duplicate)
        issues = validate_registry_data(data)
        codes = {issue.code for issue in issues}
        self.assertIn("duplicate_concept_id", codes)
        self.assertIn("duplicate_code_identifier", codes)

    def test_semantic_binding_collision_is_rejected(self):
        data = _raw_registry()
        original = next(
            item
            for item in data["concepts"]
            if item["id"] == "switchgear.circuit_breaker"
        )
        duplicate = copy.deepcopy(original)
        duplicate["id"] = "test.conflicting_breaker"
        duplicate["code_identifier"] = "ConflictingBreaker"
        duplicate["canonical"] = {"ru": "тестовый выключатель", "en": "test breaker"}
        duplicate["aliases"] = {"ru": [], "en": []}
        duplicate["abbreviations"] = {"ru": [], "en": []}
        duplicate["deprecated_aliases"] = []
        data["concepts"].append(duplicate)

        issues = validate_registry_data(data)
        self.assertIn("semantic_binding_collision", {issue.code for issue in issues})

    def test_second_canonical_name_shape_is_rejected(self):
        data = _raw_registry()
        concept = data["concepts"][0]
        concept["canonical"]["ru_alt"] = "второе имя"
        issues = validate_registry_data(data)
        self.assertIn("invalid_canonical", {issue.code for issue in issues})

    def test_accepted_concept_requires_current_provenance(self):
        data = _raw_registry()
        concept = next(item for item in data["concepts"] if item["status"] == "accepted")
        concept["sources"] = [
            {
                "source_id": "gost-r-iec-60050-441-2012",
                "role": "legacy",
                "locator": "legacy-only test",
            }
        ]
        issues = validate_registry_data(data)
        self.assertIn(
            "accepted_without_current_source",
            {issue.code for issue in issues},
        )

    def test_registry_constructor_raises_with_deterministic_issues(self):
        data = _raw_registry()
        data["registry_version"] = "999"
        with self.assertRaises(RegistryValidationError) as caught:
            TerminologyRegistry(data)
        self.assertEqual(
            caught.exception.issues[0].code,
            "unsupported_registry_version",
        )


if __name__ == "__main__":
    unittest.main()
