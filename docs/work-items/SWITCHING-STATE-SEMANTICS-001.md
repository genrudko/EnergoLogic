# SWITCHING-STATE-SEMANTICS-001

Status: In progress  
Issue: #7

## Objective

Add deterministic switching-state and withdrawable-position semantics on top of `electrical-v1`.

## Dependency

Stacked on owner-accepted ELECTRICAL-DOMAIN-PROFILE-V1-001 head:

`335dd437530ad296e18111b451136532873fc749`

## Canonical state contract

- `switch_state = open | closed`
- `mounting_type = fixed | withdrawable`
- withdrawable devices additionally use `withdrawable_position = working | repair | control`

## Initial switching kinds

- `circuit_breaker`
- `disconnector`

Grounding-switch semantics, interlocks and energized-network traversal are explicitly excluded.

## Evidence

Pending implementation and live qualification.
