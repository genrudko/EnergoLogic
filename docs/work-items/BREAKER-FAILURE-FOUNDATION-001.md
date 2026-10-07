# BREAKER-FAILURE-FOUNDATION-001 — Explicit breaker-failure state machine

Status: **Accepted and merged to `main`**
Workstream: **WS-9B — Generic Protection Engine / breaker-failure logic**
Issue: **#29**
Branch: `protection/breaker-failure-foundation-001`
Stacked base: `protection/protection-engine-foundation-001@6de4d5937ba0aa56fcf25f2c20643aff64ce9147`


## Final repository reconciliation

Merged via PR #30 as `734f64a` on 2026-10-04.

Any unchecked owner/Ready/Merge boxes or pre-merge wording later in this file are **historical candidate-state evidence** and do not override this final repository status.

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

## Acceptance status

- [x] dedicated stacked branch and Draft PR;
- [x] explicit breaker-failure binding contract;
- [x] deterministic runtime input/state/result model;
- [x] maintained-start behavior tested;
- [x] latched-start behavior tested;
- [x] all four criterion modes tested;
- [x] missing required feedback fails closed;
- [x] criterion clearing before delay prevents backup trip;
- [x] exact delay boundary operates;
- [x] zero-delay operation qualified;
- [x] output requests are deterministic and declarative;
- [x] no repeated requests while operated;
- [x] monitored-breaker retrip is explicitly rejected in this bounded foundation;
- [x] unsupported current-threshold/multi-stage vendor semantics fail closed;
- [x] no WS-6/solver/frontend dependency;
- [x] architecture/how-to/evidence docs complete;
- [x] implementation CI green;
- [x] PR remains Draft until explicit owner command.

## Verification checkpoint

Implementation candidate
`d1d449e1b334a1b530be2fd62423f5201f0b4519`:

- CI **37218116201 — SUCCESS**;
- representative Ubuntu job: **151 tests — OK**.

Documentation-reconciled head `dfa0604a7bbd7395632800988141ec69ba5b32b5`: CI **37218303079 — SUCCESS**, 4/4 matrix jobs; representative Ubuntu job ran **151 tests — OK**.
