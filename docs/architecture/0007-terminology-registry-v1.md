# ADR 0007 — Terminology Registry v1

Status: **Proposed in TERMINOLOGY-REGISTRY-V1-001 / Draft PR #18**

## Context

EnergoLogic requires one controlled terminology contract across Russian UI text,
English code/API identifiers, legacy import, documentation and later normative rules.

The existing canonical model already contains accepted semantic identifiers such as
`circuit_breaker`, `disconnector`, `bus`, `current_transformer`,
`transformer_2w` and `switch_state=open|closed`. Terminology work must describe
those concepts without silently redefining their electrical meaning.

Normative research also shows that text alone is not a safe identity key:

- current ГОСТ IEC 60050-441-2015 uses «заземляющий выключатель» for
  `earthing switch`;
- ГОСТ 24291-90 uses «заземлитель» for `earth electrode`;
- the superseded ГОСТ Р МЭК 60050-441-2012 used «заземлитель» for
  `earthing switch`.

Therefore a registry that assumes globally unique term strings would resolve real
normative homonyms incorrectly.

## Decision

### 1. Concept identity is independent from wording

Each concept has a stable `id` and exactly one scalar canonical term per language:

```text
concept ID
  ├── canonical.ru
  ├── canonical.en
  ├── code_identifier
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

Lookup returns all matches with match kind. `resolve_unique()` fails closed with
`AmbiguousTermError` unless the term resolves to one concept, optionally after a
domain filter.

This is intentional for cases such as the legacy/current meanings of
«заземлитель» and the English word `open` used as state/action vocabulary.

### 4. Existing electrical semantics are protected by semantic bindings

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

### 5. Aliases are recognition/search data, not output terminology

Aliases support:

- legacy Visio/import recognition;
- search;
- compatibility;
- migration from older terminology.

Generated UI/docs should request the canonical term explicitly.

### 6. Lifecycle status represents evidence maturity

- `accepted` — current authoritative provenance is sufficient for the scoped concept;
- `provisional` — wording/scope has unresolved normative or project-policy evidence;
- `deprecated` — concept remains addressable for compatibility but is no longer preferred.

An accepted concept must reference at least one source marked `current`.

### 7. Sources and concept provenance are separate records

The registry stores source identity/edition/status once and concepts reference a
source by locator (clause, term number or IEV number). This is the first bounded
Normative Source Registry foundation; executable normative rules remain out of
scope.

### 8. Registry runtime stays headless and dependency-free

The implementation lives under `energologic.terminology`, uses only the Python
standard library and does not depend on Visio, COM, solvers or frontends.

## Consequences

- schema/code/UI can share a controlled vocabulary without making Visio canonical;
- normative homonyms are represented honestly;
- old imports remain searchable without contaminating generated terminology;
- terminology changes affecting accepted semantic bindings require explicit review;
- disputed concepts can ship as `provisional` evidence rather than being falsely
  presented as settled.
