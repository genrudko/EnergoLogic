# TERMINOLOGY-REGISTRY-V1-001 — Terminology Registry v1

Status: **Implementation complete in Draft; owner terminology decisions pending**  
Workstream: **WS-2 — Terminology & Normative Foundations**  
Issue: **#17**  
Draft PR: **#18**  
Branch: `terminology/terminology-registry-v1-001`

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
4. Transliteration is not an accepted naming strategy.
5. An alias is never automatically promoted to canonical terminology.
6. Existing accepted electrical semantics are not changed by terminology curation.
7. Normative homonyms are not resolved by guessing: lookup must expose ambiguity or accept a domain filter.
8. Every accepted/provisional concept has provenance.
9. The registry is headless and has no Visio dependency.
10. Ready for Review and merge remain owner-controlled.

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
- [x] lookup API and alias lookup are tested;
- [x] terminology lint is tested;
- [x] documentation explains how to add a term;
- [x] disputed terms and competing evidence are explicit;
- [x] repository test suite passes;
- [x] CI evidence is recorded.

Owner acceptance, Ready for Review and merge are intentionally **not** implied by these
implementation checks.

## Resolved terminology findings

- A physical electrical `terminal` is canonical Russian **«вывод»**; literal
  «электрический терминал» is forbidden as a UI/code translation.
- `присоединение распределительного устройства` maps to `feeder bay`, while
  `ячейка` maps to `bay`; they are separate concepts.
- In the EnergoLogic power/KRU scope, **«сборная шина»** is used as the Russian
  `busbar` canonical candidate; generic «шина» remains an alias/supporting IEV form.
- For the operational Russian UI, current switching rules support
  **«включение/отключение»** and **«включенное/отключенное положение»**.
  IEV mechanical wording remains searchable as aliases.
- `заземлитель` is modeled explicitly as `earth electrode`, while its historical
  use for `earthing switch` is a deprecated alias. Lookup therefore fails closed on
  the real normative homonym instead of guessing.

## Owner decisions still required

1. **Circuit-breaker Russian UI canonical**
   - generic current ГОСТ IEC terminology: «автоматический выключатель»;
   - current 3–750 kV Russian equipment standard: «выключатель»;
   - WS-2 proposal: **«выключатель»** for EnergoLogic's power/HV domain, with
     «автоматический выключатель» as an alias.

2. **Earthing-switch Russian UI canonical**
   - current ГОСТ IEC terminology: «заземляющий выключатель»;
   - current ГОСТ Р 57190 terminology: «выключатель заземления»;
   - WS-2 proposal: **«заземляющий выключатель»**, with
     «выключатель заземления» as an alias and historical «заземлитель» deprecated.

Other `provisional` entries are retained because their final wording depends on
additional primary evidence or on future WS-1 domain boundaries. They must not be
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

Implementation head `16b3ea6f73a8cd2a60c5e0ae950a8cb6329c88e8`:
CI run **37204617645 — SUCCESS**.

Final Draft head may contain documentation-only reconciliation commits after this
implementation checkpoint; those commits must also retain green CI before acceptance.
