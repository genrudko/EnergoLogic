# SWITCHING-STATE-SEMANTICS-001

Status: **Accepted and merged to `main`**
Issue: #7
Draft PR: #8


## Final repository reconciliation

Merged via PR #8 as `182ff26` on 2026-10-03.

Any unchecked owner/Ready/Merge boxes or pre-merge wording later in this file are **historical candidate-state evidence** and do not override this final repository status.

## Objective

Add deterministic switching-state and withdrawable-position semantics on top of `electrical-v1`, grounded in native VTD/GOST behavior.

## Dependency

Stacked on owner-accepted ELECTRICAL-DOMAIN-PROFILE-V1-001 head:

`335dd437530ad296e18111b451136532873fc749`

PR #6 remains Draft/unmerged until an explicit merge command.

## Canonical state contract

Supported switching kinds:

- `circuit_breaker`;
- `disconnector`.

Canonical attributes:

- `switch_state = open | closed`;
- `mounting_type = fixed | withdrawable`;
- withdrawable devices require
  `withdrawable_position = working | repair | control`.

`disconnector(a,b)` was also added to the static `electrical-v1` equipment subset.

## Local primary-circuit conduction

`switch_allows_primary_conduction()` is deterministic:

| Contact state | Mounting / position | Conducts |
| --- | --- | --- |
| open | any valid | no |
| closed | fixed | yes |
| closed | withdrawable + working | yes |
| closed | withdrawable + repair | no |
| closed | withdrawable + control | no |

This is deliberately a local device predicate. Full energized-network traversal is out of scope.

## Native VTD contract

Qualified exact mapping:

- `Actions.Row_1.Action = TRUE` → `closed`;
- `Actions.Row_1.Action = FALSE` → `open`;
- `User.p = 0` → `working`;
- `User.p = 1` → `repair`;
- `User.p = 2` → `control`.

Menu text is an **available action**, not the current state. Thus Action TRUE with menu “Положение Отключено” means the apparatus is currently closed.

Visio import fails closed when native state is absent or outside the qualified value set. The render plan carries the exact desired native Action/cart state back toward VTD.

## Domain validation

`validate_switching_state_model()` layers on top of `validate_electrical_model()` and reports a complete stable issue set for:

- invalid/missing `switch_state`;
- invalid/missing `mounting_type`;
- invalid/missing withdrawable position;
- unexpected withdrawable position on fixed switchgear;
- switching attributes on non-switching equipment.

`read_switching_state()` remains the strict fail-fast runtime API.

## CLI

```bash
energologic validate examples/kru35-v1-cell.switching-state-v1.json \
  --profile switching-state-v1
```

## Regression evidence

Code candidate head:

`fadd710910a81349758880928b99bfb8e17daf8c`

Code CI:

https://github.com/genrudko/EnergoLogic/actions/runs/37112603967

Result: **4/4 PASS**

- Ubuntu / Python 3.11 — PASS;
- Ubuntu / Python 3.12 — PASS;
- Windows / Python 3.11 — PASS;
- Windows / Python 3.12 — PASS.

Representative job: **50 tests — PASS**.

Coverage includes:

- breaker and disconnector domain semantics;
- open/closed conduction behavior;
- fixed vs withdrawable behavior;
- working/repair/control conduction behavior;
- full deterministic validation issue sets;
- state-less switch rejection;
- non-switching switching-attribute rejection;
- CLI `switching-state-v1`;
- native TRUE/FALSE mapping;
- exact cart 0/1/2 bidirectional mapping;
- breaker/disconnector Visio round-trip;
- missing/invalid native VTD state fail-closed behavior;
- state-sensitive fingerprints.

Stateful example fingerprint:

`a5f5ed2ce70be3063dc8465c6e6b5c23f001f8ab4f6c159a82ca70aa82339373`

## Live source evidence

Source document/page:

`KRU-35_normal_scheme_v2_energologic_v1.vsdx / MCP-v2`

Observed reference apparatus:

- breaker `#66 / В-1-35`: Action TRUE, cart 0 → **closed + working**;
- reserve breaker `#237 / В-Р-35`: Action FALSE, cart 1 → **open + repair**;
- line disconnector `#121 / ЛР-35 КЛ-1`: Action TRUE, cart 0 → **closed + working**.

A grounding disconnector was observed but deliberately excluded from this work item.

## Live isolated qualification

Created separate A3 page:

`EnergoLogic-Switching-V1`

Native shapes:

- `#1` — withdrawable breaker `В-1-35`: 35 kV, **closed + working**;
- `#4` — withdrawable breaker `В-Р-35`: 35 kV, **open + repair**;
- `#7` — `Разъединитель выдвижной` `ЛР-35 КЛ-1`: 35 kV, **closed + working**.

All state writes used the managed VTD state API with read-before-write/read-back discipline; no arbitrary ShapeSheet mutation was used.

Native `control` position was additionally qualified live on shape #4:

- repair `1` → control `2`;
- read-back reported `контрольное`, value `2`;
- final state was restored to open + repair.

Rendered visual gates confirmed the native symbols visibly distinguish closed/open states and remain proper VTD/GOST shapes.

Final qualification-page PNG SHA-256:

`d8264df82583bd1281f543a240c95223dbe58ea91ce0fa132ed52df3e9d69bf7`

The reference page `MCP-v2` was rendered after all mutations and retained its historical exact PNG SHA-256:

`71eaa6244aef0dfe478ed052cf25b6ec8da58bd6d6cb32de7f83713e32f91648`

Therefore the reference page was not changed.

Operator-notes queue was empty at each qualification checkpoint.

After final rendered inspection, the result was saved as a separate copy:

`C:\Users\Gennadiy\AppData\Local\OpenAI\VisioMCP\workspace\KRU-35_normal_scheme_v2_energologic_switching_v1.vsdx`

The saved copy has four pages.

## Verification commands

```bash
python -m pip install -e .
python -m compileall -q src
python -m unittest discover -s tests -v
energologic validate examples/kru35-v1-cell.switching-state-v1.json --profile switching-state-v1
```

## Explicit non-goals

- grounding switches / earthing topology;
- interlocks;
- energized-network traversal;
- transformer multi-voltage semantics;
- Planner;
- RZA/protection;
- CIM;
- pandapower/power-flow/short-circuit solvers;
- heuristic/LLM state inference.

## Acceptance checks

- [x] Dedicated stacked branch and Draft PR.
- [x] `disconnector` added to static electrical profile.
- [x] `switching-state-v1` profile API implemented.
- [x] Canonical state/mounting attributes validated.
- [x] Deterministic local conduction predicate implemented and tested.
- [x] Native VTD TRUE/FALSE action mapping covered.
- [x] Native cart positions 0/1/2 bidirectional mapping covered.
- [x] Breaker and disconnector mappings covered.
- [x] CLI profile selection covered.
- [x] Stateful canonical fingerprint pinned.
- [x] Live separate-page native state qualification completed.
- [x] Final rendered visual inspection completed.
- [x] Reference page proven unchanged.
- [x] Code candidate Linux/Windows CI green.
- [x] Final PR-head CI gate is mandatory; final result is recorded in Issue/PR metadata.
- [ ] Owner acceptance.
- [x] No merge or Ready for Review without explicit owner command.
