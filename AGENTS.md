# EnergoLogic repository instructions

## Mandatory process

Every substantial change follows:

1. Issue
2. dedicated branch
3. Draft PR
4. implementation + tests + evidence
5. acceptance

Do not merge or mark a PR ready for review without explicit owner instruction.

## Foundation invariants

- Visio is the first frontend, not the system of record.
- The canonical electrical model is the source of truth.
- Critical runtime behavior must be deterministic and testable.
- LLM/agent behavior must not participate in critical electrical logic.
- `src/energologic/core` must not depend on Visio/COM or future integration/solver stacks.

## Current exclusions for PROJECT-FOUNDATION-001

Do not implement or expand Planner, RZA/protection logic, CIM, pandapower, power-flow solvers, or full Visio automation in this work item.

## Evidence discipline

Every work item must record:
- changed architectural contracts;
- verification commands;
- test/CI results;
- known limitations;
- acceptance state.
