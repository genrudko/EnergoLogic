# PROJECT-FOUNDATION-001

Status: In progress  
Issue: #1  
Draft PR: #2

## Objective

Create the first EnergoLogic foundation baseline while preserving these invariants:

- Visio is the first frontend, not the system of record.
- The canonical electrical model is the source of truth.
- Critical runtime behavior is deterministic.
- LLM/agent behavior is outside critical electrical logic.

## Delivered baseline

- versioned canonical model contract `0.1`;
- dependency-free runtime core for decode/validate/canonicalize/fingerprint;
- explicit Visio frontend protocol with projection-only shape bindings;
- CLI smoke path;
- JSON Schema and minimal example;
- architecture ADR;
- CI and regression tests.

## Explicit non-goals

Planner, RZA/protection logic, CIM, pandapower/solver integration, and full Visio automation are excluded from this work item.

## Acceptance checks

- [x] Dedicated issue, branch and Draft PR exist.
- [x] Canonical model is versioned and documented.
- [x] Equivalent identity ordering canonicalizes identically.
- [x] Duplicate IDs and broken endpoint references are rejected.
- [x] Core has no dependency on Visio/COM, LLM SDKs or excluded future stacks.
- [x] Visio-specific identity remains outside the canonical model.
- [ ] CI is green on the PR head.
- [ ] Owner acceptance.

## Verification commands

```bash
python -m pip install -e .
python -m compileall -q src
python -m unittest discover -s tests -v
energologic validate examples/minimal.energologic.json
energologic canonicalize examples/minimal.energologic.json
energologic fingerprint examples/minimal.energologic.json
```

## Evidence

Pending execution on the committed PR head.

## Known limitations

- Model `0.1` intentionally does not define a complete equipment taxonomy.
- No electrical calculation engine exists in this baseline.
- Visio contract exists, but no COM implementation is part of this work item.
