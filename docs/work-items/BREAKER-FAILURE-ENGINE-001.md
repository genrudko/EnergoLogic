# BREAKER-FAILURE-ENGINE-001 — Breaker failure engine

Status: **In progress**  
Workstream: **WS-9B — Generic Protection Engine / breaker failure**  
Issue: **#27**  
Branch: `protection/breaker-failure-engine-001`  
Stacked base: `protection/protection-engine-foundation-001@6de4d5937ba0aa56fcf25f2c20643aff64ce9147`

## Goal

Qualify one deterministic breaker-failure state-machine pattern from explicit runtime
inputs without importing WS-6.

The card supplies the breaker-failure delay and configured stage actions.
A separate binding supplies:

- monitored breaker stable ID;
- start signal stable ID;
- breaker-open feedback stable ID.

## Core invariants

1. No signal-name guessing.
2. No wall-clock timer.
3. No breaker mutation.
4. Start and breaker feedback are explicit booleans.
5. Exact configured delay is honored with Decimal logical time.
6. Opening the monitored breaker before expiry resets timing.
7. Removing start before expiry resets timing.
8. Output requests are emitted once per operate cycle.
9. Function/stage settings outside the bounded contract fail closed.
10. Current-supervised/vendor-specific УРОВ behavior is not invented.
11. No direct dependency on WS-6, WS-8, Visio or frontends.

## Acceptance

- [ ] separate issue / stacked branch / Draft PR;
- [ ] explicit binding contract;
- [ ] binary signal snapshot;
- [ ] idle → timing → operated state machine;
- [ ] exact-delay and zero-delay tests;
- [ ] breaker-open reset;
- [ ] start-removal reset;
- [ ] no repeated requests after operation;
- [ ] fresh cycle after reset;
- [ ] signal/time/binding failures are fail-closed;
- [ ] declarative outputs only;
- [ ] architecture/evidence docs;
- [ ] Linux/Windows CI green;
- [ ] PR remains Draft.
