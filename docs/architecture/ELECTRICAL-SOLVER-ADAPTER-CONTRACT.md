# Electrical Solver Adapter Contract

Status: **WS-8 spike-qualified candidate contract**  
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

## 9. Explicitly unresolved by this contract

The spike does not decide:

- production canonical semantics for lines/cables, loads and external sources;
- generator and motor semantics;
- shunts/capacitors/reactors;
- three-winding transformers or autotransformers;
- tap changer/RPN semantics;
- explicit phase-domain canonical topology;
- neutral and earthing network representation;
- current through switching devices as a first-class normalized result;
- minimum short-circuit case parameters;
- solver selection policy for unbalanced/harmonic/QSTS studies;
- production process boundary / IPC / crash isolation;
- final Windows runtime bundling mechanism.

Those require later bounded architectural decisions.
