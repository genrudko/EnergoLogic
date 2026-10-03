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

## Current exclusions for SWITCHING-STATE-SEMANTICS-001

Do not expand this work item into:

- grounding-switch / earthing semantics;
- interlocks;
- full energized-network traversal;
- transformer multi-voltage semantics;
- Planner;
- RZA/protection logic;
- CIM;
- pandapower/power-flow/short-circuit solvers.

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
