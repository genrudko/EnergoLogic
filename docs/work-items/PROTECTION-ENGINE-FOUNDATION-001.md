# PROTECTION-ENGINE-FOUNDATION-001 — Generic protection engine foundation

Status: **In progress**  
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
