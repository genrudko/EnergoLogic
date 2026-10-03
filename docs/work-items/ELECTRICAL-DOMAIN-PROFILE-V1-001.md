# ELECTRICAL-DOMAIN-PROFILE-V1-001

Status: Awaiting owner acceptance  
Issue: #5  
Draft PR: #6

## Objective

Add deterministic electrical semantics on top of canonical schema `0.1` while preserving the open structural core.

## Dependency

Stacked on owner-accepted VISIO-CANONICAL-BRIDGE-001 head:

`ded99d866f55287dbb0836572a8edab40d380cfb`

PR #4 remains Draft and unmerged until an explicit merge command.

## Architectural decision

Structural and electrical validation are deliberately separate:

- `validate_model()` remains the open schema-level validator;
- `validate_electrical_model()` applies explicit profile `electrical-v1`.

No schema bump is required because serialized structure did not change.

The profile registry is read-only at runtime.

## Supported v1 domain subset

| Kind | Terminals | Maximum external degree |
| --- | --- | --- |
| `bus` | `node` | unbounded |
| `circuit_breaker` | `a`, `b` | 1 per terminal |
| `current_transformer` | `a`, `b` | 1 per terminal |
| `external_link` | `node` | 1 |

## Canonical quantity rule

Nominal voltage is:

`attributes.nominal_voltage_v: positive integer`

Frontend display units do not enter canonical semantics.

For the qualified Visio/VTD slice:

`INDEX(10, Prop.u.Format) = 35 kV → 35000 V`

The prior frontend-oriented `nominal_voltage_kv=35` representation is replaced by canonical `nominal_voltage_v=35000`.

## Deterministic validation rules

The profile reports stable ordered issues for:

- unsupported element kinds;
- exact terminal-contract violations;
- missing/invalid nominal voltage;
- direct nominal-voltage mismatch;
- duplicate electrical edges;
- intra-element external connections;
- bounded terminal degree overflow.

The renderer for the qualified Visio slice also fails closed if the canonical model does not pass `electrical-v1`.

## CLI

Default structural behavior is preserved:

```bash
energologic validate examples/minimal.energologic.json
```

Explicit domain validation:

```bash
energologic validate examples/kru35-v1-cell.electrical-v1.json --profile electrical-v1
```

## Regression evidence

Code candidate head:

`149694ba74199f0592c837070d9e4af16331e32b`

Code CI:

https://github.com/genrudko/EnergoLogic/actions/runs/37111315230

Result: **4/4 PASS**

- Ubuntu / Python 3.11 — PASS;
- Ubuntu / Python 3.12 — PASS;
- Windows / Python 3.11 — PASS;
- Windows / Python 3.12 — PASS.

A representative Linux job ran **33 tests — PASS**.

Regression coverage includes:

- structural validation remains open for future/unknown kinds;
- valid electrical-v1 slice;
- immutable profile registry;
- exact terminal contract;
- missing/invalid voltage;
- voltage mismatch;
- bounded-terminal branching;
- duplicate electrical edge;
- intra-element connection;
- input-order-independent issue ordering;
- CLI structural compatibility;
- CLI electrical-v1 selection;
- Visio 35 kV → canonical 35000 V;
- Visio renderer rejects domain-invalid voltage topology;
- Visio round-trip remains deterministic.

## Canonical fingerprint migration

The live-like qualified KRU-35 source snapshot now canonicalizes under integer-volts semantics to:

`364a379c2756d7801090d7602dc2f1ddadca3203069b779a248e3ed7652e053b`

This value is pinned by regression test.

## Live Visio read-only confirmation

Node `visio-workstation` was online with no pending/uncertain operations and no operator notes.

On:

`KRU-35_normal_scheme_v2_energologic_v1.vsdx / MCP-v2 / breaker #66`

the native VTD state still reports:

- `Prop.u = INDEX(10,Prop.u.Format)`;
- rendered/result value = `35 кВ`;
- `voltage_index = 10`;
- `voltage_kv = 35`.

The frontend mapping for index 10 is now explicitly canonical `35000 V`.

No Visio mutation was required for this work item.

## Verification commands

```bash
python -m pip install -e .
python -m compileall -q src
python -m unittest discover -s tests -v
energologic validate examples/minimal.energologic.json
energologic validate examples/kru35-v1-cell.electrical-v1.json --profile electrical-v1
```

## Explicit non-goals

- complete equipment taxonomy;
- breaker/disconnector operating-state semantics;
- transformer multi-voltage semantics;
- Planner;
- RZA/protection;
- CIM;
- pandapower/power-flow/short-circuit solvers;
- heuristic or LLM-based electrical decisions.

## Acceptance checks

- [x] Dedicated stacked branch and Draft PR.
- [x] `electrical-v1` profile API implemented.
- [x] Profile registry immutable at runtime.
- [x] Exact terminal contracts covered by tests.
- [x] Canonical nominal voltage uses integer volts.
- [x] Voltage mismatch detection covered by tests.
- [x] Bounded terminal degree rules covered by tests.
- [x] Duplicate/intra-element connection rules covered by tests.
- [x] Existing structural validation remains open/backwards compatible.
- [x] CLI explicitly selects `electrical-v1`.
- [x] Supported Visio slice maps 35 kV to 35000 V.
- [x] Visio renderer fails closed on electrical-v1 violations.
- [x] Live read-only VTD unit evidence recorded.
- [x] Code candidate Linux/Windows CI green.
- [x] Final PR-head CI gate is mandatory; the actual final-head result is recorded in Issue/PR metadata.
- [ ] Owner acceptance.
- [x] No merge or Ready for Review without explicit owner command.
