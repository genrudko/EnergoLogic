# ADR 0004 — Electrical semantic profile v1

Status: Accepted for implementation in ELECTRICAL-DOMAIN-PROFILE-V1-001

## Context

Canonical schema `0.1` intentionally keeps `Element.kind` and attribute dictionaries open. That is useful for structural longevity, but electrical correctness needs stronger deterministic rules.

Those rules must not make Visio, a solver, CIM or an LLM part of the critical model contract.

## Decision

EnergoLogic separates:

1. **structural schema/version validation**, which remains open;
2. **named electrical semantic profiles**, which are explicitly selected.

The first profile is `electrical-v1`.

### Initial kinds

| Kind | Terminals | Terminal degree |
| --- | --- | --- |
| `bus` | `node` | unbounded |
| `circuit_breaker` | `a`, `b` | max 1 each |
| `disconnector` | `a`, `b` | max 1 each |
| `current_transformer` | `a`, `b` | max 1 each |
| `external_link` | `node` | max 1 |

This is intentionally a small qualified subset, not the final taxonomy.

### Canonical voltage unit

Nominal voltage is stored as positive integer **volts** in:

`attributes.nominal_voltage_v`

Frontend display units are projections. For example, a Visio/VTD value displayed as `35 kV` maps to canonical `35000 V`.

This avoids making display-unit choices part of canonical semantics and avoids float-equivalence problems for common nominal voltage classes.

### Profile rules

`electrical-v1` rejects:

- unsupported element kinds;
- wrong terminal contracts;
- missing or invalid `nominal_voltage_v`;
- direct connections across unequal nominal voltages;
- multiple electrical edges describing the same endpoint pair;
- external connections between two terminals of the same element;
- degree greater than the declared maximum for bounded terminals.

Structural validation remains separately available and does not reject future unknown kinds merely because the current profile does not know them.

## Consequences

- Schema `0.1` does not need a version bump.
- Domain growth can occur by adding future named profiles or profile revisions.
- Frontends translate presentation units into canonical SI-oriented values.
- Future transformers require an explicit multi-voltage semantic design rather than bypassing voltage mismatch validation.
- Switching-state semantics remain a separate work item.


## Evolution in SWITCHING-STATE-SEMANTICS-001

The static `electrical-v1` subset was extended with `disconnector(a,b)`.
This is a backward-compatible profile extension: structural schema `0.1` is unchanged,
and switching-state attributes remain governed by the separate
`switching-state-v1` layer.
