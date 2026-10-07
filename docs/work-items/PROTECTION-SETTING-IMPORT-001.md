# PROTECTION-SETTING-IMPORT-001 — Protection setting-card import foundation

Status: **Accepted and merged to `main`**
Workstream: **WS-9A — Protection & Automation / setting-card importer and data model**
Issue: **#21**
Branch: `protection/protection-setting-import-001`
Base: `main@9edc59a0e83f17e94c50ca10f7feac320332b2a1`


## Final repository reconciliation

Merged via PR #22 as `92a62d7` on 2026-10-04.

Any unchecked owner/Ready/Merge boxes or pre-merge wording later in this file are **historical candidate-state evidence** and do not override this final repository status.

## Goal

Create the first source-neutral, deterministic EnergoLogic model and importer boundary for
relay-protection / automation setting cards.

The output is authoritative **settings data**, not protection execution state.

## Architecture boundary

```text
site/vendor setting source
        ↓
source adapter
        ↓
ProtectionSettingCard v1
        ↓
future WS-9B Protection Engine
```

WS-9A must not depend on:

- Visio;
- WS-6 energized-network traversal;
- solver implementation/types;
- protection execution/event logic;
- LLM/OCR heuristics.

WS-6 is explicitly allowed to proceed in parallel.

## Core invariants

1. Preserve source provenance and original source representation.
2. Normalize units only when the conversion is deterministic and dimension-compatible.
3. Never invent missing engineering settings.
4. A source adapter must use an explicit mapping contract; header guessing is forbidden.
5. Parsing/validation errors carry source locators.
6. Stable IDs, not display names, link protected objects, functions, stages and targets.
7. Function concept IDs use English controlled identifiers compatible with WS-2 terminology,
   but this branch has no hard runtime dependency on unmerged WS-2 code.
8. Import is data-only. Pickup, reset, delay expiration, trip and breaker action belong to WS-9B/Gate E.

## Deliverables

- versioned external schema;
- dependency-free runtime model;
- deterministic validator;
- exact quantity/unit normalization;
- source-document provenance + locators;
- explicit function-level measurement-input references;
- JSON adapter;
- configurable CSV/tabular adapter;
- synthetic protection-card fixtures;
- tests;
- architecture/evidence documentation.

## Initial qualified content

Fixtures cover:

- `protection.overcurrent`;
- `protection.instantaneous_overcurrent`;
- `protection.earth_fault`;
- `protection.breaker_failure` associations/settings.

No algorithm is implemented for these functions.

## Out of scope

- arbitrary PDF/image recognition;
- OCR;
- vendor-specific Excel adapters without real source examples;
- pickup/reset/trip execution;
- event timeline;
- breaker operation;
- solver feeds;
- arc optical logic;
- distance/differential calculation logic;
- Ready for Review / merge without owner instruction.

## Acceptance

- [x] separate issue / branch / Draft PR;
- [x] schema is versioned and extensible;
- [x] provenance is mandatory;
- [x] source precision/text is preserved;
- [x] normalized quantities use controlled units;
- [x] incompatible unit/quantity pairs fail closed;
- [x] duplicate IDs fail closed;
- [x] delay semantics are represented as settings, not executed;
- [x] action/target associations are representable without acting on equipment;
- [x] measurement inputs are explicit and function-scoped;
- [x] JSON import is deterministic and rejects unknown/duplicate fields;
- [x] tabular import requires explicit mapping;
- [x] ambiguous/missing required source values fail explicitly;
- [x] tests cover round-trip/data-loss invariants;
- [x] docs explain adding a new source adapter;
- [x] no WS-6/Visio/solver coupling;
- [x] repaired runtime head has Linux/Windows CI green;
- [x] PR remains Draft until explicit owner command.

## Verification

Primary command:

```bash
python -m unittest discover -s tests -v
```


## Verification checkpoints

- fail-closed decoder repair: CI `37208241974` — SUCCESS, representative job
  **93 tests — OK**;
- measurement-input repair head `6153d09ef744af88258b44819ec9c23dbf53a410`:
  CI `37211970711` — SUCCESS.

A final documentation/regression commit is run through the same Linux/Windows
Python 3.11/3.12 matrix before owner acceptance.


## Parallel WS-6 status

WS-6 is active independently in Issue #19 / Draft PR #20 and Issue #23 / Draft PR #24.
Those work items explicitly exclude RZA/protection. WS-9A imports no WS-6 modules and
remains directly based on `main`.

Future integration belongs to Gate E / WS-9B, not this importer work item.

## Final candidate checkpoint

Head before final evidence-only reconciliation:
`a8ddbf0a1e8998c86b783682ca7d2b99a6674f97`.

CI **37212137461 — SUCCESS**, Linux/Windows × Python 3.11/3.12,
**97 tests — OK** in the representative job.

Owner acceptance is not assumed. Draft/merge governance remains unchanged.
