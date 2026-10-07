# TERMINOLOGY-REGISTRY-V1-001 — Terminology Registry v1

Status: **Accepted and merged to `main`**
Workstream: **WS-2 — Terminology & Normative Foundations**
Issue: **#17**
Draft PR: **#18**
Branch: `terminology/terminology-registry-v1-001`


## Final repository reconciliation

Merged via PR #18 as `fee3b53` on 2026-10-04.

Any unchecked owner/Ready/Merge boxes or pre-merge wording later in this file are **historical candidate-state evidence** and do not override this final repository status.

## Goal

Deliver the first production-grade, Visio-independent EnergoLogic Terminology Registry.

The registry is the controlled contract between:

- canonical Russian user-facing terminology;
- canonical international English terminology;
- stable English code identifiers;
- legacy/search aliases;
- authoritative terminology provenance.

## Baseline invariants

1. Russian is the user-facing language.
2. Code, APIs, schemas and internal identifiers use English.
3. Canonical terminology must be sourced, not invented, when an authoritative term exists.
4. Engineering scope is established before choosing between competing normative wordings.
5. A directly applicable current equipment/operating standard may be more authoritative for that scoped concept than a generic vocabulary entry.
6. Transliteration is not an accepted naming strategy.
7. An alias is never automatically promoted to canonical terminology.
8. Existing accepted electrical semantics are not changed by terminology curation.
9. Normative homonyms are not resolved by guessing: lookup must expose ambiguity or accept a domain filter.
10. Every accepted/provisional concept has provenance.
11. The registry is headless and has no Visio dependency.
12. Ready for Review and merge remain owner-controlled.

## Deliverables

- versioned machine-readable registry;
- versioned JSON Schema;
- deterministic stdlib-only validator;
- lookup API by concept ID, code identifier and RU/EN term;
- alias/abbreviation lookup with match-kind reporting;
- uniqueness checks for stable IDs and code identifiers;
- semantic-binding collision checks;
- terminology lint for prose/schema/code inputs;
- initial electrical/power-system vocabulary requested by the owner;
- documentation for adding and reviewing terms;
- evidence/decision log for disputed terminology;
- regression tests.

## Out of scope

- executable normative Rules Engine;
- site-specific operational-rule execution;
- changes to VISIO-EDITOR-QOL-001;
- Visio UI integration;
- energized-network traversal;
- protection algorithms;
- changing electrical-v1/switching-state-v1/transformer semantics solely to fit terminology.

## Acceptance

- [x] schema is understandable and extensible;
- [x] requested baseline concepts are represented with provenance;
- [x] canonical RU/EN and code identifiers are internally consistent;
- [x] aliases are structurally separate from canonical terminology;
- [x] duplicate IDs/code identifiers fail closed;
- [x] canonical names are singular fields, not synonym sets;
- [x] ambiguous normative homonyms are surfaced, never silently selected;
- [x] voltage/domain-separated concepts can share an English term without being merged;
- [x] lookup API and alias lookup are tested;
- [x] terminology lint is tested;
- [x] documentation explains how to add a term;
- [x] disputed terms and competing evidence are explicit;
- [x] repository test suite passes on the pre-correction head;
- [x] corrected breaker/earthing terminology head has final green CI recorded.

Owner acceptance, Ready for Review and merge are intentionally **not** implied by
implementation checks.

## Corrected equipment taxonomy

### Breakers are not one Russian concept

EnergoLogic now separates:

- high-voltage/power-system `CircuitBreaker` → **выключатель**;
- low-voltage `LowVoltageCircuitBreaker` → **автоматический выключатель**.

Both may legitimately have English `circuit-breaker`; domain/ID disambiguates them.

The existing `energologic.element.kind=circuit_breaker` semantic binding remains on
the high-voltage concept because current qualified EnergoLogic data is 35 kV.

### High-voltage earthing switch

For the >1 kV switchgear domain:

- canonical RU: **заземлитель**;
- canonical EN: **earthing switch**;
- aliases include:
  `заземляющий выключатель`,
  `выключатель заземления`,
  `заземляющий разъединитель`,
  `заземляющий нож`,
  `нож заземления`.

A separate `earth electrode` concept also has Russian canonical **заземлитель**.
This is retained as an intentional normative homonym and requires domain-qualified
resolution.

## Other established terminology findings

- physical electrical `terminal` → **«вывод»**;
- `присоединение распределительного устройства` → **`feeder bay`**;
- `ячейка` → **`bay`**;
- power/KRU `busbar` candidate → **«сборная шина»**;
- operational Russian switching UI →
  **«включение/отключение»** and
  **«включенное/отключенное положение»**.

Remaining `provisional` entries are evidence/domain-contract gaps. They must not be
promoted by guesswork.

## Verification

Canonical command:

```bash
python -m unittest discover -s tests -v
```

Repository CI matrix:

- Ubuntu latest / Python 3.11;
- Ubuntu latest / Python 3.12;
- Windows latest / Python 3.11;
- Windows latest / Python 3.12.

Corrected code head `9323c5979f65077686934bc654efd52384494b03`: CI run **37205909855 — SUCCESS**, **95 tests — OK** in each matrix job.\n\nDocumentation-reconciled head `e9f3599e7922f828c8cf911363b578199b9663a1`: CI run **37206082055 — SUCCESS**.
