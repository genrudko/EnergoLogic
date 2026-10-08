# Integrated Protection Loop v1 — headless bounded contract

**Work item:** INTEGRATED-PROTECTION-LOOP-001 · Issue #35 · WS-6 + WS-8 + WS-9B + WS-0 projection · Status: Draft.

## Invariants / authority

The **canonical electrical model** remains source of truth. The short-circuit solver produces measured physical quantities; the protection runtime produces decisions/output requests; operational runtime mutates only a *simulated* canonical switch state; Visio receives only a **dry-run update intent**. No COM/document write, physical device command or live safety authorization occurs.

Russian-facing terms: **трёхфазное короткое замыкание**, **фазный ток**, **измеряемая ветвь**, **время срабатывания**, **срабатывание РЗА**, **команда отключения**, **фактическое изменение состояния выключателя**, **перерасчёт питания**, **проекция состояния в Visio**. Python/API identifiers use `ShortCircuitResult`, `BranchCurrentBinding`, `ProtectionOutputRequest`, `SwitchStateOperation`, `VisioStateUpdate`.

### Gate A: source + topology

The accepted WS-8 synthetic network includes `line`, `load` and `external_grid`, which are outside the original strict `electrical-v1` topology. The integration explicitly selects the new additive `ELECTRICAL_OPERATIONAL_SOLVER_V1` profile described in [Electrical Operational Solver v1](ELECTRICAL-OPERATIONAL-SOLVER-V1-CONTRACT.md). It validates direct bus voltage for those elements and makes `line.from↔to` conductive in WS-6, while keeping `load` passive. The accepted strict base profile is preserved and remains the default for all other callers.

Callers supply `CanonicalModel`, a `SolverStudyInput` whose embedded canonical model has the **same fingerprint**, and nonempty explicit `SourceRef` set. WS-6 initial operational simulation must succeed; fault target must be a canonical `bus`. A circuit breaker for the one supported trip action must be present and initially **closed**.

### Gate D: three-phase short circuit

A solver with `short_circuit(study, request)` runs the existing solver-neutral interface. v1 requires `FaultType.THREE_PHASE`, branch output enabled, `SolverStatus.SUCCESS`, a matching fault bus, matching positive/zero finite node current and known solver identity. Failures/unknowns do **not** trigger protection or switch mutation. 2φ and 1φ-to-earth may be qualified in the solver spike but are **not accepted** at the integrated measurement gate in this work item.

### Gate E: explicitly bound measurement

`BranchCurrentBinding` names the canonical `line` or `transformer_2w` branch, its **`from` or `to`** current side, the exact protection measurement input ID and a nonempty provenance reference. It never infers CT position, winding ratio, protection zone, direction or residual current. Result must contain **exactly one** matching branch contribution and a finite non-negative scalar current in **A**; type, side and fingerprint must match the explicit contract. Only a **primary phase-current** stage (`protection.overcurrent` or `protection.instantaneous_overcurrent`) is enabled.

A provenance reference is a source locator, **not independent evidence of instrument accuracy or CT mapping qualification**. Producing a plausible float cannot certify physical relaying.

### Protection runtime

A compiled, selected `ProtectionProgram` must carry `full_configuration` and `approved` or `implemented` lifecycle, with **exactly one active selected stage and one equipment trip action**. Its origin remains governed by the upstream settings model; the synthetic fixture is not an approved real site setting card. Two explicit monotonic logical timestamps are evaluated with the same qualified fault current. The engine controls pickup, delay and operate; it may return **NO_TRIP** if threshold/delay are not met.

### Trip request != breaker opened

One validated `ProtectionOutputRequest` for the declared circuit breaker is translated to a deterministic `SwitchStateOperation(target_state="open")`. This is an **explicit simulated breaker operation** through WS-6 `execute_switching_operation`; optional existing `OperationValidator` gates are honored. A denied/failed operation returns `BLOCKED`, **no new canonical model**, and **no projection**. Simulated success creates separate ordered events:
1. `trip_requested`
2. `breaker_opened`
3. `topology_recalculated`
4. `visio_update_prepared`

`OperationalDelta` comes from WS-6 topology/energization recomputation. A request alone must not report `breaker_opened`.

### Visio state projection boundary

A unique `VisioShapeBinding(element_id, page_name, shape_id)` for the protected breaker is required in preflight. After successful simulated switching, emit `VisioStateUpdate` with exact canonical ID, page, shape ID, `switch_state=open`, and **new** canonical model fingerprint. **No Visio COM operation is performed**. The live Visio bridge, document identity/shape validation, actual ShapeSheet update, Undo/redo and confirmation of displayed state remain a **separate acceptance gate** requiring a Windows/Visio test.

### Fail-closed / scope limitations

`BLOCKED` never returns a mutated model or Visio projection. Missing/duplicate/malformed/unqualified results, invalid source/fault, unsupported action/fault type, nonfinite values, absent binding, bad configuration, solver exceptions, failed validators and target mismatch deny execution. Do not treat a `NO_TRIP` as a protection trip. No implicit use of unfinished PR #32 or PR #34.

**Out of scope:** site safety/rule qualification, actual switching permission, earthing/grounding, differential/directional protection, CT ratio and phase mapping, multiple independent actions, physical SCADA breaker command, live Visio write, realistic protection time simulation and packaged solver runtime.

## Verification

Pure-Python synthetic solver contract tests must run on VPS and on Linux/Windows base CI. A dedicated optional test must exercise the real pinned `PandapowerAdapter` in the Linux/Windows solver-extra jobs; it may skip only where the dependency is absent. Production qualification remains incomplete until live Visio end-to-end acceptance and site-specific measured-value verification.
