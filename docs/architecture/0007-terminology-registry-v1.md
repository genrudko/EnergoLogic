# ADR 0007 — Terminology Registry v1

Status: **Proposed in TERMINOLOGY-REGISTRY-V1-001 / Draft PR #18**

## Context

EnergoLogic requires one controlled terminology contract across Russian UI text,
English code/API identifiers, legacy import, documentation and later normative rules.

The existing canonical model already contains accepted semantic identifiers such as
`circuit_breaker`, `disconnector`, `bus`, `current_transformer`,
`transformer_2w` and `switch_state=open|closed`. Terminology work must describe
those concepts without silently redefining their electrical meaning.

Normative research shows two independent problems that a string-only vocabulary cannot
solve.

### The same term can name different concepts

For Russian `заземлитель`:

- ГОСТ Р 52726-2007, directly applicable to AC disconnectors and earthing switches
  above 1 kV, defines `заземлитель` as the switching apparatus;
- ГОСТ 24291-90 uses `заземлитель` for `earth electrode`;
- generic IEC-derived vocabulary also exposes Russian forms such as
  `заземляющий выключатель`.

These are scope-qualified normative concepts, not one globally unique string.

### Different Russian concepts can share one English base term

For `circuit-breaker`:

- ГОСТ Р 52565-2006 uses Russian `выключатель` for the 3–750 kV equipment family;
- ГОСТ IEC 60947-2-2021 uses Russian `автоматический выключатель` for the
  low-voltage equipment family;
- both use English `circuit-breaker(s)`.

Therefore voltage/domain scope is part of concept identity even when the English
surface term is identical.

## Decision

### 1. Concept identity is independent from wording

Each concept has a stable `id` and exactly one scalar canonical term per language:

```text
concept ID
  ├── canonical.ru
  ├── canonical.en
  ├── code_identifier
  ├── domain/category
  ├── abbreviations
  ├── aliases
  ├── deprecated/forbidden aliases
  ├── provenance
  └── lifecycle status
```

Canonical term strings are not primary keys.

### 2. One concept cannot acquire a second canonical name accidentally

The schema permits exactly:

```json
"canonical": {
  "ru": "...",
  "en": "..."
}
```

and rejects additional canonical fields. Alternate forms belong to aliases or
deprecated/forbidden aliases with explicit disposition.

### 3. Homonyms are allowed; silent ambiguity is not

Different concepts may legitimately use the same string.

Examples in v1:

- RU `заземлитель` can resolve to high-voltage earthing switching apparatus or to
  an earth electrode;
- EN `circuit-breaker` can resolve to the high-voltage breaker concept or the
  low-voltage automatic-circuit-breaker concept.

Lookup returns all matches with match kind. `resolve_unique()` fails closed with
`AmbiguousTermError` unless the term resolves to one concept, optionally after a
domain filter.

Terminology lint also reports an ambiguous canonical string when insufficient domain
context is supplied.

### 4. Source selection is scope-first, not vocabulary-first

There is no unconditional rule that a generic IEV wording overrides a current,
directly applicable equipment or operating standard.

For an EnergoLogic concept:

1. determine the engineering scope first;
2. prefer current authoritative sources that directly govern that scope;
3. use GOST IEC / IEC IEV terminology to verify the concept and international English
   correspondence;
4. retain conflicting current generic/specific forms as aliases or separate concepts
   when they denote different scoped entities;
5. never merge concepts merely because one language uses the same surface term.

This rule is what separates:

- high-voltage `выключатель` from low-voltage `автоматический выключатель`;
- high-voltage switching-device `заземлитель` from earth-electrode `заземлитель`.

### 5. Existing electrical semantics are protected by semantic bindings

A terminology concept may bind to an already accepted semantic value, for example:

```text
switchgear.circuit_breaker
  -> energologic.element.kind = circuit_breaker

state.switch.open
  -> energologic.switch_state = open
```

The validator rejects a second concept claiming the same namespace/value pair.
Terminology curation therefore cannot silently create a competing canonical concept
for an existing electrical semantic identifier.

The existing `energologic.element.kind=circuit_breaker` binding remains on the
qualified high-voltage concept because current EnergoLogic electrical acceptance is
based on 35 kV switchgear. The new low-voltage automatic-circuit-breaker concept has
no such binding.

### 6. Aliases are recognition/search data, not output terminology

Aliases support:

- legacy Visio/import recognition;
- search;
- compatibility;
- common operational wording;
- migration from older terminology.

Generated UI/docs should request the canonical term explicitly.

### 7. Lifecycle status represents evidence maturity

- `accepted` — current authoritative provenance is sufficient for the scoped concept;
- `provisional` — wording/scope has unresolved normative or project-contract evidence;
- `deprecated` — concept remains addressable for compatibility but is no longer preferred.

An accepted concept must reference at least one source marked `current`.

### 8. Sources and concept provenance are separate records

The registry stores source identity/edition/status once and concepts reference a
source by locator (clause, term number or IEV number). This is the first bounded
Normative Source Registry foundation; executable normative rules remain out of
scope.

### 9. Registry runtime stays headless and dependency-free

The implementation lives under `energologic.terminology`, uses only the Python
standard library and does not depend on Visio, COM, solvers or frontends.

## Consequences

- schema/code/UI can share a controlled vocabulary without making Visio canonical;
- normative homonyms are represented honestly;
- voltage/domain-separated equipment classes cannot be collapsed by a shared English
  term;
- old/import terminology remains searchable without contaminating generated terms;
- terminology changes affecting accepted semantic bindings require explicit review;
- disputed concepts can remain `provisional` instead of being falsely presented as
  settled.
