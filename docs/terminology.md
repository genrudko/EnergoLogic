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

## Evidence rule: determine scope before choosing wording

Terminology sources are not applied as a flat ranking.

First define the engineering concept and its scope: equipment family, voltage domain,
operational context, physical/topological meaning and applicable installation class.

Then prefer current authoritative evidence in this order of relevance:

1. a current standard/rule directly governing the exact equipment or operational scope;
2. current GOST IEC / GOST R IEC terminology and IEC IEV/Electropedia for the
   international concept and language correspondence;
3. other current Russian normative/industry documents that define or normatively use
   the same scoped concept;
4. historical/superseded documents only for legacy provenance.

A more generic vocabulary entry does **not** automatically override a more specific
current equipment standard.

Examples:

- high-voltage `выключатель` and low-voltage `автоматический выключатель` are
  distinct concepts even though both map to English `circuit-breaker`;
- `заземлитель` can be either an earthing switching apparatus or an earth electrode,
  depending on domain.

Do not invent a translation merely because a convenient English/Russian form is common.

## Adding a concept

1. **Define the concept before the string.** Decide what physical/logical concept is being named and its domain.
2. **Establish applicability.** Voltage class, equipment family and operational context may be identity-bearing.
3. **Search current scope-specific normative sources.** Record conflicting scopes instead of selecting the first plausible hit.
4. **Cross-check GOST IEC / IEC IEV.** Verify international English terminology and identify generic-vs-specific differences.
5. **Add/reuse source metadata.** Store document designation, edition/revision, lifecycle status and title.
6. **Choose a stable concept ID.** It is an identity, not a display string.
7. **Set exactly one canonical RU and EN term.**
8. **Choose an English `code_identifier`.** Use international technical terminology; no transliteration.
9. **Record abbreviations separately.**
10. **Record active aliases separately.** Aliases are for recognition/search/import.
11. **Record deprecated/forbidden forms with a reason.**
12. **Add provenance locators.** Use a clause/term/IEV number where available.
13. **Set lifecycle status.** If evidence or scope is disputed, use `provisional`.
14. **Bind existing semantics when applicable.** Do not give two concepts the same semantic binding.
15. **Add tests for ambiguity and domain separation.**
16. **Run the full repository suite and record CI evidence.**

## Canonical output vs lookup

```python
from energologic.terminology import TerminologyRegistry

registry = TerminologyRegistry.load_default()

registry.canonical_term("topology.terminal", "ru")
# "вывод"

registry.lookup("электрический терминал", language="ru")
# forbidden literal/calque match; canonical output remains "вывод"
```

## Ambiguity is a first-class result

Do not assume a term string identifies one concept.

```python
registry.lookup("заземлитель", language="ru")
# high-voltage earthing switch + earth electrode

registry.resolve_unique(
    "заземлитель",
    language="ru",
    domain="power.switchgear.high_voltage",
)
# -> switchgear.earthing_switch
```

The same applies across languages:

```python
registry.lookup("circuit-breaker", language="en")
# high-voltage breaker + low-voltage automatic circuit-breaker

registry.resolve_unique(
    "circuit-breaker",
    language="en",
    domain="power.switchgear.low_voltage",
)
# -> switchgear.low_voltage_circuit_breaker
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
- `ambiguous_term` — warning when the same canonical/alias string maps to multiple
  concepts in the supplied context.

Approved abbreviations and an unambiguous canonical term are not lint errors.

## Changing an existing accepted concept

A change to a canonical RU/EN term, domain or semantic binding is not a routine
spelling edit. The PR must include:

- old and proposed canonical wording/scope;
- authoritative source evidence;
- migration impact on aliases/imports/generated docs;
- impact on schema/code identifiers;
- explicit statement whether electrical semantics change.

Never silently repurpose an existing concept ID for a different electrical concept.
