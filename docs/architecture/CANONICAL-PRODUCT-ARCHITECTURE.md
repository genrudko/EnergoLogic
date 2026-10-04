# EnergoLogic — canonical product architecture and delivery plan

Status: **Canonical target architecture**  
Language of user interface: **Russian**  
Language of code and internal identifiers: **English**  

This document defines the target product boundary and non-negotiable architectural requirements for EnergoLogic. Individual work items implement this target incrementally and must not silently redefine it.

## 1. Product definition

EnergoLogic is an engineering electrical-system platform in which Microsoft Visio is the primary engineering frontend, editor and mnemonic display, while the canonical electrical model remains the source of truth.

The target product combines:

1. a Visio-based engineering editor;
2. a canonical electrical topology and equipment model;
3. live operational-state simulation;
4. switching-operation and switching-form simulation;
5. electrical calculations;
6. protection and automation simulation;
7. Russian normative and site-rule validation;
8. import/migration of existing diagrams;
9. automatic diagram generation;
10. fully self-contained offline deployment.

Visio is a frontend and renderer, not the computational or normative source of truth.

## 2. Non-negotiable platform requirements

### 2.1 Supported operating systems

Production target:

- Windows 10;
- Windows 11.

### 2.2 Supported Microsoft Visio range

EnergoLogic must support desktop Microsoft Visio from **Visio 2010 through the latest supported desktop Visio / Microsoft 365 Visio release**.

Implementation rules:

- use the oldest common Visio API surface where practical;
- detect version/capabilities at runtime;
- isolate newer-version-only behavior behind explicit capability checks;
- provide compatible fallback behavior where possible;
- qualify supported x86/x64 combinations instead of assuming one Office bitness;
- maintain a release compatibility matrix and automated/manual acceptance gates across representative Visio generations.

The requirement is intentionally version-relative: it is not limited to a fixed latest version such as Visio 2024.

### 2.3 Standalone / offline delivery

The only product-level external prerequisite on a target workstation should be a supported Windows installation and a supported installed Microsoft Visio.

EnergoLogic must ship the runtimes and libraries it needs. A user must not be required to install or configure separately:

- Python;
- Python packages;
- .NET runtime components required by EnergoLogic;
- calculation libraries;
- native solver dependencies;
- Git;
- Node.js;
- developer SDKs;
- EnergoLogic stencil libraries;
- protection libraries;
- normative rule data.

Internet access must not be required for:

- editing;
- diagram generation;
- import/migration;
- operational simulation;
- power-flow calculation;
- short-circuit calculation;
- protection simulation;
- switching-form validation.

Network access may be used for optional software, library or normative-dataset updates.

A conventional installer/bootstrapper is acceptable. “Standalone” does not require one monolithic executable.

## 3. Terminology contract

EnergoLogic must use controlled professional electrical terminology.

### 3.1 User-facing language

The application UI is Russian.

User-facing equipment names, states, operations, calculations, protection functions and engineering concepts must use canonical Russian power-engineering terminology.

### 3.2 Code language

Source code, APIs, schemas and internal identifiers use English.

English identifiers must use canonical international electrical terminology rather than transliteration or ad-hoc synonyms.

Examples:

- `CircuitBreaker` — выключатель;
- `Disconnector` — разъединитель;
- `EarthingSwitch` — заземлитель;
- `CurrentTransformer` — трансформатор тока;
- `VoltageTransformer` — трансформатор напряжения;
- `Busbar` / `BusbarSection` — шина / секция шин;
- `ShortCircuitCalculation` — расчёт токов короткого замыкания.

For switching state, use domain terms such as `open/closed` rather than generic `on/off` where the domain concept requires it.

### 3.3 Terminology Registry

A controlled Terminology Registry is a first-class project artifact.

Every new domain concept must define, before acceptance:

- stable concept ID;
- canonical Russian term;
- canonical English term;
- code identifier;
- authoritative terminology source(s);
- approved abbreviations;
- import aliases/synonyms;
- deprecated/forbidden aliases where needed.

Aliases may be accepted during legacy import but must not replace canonical terminology in generated documents or UI.

The primary terminology sources should be the applicable GOST/IEC terminology and IEC International Electrotechnical Vocabulary, supplemented by Russian normative and industry documents where required.

## 4. Layered architecture

Target high-level architecture:

```text
Microsoft Visio
  Engineering Editor / Mnemonic / User Commands
                     |
                     v
            EnergoLogic Canonical Model
                     |
        +------------+-------------+
        |            |             |
        v            v             v
Operational      Electrical     Protection
Runtime          Solver Layer    Engine
        |            |             |
        +------------+-------------+
                     |
                     v
              RU Rules Engine
                     |
                     v
          Results / Validation / UI
```

Supporting subsystems:

- Visio Importer / Legacy Migrator;
- Scheme Generator / Auto-layout;
- Terminology Registry;
- Normative Source Registry;
- Site Profile;
- packaging/runtime layer.

No solver, Visio document or protection implementation may become the canonical data model.

## 5. Canonical electrical model

The canonical model must represent at least:

- stations/substations;
- voltage levels;
- busbars and busbar sections;
- bays/cells/feeders;
- circuit-breakers;
- disconnectors;
- earthing switches;
- current transformers;
- voltage transformers;
- power transformers;
- lines/cables;
- sources;
- loads;
- generators where applicable;
- terminals;
- electrical nodes;
- equipment connectivity;
- switching state;
- earthing state;
- equipment identity;
- electrical parameters;
- protection associations;
- normative/site metadata.

Visual geometry and Visio Glue are representations of connectivity, not the sole definition of the electrical network.

## 6. Visio role

Visio is the primary:

- engineering editor;
- diagram renderer;
- mnemonic display;
- command surface for switching simulation;
- visualization surface for calculated values and protection events.

Visio is not intended to become a full industrial SCADA platform.

For simulation rendering:

- update only changed/dirty objects;
- batch COM/ShapeSheet changes;
- use ShapeSheet-driven visual states where practical;
- avoid full-diagram redraws after every model change;
- keep calculation and protection state outside Visio.

Target interaction latency is human-interactive engineering use, not high-frequency telemetry.

## 7. Operational simulation

The operational runtime must support live network-state simulation based on canonical topology.

Initial target capabilities:

- energized/de-energized network traversal;
- source-of-supply tracing;
- circuit-breaker state;
- disconnector state;
- earthing-switch state;
- bus/section state;
- alternative supply paths;
- interlocks;
- invalid switching-state detection;
- operation sequencing;
- event timeline.

A switching action must modify canonical state, trigger topology recalculation and update only affected visual objects.

## 8. Switching forms and training scenarios

EnergoLogic must support simulation and validation of switching forms / switching programs.

Target workflow:

1. define initial network state;
2. define target operational state;
3. execute operations step-by-step;
4. validate each operation against topology, interlocks, protection state, normative rules and site rules;
5. record the operation timeline;
6. explain rejected operations;
7. validate the final state.

This supports both engineering checking and training scenarios.

## 9. Electrical solver layer

Electrical calculations must be isolated behind solver adapters.

Initial preferred open-source solver: **pandapower**.

Potential additional adapter: **OpenDSS**.

The canonical model must not depend on a solver-specific schema.

### 9.1 Initial calculation scope

- AC power flow;
- bus voltages;
- branch currents;
- active/reactive power flows;
- transformer loading;
- losses;
- limit/overload checks;
- short-circuit calculations;
- results attached back to canonical model objects.

### 9.2 Short-circuit calculations

Target scope includes, as data and solver support permit:

- three-phase faults;
- phase-to-phase faults;
- single-phase-to-earth faults;
- other asymmetrical fault cases;
- initial symmetrical short-circuit current;
- peak current;
- thermal short-circuit current;
- branch contributions;
- dependence on actual switching topology.

Russian/IEC calculation-method requirements must be versioned and verified independently from the solver implementation.

## 10. Protection and automation engine

Protection simulation is a separate layer from the electrical solver.

The solver computes electrical quantities; the Protection Engine evaluates protection logic and device behavior using real site settings.

Site protection-setting cards are first-class input data.

Initial/target protection functions include progressively:

- overcurrent protection;
- instantaneous overcurrent;
- earth-fault protection;
- directional overcurrent / earth-fault protection;
- under/overvoltage;
- under/overfrequency;
- negative-sequence functions;
- power-direction functions;
- breaker failure protection;
- automatic transfer/reclosing logic where applicable;
- differential protection;
- distance protection;
- other site-specific functions.

Protection behavior must model:

- pickup criteria;
- measured quantities;
- delays;
- logical enabling/blocking;
- input signals;
- trip matrices;
- target breakers;
- reserve actions;
- reset conditions;
- event timing.

## 11. Arc-fault protection

Arc-fault protection is a first-class protection function for applicable switchgear.

The model must support, depending on the real station implementation:

- optical/light detection;
- current supervision;
- zone/compartment association;
- start logic;
- blocking/permission logic;
- trip matrix;
- associated breakers;
- breaker opening time;
- breaker-failure escalation;
- event sequence and clearing time.

Arc-fault protection simulation is distinct from personnel arc-flash incident-energy calculation. If arc-flash energy analysis is added later, it must be a separate calculation module with its own validated methodology.

## 12. Russian normative and site-rule model

Compliance with Russian operating reality is a core product requirement.

The rules layer must separate:

### Federal / industry normative rules

Versioned requirements from applicable Russian laws, rules, orders, GOST/IEC standards and other authoritative documents.

### Site-specific rules

- local operating instructions;
- actual protection setting cards;
- switching interlocks;
- protection action matrices;
- local switching forms/programs;
- approved equipment data;
- station-specific operating practices.

Every machine-enforced rule should carry provenance:

- stable rule ID;
- source document;
- revision/date;
- clause/section where possible;
- applicability/scope;
- effective status;
- machine-readable condition/action.

Rules must be updateable without rewriting the electrical core.

When EnergoLogic rejects an operation or reports a protection/compliance result, it should be able to explain the technical/normative reason.

## 13. Existing-Visio migration

The Kochubeevskaya WPP existing Visio diagram is the primary real-world migration acceptance case.

The existing diagram is not required to use EnergoLogic masters.

Migration pipeline:

```text
Legacy Visio document
        |
        v
Shape / group / master / text / geometry / Glue analysis
        |
        v
Legacy symbol classification
        |
        v
Connectivity reconstruction
        |
        v
Canonical EnergoLogic model
        |
        v
Regeneration with EnergoLogic library
```

Recognition should use, where available:

- Master identity;
- group structure;
- shape geometry/fingerprint;
- text/designation;
- layers;
- ShapeSheet properties;
- native Glue/connections;
- spatial proximity as a fallback;
- repeated symbol patterns.

The user should classify a legacy symbol family once, not redraw every instance.

Migration must support confidence levels and manual review of ambiguous objects.

The design objective is:

> import → classify → reconstruct → review/fix → regenerate,

not manual redraw.

## 14. Scheme Generator

EnergoLogic must generate new Visio electrical diagrams from the canonical model using the EnergoLogic shape library.

Generator capabilities should evolve toward:

- busbar generation;
- bay/cell placement;
- standard cell/bay templates;
- deterministic cell pitch;
- automatic connection/Glue;
- equipment placement;
- numbering;
- labels;
- sectioning;
- layout alignment;
- minimal crossings;
- regeneration after model changes.

The generator operates on domain primitives such as cells, bays, buses and equipment, not raw arbitrary shape coordinates alone.

Reusable template examples:

- 35 kV feeder;
- 35 kV incomer;
- bus coupler/section breaker;
- voltage transformer cell;
- station service transformer cell.

## 15. Data and site profiles

A project/site profile should encapsulate:

- canonical electrical model;
- actual equipment parameters;
- protection settings;
- protection logic;
- local interlocks;
- normative profile/version;
- source documents;
- legacy symbol mappings;
- diagram generation settings;
- scenario/training data.

The same canonical site model should drive Visio, simulation, calculations and protection behavior.

## 16. Delivery topology — parallel workstreams

The delivery plan is **not a single sequential phase chain**. EnergoLogic is developed through bounded workstreams that may run independently whenever their explicit contracts are satisfied.

There is no global rule such as “migration must finish before solver work can begin”. Dependencies are expressed through small shared gates.

### 16.1 Shared dependency gates

#### Gate A — Domain Model Contract

Minimum stable canonical concepts and IDs for:

- equipment;
- terminals/nodes;
- connectivity;
- switching state;
- electrical parameters;
- protection associations;
- site/profile metadata.

This gate is required for full integration of migration, generation, simulation, solver and protection work, but those workstreams may prototype behind adapters before the gate is complete.

#### Gate B — Terminology Contract

Terminology Registry structure and canonical RU↔EN naming rules are stable enough for schemas, UI labels and import aliases.

Terminology curation itself remains continuous and does not block unrelated implementation unless a new domain concept is being accepted.

#### Gate C — Visio Integration Contract

Stable interfaces between canonical objects and:

- Visio shapes/masters;
- Glue/connectivity representation;
- renderer state updates;
- selection/command identity;
- version/capability detection.

This gate is required for generator/rendering integration, but not for solver, protection-engine or normative-rule development.

#### Gate D — Electrical Calculation Contract

Canonical electrical parameters/results and solver-adapter interfaces are stable.

This enables independent solver implementations without coupling the canonical model to pandapower/OpenDSS schemas.

#### Gate E — Event / Protection Contract

Stable event timeline, measured-value input, protection pickup/trip output, breaker action and reset semantics.

Protection algorithms may be developed before full operational UI integration once this contract exists.

#### Gate F — Rules / Provenance Contract

Stable representation for normative/site rules, source provenance, revision/applicability and machine-readable decisions.

Normative source cataloging can start before this gate; executable rule integration depends on it.

### 16.2 Parallel workstreams

#### WS-0 — Current Visio Editor Baseline

Scope:

- finish topology-safe Cell Pitch;
- complete practical editor UX/polish;
- preserve current Glue/topology invariants.

This remains the active VISIO-EDITOR-QOL-001 work item.

**Does not block:** terminology research, packaging architecture, legacy-Visio inspection, solver-adapter prototyping, normative-source cataloging.

**Blocks/limits:** production-grade generator integration that relies on the final editor/Glue primitives.

#### WS-1 — Canonical Domain & Contracts

Scope:

- harden canonical model;
- define Gates A, D and E;
- site-profile structure;
- stable IDs and serialization contracts.

This is the principal shared foundation workstream.

It should remain small and contract-focused rather than absorbing implementations from other streams.

#### WS-2 — Terminology & Normative Foundations

Scope:

- Terminology Registry;
- authoritative RU/EN term sourcing;
- Normative Source Registry;
- rule provenance schema;
- terminology linting/validation.

**Can start immediately and run continuously.**

Executable normative rules later depend on WS-1/WS-6 operational semantics, but source collection and terminology do not.

#### WS-3 — Visio Compatibility & Packaging

Scope:

- Visio 2010 → latest capability/version abstraction;
- x86/x64 qualification harness;
- bundled runtime/dependency inventory;
- offline installer/bootstrapper architecture;
- update/diagnostic strategy.

**Can run in parallel with all functional streams.**

Final packaging acceptance is downstream of feature completion, but packaging architecture and compatibility qualification must not be deferred until the end.

#### WS-4 — Legacy Visio Migration

Scope:

- shape/master/group/text/ShapeSheet inspection;
- legacy symbol fingerprinting;
- symbol-family mapping;
- native Glue extraction;
- spatial topology reconstruction fallback;
- confidence/review workflow;
- canonical import.

Primary acceptance source: Kochubeevskaya WPP existing Visio.

**Can start immediately** with inspection/classification tooling.

Full canonical import depends on Gate A; generated replacement documents additionally depend on WS-5.

#### WS-5 — Scheme Generator & Auto-layout

Scope:

- domain templates for cells/bays;
- deterministic bus/cell placement;
- pitch/layout primitives;
- Glue generation;
- numbering/labels;
- regeneration from canonical model.

Can prototype layout/templates in parallel.

Production integration depends on:

- Gate A;
- Gate C;
- sufficiently stable EnergoLogic masters/editor primitives from WS-0.

WS-4 and WS-5 deliberately remain separate: migration reconstructs meaning; generation renders canonical meaning.

#### WS-6 — Operational Simulation

Scope:

- energized-network traversal;
- source tracing;
- switching state;
- earthing;
- interlocks;
- invalid-state detection;
- event timeline.

This workstream is independent of Visio rendering and should be testable headlessly.

Depends primarily on Gate A and existing switching semantics, not on migration/generator completion.

#### WS-7 — Switching Forms & Training

Scope:

- switching-form/program model;
- initial/target states;
- step execution;
- sequence validation;
- explanations;
- scenario/training results.

Document/scenario schema can begin early.

Full execution depends on WS-6 plus executable rules from WS-9.

#### WS-8 — Electrical Solver

Scope:

- solver-adapter API;
- pandapower adapter first;
- optional OpenDSS adapter;
- power flow;
- short-circuit calculation;
- result normalization.

**Can run headlessly and in parallel with Visio/migration/generator work.**

Depends on Gate D, not on Visio.

It should use synthetic/golden canonical test networks before site migration is complete.

#### WS-9 — Protection & Automation

Scope:

- protection setting-card import;
- generic protection-function model;
- pickup/delay/reset semantics;
- trip matrices;
- breaker-failure logic;
- advanced functions;
- arc-fault protection.

Substreams may run independently:

- WS-9A setting-card importer/data model;
- WS-9B generic protection engine;
- WS-9C arc-fault protection;
- WS-9D advanced protection functions.

WS-9A/WS-9B can begin before the solver is complete using synthetic measured quantities.

Integrated protection simulation depends on Gates D/E and WS-8 result feeds.

Arc-fault optical/logic behavior does not need to wait for every advanced electrical-protection function.

#### WS-10 — Russian Rules Engine

Scope:

- executable switching rules;
- site-specific operating rules;
- protection/normative validation;
- source-attributed explanations.

Normative research runs in WS-2 continuously.

Executable integration depends on Gate F and the relevant operational/protection semantics.

#### WS-11 — Acceptance Fixtures & Site Digital Twin

Scope:

- Kochubeevskaya source Visio as golden migration fixture;
- actual equipment parameter datasets;
- real protection-setting cards;
- approved topology snapshots;
- switching scenarios;
- expected calculation/protection outcomes.

This workstream supplies stable real-world fixtures to all others and should start early.

Sensitive/site-specific data must remain separated from generic product code as appropriate.

### 16.3 Recommended concurrency after the current checkpoint

Once separate bounded work items/branches exist, work may proceed approximately as:

```text
WS-0  Visio Editor baseline ────────────────┐
WS-1  Canonical contracts ────────┐         │
WS-2  Terminology/Normative ───────────────────────────────► continuous
WS-3  Compatibility/Packaging ─────────────────────────────► continuous
WS-4  Legacy migration ───────────┼─────────► canonical import
WS-5  Scheme generator ───────────┼─────────► generated Visio
WS-6  Operational simulation ─────┼─────────► switching runtime
WS-8  Solver adapter ─────────────┼─────────► power flow / SC
WS-9A Protection settings import ─┤
WS-9B Protection core ────────────┼─────────► integrated RZA
WS-11 Site fixtures ────────────────────────────────────────► continuous
                                  │
                                  ├─ WS-7 switching forms/training
                                  ├─ WS-9C/9D arc + advanced protection
                                  └─ WS-10 executable RU/site rules
```

The drawing above expresses dependencies, not mandatory calendar order.

### 16.4 Rules for parallel development

1. Each workstream gets its own bounded work item, branch and acceptance criteria.
2. Do not share mutable implementation branches between independent streams.
3. Shared contracts change through explicit versioned schema/interface changes.
4. A workstream may prototype against mocks/fixtures before an upstream gate is complete.
5. Integration must be fail-closed when contract versions are incompatible.
6. Generic product code and Kochubeevskaya/site-specific data remain separable.
7. Headless logic must be tested without requiring Visio where Visio is not intrinsic to the function.
8. No stream may silently redefine canonical terminology or canonical model semantics.
9. Packaging/compatibility and normative provenance are continuous streams, not “finish at the end” chores.
10. PR Ready/merge remains owner-controlled.

### 16.5 Near-term parallelization decision

While VISIO-EDITOR-QOL-001 is still being closed, the following work is safe to start independently:

- Terminology Registry and authoritative RU↔EN vocabulary;
- Visio version/capability matrix and packaging dependency inventory;
- Kochubeevskaya legacy-Visio inspection/fingerprinting tooling;
- solver-adapter spike with synthetic canonical networks;
- protection-setting-card schema/import spike using sanitized/test fixtures;
- normative source/provenance catalog;
- site/golden-fixture inventory.

Do **not** start production generator integration against unstable Glue behavior; generator layout/template research may proceed behind an adapter.

## 17. Current implementation state boundary

The current active work item remains **VISIO-EDITOR-QOL-001**.

Its purpose is to finish a topology-safe and usable Visio engineering editor. It must not absorb solver, RZA, normative or generator implementation merely because those capabilities are now part of the canonical product target.

As of the latest development checkpoint:

- v3.14 live acceptance did not solve the remaining Cell Pitch VTD half-Glue issue;
- development-bridge contains a v3.15 event-isolated GlueTo implementation;
- v3.15 has not yet completed live deployment/acceptance after the bridge service restart;
- the source MCP-v2 page remains immutable during destructive acceptance;
- PR #12 remains Draft and must not be marked Ready or merged without explicit owner instruction.

## 18. Architectural invariants

The following are canonical invariants:

1. Canonical electrical model is the source of truth.
2. Visio is a replaceable frontend/renderer, not the model.
3. Solvers are replaceable adapters.
4. Protection logic is separate from the electrical solver.
5. Russian normative/site rules are separate, versioned and source-attributed.
6. Existing large Visio diagrams must be migratable without full manual redraw.
7. New diagrams must be generatable from the canonical model.
8. Production deployment is offline/self-contained except for installed Windows + Visio.
9. Visio 2010 through latest desktop Visio is the compatibility target.
10. UI terminology is canonical Russian; code terminology is canonical English.
11. New domain concepts require controlled RU/EN terminology before acceptance.
12. Site-realistic behavior and traceable normative provenance take priority over visually plausible but ungrounded simulation.
