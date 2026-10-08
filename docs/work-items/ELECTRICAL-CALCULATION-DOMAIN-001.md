# ELECTRICAL-CALCULATION-DOMAIN-001

Status: **IMPLEMENTED CANDIDATE — Draft PR, NOT ACCEPTED**
Workstreams: WS-1 / WS-8
Issue: [#31](https://github.com/genrudko/EnergoLogic/issues/31)
Branch: `domain/electrical-calculation-domain-001`
Draft PR: [#32](https://github.com/genrudko/EnergoLogic/pull/32)

## Goal

Promote the accepted WS-8 solver-neutral DTO boundary to a separately
versioned engineering-parameter source. `CanonicalModel` owns topology,
switching and identity; `electrical-calculation-v1` owns attributable
calculation facts; existing `SolverStudyInput` stays an ephemeral projection.

## Implemented

- JSON Schema + runtime domain parser/serializer; known/unknown/not_applicable
  facts, missing distinct, provenance/source locator.
- Bound kinds: external_grid, line (overhead/cable), load, existing bus/
  transformer_2w/circuit_breaker/disconnector.
- SI positive-sequence values; separately sourced zero-sequence values and
  explicit study limitations. No phase/neutral/grounding topology invented.
- Exact voltage and terminal compatibility rules, switching validation,
  duplicate/orphan and rating/impedance checks, fail-closed required facts.
- Canonical-ID preserving normalized Gate-D DTO/manifest + SHA-256.
- Synthetic 35 kV external grid / 35/0.4 kV transformer / 0.4 kV
  cable / load fixture; static golden JSON; optional adapter integration test.
- Architecture contract and evidence in dedicated files.

## Acceptance

- [x] A. Identical normalized JSON/fingerprint for input order permutations
- [x] B. No backend library import in domain; existing Gate-D DTO unchanged
- [x] C. Explicit voltage/rating/impedance/SC/sequence diagnostics
- [x] D. Source ID/locator/revision preserved in normalized output
- [x] E. End-to-end synthetic golden checked
- [x] F. Existing pure-Python regression tests pass on available VPS
- [ ] GitHub Linux/Windows base + optional pandapower solver CI acceptance
- [ ] Owner acceptance
- [ ] Ready for Review (owner command required)
- [ ] Merge (owner command required)

## Out of scope

- `electrical-v1` changes, pandapower schema in canonical public concepts;
- complete negative/zero-sequence/ground-return qualifications;
- phase/neutral topology; solver worker/IPC/packaging;
- Visio, protection, real site parameter import and numerical reference
  qualification of Kochubeevskaya data.

## Follow-ups

`PHASE-NEUTRAL-TOPOLOGY-001`, fault/negative-sequence capability
qualification, `SOLVER-RUNTIME-HOST-001`, `SITE-SOLVER-ACCEPTANCE-001`,
`SWITCH-FLOW-RESULTS-001` (when needed) and `OPENDSS-ADAPTER-001` after
phase/neutral qualification.

See [calculation contract](../architecture/ELECTRICAL-CALCULATION-V1-CONTRACT.md)
and [acceptance evidence](../evidence/ELECTRICAL-CALCULATION-DOMAIN-001.md).

**Do not merge or mark Ready without explicit owner authorization.**
