from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Mapping


REGISTRY_VERSION = "1.0"
_CONCEPT_ID_RE = re.compile(r"^[a-z][a-z0-9._-]*$")
_CODE_ID_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")
_NAMESPACE_RE = re.compile(r"^[a-z][a-z0-9._-]*$")
_LANGUAGES = ("ru", "en")
_CONCEPT_STATUSES = frozenset({"accepted", "provisional", "deprecated"})
_SOURCE_STATUSES = frozenset({"current", "historical", "superseded"})
_SOURCE_AUTHORITIES = frozenset(
    {"gost", "gost_iec", "gost_r", "gost_r_iec", "iec_iev", "iec", "russian_normative"}
)
_SOURCE_ROLES = frozenset({"primary", "supporting", "legacy"})
_ALIAS_DISPOSITIONS = frozenset({"deprecated", "forbidden"})
_HYPHENS = str.maketrans({"‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-"})


@dataclass(frozen=True, order=True, slots=True)
class RegistryIssue:
    code: str
    path: str
    message: str


@dataclass(frozen=True, order=True, slots=True)
class TermMatch:
    concept_id: str
    language: str
    matched_term: str
    match_kind: str
    status: str


class TerminologyError(ValueError):
    pass


class RegistryValidationError(TerminologyError):
    def __init__(self, issues: Iterable[RegistryIssue]):
        self.issues = tuple(sorted(set(issues)))
        super().__init__(
            "invalid terminology registry: "
            + "; ".join(f"{item.code}@{item.path}" for item in self.issues)
        )


class UnknownTermError(TerminologyError):
    pass


class AmbiguousTermError(TerminologyError):
    def __init__(self, term: str, concept_ids: Iterable[str]):
        self.term = term
        self.concept_ids = tuple(sorted(set(concept_ids)))
        super().__init__(
            f"ambiguous terminology {term!r}: {', '.join(self.concept_ids)}"
        )


def normalize_term(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).translate(_HYPHENS)
    return " ".join(normalized.split()).casefold()


def _issue(issues: list[RegistryIssue], code: str, path: str, message: str) -> None:
    issues.append(RegistryIssue(code, path, message))


def _require_text(
    value: object,
    *,
    path: str,
    issues: list[RegistryIssue],
    code: str = "invalid_text",
) -> str | None:
    if not isinstance(value, str) or not value.strip():
        _issue(issues, code, path, "expected a non-empty string")
        return None
    return value


def _validate_localized_lists(
    value: object,
    *,
    path: str,
    issues: list[RegistryIssue],
) -> Mapping[str, list[str]] | None:
    if not isinstance(value, dict) or set(value) != set(_LANGUAGES):
        _issue(
            issues,
            "invalid_localized_lists",
            path,
            "expected exactly ru and en arrays",
        )
        return None
    for language in _LANGUAGES:
        terms = value[language]
        if not isinstance(terms, list):
            _issue(issues, "invalid_term_list", f"{path}/{language}", "expected an array")
            continue
        seen: set[str] = set()
        for index, term in enumerate(terms):
            item_path = f"{path}/{language}/{index}"
            text = _require_text(term, path=item_path, issues=issues)
            if text is None:
                continue
            key = normalize_term(text)
            if key in seen:
                _issue(issues, "duplicate_term", item_path, f"duplicate term {text!r}")
            seen.add(key)
    return value


def validate_registry_data(data: object) -> tuple[RegistryIssue, ...]:
    issues: list[RegistryIssue] = []
    if not isinstance(data, dict):
        return (RegistryIssue("invalid_registry", "/", "registry root must be an object"),)

    allowed_root = {"registry_version", "sources", "concepts"}
    extra_root = set(data) - allowed_root
    if extra_root:
        _issue(
            issues,
            "unexpected_registry_fields",
            "/",
            f"unexpected fields: {sorted(extra_root)!r}",
        )

    if data.get("registry_version") != REGISTRY_VERSION:
        _issue(
            issues,
            "unsupported_registry_version",
            "/registry_version",
            f"expected {REGISTRY_VERSION!r}",
        )

    raw_sources = data.get("sources")
    raw_concepts = data.get("concepts")
    if not isinstance(raw_sources, list):
        _issue(issues, "invalid_sources", "/sources", "expected an array")
        raw_sources = []
    if not isinstance(raw_concepts, list):
        _issue(issues, "invalid_concepts", "/concepts", "expected an array")
        raw_concepts = []

    source_by_id: dict[str, Mapping[str, object]] = {}
    allowed_source = {
        "id", "authority", "document", "edition", "status", "title", "url", "notes"
    }
    for index, raw in enumerate(raw_sources):
        path = f"/sources/{index}"
        if not isinstance(raw, dict):
            _issue(issues, "invalid_source", path, "source must be an object")
            continue
        extra = set(raw) - allowed_source
        if extra:
            _issue(issues, "unexpected_source_fields", path, f"unexpected fields: {sorted(extra)!r}")
        source_id = _require_text(raw.get("id"), path=f"{path}/id", issues=issues)
        if source_id is not None:
            if not _CONCEPT_ID_RE.fullmatch(source_id):
                _issue(issues, "invalid_source_id", f"{path}/id", source_id)
            if source_id in source_by_id:
                _issue(issues, "duplicate_source_id", f"{path}/id", source_id)
            else:
                source_by_id[source_id] = raw
        authority = _require_text(raw.get("authority"), path=f"{path}/authority", issues=issues)
        if authority is not None and authority not in _SOURCE_AUTHORITIES:
            _issue(issues, "invalid_source_authority", f"{path}/authority", authority)
        for field in ("document", "edition", "title"):
            _require_text(raw.get(field), path=f"{path}/{field}", issues=issues)
        if "url" in raw and (not isinstance(raw["url"], str) or not raw["url"].strip()):
            _issue(issues, "invalid_source_url", f"{path}/url", "expected a non-empty string")
        if "notes" in raw and not isinstance(raw["notes"], str):
            _issue(issues, "invalid_source_notes", f"{path}/notes", "expected a string")
        status = raw.get("status")
        if status not in _SOURCE_STATUSES:
            _issue(issues, "invalid_source_status", f"{path}/status", repr(status))

    concept_ids: set[str] = set()
    code_ids: set[str] = set()
    semantic_bindings: dict[tuple[str, str], str] = {}
    allowed_concept = {
        "id", "domain", "category", "canonical", "code_identifier",
        "abbreviations", "aliases", "deprecated_aliases", "sources",
        "semantic_bindings", "notes", "status",
    }

    for index, raw in enumerate(raw_concepts):
        path = f"/concepts/{index}"
        if not isinstance(raw, dict):
            _issue(issues, "invalid_concept", path, "concept must be an object")
            continue
        extra = set(raw) - allowed_concept
        if extra:
            _issue(issues, "unexpected_concept_fields", path, f"unexpected fields: {sorted(extra)!r}")

        concept_id = _require_text(raw.get("id"), path=f"{path}/id", issues=issues)
        if concept_id is not None:
            if not _CONCEPT_ID_RE.fullmatch(concept_id):
                _issue(issues, "invalid_concept_id", f"{path}/id", concept_id)
            if concept_id in concept_ids:
                _issue(issues, "duplicate_concept_id", f"{path}/id", concept_id)
            concept_ids.add(concept_id)

        for field in ("domain", "category", "notes"):
            text = raw.get(field)
            if field == "notes":
                if not isinstance(text, str):
                    _issue(issues, "invalid_notes", f"{path}/notes", "expected a string")
            else:
                value = _require_text(text, path=f"{path}/{field}", issues=issues)
                if value is not None and not _CONCEPT_ID_RE.fullmatch(value):
                    _issue(issues, f"invalid_{field}", f"{path}/{field}", value)

        code_identifier = _require_text(
            raw.get("code_identifier"),
            path=f"{path}/code_identifier",
            issues=issues,
        )
        if code_identifier is not None:
            if not _CODE_ID_RE.fullmatch(code_identifier):
                _issue(issues, "invalid_code_identifier", f"{path}/code_identifier", code_identifier)
            if code_identifier in code_ids:
                _issue(issues, "duplicate_code_identifier", f"{path}/code_identifier", code_identifier)
            code_ids.add(code_identifier)

        status = raw.get("status")
        if status not in _CONCEPT_STATUSES:
            _issue(issues, "invalid_concept_status", f"{path}/status", repr(status))

        canonical = raw.get("canonical")
        canonical_keys: dict[str, str] = {}
        if not isinstance(canonical, dict) or set(canonical) != set(_LANGUAGES):
            _issue(
                issues,
                "invalid_canonical",
                f"{path}/canonical",
                "canonical must contain exactly one ru and one en string",
            )
        else:
            for language in _LANGUAGES:
                value = _require_text(
                    canonical.get(language),
                    path=f"{path}/canonical/{language}",
                    issues=issues,
                )
                if value is not None:
                    canonical_keys[language] = normalize_term(value)

        abbreviations = _validate_localized_lists(
            raw.get("abbreviations"),
            path=f"{path}/abbreviations",
            issues=issues,
        )
        aliases = _validate_localized_lists(
            raw.get("aliases"),
            path=f"{path}/aliases",
            issues=issues,
        )

        occupied: dict[str, set[str]] = {language: set() for language in _LANGUAGES}
        for language, key in canonical_keys.items():
            occupied[language].add(key)

        for collection_name, collection in (("abbreviations", abbreviations), ("aliases", aliases)):
            if collection is None:
                continue
            for language in _LANGUAGES:
                for term_index, term in enumerate(collection[language]):
                    if not isinstance(term, str) or not term.strip():
                        continue
                    key = normalize_term(term)
                    if key in occupied[language]:
                        _issue(
                            issues,
                            "term_collides_with_same_concept",
                            f"{path}/{collection_name}/{language}/{term_index}",
                            f"{term!r} duplicates another term for the same concept",
                        )
                    occupied[language].add(key)

        deprecated = raw.get("deprecated_aliases")
        if not isinstance(deprecated, list):
            _issue(issues, "invalid_deprecated_aliases", f"{path}/deprecated_aliases", "expected an array")
            deprecated = []
        for alias_index, item in enumerate(deprecated):
            alias_path = f"{path}/deprecated_aliases/{alias_index}"
            if not isinstance(item, dict):
                _issue(issues, "invalid_deprecated_alias", alias_path, "expected an object")
                continue
            if set(item) != {"language", "term", "disposition", "reason"}:
                _issue(
                    issues,
                    "invalid_deprecated_alias_fields",
                    alias_path,
                    "expected language, term, disposition and reason",
                )
            language = item.get("language")
            if language not in _LANGUAGES:
                _issue(issues, "invalid_alias_language", f"{alias_path}/language", repr(language))
                continue
            term = _require_text(item.get("term"), path=f"{alias_path}/term", issues=issues)
            if item.get("disposition") not in _ALIAS_DISPOSITIONS:
                _issue(issues, "invalid_alias_disposition", f"{alias_path}/disposition", repr(item.get("disposition")))
            _require_text(item.get("reason"), path=f"{alias_path}/reason", issues=issues)
            if term is not None:
                key = normalize_term(term)
                if key in occupied[language]:
                    _issue(
                        issues,
                        "term_collides_with_same_concept",
                        f"{alias_path}/term",
                        f"{term!r} duplicates another term for the same concept",
                    )
                occupied[language].add(key)

        source_refs = raw.get("sources")
        if not isinstance(source_refs, list) or not source_refs:
            _issue(issues, "missing_provenance", f"{path}/sources", "at least one source reference is required")
            source_refs = []
        has_current_source = False
        for source_index, source_ref in enumerate(source_refs):
            ref_path = f"{path}/sources/{source_index}"
            if not isinstance(source_ref, dict):
                _issue(issues, "invalid_source_ref", ref_path, "expected an object")
                continue
            allowed_ref = {"source_id", "role", "locator", "notes"}
            extra_ref = set(source_ref) - allowed_ref
            if extra_ref:
                _issue(issues, "unexpected_source_ref_fields", ref_path, f"unexpected fields: {sorted(extra_ref)!r}")
            source_id = _require_text(source_ref.get("source_id"), path=f"{ref_path}/source_id", issues=issues)
            role = source_ref.get("role")
            if role not in _SOURCE_ROLES:
                _issue(issues, "invalid_source_role", f"{ref_path}/role", repr(role))
            _require_text(source_ref.get("locator"), path=f"{ref_path}/locator", issues=issues)
            if source_id is not None:
                source = source_by_id.get(source_id)
                if source is None:
                    _issue(issues, "unknown_source", f"{ref_path}/source_id", source_id)
                elif source.get("status") == "current":
                    has_current_source = True
        if status == "accepted" and not has_current_source:
            _issue(
                issues,
                "accepted_without_current_source",
                f"{path}/status",
                "accepted concepts require at least one current source",
            )

        bindings = raw.get("semantic_bindings", [])
        if not isinstance(bindings, list):
            _issue(issues, "invalid_semantic_bindings", f"{path}/semantic_bindings", "expected an array")
            bindings = []
        local_bindings: set[tuple[str, str]] = set()
        for binding_index, binding in enumerate(bindings):
            binding_path = f"{path}/semantic_bindings/{binding_index}"
            if not isinstance(binding, dict) or set(binding) != {"namespace", "value"}:
                _issue(issues, "invalid_semantic_binding", binding_path, "expected namespace and value")
                continue
            namespace = _require_text(binding.get("namespace"), path=f"{binding_path}/namespace", issues=issues)
            value = _require_text(binding.get("value"), path=f"{binding_path}/value", issues=issues)
            if namespace is not None and not _NAMESPACE_RE.fullmatch(namespace):
                _issue(issues, "invalid_semantic_namespace", f"{binding_path}/namespace", namespace)
            if namespace is None or value is None:
                continue
            key = (namespace, value)
            if key in local_bindings:
                _issue(issues, "duplicate_semantic_binding", binding_path, repr(key))
            local_bindings.add(key)
            owner = semantic_bindings.get(key)
            if owner is not None and owner != concept_id:
                _issue(
                    issues,
                    "semantic_binding_collision",
                    binding_path,
                    f"{namespace}={value!r} is already bound to {owner}",
                )
            elif concept_id is not None:
                semantic_bindings[key] = concept_id

    return tuple(sorted(set(issues)))


class TerminologyRegistry:
    def __init__(self, data: Mapping[str, object]):
        issues = validate_registry_data(data)
        if issues:
            raise RegistryValidationError(issues)
        self._data = data
        concepts = data["concepts"]
        assert isinstance(concepts, list)
        self._by_id = MappingProxyType({item["id"]: item for item in concepts})
        self._by_code = MappingProxyType({item["code_identifier"]: item for item in concepts})

    @classmethod
    def from_file(cls, path: str | Path) -> "TerminologyRegistry":
        raw = Path(path).read_text(encoding="utf-8")
        return cls(json.loads(raw))

    @classmethod
    def load_default(cls) -> "TerminologyRegistry":
        resource = files("energologic.terminology").joinpath("registry-v1.json")
        return cls(json.loads(resource.read_text(encoding="utf-8")))

    @property
    def version(self) -> str:
        return str(self._data["registry_version"])

    @property
    def concepts(self) -> tuple[Mapping[str, object], ...]:
        return tuple(self._by_id[key] for key in sorted(self._by_id))

    def by_id(self, concept_id: str) -> Mapping[str, object]:
        try:
            return self._by_id[concept_id]
        except KeyError as exc:
            raise UnknownTermError(f"unknown concept id: {concept_id}") from exc

    def by_code_identifier(self, code_identifier: str) -> Mapping[str, object]:
        try:
            return self._by_code[code_identifier]
        except KeyError as exc:
            raise UnknownTermError(f"unknown code identifier: {code_identifier}") from exc

    @staticmethod
    def _domain_matches(concept_domain: object, requested: str | None) -> bool:
        if requested is None:
            return True
        return isinstance(concept_domain, str) and (
            concept_domain == requested or concept_domain.startswith(requested + ".")
        )

    def lookup(
        self,
        term: str,
        *,
        language: str | None = None,
        domain: str | None = None,
        include_deprecated: bool = True,
    ) -> tuple[TermMatch, ...]:
        if language is not None and language not in _LANGUAGES:
            raise ValueError("language must be 'ru', 'en' or None")
        key = normalize_term(term)
        matches: list[TermMatch] = []
        languages = _LANGUAGES if language is None else (language,)

        for concept in self.concepts:
            if not self._domain_matches(concept["domain"], domain):
                continue
            canonical = concept["canonical"]
            abbreviations = concept["abbreviations"]
            aliases = concept["aliases"]
            status = str(concept["status"])
            for lang in languages:
                if normalize_term(canonical[lang]) == key:
                    matches.append(TermMatch(concept["id"], lang, canonical[lang], "canonical", status))
                for abbreviation in abbreviations[lang]:
                    if normalize_term(abbreviation) == key:
                        matches.append(TermMatch(concept["id"], lang, abbreviation, "abbreviation", status))
                for alias in aliases[lang]:
                    if normalize_term(alias) == key:
                        matches.append(TermMatch(concept["id"], lang, alias, "alias", status))
                if include_deprecated:
                    for alias in concept["deprecated_aliases"]:
                        if alias["language"] == lang and normalize_term(alias["term"]) == key:
                            matches.append(
                                TermMatch(
                                    concept["id"],
                                    lang,
                                    alias["term"],
                                    alias["disposition"],
                                    status,
                                )
                            )
        return tuple(sorted(set(matches)))

    def resolve_unique(
        self,
        term: str,
        *,
        language: str | None = None,
        domain: str | None = None,
        include_deprecated: bool = True,
    ) -> Mapping[str, object]:
        matches = self.lookup(
            term,
            language=language,
            domain=domain,
            include_deprecated=include_deprecated,
        )
        concept_ids = {item.concept_id for item in matches}
        if not concept_ids:
            raise UnknownTermError(f"unknown terminology: {term!r}")
        if len(concept_ids) != 1:
            raise AmbiguousTermError(term, concept_ids)
        return self.by_id(next(iter(concept_ids)))

    def canonical_term(self, concept_id: str, language: str) -> str:
        if language not in _LANGUAGES:
            raise ValueError("language must be 'ru' or 'en'")
        concept = self.by_id(concept_id)
        return str(concept["canonical"][language])
