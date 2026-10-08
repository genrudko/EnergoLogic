# OPERATION-PERMISSION-CONTRACT-001 — evidence

**Issue:** #33 · **Branch:** `domain/operation-permission-contract-001` · **Base:** `main@f92f89b`.

## Verified VPS Python tests (2026-10-08)

- Focused initial permission suite: 13 PASS.
- Full repo after final two adversarial additions: `PYTHONPATH=src python3 -m unittest discover -s tests -q` → **295 tests, 7 skipped, 0 failures**.
- `python3 -m compileall -q src/energologic/operational tests/test_operation_permission.py` → PASS.
- `git diff --check` → PASS.
- GitHub CI [run #37743162289](https://github.com/genrudko/EnergoLogic/actions/runs/37743162289) on implementation commit `872f68fdce3a6dadbf80e2f26c583466b7330faa`: **SUCCESS 6/6 jobs**, including Ubuntu/Windows Python 3.11/3.12 test matrix and Ubuntu/Windows Python 3.11 solver jobs. This is the accepted code-head CI evidence; subsequent documentation-only commits require their own status check before concluding the final PR branch is green.

## Functional evidence

Explicit PASS assertions with source references and exact model/operation identity permit synthetic switching through the optional validator. Missing, empty, stale, contradictory, unknown, duplicate, mismatched or unsourced assertions deny state mutation: `BLOCKED`, unchanged canonical model and fingerprint, and empty event trace. Denial diagnostic ordering is deterministic. Targeting a withdrawable position uses distinct operation binding. An invalid pre-operation snapshot denies. Existing no-op returns NO_CHANGE without permitting an operation or generating events.

## Limitations / deferred

The `PERMITTED` enum is structural acceptance of supplied synthetic claims; provenance is not authenticated, and neither normative compliance nor actual electrical safety is established. Existing `execute_switching_operation` validators remain optional, and its no-change path bypasses them. No live switching/SCADA/earthing topology/site interlocks here. PR remains Draft pending owner acceptance.
