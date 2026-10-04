# EnergoLogic terminology registry

The authoritative machine-readable registry is:

```text
src/energologic/terminology/registry-v1.json
```

Schema:

```text
schema/terminology-registry-1.0.schema.json
```

Runtime API:

```text
src/energologic/terminology/
```

## Source hierarchy

For electrical/power terminology, prefer evidence in this order:

1. current applicable ГОСТ IEC / ГОСТ Р МЭК terminology;
2. IEC IEV / Electropedia;
3. current Russian national/industry standards defining the scoped power-system concept;
4. other current Russian normative documents when they normatively define or use the term;
5. historical/superseded documents only for legacy provenance.

Do not invent a translation merely because a convenient English/Russian form is common.

## Adding a concept

1. **Define the concept before the string.** Decide what physical/logical concept is being named and its domain.
2. **Search current normative sources.** Record conflicting scopes instead of selecting the first plausible hit.
3. **Add/reuse source metadata.** Store document designation, edition/revision, lifecycle status and title.
4. **Choose a stable concept ID.** It is an identity, not a display string.
5. **Set exactly one canonical RU and EN term.**
6. **Choose an English `code_identifier`.** Use international technical terminology; no transliteration.
7. **Record abbreviations separately.**
8. **Record active aliases separately.** Aliases are for recognition/search/import.
9. **Record deprecated/forbidden forms with a reason.**
10. **Add provenance locators.** Use a clause/term/IEV number where available.
11. **Set lifecycle status.** If evidence or scope is disputed, use `provisional`.
12. **Bind existing semantics when applicable.** For example an accepted canonical kind or state.
13. **Add tests for ambiguity/legacy behavior.**
14. **Run the full repository suite and record CI evidence.**

## Canonical output vs lookup

```python
from energologic.terminology import TerminologyRegistry

registry = TerminologyRegistry.load_default()

registry.canonical_term("topology.terminal", "ru")
# "вывод"

registry.lookup("электрический терминал", language="ru")
# returns a forbidden legacy/calque match; it does not change canonical terminology
```

## Ambiguity is a first-class result

Do not assume a term string identifies one concept:

```python
registry.lookup("заземлитель", language="ru")
# can match earth electrode and a deprecated earthing-switch form

registry.resolve_unique(
    "заземлитель",
    language="ru",
    domain="electrical.earthing",
)
# resolves only after domain qualification
```

If resolution is still ambiguous, the API raises `AmbiguousTermError`.

## Terminology lint

```python
from energologic.terminology import lint_text

issues = lint_text(
    "Каждый электрический терминал должен быть идентифицирован.",
    registry,
    language="ru",
)
```

The lint distinguishes:

- `forbidden_term` — error;
- `deprecated_term` — warning;
- `noncanonical_alias` — informational canonicalization suggestion;
- `ambiguous_noncanonical_term` — warning with no automatic replacement.

Approved abbreviations and already canonical phrases are not lint errors.

## Changing an existing accepted concept

A change to a canonical RU/EN term or to a semantic binding is not a routine spelling
edit. The PR must include:

- old and proposed canonical wording;
- authoritative source evidence and scope;
- migration impact on aliases/imports/generated docs;
- impact on schema/code identifiers;
- explicit statement whether electrical semantics change.

Never silently repurpose an existing concept ID for a different electrical concept.
