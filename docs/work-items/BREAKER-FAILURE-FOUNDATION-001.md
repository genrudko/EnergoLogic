# BREAKER-FAILURE-FOUNDATION-001 — Explicit breaker-failure state machine

Status: **In progress**  
Workstream: **WS-9B — Generic Protection Engine / breaker-failure logic**  
Issue: **#29**  
Branch: `protection/breaker-failure-foundation-001`  
Stacked base: `protection/protection-engine-foundation-001@6de4d5937ba0aa56fcf25f2c20643aff64ce9147`

## Goal

Add deterministic circuit-breaker-failure / УРОВ logic without importing WS-6 runtime types or inventing site-specific wiring.

## Inputs

- explicit binding between a breaker-failure function and monitored breaker;
- explicit failure-criterion mode;
- explicit start behavior;
- caller-supplied logical time;
- `start_active`;
- `breaker_closed` when required;
- `current_flow_present` when required.

## Output

- immutable breaker-failure state;
- pickup/reset/operate events;
- declarative backup output requests reusing the WS-9B request contract.

## Invariants

1. No failure criterion is assumed by default.
2. No start behavior is assumed by default.
3. The stage delay is read from the WS-9A breaker-failure function.
4. Missing required feedback fails closed.
5. Logical time is explicit and nondecreasing.
6. Output requests do not mutate the monitored or backup breakers.
7. The current foundation does not invent current thresholds or vendor-specific two-timer logic.
8. No direct dependency on WS-6, solver, frontend/Visio or unmerged terminology runtime.

## Verification

`python -m unittest discover -s tests -v`

Ready/Merge remain owner-controlled.