from __future__ import annotations

import re
from dataclasses import dataclass

from .registry import TerminologyRegistry, normalize_term


@dataclass(frozen=True, order=True, slots=True)
class LintIssue:
    start: int
    end: int
    code: str
    severity: str
    term: str
    concept_ids: tuple[str, ...]
    replacement: str | None


def _literal_pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(term)
    left = r"(?<!\w)" if term and term[0].isalnum() else ""
    right = r"(?!\w)" if term and term[-1].isalnum() else ""
    return re.compile(left + escaped + right, re.IGNORECASE)


def _domain_matches(concept_domain: str, requested: str | None) -> bool:
    if requested is None:
        return True
    return concept_domain == requested or concept_domain.startswith(requested + ".")


def _is_inside_preferred_phrase(
    text: str,
    *,
    start: int,
    end: int,
    candidate: str,
    affected_concept_ids: tuple[str, ...],
    registry: TerminologyRegistry,
    language: str,
) -> bool:
    """Suppress aliases nested inside a longer canonical/approved phrase of the same concept."""

    candidate_key = normalize_term(candidate)
    for concept_id in affected_concept_ids:
        concept = registry.by_id(concept_id)
        preferred = [str(concept["canonical"][language])]
        preferred.extend(str(item) for item in concept["abbreviations"][language])
        for term in preferred:
            if normalize_term(term) == candidate_key:
                continue
            for match in _literal_pattern(term).finditer(text):
                if match.start() <= start and end <= match.end():
                    return True
    return False


def lint_text(
    text: str,
    registry: TerminologyRegistry,
    *,
    language: str,
    domain: str | None = None,
) -> tuple[LintIssue, ...]:
    if language not in {"ru", "en"}:
        raise ValueError("language must be 'ru' or 'en'")

    candidate_terms: set[str] = set()
    for concept in registry.concepts:
        if not _domain_matches(str(concept["domain"]), domain):
            continue
        candidate_terms.update(str(item) for item in concept["aliases"][language])
        candidate_terms.update(
            str(item["term"])
            for item in concept["deprecated_aliases"]
            if item["language"] == language
        )

    issues: list[LintIssue] = []
    for candidate in sorted(
        candidate_terms,
        key=lambda value: (-len(value), value.casefold()),
    ):
        matches = registry.lookup(candidate, language=language, domain=domain)
        affected = tuple(sorted({item.concept_id for item in matches}))
        if not affected:
            continue

        dispositions = {item.match_kind for item in matches}
        if "forbidden" in dispositions:
            code, severity = "forbidden_term", "error"
        elif "deprecated" in dispositions:
            code, severity = "deprecated_term", "warning"
        else:
            code, severity = "noncanonical_alias", "info"

        replacement: str | None = None
        if len(affected) == 1:
            replacement = registry.canonical_term(affected[0], language)
        else:
            code, severity = "ambiguous_noncanonical_term", "warning"

        for match in _literal_pattern(candidate).finditer(text):
            if _is_inside_preferred_phrase(
                text,
                start=match.start(),
                end=match.end(),
                candidate=candidate,
                affected_concept_ids=affected,
                registry=registry,
                language=language,
            ):
                continue
            issues.append(
                LintIssue(
                    start=match.start(),
                    end=match.end(),
                    code=code,
                    severity=severity,
                    term=match.group(0),
                    concept_ids=affected,
                    replacement=replacement,
                )
            )
    return tuple(sorted(set(issues)))
