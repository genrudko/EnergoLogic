# ADR 0005 — Switching-state semantics v1

Status: Accepted baseline in `main` via PR #8 / `182ff26`

## Context

Static topology and nominal-voltage semantics are insufficient for switchgear. A breaker or disconnector may have closed contacts while a withdrawable part is outside the working position.

The live VTD/GOST library exposes two independent facts:

- main contact state through the native `Actions.Row_1` state;
- withdrawable position through `User.p`:
  - `0 = рабочее`;
  - `1 = ремонтное`;
  - `2 = контрольное`.

These must not be collapsed into one boolean.

## Decision

A named semantic layer `switching-state-v1` is validated on top of `electrical-v1`.

Supported switching kinds:

- `circuit_breaker`;
- `disconnector`.

Canonical attributes:

- `switch_state = open | closed`;
- `mounting_type = fixed | withdrawable`;
- withdrawable devices additionally require
  `withdrawable_position = working | repair | control`.

### Local primary-circuit conduction

For a supported switching element:

| State | Mounting / position | Conducts primary circuit |
| --- | --- | --- |
| open | any valid | no |
| closed | fixed | yes |
| closed | withdrawable + working | yes |
| closed | withdrawable + repair | no |
| closed | withdrawable + control | no |

This is deliberately a **local device predicate**. It is not yet a complete energized-network traversal algorithm.

### Native VTD mapping

For the qualified withdrawable breaker/disconnector masters:

- `Actions.Row_1.Action = TRUE` → canonical `closed`;
- `Actions.Row_1.Action = FALSE` → canonical `open`;
- `User.p = 0` → `working`;
- `User.p = 1` → `repair`;
- `User.p = 2` → `control`;
- `mounting_type = withdrawable`.

The menu text is treated as an operator action label, not as the current state. For example, when Action is TRUE the menu offers “Положение Отключено”, meaning the current state is closed and the available action is to open it.

## Consequences

- `disconnector(a,b)` is added to the static electrical-v1 equipment subset.
- Grounding-switch semantics remain separate.
- Interlocks remain separate.
- Future fixed switchgear can use the same canonical state contract with `mounting_type=fixed`.
- Frontends must fail closed if native state is missing or cannot be mapped exactly.
