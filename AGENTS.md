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
- Structural schema validation and named electrical semantic profiles are separate layers.
- Critical runtime behavior must be deterministic and testable.
- LLM/agent behavior must not participate in critical electrical logic.
- `src/energologic/core` must not depend on domain, frontend, COM or solver stacks.
- `src/energologic/domain` may depend on core but must not depend on frontends, COM or solver stacks.
- Frontends may depend downward on domain/core.

## Electrical-domain rules

- `electrical-v1` is explicit; do not silently make structural validation equivalent to it.
- Canonical nominal voltage for the profile is positive integer `attributes.nominal_voltage_v`.
- Frontend display units such as kV must be converted before entering canonical semantics.
- Do not weaken fail-closed terminal, voltage or topology rules to accommodate a frontend.
- Extend equipment semantics through an explicit profile/work item rather than guessing unknown kinds.

## Current exclusions for ELECTRICAL-DOMAIN-PROFILE-V1-001

Do not expand this work item into:

- complete equipment taxonomy;
- switching-state semantics;
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

For Visio mutations, preserve the established operator-notes and rendered visual-gate discipline.
