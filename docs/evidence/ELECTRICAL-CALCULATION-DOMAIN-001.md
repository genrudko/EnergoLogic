# ELECTRICAL-CALCULATION-DOMAIN-001 — evidence

Status: **Draft candidate / owner acceptance pending**.
Issue #31 · Draft PR #32 · branch `domain/electrical-calculation-domain-001`.

## Source baseline and boundaries

Base `main`: `f92f89b5939a2f4aa798a295389daf5f2b3db185`
(2026-10-08 read from GitHub and cloned to isolated VPS workspace).
Existing `SolverStudyInput` / `PandapowerAdapter` are unchanged.
`electrical-v1` remains unmodified.

New files: domain calculation module; Gate-D materializer; JSON Schema;
synthetic canonical network + separately attributed parameter profile;
normalized deterministic golden; tests; architecture/work-item/evidence.

## Local reproducibility

Isolated VPS checkout:
`/home/admin/worktrees/energologic-electrical-calculation-001`.
Environment: Python **3.14.4**, `PYTHONPATH=src`; base package has no
mandatory Python dependencies.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
# Ran 294 tests in 0.898s
# OK (skipped=8)
```

Eight skips include the existing optional adapter tests and one new optional
integration test: `pandapower` is not installed in this VPS Python.
This is **not** numerical pandapower-acceptance evidence. The CI solver jobs
install the pinned optional extra on both OS platforms.

## Golden and determinism

Fixtures:
- `examples/electrical-calculation-v1.synthetic-network.json`
- `examples/electrical-calculation-v1.synthetic-profile.json`
- `tests/fixtures/electrical-calculation-v1.golden.json`

Synthetic topology:

`External Grid → HV Bus (35 kV) → Transformer 2W (35/0.4 kV) →
 LV Bus (400 V) → cable (400 V) → Remote Bus → Load`.

Input fingerprint on this fixture:

`8152f32ef377c5ae55635a1997cc6d670f0ee73f9a4af3e60f7e20e03e0c7480`

The test compares the **entire** normalized manifest byte-for-byte to the
golden, and checks invariance to canonical element, connection, connection
endpoint, profile-record and parameter-key reordering. The manifest retains
each recorded fact's state, source ID, locator and revision.

## Fail-closed tests / diagnostics

Covered:
- `missing_exact_nominal_voltage`;
- `incompatible_terminal_node_voltage`;
- `invalid_calculation_parameter`, `invalid_line_impedance`,
  `invalid_transformer_impedance`;
- `missing_required_parameter`, `unknown_required_parameter`,
  `not_applicable_required_parameter`;
- `missing_sequence_parameter`, `unsupported_sequence_study`,
  `unsupported_phase_neutral_topology`;
- missing/wrong profile version/model linkage, unprovenanced facts,
  unknown extra field and invalid switch state;
- no guessed zero-sequence data (unknown -> `None` in Gate-D DTO).

The power-flow boundary requires explicit external-grid short-circuit
strength because the unchanged WS-8 Gate-D adapter currently requires it.
No implicit solver DTO defaults are accepted as engineering data.

## Capability limits

- `power_flow` and `short_circuit_3ph` materialize.
- `short_circuit_2ph` is not yet independently negative-sequence qualified.
- `short_circuit_1ph` remains unsupported until ground-return/
  phase-neutral capability qualification; missing zero values are diagnosed.
- No source values for actual Kochubeevskaya WPP are asserted or inferred.
- Numerical backend golden comparison is optional/CI-dependent and distinct
  from the deterministic domain golden in this work item.
- Solver runtime host, offline bundle and site-level reference analysis
  remain separately bounded.

## Numerical CI feedback and synthetic fixture correction

First published candidate `66e4733580f831b4850d1cebdd101b8cae3225bf`
passed all four base tests but **failed both optional-solver jobs**:
GitHub Actions [run #37692907900](https://github.com/genrudko/EnergoLogic/actions/runs/37692907900).
The added synthetic pandapower integration test returned
`NON_CONVERGED` (Newton-Raphson 10 iterations). Examination of the
synthetic parameters found a physically inappropriate combination copied
from the WS-8 35 kV example: **1 MW + 0.3 Mvar** load downstream of
a **2,000 m** cable operating at **400 V**. This was a **test-data defect**,
not evidence of a solver-mapping defect. The synthetic sample has been
corrected to a **100 m** cable and **20 kW + 6 kvar** load for the LV
contour, using the same explicitly attributed synthetic source locators.
Normalized golden/fingerprint were regenerated; numeric confirmation is
delegated to the next pinned-pandapower CI solver jobs. The failed original
run is preserved as evidence, not hidden.

## CI / governance

GitHub Actions matrix: Python 3.11/3.12 × Ubuntu/Windows base jobs;
Python 3.11 × Ubuntu/Windows solver-extra jobs.

**CI status:** pending initial PR candidate push and GitHub runs. Update this
section with observed run URLs/statuses; do not call this item merged/accepted.

**Ready: not requested · Merge: not requested; neither performed.**
