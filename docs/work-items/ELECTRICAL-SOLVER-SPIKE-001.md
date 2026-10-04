# ELECTRICAL-SOLVER-SPIKE-001

Status: In progress  
Workstream: WS-8 — Electrical Solver  
Issue: #14  
Branch: `solver/electrical-solver-spike-001`  
Draft PR: pending at work-item creation

## Objective

Qualify a Visio-independent, headless electrical-solver boundary:

```text
EnergoLogic Canonical Model
        ↓
Solver Adapter
        ↓
pandapower
        ↓
Normalized EnergoLogic Results
```

pandapower remains an implementation detail behind the adapter and does not define the EnergoLogic canonical model.

## Baseline

The branch starts from `main` after `TRANSFORMER-SEMANTICS-001`.

Relevant accepted architecture:
- canonical model is source of truth;
- `energologic.core` remains dependency-free;
- `energologic.domain` depends only on core and must not import solver stacks;
- switching state is canonical and independent of frontend state;
- two-winding transformer voltage semantics are terminal-scoped;
- solver integration is a separate bounded work item.

The later canonical product plan defines WS-8 as a headless workstream and Gate D as the electrical-calculation contract. This spike implements a bounded candidate contract without changing existing canonical semantics by implication.

## Deliverables

- solver-neutral public contract and normalized result types;
- explicit unit conversion boundary;
- synthetic canonical network independent of pandapower;
- pandapower adapter;
- State A / State B power-flow qualification;
- short-circuit qualification;
- golden fixtures and deterministic tests;
- analytical cross-check;
- packaging/dependency findings;
- limitations and production recommendation.

## Architectural rules

1. No pandapower import from `src/energologic/core` or `src/energologic/domain`.
2. No pandapower DataFrame/index/type in a public EnergoLogic result.
3. Stable canonical IDs are the only external identity in normalized results.
4. Raw Python/pandapower exceptions are translated to normalized solver status/errors.
5. Solver-specific units are converted explicitly at the boundary.
6. Synthetic fixtures are canonical first; pandapower networks are generated from them.
7. No Visio imports in the solver package.
8. No production-canonical semantic change without a separate architecture decision.

## Acceptance checklist

- [ ] Solver Adapter contract
- [ ] Synthetic canonical network
- [ ] Power-flow State A
- [ ] Power-flow State B with topology/result delta
- [ ] 3-phase short circuit
- [ ] 2-phase short circuit qualified or explicitly rejected with evidence
- [ ] 1-phase-to-earth qualified or explicitly rejected with evidence
- [ ] normalized results keyed by canonical IDs
- [ ] unit conversion tests
- [ ] golden numerical fixture
- [ ] independent analytical check
- [ ] canonical-ID preservation
- [ ] static no-pandapower-import guard for core/domain
- [ ] packaging/dependency findings
- [ ] pandapower limitations
- [ ] production recommendation
- [ ] CI green
- [ ] owner acceptance
- [ ] Ready/Merge only by explicit owner instruction

## Out of scope

- Visio UI/rendering/editor changes;
- protection/RZA;
- rules engine;
- Kochubeevskaya site model;
- production installer;
- production packaging;
- real Site Profile;
- canonical semantics redesign outside this bounded spike.
