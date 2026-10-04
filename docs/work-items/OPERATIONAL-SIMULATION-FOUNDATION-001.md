# OPERATIONAL-SIMULATION-FOUNDATION-001

Status: **Implementation in progress**  
Workstream: WS-6 — Operational Simulation  
Issue: #19  
Branch: `operational/operational-simulation-foundation-001`

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
- [ ] Draft PR;
- [ ] public headless operational contract;
- [ ] deterministic terminal graph traversal;
- [ ] explicit source references;
- [ ] source attribution including multiple sources;
- [ ] closed/open switching topology delta;
- [ ] withdrawable repair/control non-conduction;
- [ ] transformer topological energization;
- [ ] disconnected island handling;
- [ ] normalized invalid-model / invalid-source failure;
- [ ] deterministic before/after state delta;
- [ ] full existing regression green;
- [ ] Linux/Windows CI green;
- [ ] evidence and known limitations;
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
