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

## 16. Delivery sequence

The product is implemented through bounded work items. Do not fold all of this into VISIO-EDITOR-QOL-001.

### Phase 0 — finish current Visio editor baseline

Close the remaining topology-safe Cell Pitch issue and complete the practical EnergoLogic Editor UX baseline.

One-user-Undo remains deferred technical debt unless it becomes necessary for another accepted requirement.

### Phase 1 — canonical architecture hardening

Create/lock:

- Terminology Registry;
- version/capability abstraction for Visio 2010 → latest;
- packaging/runtime architecture;
- site-profile structure;
- explicit model/solver/protection/rules interfaces.

### Phase 2 — Visio legacy migration foundation

Implement legacy-Visio inspection, symbol-family classification, connectivity reconstruction and canonical import.

Use the Kochubeevskaya WPP source Visio as the primary acceptance case.

### Phase 3 — Scheme Generator v1

Generate canonical bus/cell/bay structures using EnergoLogic masters and deterministic layout primitives.

### Phase 4 — operational network simulation

Implement energized-network traversal, switching state, earthing, interlocks and live mnemonic rendering.

### Phase 5 — switching forms / training

Implement operation sequencing, validation, explanation and scenario execution.

### Phase 6 — electrical calculations v1

Add solver adapter architecture and pandapower-based power-flow and short-circuit calculation.

### Phase 7 — protection simulation v1

Import real setting cards and implement the first set of protection functions, trip matrices and event timing.

### Phase 8 — arc protection / advanced protection

Add station-realistic arc-fault protection, breaker-failure logic and progressively more complex protection functions.

### Phase 9 — normative rules integration

Formalize machine-enforced Russian normative and site rules with provenance and version control; integrate them into switching and protection validation.

Normative provenance must be designed earlier, but broad rule coverage is a dedicated workstream.

### Phase 10 — product hardening and compatibility release gates

Qualify representative Visio generations/bitness combinations, offline packaging, upgrade paths, migration compatibility and end-to-end station scenarios.

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
