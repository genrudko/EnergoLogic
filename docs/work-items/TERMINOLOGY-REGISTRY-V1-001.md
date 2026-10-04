# TERMINOLOGY-REGISTRY-V1-001 — Terminology Registry v1

Status: **In progress**  
Workstream: **WS-2 — Terminology & Normative Foundations**  
Issue: **#17**  
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

- [ ] schema is understandable and extensible;
- [ ] requested baseline concepts are represented with provenance;
- [ ] canonical RU/EN and code identifiers are internally consistent;
- [ ] aliases are structurally separate from canonical terminology;
- [ ] duplicate IDs/code identifiers fail closed;
- [ ] canonical names are singular fields, not synonym sets;
- [ ] ambiguous normative homonyms are surfaced, never silently selected;
- [ ] lookup API and alias lookup are tested;
- [ ] terminology lint is tested;
- [ ] documentation explains how to add a term;
- [ ] disputed terms and competing evidence are explicit;
- [ ] repository test suite passes;
- [ ] CI evidence is recorded.

## Known terminology decisions requiring evidence

The initial research has already identified cases that must not be flattened into one informal vocabulary:

- `circuit-breaker`: Russian high-voltage product standards use «выключатель», while generic IEC-derived low-voltage terminology also uses «автоматический выключатель»;
- `earthing switch`: current Russian high-voltage apparatus standards use «заземлитель», while another normative vocabulary also uses «заземлитель» for `earth electrode`; the registry therefore must support domain-qualified homonyms;
- `terminal`: IEC terminology distinguishes physical equipment terminals from abstract circuit/topology connection points;
- bus/bay/feeder terminology: Russian power-system standards distinguish «присоединение» and «ячейка», and their IEC English counterparts must not be collapsed;
- energized/de-energized terminology has edition/scope differences in IEC live-working vocabulary.

These are to be resolved or marked provisional with evidence in the implementation/PR rather than chosen implicitly.

## Verification

Canonical local command:

```bash
python -m unittest discover -s tests -v
```

Additional registry-specific validation/lint commands will be documented with the implementation.
