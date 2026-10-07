# OPERATIONAL-SIMULATION-FOUNDATION-001

Status: **Accepted and merged to `main`**
Workstream: WS-6 — Operational Simulation
Issue: #19
Branch: `operational/operational-simulation-foundation-001`
Draft PR: #20


## Final repository reconciliation

Merged via PR #20 as `6dd5e60` on 2026-10-04.

Any unchecked owner/Ready/Merge boxes or pre-merge wording later in this file are **historical candidate-state evidence** and do not override this final repository status.

## Objective

Qualify a deterministic, headless operational-runtime foundation over accepted
canonical topology and switching-state semantics.

Target:

```text
CanonicalModel
+ explicit source terminal references
        ↓
Operational Runtime
        ↓
terminal energization
+ source tracing
+ deterministic state delta
```

## Architectural boundary

This work item consumes:

- `CanonicalModel` topology;
- `electrical-v1` terminal contracts;
- `switching-state-v1`;
- `switch_allows_primary_conduction()`.

It does not redefine those contracts.

The runtime is independent of:

- Visio/COM;
- pandapower/OpenDSS;
- protection/RZA;
- normative Rules Engine;
- site-specific data.

## Bounded v1 semantics

The operational graph is terminal-based.

External canonical `Connection` objects are conductive topology edges.

Internal element conduction for this bounded foundation:

- `bus` — one node terminal;
- `external_link` — one node terminal; source status is explicit runtime input;
- `current_transformer` — conducts between `a` and `b`;
- `transformer_2w` — conducts topologically between `hv` and `lv`;
- `circuit_breaker`, `disconnector` — conduct only when
  `switch_allows_primary_conduction()` returns true.

No source is inferred from element name, kind, voltage, text or geometry.

## Acceptance checklist

- [x] issue and isolated branch from current main;
- [x] Draft PR;
- [x] public headless operational contract;
- [x] deterministic terminal graph traversal;
- [x] explicit source references;
- [x] source attribution including multiple sources;
- [x] closed/open switching topology delta;
- [x] withdrawable repair/control non-conduction;
- [x] transformer topological energization;
- [x] disconnected island handling;
- [x] normalized invalid-model / invalid-source failure;
- [x] deterministic before/after state delta;
- [x] full existing regression green — 84/84 PASS locally;
- [ ] Linux/Windows CI green;
- [x] evidence and known limitations;
- [ ] owner acceptance;
- [ ] Ready for Review — owner command only;
- [ ] Merge — owner command only.

## Explicit out of scope

- earthing/grounding-switch semantics;
- interlocks;
- operation permission/safety rules;
- event timeline;
- switching forms/training;
- protection/RZA;
- normative rules;
- power flow / short circuit;
- Visio rendering;
- Site Profile integration.

## Governance

Keep the PR Draft. Do not mark Ready for Review or merge without explicit owner
instruction.
