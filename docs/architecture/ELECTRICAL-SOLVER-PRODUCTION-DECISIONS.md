# Electrical Solver — Production Architecture Decisions after WS-8

Status: **candidate architecture for owner acceptance in ELECTRICAL-SOLVER-SPIKE-001**  
Workstream: WS-8 — Electrical Solver  
Issue: #14  
Draft PR: #15

This document closes the architectural questions that can be decided from the
WS-8 spike and the canonical project plan. Items that require new domain
semantics or real site data are converted into explicit bounded follow-up work,
not left as open-ended questions.

## Decision 1 — Electrical parameters belong to the canonical domain, not to a solver

The canonical project plan already fixes this direction:

- Gate A includes **Electrical Parameters** in the Domain Model Contract;
- Gate D defines solver input, electrical parameters, normalized results and
  result/error states;
- Site Profile contains the site-specific canonical electrical model,
  equipment and parameters.

Therefore:

1. Solver-neutral engineering parameters are canonical engineering facts.
2. Site Profile owns the site-specific instance, revision and provenance of
   those facts.
3. Operating values/state that change by scenario are a separate operating
   state/scenario layer.
4. pandapower/OpenDSS field names and units never become canonical field names.
5. The current SolverStudyInput parameter tuples are a **spike DTO** used to
   qualify Gate D. They are not a second source of truth and are not the final
   persistence model.
6. In production, the solver input DTO is materialized from:
   - canonical model;
   - canonical electrical parameters;
   - current operating/scenario state.

### Consequence

Before a production solver integration is merged into the product baseline, a
bounded WS-1/WS-8 domain item must define the production electrical-calculation
profile and then adapt SolverStudyInput to consume that profile.

## Decision 2 — Do not silently mutate electrical-v1

The accepted electrical-v1 profile remains the qualified static subset already
in main.

The WS-8 synthetic kinds external_grid, line and load proved adapter feasibility,
but this spike does not retroactively promote them to accepted production
semantics.

The production expansion must be a separate versioned profile/contract,
provisionally named:

electrical-calculation-v1

Minimum first scope:

- network source / external network;
- line with explicit construction semantics (overhead/cable where relevant);
- load;
- existing bus/switchgear/transformer semantics reused by reference;
- electrical parameters required by balanced power flow and IEC 60909.

Generator, motor, shunt, capacitor/reactor, tap changer, three-winding
transformer and autotransformer semantics are added only when a bounded use case
requires them.

Final RU/EN names and code identifiers remain subject to Gate B terminology
qualification before the new profile is frozen.

## Decision 3 — Sequence data is explicit engineering data

Production calculation semantics must not infer zero-sequence data from
positive-sequence data merely because a solver can accept a default.

The production electrical-parameter model must support structured sequence
data, in SI units, with provenance:

- positive sequence;
- negative sequence where the study requires an independent value;
- zero sequence where the study requires it.

For single-phase-to-earth short-circuit studies, the required source, line,
transformer vector-group, neutral/earthing and zero-sequence data are mandatory.
If they are absent, the normalized result is missing_parameters.

If a deterministic engineering derivation is ever allowed, the derivation rule
and source provenance must be explicit and testable; it must not be an adapter
guess.

## Decision 4 — Balanced positive-sequence studies are production v1

The first production solver capability is:

- balanced AC power flow;
- IEC 60909 short-circuit studies qualified by the production profile.

Pandapower 3.5.5 also exposes asymmetric/three-phase power flow and several
other calculation families, but API existence is not production qualification.

Phase-domain topology, explicit neutral conductors and detailed unbalanced
studies require a separate canonical extension. They must not be squeezed into
the balanced electrical-calculation-v1 contract.

## Decision 5 — Switchgear current is terminal-scoped and may be unavailable

A circuit breaker or disconnector is a canonical switching/topology object, not
a pandapower branch.

Production normalized results therefore follow these rules:

1. Do not invent one aggregate breaker current from fused solver buses.
2. If a solver can uniquely attribute current to the switching device, expose
   side/terminal currents keyed by canonical terminal IDs.
3. If the device lies in a validated single-series path, a derived current may
   be associated with it from the adjacent branch only when the derivation is
   explicit and provenance is retained.
4. If current attribution is ambiguous, return it as unavailable/ambiguous
   rather than selecting an arbitrary adjacent branch.
5. Protection logic must consume qualified measured/derived quantities through
   Gate E, not raw solver table columns.

A dedicated switch-flow result contract may be added later if a concrete
consumer requires it.

## Decision 6 — Production solver runtime is out-of-process and x64

The production architecture is:

EnergoLogic Runtime → local Solver Worker process → Solver Adapter

The solver worker:

- is headless;
- is independent of Visio COM;
- ships with its own bundled x64 Python runtime and pinned dependencies;
- works with both x86 and x64 Visio because process bitness is decoupled;
- can be restarted after solver/native-library failure without taking Visio
  down;
- performs a version/capability handshake before accepting studies;
- accepts versioned request/response messages;
- supports timeout/cancellation and returns normalized failure status.

The exact local IPC transport is an implementation choice for WS-3
Packaging/Runtime. It is not allowed to change the canonical or Gate-D solver
contract.

There is no requirement for the target PC to have Python, pip or solver
packages installed separately.

## Decision 7 — Solver selection is explicit capability routing

No adapter may silently fall back to another solver after failure and present
the result as if it came from the originally selected backend.

Production routing is by explicit study capability.

### pandapower — first/default production adapter

Use for the first qualified scope:

- balanced AC power flow;
- voltage/angle/P/Q;
- line and transformer loading/losses;
- topology changes from canonical switching state;
- qualified IEC 60909 short-circuit studies.

### OpenDSS — second adapter after phase/neutral domain qualification

Use where a phase-domain distribution model is materially required:

- unbalanced phase-domain networks;
- explicit neutral/earth conductors;
- detailed distribution studies;
- harmonics;
- long quasi-static time-series (QSTS / daily / yearly);
- distribution DER/control cases that depend on those capabilities.

OpenDSS is not a reason to change the canonical model into an OpenDSS schema.

### Specialized solver

Use a dedicated engine for study classes outside both qualified adapters,
especially EMT/waveform transients and high-fidelity dynamic/transient-stability
studies.

### Routing rule

A study request declares its study type and required capabilities. If the
selected/available adapter cannot satisfy them, EnergoLogic returns
unsupported_configuration, or a higher-level router explicitly selects a
different qualified adapter and records that choice in result provenance.

## Decision 8 — Solver and golden versions are release-controlled

Every production solver bundle pins:

- adapter contract version;
- adapter implementation version;
- solver name/version;
- Python/runtime version;
- dependency lock/bundle identity.

Normalized result provenance must include at least solver name/version and input
model/study fingerprint.

A solver upgrade is not an ordinary dependency bump. It requires:

1. release-note/API review;
2. full numerical golden rerun;
3. explicit review of all changed golden values;
4. independent analytical/trusted-reference rerun;
5. Linux development CI and Windows production-platform CI;
6. dependency/native-binary and footprint review;
7. packaging/offline qualification;
8. explicit project acceptance before changing the production pin.

No automatic updater may silently replace the solver runtime in an accepted
offline installation.

## Decision 9 — Kochubeevskaya solver acceptance has a reference hierarchy

The canonical plan already names Kochubeevskaya WPP as the principal real
end-to-end acceptance case.

The solver acceptance methodology is:

1. hand calculations for simple/reducible subnetworks;
2. authoritative design/commissioning/source calculations where available;
3. independent second-solver comparison for selected non-trivial cases;
4. engineering invariants such as connectivity, expected de-energization and
   conservation/balance checks;
5. predeclared tolerances per quantity and study class;
6. golden fixtures stored with source/provenance.

A second solver is corroborating evidence, not automatically ground truth.

The real numerical reference set cannot be completed in WS-8 because the
Kochubeevskaya production Site Profile is explicitly out of scope. Populating
that set is a bounded site-acceptance task, not an unresolved architecture
question.

## Bounded follow-up work created by these decisions

The following are no longer open design questions; they are explicit dependent
work items to schedule.

### ELECTRICAL-CALCULATION-DOMAIN-001 — WS-1 + WS-8

Define and qualify:

- electrical-calculation-v1;
- production source/line/cable/load semantics;
- solver-neutral equipment electrical parameters;
- sequence parameter structures;
- parameter validation/provenance;
- materialization into Gate-D solver input.

### PHASE-NEUTRAL-TOPOLOGY-001 — WS-1

Define phase/conductor/neutral/earthing topology without breaking the balanced
canonical baseline. This is a prerequisite for a production OpenDSS
phase-domain adapter.

### SOLVER-RUNTIME-HOST-001 — WS-3 + WS-8

Implement and qualify:

- bundled x64 solver worker;
- local versioned IPC;
- lifecycle/restart/timeout/cancellation;
- offline runtime bundle;
- x86/x64 Visio interoperability.

### SWITCH-FLOW-RESULTS-001 — WS-8 / Gate E dependency

Only when a real consumer requires it, qualify current attribution for
switchgear and the normalized terminal-current contract.

### OPENDSS-ADAPTER-001 — WS-8

Start only after the phase/neutral domain contract needed by its target studies
is accepted.

### SITE-SOLVER-ACCEPTANCE-001 — WS-11 + WS-8

Build the Kochubeevskaya reference/golden set using the hierarchy above.

## What remains genuinely unknown

Only data-dependent details remain unknown, not architectural direction:

- the exact real Kochubeevskaya parameter/reference values until source data are
  ingested;
- which later study classes the project will actually need beyond the canonical
  roadmap;
- the exact IPC implementation chosen by WS-3 after runtime-host prototyping.

Those unknowns do not block acceptance of the WS-8 pandapower adapter spike.

## External capability references

- pandapower 3.5.5 power-flow documentation:
  https://pandapower.readthedocs.io/en/stable/powerflow/run.html
- pandapower 3.5.5 IEC 60909 short-circuit documentation:
  https://pandapower.readthedocs.io/en/latest/shortcircuit.html
- OpenDSS general n-phase / distribution-system model:
  https://opendss.epri.com/OpenDSSDistributionSystem.html
- OpenDSS explicit phases/neutral/other conductors:
  https://opendss.epri.com/PhasesandOtherConductors.html
- OpenDSS Daily/Yearly/Harmonic solution modes:
  https://opendss.epri.com/Mode2.html
