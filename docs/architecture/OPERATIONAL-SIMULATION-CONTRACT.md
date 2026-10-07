# Operational Simulation Contract — WS-6 foundation

Status: **Accepted baseline in `main` via PR #20 / `6dd5e60`**
Issue: #19
Draft PR: #20

## 1. Meaning of "energized"

In this bounded contract, **energized** means:

> a canonical terminal is topologically reachable from at least one explicitly
> declared active source terminal through canonical connections and equipment
> whose accepted operational semantics currently allow primary conduction.

It does **not** mean that a load-flow calculation has produced a non-zero
voltage magnitude.

WS-6 therefore answers topology/operational questions such as:

- which terminals are reachable from an active source;
- which source or sources can energize a terminal;
- what becomes unreachable after a switch-state change.

Electrical voltage/current/power values remain the responsibility of Gate D
and the solver layer.

## 2. Inputs

The runtime consumes:

- one validated `CanonicalModel`;
- zero or more explicit `SourceRef(element_id, terminal_id)` boundary
  conditions.

Source status is runtime/scenario state. The runtime does not infer a source
from:

- element name;
- text;
- element voltage;
- geometry;
- Visio master;
- the fact that an element is an `external_link`.

An empty source set is a valid all-deenergized operating state.

## 3. Terminal graph

The graph vertex is a canonical terminal:

`(element_id, terminal_id)`

Canonical `Connection` records form conductive edges between their endpoints.

Internal element conduction in this bounded foundation is:

| Kind | Internal topological conduction |
|---|---|
| `bus` | none required; its single `node` terminal is the junction |
| `external_link` | none; source status is explicit runtime input |
| `current_transformer` | `a ↔ b` |
| `transformer_2w` | `hv ↔ lv` |
| `circuit_breaker` | `a ↔ b` only when accepted switching semantics conduct |
| `disconnector` | `a ↔ b` only when accepted switching semantics conduct |

For switchgear the runtime reuses
`switch_allows_primary_conduction()`; it does not duplicate or reinterpret
switch state.

Transformer topological conduction means only that energization can propagate
across an in-service two-winding transformer in the operational graph. It does
not calculate transformation ratio, voltage drop, power flow or losses.

## 4. Terminal-first state

State is terminal-first because a switching device can have different
conditions on its two sides.

For example, an **open bus coupler** can legitimately have:

- terminal `a`: energized from Source A;
- terminal `b`: energized from Source B;
- no conductive path through the breaker.

Therefore a single boolean "breaker energized" is insufficient as the primary
truth.

`TerminalOperationalState` carries:

- canonical element ID;
- canonical terminal ID;
- energized/de-energized state;
- all reachable explicit source refs.

`ElementOperationalState` is a derived summary only:

- `energized`: at least one terminal is energized;
- `fully_energized`: every terminal is energized;
- energized/de-energized terminal IDs;
- union of terminal source refs.

"Fully energized" does not imply that an open switch conducts.

## 5. Multiple sources

Source attribution is set-valued and deterministic.

If closing a coupler joins two source-fed sections, terminals in the joined
component carry both source refs.

No preferred source is invented.

## 6. Normalized result states

The first public statuses are:

- `success`;
- `invalid_model`;
- `invalid_source`;
- `incompatible_models`.

Invalid canonical/domain state is returned as normalized
`OperationalMessage` records. Raw exceptions are not the public result
contract.

## 7. State delta

`compare_operational_results(before, after)` compares two successful results
with the same canonical terminal set.

A terminal is reported changed when either:

- energized/de-energized state changes; or
- reachable source attribution changes.

The result separately reports whether the effective conductive-topology
fingerprint changed.

This means a coupler close can produce a meaningful operational delta even when
both sections were already energized before the operation: source reachability
changes from A/B separately to A+B.

## 8. Dependency boundary

`energologic.operational` may depend downward on:

- `energologic.core`;
- `energologic.domain`.

It must not depend on:

- Visio/frontends/COM;
- pandapower/OpenDSS/solver adapters;
- protection/RZA;
- normative Rules Engine;
- site-specific data.

## 9. Explicitly deferred

Not part of this bounded contract:

- grounding switches and earthing topology;
- interlocks;
- operation permission / safety validation;
- switching operation commands;
- event timeline;
- switching forms;
- training/scoring;
- protection pickup/trip;
- load flow / short circuit;
- phase-domain/neutral topology;
- Site Profile persistence.

Those capabilities can consume this runtime later but must not be guessed into
the foundation.
