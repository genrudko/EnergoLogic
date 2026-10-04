# PROTECTION-ENGINE-FOUNDATION-001 — Generic protection engine foundation

Status: **Implementation complete in Draft; owner acceptance pending**  
Workstream: **WS-9B — Protection & Automation / generic protection engine**  
Issue: **#25**  
Branch: `protection/protection-engine-foundation-001`  
Stacked base: `protection/protection-setting-import-001@2fc665a9be2e73fbeb059650a822c041791df11c`

## Goal

Implement a deterministic, headless protection runtime that consumes the WS-9A
`ProtectionSettingCard v1` contract and synthetic measured quantities.

It produces protection state transitions and declarative action requests. It does not
operate electrical equipment.

## Qualified first scope

- `protection.overcurrent` — МТЗ;
- `protection.instantaneous_overcurrent` — ТО;
- `protection.earth_fault` — токовая защита от замыканий на землю;
- definite-time pickup/delay/reset behavior;
- explicit zero-delay operation;
- deterministic output/trip requests;
- exact synthetic measured-value snapshots.

## Invariants

1. Logical time is explicit and monotonic; no wall clock.
2. Numeric processing uses exact Decimal values.
3. Measured quantity kind/unit/basis must match configured measurement identity.
4. Primary/secondary conversion is never inferred.
5. Required pickup and delay settings are explicit; missing values fail closed.
6. Equality at pickup threshold counts as pickup.
7. Without a separately qualified reset characteristic, reset occurs when the pickup
   criterion becomes false (measured value < pickup threshold).
8. Disabled functions/stages do not operate.
9. Unknown enable state is not treated as enabled.
10. Operation emits declarative requests; it never mutates switch state.
11. Unsupported protection functions remain explicit and are never interpreted as a
    supported algorithm.
12. No direct dependency on WS-6, WS-8, Visio/frontends or unmerged WS-2 runtime.

## Deferred

- breaker-failure state machine until explicit start + breaker feedback contract exists;
- inverse-time curves;
- directional elements;
- distance/differential protection;
- arc protection;
- solver integration;
- live measured values;
- breaker execution.

## Verification

```bash
python -m unittest discover -s tests -v
```

Ready/Merge remain owner-controlled.


## Acceptance status

- [x] dedicated stacked branch and Draft PR;
- [x] deterministic measured-value snapshot model;
- [x] deterministic runtime state;
- [x] МТЗ pickup/delay/reset qualified;
- [x] ТО pickup/delay/reset qualified;
- [x] earth-fault pickup/delay/reset qualified;
- [x] explicit zero-delay operation qualified;
- [x] exact threshold boundary behavior tested;
- [x] missing/ambiguous settings fail closed;
- [x] incompatible measurement basis/unit fails closed;
- [x] time reversal fails closed;
- [x] trip/output requests are deterministic and do not mutate electrical state;
- [x] disabled/null-enabled behavior tested;
- [x] incomplete/non-authoritative settings are fail-closed by default;
- [x] architecture tests prohibit wall-clock and cross-workstream execution dependencies;
- [x] breaker-failure remains explicitly unsupported rather than guessed;
- [x] architecture/how-to/evidence docs complete;
- [x] current implementation CI green;
- [x] PR remains Draft until explicit owner command.

## Verification checkpoints

- 48afdb1e4d13727d3b965e1fd00f0722c393055b —
  CI 37215872927 SUCCESS, 118 tests on representative job.
- 9227a21427235f1edf31be6652fa6bbd7a47a237 —
  CI 37216082437 SUCCESS, 124 tests on representative job.

A final documentation reconciliation commit is run through the same
Ubuntu/Windows × Python 3.11/3.12 matrix before owner acceptance.


## Final adversarial checkpoint

Head 55ab646b5c3e65e8616f455eec13e0af626fad75 adds the last bounded safety checks:

- delay basis must be not_applicable;
- qualified overcurrent functions reject non-current operating quantities;
- active restored runtime state requires a logical last_time_s.

CI 37216416925 — SUCCESS, 4/4 matrix jobs, 127 tests — OK on the representative job.

Owner acceptance is not assumed. PR #26 remains Draft.
