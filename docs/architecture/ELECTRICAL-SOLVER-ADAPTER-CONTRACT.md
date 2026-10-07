# Electrical Solver Adapter Contract

Status: **Accepted baseline in `main` via PR #15 / `a5252e1`**
Work item: `ELECTRICAL-SOLVER-SPIKE-001`
Issue: #14
Draft PR: #15

This contract defines the boundary required by Gate D (Electrical Calculation
Contract). It deliberately does **not** change the accepted canonical
`electrical-v1` domain semantics.

## 1. Architectural boundary

```text
EnergoLogic CanonicalModel
        │
        ├── canonical connectivity
        ├── canonical switching state
        │
        └── stable canonical IDs
                 │
                 ▼
        SolverStudyInput
        (solver-neutral parameters)
                 │
                 ▼
          Solver Adapter
                 │
        ┌────────┴────────┐
        ▼                 ▼
   pandapower         future solver
        │
        ▼
Normalized EnergoLogic Results
```

Invariants:

1. `energologic.core` does not import solver stacks.
2. `energologic.domain` does not import solver stacks.
3. pandapower objects, DataFrames, table indices and element schemas are private
   implementation details of `PandapowerAdapter`.
4. Public inputs and outputs use EnergoLogic dataclasses and canonical stable IDs.
5. A solver may be replaced without changing the canonical object identity.
6. Raw Python exception objects are never part of the public result contract.
7. Solver-specific units are converted explicitly at the adapter boundary.
8. Visio is not imported or required by the solver package.

## 2. Public input

`SolverStudyInput` contains:

- `model: CanonicalModel`;
- solver-neutral external-grid electrical parameters;
- solver-neutral line electrical parameters;
- solver-neutral two-winding transformer electrical parameters;
- solver-neutral load electrical parameters;
- `inactive_equipment_ids`.

Canonical topology and switching state remain in `CanonicalModel`.
Electrical calculation parameters are expressed in engineering quantities, not
pandapower table fields.

The spike uses the following SI-facing quantities:

| Quantity | EnergoLogic contract |
|---|---|
| nominal voltage | V |
| current | A |
| active power | W |
| reactive power | var |
| apparent/rated/short-circuit power | VA |
| resistance/reactance | ohm, ohm/m |
| capacitance | F/m |
| length | m |
| angle | degree |
| loading | percent |
| voltage magnitude where dimensionless is required | p.u. |

Pandapower's kV, kA, MW, Mvar, MVA, ohm/km, nF/km and p.u. representation is
converted only inside the adapter.

## 3. Operating state

For `circuit_breaker` and `disconnector`, the adapter consumes the accepted
canonical switching semantics through `switch_allows_primary_conduction()`.

A switch conducts only when the canonical state says it conducts. The adapter
does not infer switch state from pandapower.

`inactive_equipment_ids` is an orthogonal calculation-state overlay for
sources, branches, transformers, loads and switching equipment. The current
spike intentionally rejects inactive canonical buses.

## 4. Topology mapping

The spike requires each solver equipment terminal to connect directly to one
canonical bus terminal. This is a bounded adapter constraint, not a statement
that future EnergoLogic topology must always use this representation.

Spike terminal contracts:

| Candidate kind | Terminals |
|---|---|
| `bus` | `node` |
| `external_grid` | `node` |
| `line` | `from`, `to` |
| `load` | `node` |
| `transformer_2w` | `hv`, `lv` |
| `circuit_breaker` | `a`, `b` |
| `disconnector` | `a`, `b` |

### Important domain-model qualification

`bus`, `circuit_breaker`, `disconnector` and `transformer_2w` already
have accepted domain semantics in the repository.

The spike's `external_grid`, `line` and `load` kinds are used in a
**structurally canonical test fixture** so that the adapter can be qualified
without polluting `electrical-v1`.

They are **not promoted to accepted production `electrical-v1` semantics by
this work item**. Production adoption requires a separate bounded domain
decision defining source/load/line semantics, required parameters and
validation rules.

## 5. Power-flow output

`PowerFlowResult` returns:

- normalized status;
- solver name/version for provenance;
- deterministic topology signature;
- bus results keyed by canonical bus ID;
- branch results keyed by canonical line/transformer ID;
- normalized warnings/errors.

Bus results:

- voltage in V;
- voltage magnitude in p.u.;
- voltage angle in degrees;
- net active power in W;
- net reactive power in var.

Branch results:

- element kind;
- line current in A;
- side-specific currents in A;
- active/reactive power at both ends in W/var;
- active/reactive losses in W/var;
- loading in percent.

For a line, `current_a` is the maximum of the two terminal magnitudes and both
terminal currents are also retained.

For a transformer, `current_a` is intentionally `None`; HV and LV currents
are returned separately because a single max(HV, LV) magnitude is physically
misleading across a transformation ratio.

## 6. Short-circuit output

`ShortCircuitRequest` identifies the fault location by canonical bus ID and
uses solver-neutral fault types:

- `3ph`;
- `2ph`;
- `1ph`.

`ShortCircuitResult` returns, where the backend provides them:

- `Ik''` in A;
- peak current `ip` in A;
- equivalent thermal current `Ith` in A;
- short-circuit apparent power in VA;
- equivalent R/X in ohm;
- branch contributions keyed by canonical branch ID.

Missing backend values remain `None`; the adapter does not synthesize them.

For transformer branch contributions, HV/LV currents are side-specific and no
single aggregate transformer current is invented.

## 7. Normalized result states

The public status enum is:

- `success`;
- `non-converged`;
- `invalid_model`;
- `unsupported_configuration`;
- `missing_parameters`;
- `solver_failure`.

Public errors are `SolverMessage` records with:

- stable error code;
- human-readable diagnostic;
- optional canonical ID.

The raw Python exception object and traceback are not returned.

## 8. Solver dependency isolation

Pandapower is an optional extra:

```text
energologic[solver-pandapower]
```

The base EnergoLogic package remains dependency-free at runtime.

The adapter imports pandapower lazily. Importing the public solver contract does
not require pandapower to be installed.

The spike pins pandapower to `3.5.5` so numerical goldens and backend behavior
are reproducible.

## 9. Production boundary after the spike

The architectural questions exposed by this contract are resolved/reclassified
in:

ELECTRICAL-SOLVER-PRODUCTION-DECISIONS.md

The resulting production boundary is:

- canonical electrical parameters are solver-neutral canonical engineering
  facts;
- the current SolverStudyInput parameter tuples are spike DTOs, not persisted
  source of truth;
- electrical-v1 remains unchanged; production calculation semantics are added
  through a separately qualified electrical-calculation-v1 contract;
- sequence and zero-sequence data is explicit and provenance-bearing;
- balanced AC power flow plus qualified IEC 60909 is the first production
  calculation scope;
- switchgear current is terminal-scoped and may be unavailable when solver
  topology does not permit unique attribution;
- the packaged production solver runs out-of-process in a bundled x64 worker;
- solver selection is explicit capability routing with no silent fallback;
- pandapower is the first/default adapter for the qualified scope;
- OpenDSS is introduced after phase/neutral topology qualification for
  unbalanced/neutral/harmonic/QSTS study classes;
- solver and numerical-golden versions are release-controlled.

Remaining implementation/data dependencies are represented as bounded follow-up
work items instead of open architecture questions.
