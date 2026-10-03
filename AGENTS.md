# EnergoLogic repository instructions

## Mandatory process

Every substantial change follows:

1. Issue
2. dedicated branch
3. Draft PR
4. implementation + tests + evidence
5. owner acceptance

Do not merge or mark a PR ready for review without explicit owner instruction.

## Architecture invariants

- Visio is the first frontend, not the system of record.
- The canonical electrical model is the source of truth.
- Structural schema validation and named domain profiles are separate layers.
- Critical runtime behavior must be deterministic and testable.
- LLM/agent behavior must not participate in critical electrical logic.
- `src/energologic/core` must not depend on domain, frontend, COM or solver stacks.
- `src/energologic/domain` may depend on core but must not depend on frontends, COM or solver stacks.
- Frontends may depend downward on domain/core.

## Electrical-domain rules

- `electrical-v1` is explicit; do not silently make structural validation equivalent to it.
- Canonical nominal voltage is positive integer `attributes.nominal_voltage_v`.
- Frontend display units must be converted before entering canonical semantics.
- Do not weaken fail-closed terminal, voltage or topology rules to accommodate a frontend.
- `disconnector(a,b)` is part of the qualified static `electrical-v1` subset.

## Switching-state rules

- `switching-state-v1` is an explicit layer on top of `electrical-v1`.
- Supported switching kinds: `circuit_breaker`, `disconnector`.
- Keep `switch_state` independent from `withdrawable_position`.
- A closed withdrawable switch conducts the primary circuit only in `working` position.
- `repair` and `control` positions are non-conducting for the primary circuit even if main contacts are closed.
- Treat VTD action-menu text as an available action, not the current state. Current state is derived from the native action value.
- Qualified VTD mapping is exact: Action TRUE/FALSE → closed/open; User.p 0/1/2 → working/repair/control.
- Do not infer missing switching state heuristically or with an LLM.
- Grounding switches and earthing topology are NOT ordinary disconnectors in this contract.

## Transformer rules

- `transformer_2w` uses terminal-scoped voltage semantics on `hv` and `lv`; do not assign one element-level nominal voltage.
- Preserve source precision. If VTD only says «ниже 3 кВ», canonical data must remain a voltage class rather than inventing 400 V.
- Exact 400 V may exist in canonical data when supplied by an authoritative source.
- Never silently degrade exact canonical voltage to a broader VTD voltage class on render.
- Store qualified winding connection on the corresponding transformer terminal.
- Validate external connections against the voltage specification of the actual endpoint.
- Do not extract engineering values from nearby free-text labels heuristically.
- Reject a transformer when hv is provably below lv.

## Current exclusions for TRANSFORMER-SEMANTICS-001

Do not expand this work item into:

- tap-changer / RPN semantics;
- transformer rated power from free text;
- uk%, losses, equivalent impedance;
- three-winding transformers;
- autotransformers;
- grounding-switch / earthing semantics;
- interlocks;
- full energized-network traversal;
- Planner;
- RZA/protection logic;
- CIM;
- pandapower/power-flow/short-circuit solvers.

## Visio editor QoL rules

For VISIO-EDITOR-QOL-001:

- Treat CELL / EQUIPMENT / TERMINAL / BUS / ANCHOR / CONNECTION as the working vocabulary.
- Do not use bounding boxes as the sole cell anchor.
- Geometry may suggest a connection but must never establish electrical truth.
- Real electrical attachment requires native Glue and/or canonical terminal↔node mapping.
- Preserve VTD master internals unless a separate normalization work item proves a change necessary.
- Prefer exact millimetre-based operations over manual nudging.
- User-facing compound actions should use one Visio Undo scope when the API permits it.
- A failed compound action must rollback or leave a clearly safe, diagnosable state.
- Duplicate operations must reset logical/canonical identity instead of cloning physical-object identity.
- R0 research findings must be verified on the real MCP-v2 page, not inferred only from docs.
- The first P0 benchmark is Duplicate Cell Right / Left.

## Evidence discipline

Every work item must record:

- changed architectural contracts;
- verification commands;
- test/CI results;
- known limitations;
- acceptance state.

For Visio mutations:

- poll operator notes before substantial mutation batches and at natural checkpoints;
- use native masters/state tools instead of arbitrary ShapeSheet writes;
- perform mutate → snapshot → rendered-image inspection;
- preserve reference pages;
- perform final visual inspection before SaveAs.
