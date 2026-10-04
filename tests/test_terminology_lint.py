from __future__ import annotations

import unittest

from energologic.terminology import TerminologyRegistry, lint_text


class TerminologyLintTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = TerminologyRegistry.load_default()

    def test_forbidden_literal_calque_is_reported(self):
        issues = lint_text(
            "Каждый электрический терминал должен быть идентифицирован.",
            self.registry,
            language="ru",
        )
        self.assertEqual(len(issues), 1)
        issue = issues[0]
        self.assertEqual(issue.code, "forbidden_term")
        self.assertEqual(issue.severity, "error")
        self.assertEqual(issue.replacement, "вывод")
        self.assertEqual(issue.concept_ids, ("topology.terminal",))

    def test_transliteration_is_reported_as_forbidden(self):
        issues = lint_text(
            "Create Vyklyuchatel in the model.",
            self.registry,
            language="en",
        )
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "forbidden_term")
        self.assertEqual(issues[0].replacement, "circuit-breaker")

    def test_active_alias_is_info_with_canonical_replacement(self):
        issues = lint_text(
            "Установлен предохранитель.",
            self.registry,
            language="ru",
            domain="power.switchgear",
        )
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "noncanonical_alias")
        self.assertEqual(issues[0].replacement, "плавкий предохранитель")

    def test_canonical_phrase_does_not_trigger_nested_alias(self):
        issues = lint_text(
            "Установлен плавкий предохранитель.",
            self.registry,
            language="ru",
            domain="power.switchgear",
        )
        self.assertEqual(issues, ())

    def test_hyphenated_canonical_phrase_is_unambiguous_in_voltage_domain(self):
        issues = lint_text(
            "The circuit-breaker is open.",
            self.registry,
            language="en",
            domain="power.switchgear.high_voltage",
        )
        self.assertFalse(
            any(issue.term.casefold() in {"breaker", "circuit-breaker"} for issue in issues),
            issues,
        )

    def test_circuit_breaker_is_ambiguous_without_voltage_domain(self):
        issues = lint_text(
            "The circuit-breaker is open.",
            self.registry,
            language="en",
        )
        breaker_issues = [issue for issue in issues if issue.term.casefold() == "circuit-breaker"]
        self.assertEqual(len(breaker_issues), 1)
        self.assertEqual(breaker_issues[0].code, "ambiguous_term")
        self.assertEqual(
            set(breaker_issues[0].concept_ids),
            {"switchgear.circuit_breaker", "switchgear.low_voltage_circuit_breaker"},
        )

    def test_approved_abbreviation_is_not_linted(self):
        issues = lint_text(
            "МТЗ запущена.",
            self.registry,
            language="ru",
            domain="power.protection",
        )
        self.assertEqual(issues, ())

    def test_homonym_is_not_silently_replaced(self):
        issues = lint_text(
            "Проверить заземлитель.",
            self.registry,
            language="ru",
        )
        self.assertEqual(len(issues), 1)
        issue = issues[0]
        self.assertEqual(issue.code, "ambiguous_term")
        self.assertEqual(issue.severity, "warning")
        self.assertIsNone(issue.replacement)
        self.assertEqual(
            set(issue.concept_ids),
            {"earthing.earth_electrode", "switchgear.earthing_switch"},
        )

    def test_domain_filter_accepts_canonical_earthing_switch_homonym(self):
        issues = lint_text(
            "Проверить заземлитель.",
            self.registry,
            language="ru",
            domain="power.switchgear.high_voltage",
        )
        self.assertEqual(issues, ())

    def test_earthing_switch_synonym_is_canonicalized_in_high_voltage_domain(self):
        issues = lint_text(
            "Проверить заземляющий разъединитель.",
            self.registry,
            language="ru",
            domain="power.switchgear.high_voltage",
        )
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "noncanonical_alias")
        self.assertEqual(issues[0].replacement, "заземлитель")


if __name__ == "__main__":
    unittest.main()
