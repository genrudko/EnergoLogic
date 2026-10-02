# PROJECT-FOUNDATION-001

Status: Awaiting owner acceptance  
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
- [x] Implementation-head CI is green on Linux and Windows.
- [ ] Final documentation-head CI is green.
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

### Local verification

- compile: PASS;
- unit tests: **11/11 PASS**;
- valid example: accepted;
- deliberately broken endpoint references: rejected deterministically with exit code `2`;
- canonical example fingerprint:
  `ff8d31632f9c83f63e9a26b0e251ecdaa29d785e4be7be496bc830f5fb1a2315`;
- SHA-256 of emitted canonical bytes equals the CLI fingerprint exactly.

### GitHub verification

Implementation head:
`dd3b69a5923ff89857c2a1382b33b5629797ffda`

CI run:
https://github.com/genrudko/EnergoLogic/actions/runs/37079633539

Matrix result: **4/4 PASS**

- Ubuntu / Python 3.11 — PASS;
- Ubuntu / Python 3.12 — PASS;
- Windows / Python 3.11 — PASS;
- Windows / Python 3.12 — PASS.

Each matrix job passed install, compile, unit tests and CLI smoke.

### Repository-byte verification

The GitHub tree for implementation head was compared against the locally verified baseline by Git blob SHA for all 27 tracked foundation files; all blob SHAs matched.

## Known limitations

- Model `0.1` intentionally does not define a complete equipment taxonomy.
- No electrical calculation engine exists in this baseline.
- Visio contract exists, but no COM implementation is part of this work item.
- Planner, RZA, CIM and pandapower remain deliberately outside this baseline.

## Acceptance state

Implementation and evidence are complete. The Draft PR must remain Draft and unmerged until explicit owner acceptance.
