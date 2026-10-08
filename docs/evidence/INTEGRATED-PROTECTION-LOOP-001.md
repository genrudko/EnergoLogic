# INTEGRATED-PROTECTION-LOOP-001 — evidence

**Issue #35** · Branch `integration/integrated-protection-loop-001` · upstream `main@f92f89b`.

## Headless qualification observed

- Initial 16 targeted tests: PASS after correctly selecting the used phase-current measurement specification from the compiled program.
- After added negative tests (fault-node evidence, residual/phase distinction, explicit sources), local full suite: `PYTHONPATH=src python3 -m unittest discover -s tests -q` — **301 tests, 8 skipped, zero failures**.
- `python3 -m compileall -q src/energologic/integration ...` — PASS after adjusting new-directory ownership to normal project user.
- `git diff --check` — PASS.
- Real `PandapowerAdapter` 3φ→overcurrent→breaker scenario test is included and intended to run in pinned solver jobs; it skips where solver-extra is not installed. Record actual CI results, not assumptions.

## Negative gates checked

No trip on undercurrent or before delay; explicit validator blocks mutation; absent source/binding/shape, mismatched study/model, invalid branch current, missing node, non-finite number, wrong fault target/type or lifecycle denies. Trip request and successful simulated breaker opening are different ordered events. Shape projection is an **intent only**, not an actual Visio document modification.

## Limitations

Numerical/phase/current-transformer mapping is not independently site-validated. The synthetic setting card has only synthetic evidentiary significance. No real safety interlock, SCADA command, physical switching permission, or live Visio update. PR must remain Draft until owner acceptance.

## Final GitHub status

Awaiting PR/CI verification; fill in from actual workflow results.
