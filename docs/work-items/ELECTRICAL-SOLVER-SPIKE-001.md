# ELECTRICAL-SOLVER-SPIKE-001

Status: **Implementation complete — awaiting final CI and owner acceptance**  
Workstream: WS-8 — Electrical Solver  
Issue: #14  
Branch: `solver/electrical-solver-spike-001`  
Draft PR: #15

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

pandapower remains an implementation detail behind the adapter and does not
define the EnergoLogic canonical model.

## Baseline

The branch starts from `main` after `TRANSFORMER-SEMANTICS-001`.

Relevant accepted architecture:

- canonical model is source of truth;
- `energologic.core` remains dependency-free;
- `energologic.domain` depends only on core and must not import solver stacks;
- switching state is canonical and independent of frontend state;
- two-winding transformer voltage semantics are terminal-scoped;
- solver integration is a separate bounded work item.

The canonical project plan defines WS-8 as a headless workstream and Gate D as
the electrical-calculation contract.

## Implemented artifacts

- `src/energologic/solvers/contracts.py`
  - solver-neutral inputs/results/statuses;
- `src/energologic/solvers/units.py`
  - explicit unit conversions;
- `src/energologic/solvers/pandapower_adapter.py`
  - private pandapower mapping;
- `examples/ws8-synthetic-network.json`
  - canonical-first two-section synthetic network;
- `tests/fixtures/ws8-pandapower-3.5.5-golden.json`
  - reproducible numerical golden;
- `tools/solver_dependency_probe.py`
  - dependency/footprint evidence;
- `docs/architecture/ELECTRICAL-SOLVER-ADAPTER-CONTRACT.md`
  - Gate-D candidate contract;
- `docs/evidence/ELECTRICAL-SOLVER-SPIKE-001.md`
  - numerical, packaging and limitation evidence.

## Architectural rules

1. No pandapower import from `src/energologic/core` or
   `src/energologic/domain`.
2. No pandapower DataFrame/index/type in a public EnergoLogic result.
3. Stable canonical IDs are the only external identity in normalized results.
4. Raw Python/pandapower exception objects are translated to normalized status
   and `SolverMessage`.
5. Solver-specific units are converted explicitly at the boundary.
6. Synthetic fixtures are canonical first; pandapower networks are generated
   from them.
7. No Visio imports in the solver package.
8. No production-canonical semantic change without a separate architecture
   decision.

## Acceptance checklist

- [x] Solver Adapter contract
- [x] Synthetic canonical network
- [x] Power-flow State A
- [x] Power-flow State B with topology/result delta
- [x] 3-phase short circuit
- [x] 2-phase short circuit
- [x] 1-phase-to-earth short circuit with explicit zero-sequence data
- [x] normalized results keyed by canonical IDs
- [x] active/inactive equipment input
- [x] unit conversion tests
- [x] golden numerical fixture
- [x] independent analytical 3-phase source-bus check
- [x] canonical-ID preservation
- [x] static no-pandapower-import guard for core/domain
- [x] normalized invalid-model and missing-parameter errors
- [x] packaging/dependency findings
- [x] pandapower limitations
- [x] production recommendation
- [x] VPS headless qualification — 83 tests PASS on Python 3.14.4 / pandapower 3.5.5
- [ ] GitHub CI green on final head
- [ ] owner acceptance
- [ ] Ready for Review — owner command only
- [ ] Merge — owner command only

## Key qualification result

Canonical State A has the bus coupler open; State B changes only
`breaker:bus-coupler.switch_state` to `closed`.

Observed power-flow delta:

- feeder A current: 68.076 A → 58.358 A;
- feeder B current: 17.532 A → 27.261 A;
- section voltage difference: 13.620 V → 0 V.

Three-phase fault on section A:

- `Ik''`: 7.700 kA;
- `ip`: 17.348 kA;
- `Ith`: 7.773 kA.

The external-grid 3-phase hand reference
`S_sc / (sqrt(3) * U)` gives 8.247861 kA; the adapter result agrees to
floating-point precision.

## Recommendation

Pandapower is qualified as the preferred first production adapter for balanced
AC power flow and IEC 60909 short-circuit calculations.

OpenDSS should be added later for study classes where its phase-domain
distribution model is materially stronger, especially unbalance, neutral
behavior, harmonics and long QSTS.

Protection/RZA remains a separate EnergoLogic engine.

## Explicit unresolved architecture

This spike intentionally does **not** promote `external_grid`, `line` and
`load` to accepted `electrical-v1` production semantics.

Before production integration, separate bounded decisions are required for:

- source/load/line/generator/shunt canonical semantics;
- positive/negative/zero-sequence parameter ownership and provenance;
- breaker/disconnector current normalization;
- phase-domain/neutral topology;
- solver process/IPC boundary and Windows bundling;
- solver-version/golden upgrade policy;
- pandapower versus OpenDSS study-selection policy.

## Out of scope

- Visio UI/rendering/editor changes;
- protection/RZA logic;
- rules engine;
- Kochubeevskaya site model;
- production installer;
- production packaging;
- canonical semantics redesign outside this bounded spike.

## Governance

Keep PR #15 Draft.

Do not mark Ready for Review and do not merge without explicit owner
instruction.
