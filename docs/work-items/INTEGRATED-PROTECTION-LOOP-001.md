# INTEGRATED-PROTECTION-LOOP-001

**Issue #35** · Branch `integration/integrated-protection-loop-001` · **Draft candidate**.

## Deliverable

Build a real headless integration between existing Gate-D short-circuit output, explicit Gate-E measurement binding, WS-9B protection stage runtime, WS-6 switching event timeline and a Visio projection **plan**. Use only accepted main contracts; do not import calculation-domain PR #32 or permission PR #34.

## Implemented boundary (pending CI)

- `src/energologic/integration/protection_loop.py` composition layer, `run_integrated_protection_loop`, explicit `BranchCurrentBinding`.
- Validate study fingerprint, fault kind, branch measurement semantics/units, action/target, protection program scope and unique Visio binding.
- Operate only a breaker whose protection trip output passed the engine, with the existing WS-6 switching API.
- Return an ordered trace and dry-run `VisioStateUpdate` only after actual simulated topology recalculation.
- Synthetic adversarial tests and an optional pinned pandapower real-solver integration test; architecture and evidence.

## Acceptance criteria

1. Three-phase SC with qualified sourced branch current + full synthetic program leads to pickup, delayed operate and one trip request.
2. Trip request is distinct from breaker switching success. Simulated breaker opens and terminal energization/source attribution recomputes.
3. Headless Visio update intent targets exactly the canonical-bound shape and new model fingerprint; no claim that an open Visio document was modified.
4. Solver failure, wrong topology, missing data, 2φ/earth mode, missing source/binding, no pickup, early timeout, blocked validator and unsupported trip return explicit deterministic outcomes without unintended state change.
5. Full Python regressions and GitHub Ubuntu/Windows CI, including pinned pandapower solver jobs; evidence updated with actual results.

## Out of scope

Physical Visio/COM live visual update, real production setting card, real CT placement/provenance, actual dispatch/SCADA, mandatory interlocks/operation permission and solver runtime packaging. The integrated **headless MVP** is not the full product acceptance of the roadmap milestone.

## Governance

Issue → dedicated branch → Draft PR → tests/CI/evidence → owner acceptance. No Ready or merge without explicit direction.
