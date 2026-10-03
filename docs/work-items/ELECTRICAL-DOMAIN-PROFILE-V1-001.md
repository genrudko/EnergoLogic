# ELECTRICAL-DOMAIN-PROFILE-V1-001

Status: In progress  
Issue: #5

## Objective

Add deterministic electrical semantics on top of canonical schema `0.1` while preserving the open structural core.

## Dependency

Stacked on owner-accepted VISIO-CANONICAL-BRIDGE-001 head:

`ded99d866f55287dbb0836572a8edab40d380cfb`

PR #4 remains Draft and unmerged until an explicit merge command.

## Profile boundary

The new `electrical-v1` profile is an explicit semantic layer. Structural validation remains open and backwards compatible.

Initial supported kinds:

- `bus`;
- `circuit_breaker`;
- `current_transformer`;
- `external_link`.

Canonical nominal voltage is stored as integer `nominal_voltage_v`, independent of frontend display units.

## Explicit non-goals

Complete equipment taxonomy, switching-state semantics, transformer multi-voltage semantics, Planner, RZA/protection, CIM and solver integration are excluded.

## Evidence

Pending implementation and verification.
