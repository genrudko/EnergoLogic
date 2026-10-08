# INTEGRATED-PROTECTION-LOOP-001 — evidence

**Issue #35** · Branch `integration/integrated-protection-loop-001` · upstream `main@f92f89b`.

## Headless qualification observed

- Initial 16 targeted tests: PASS after correctly selecting the used phase-current measurement specification from the compiled program.
- After added negative tests (fault-node evidence, residual/phase distinction, explicit sources), local full suite initially: **301 tests, 8 skipped, zero failures**.
- First GitHub CI [run #37745073884](https://github.com/genrudko/EnergoLogic/actions/runs/37745073884) exposed **solver-job failure** (Ubuntu and Windows) while base tests passed. A deterministic preflight reproduction found that strict `electrical-v1` rejected the solver fixture `line/load/external_grid` kinds.
- Corrective opt-in profile `electrical-operational-solver-v1` added with direct qualified bus-voltage resolution, explicit line conduction, passive loads and default profile preservation; six new cross-domain tests and source-classification adversarial test added. Full VPS suite after additional explicit-time and unsupported-study-case hardening: **309 tests, 8 skipped, zero failures**. The second CI run #37745720908 is independently qualifying the profile extension; final result must be observed before accepting this head. Solver-extra CI remains pending this corrective commit and must be observed before acceptance.
- `python3 -m compileall -q src/energologic/integration ...` — PASS after adjusting new-directory ownership to normal project user.
- `git diff --check` — PASS.
- Real `PandapowerAdapter` 3φ→overcurrent→breaker scenario test is included and intended to run in pinned solver jobs; it skips where solver-extra is not installed. Record actual CI results, not assumptions.

## Negative gates checked

No trip on undercurrent or before delay; explicit validator blocks mutation; absent source/binding/shape, mismatched study/model, invalid branch current, missing node, non-finite number, wrong fault target/type or lifecycle denies. Trip request and successful simulated breaker opening are different ordered events. Shape projection is an **intent only**, not an actual Visio document modification.

## Limitations

Numerical/phase/current-transformer mapping is not independently site-validated. The synthetic setting card has only synthetic evidentiary significance. No real safety interlock, SCADA command, physical switching permission, or live Visio update. PR must remain Draft until owner acceptance.

## GitHub production CI qualification (2026-10-08)

- First integration head `0cf585f`, [run #37745073884](https://github.com/genrudko/EnergoLogic/actions/runs/37745073884): **FAILURE** in Linux and Windows solver-extra tests; exposed the true incompatible element-kind boundary between WS-8 and WS-6. All four base tests succeeded.
- Corrective explicit opt-in profile head `c24e7cc`, [run #37745720908](https://github.com/genrudko/EnergoLogic/actions/runs/37745720908): **SUCCESS 6/6**, including real pinned pandapower solver jobs on Ubuntu and Windows.
- Final code head `b99a5f5c2633e96a77d4fd89745a2b2e6ebe0ad6`, [run #37745892511](https://github.com/genrudko/EnergoLogic/actions/runs/37745892511): **SUCCESS 6/6**; four OS/Python base test jobs and both real solver-extra jobs passed. The real 3φ pandapower→phase-current→overcurrent→simulated breaker→energization/Visio update-intent test is included in solver-extra suite.

**Status:** headless bounded integration **qualified as Draft candidate**, NOT a live Visio acceptance and NOT a production/safety approval for real switching. Documentation-only evidence updates made after this head require their own CI confirmation before declaring the then-current PR head green.
