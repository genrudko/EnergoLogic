# Electrical Operational Solver v1 — explicit additive profile

**Work item:** INTEGRATED-PROTECTION-LOOP-001 · Issue #35. **Status:** Draft.

## Purpose

The accepted strict `electrical-v1` did not include the `line`, `load` and `external_grid` element kinds used by the accepted Gate-D solver spike. Blindly treating those kinds as `current_transformer` or `external_link` would destroy canonical electrical meaning. This bridge adds a **separate explicit profile** `electrical-operational-solver-v1`, preserving the original `ELECTRICAL_V1` unchanged.

## Structural extension

In addition to the unchanged base profile:

- `external_grid`: one `node` terminal, a stated source **only when named in `SourceRef`**.
- `load`: one `node` terminal, passive sink; NEVER an internal conducting edge.
- `line`: `from` / `to` terminals, electrically continuous in the headless energized traversal.

Maximum connection degree of each new terminal is one. Every new terminal requires **exactly one directly connected validated canonical bus**, with a known voltage. The voltage is inherited from that **bus**; it is not inferred from solver numbers or graphical state. Element-level voltage declarations on these kinds are rejected to avoid silent conflicting values. The two terminal voltages of a line must be compatible: a direct 35 kV→400 V line without a transformer is rejected.

For valid `line` elements, WS-6 adjacency includes `from↔to` conduction; `load` and `external_grid` do not create intra-element conductor edges. Independent power sources are modeled only by explicit `SourceRef`, which the integration preflight further restricts to `external_grid`/`external_link`.

## API compatibility

The following accepted APIs retain their strict default profile:

- `validate_switching_state_model(model, electrical_profile=ELECTRICAL_V1)`;
- `simulate_operational_state(model, sources, electrical_profile=ELECTRICAL_V1)`;
- `execute_switching_operation(..., electrical_profile=ELECTRICAL_V1)`.

Only the integrated protection-loop composition explicitly passes `ELECTRICAL_OPERATIONAL_SOLVER_V1`. All existing main tests continue to use their original default behavior; the new profile is not a global relaxation.

## Out of scope / fail-closed

Not a phase/residual circuit solver, grounding/earthing semantics, floating line node inference, implicit source discovery, multi-terminal mesh conductor model or physical switching permission. Indirect bus connectivity or ambiguous voltage fails validation; callers must enrich the canonical topology with a valid explicit connection contract before simulation.

This profile is a bounded compatibility contract between **already accepted** WS-8 canonical solver fixtures and WS-6 operational traversal. It does not imply that every real site model is qualified.
