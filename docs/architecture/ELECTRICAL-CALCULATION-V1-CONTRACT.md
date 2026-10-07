# ELECTRICAL-CALCULATION-V1 — production calculation facts & Gate-D materialization

Status: **Draft candidate** (`ELECTRICAL-CALCULATION-DOMAIN-001`, issue #31, PR #32).
Depends on: `electrical-v1`, switching-state-v1, transformer semantics and
[ELECTRICAL-SOLVER-ADAPTER-CONTRACT.md](ELECTRICAL-SOLVER-ADAPTER-CONTRACT.md).
Architectural baseline: [ELECTRICAL-SOLVER-PRODUCTION-DECISIONS.md](ELECTRICAL-SOLVER-PRODUCTION-DECISIONS.md).

## Boundary and ownership

```text
CanonicalModel (0.1: IDs, bus nodes, terminals, connectivity, switch state)
  + electrical-calculation-v1 (SI facts, states, provenance, scenario inactive IDs)
       |
       v
  validate_calculation()
       |
       v
  materialize_study()  [deterministic Gate-D manifest/fingerprint]
       |
       +-- existing SolverStudyInput (transient solver-neutral DTO)
                  |
                  v
             selected qualified adapter
```

**No persistence of `SolverStudyInput` as a second source of engineering
truth.** Neither canonical structural fields nor calculation facts contain
pandapower tables, IDs, column names, or inferred backend defaults.

## Contract

`schema/electrical-calculation-v1.schema.json` defines the external profile.
Python: `energologic.domain.calculation` (decode/validate/serialize) and
`energologic.solvers.materialization` (existing Gate-D DTO projection).
An equipment record has `canonical_id`, `kind`, `parameters`; each
parameter is:

- `{state: known, value: ..., provenance: {source_id, locator, revision?}}`
- `{state: unknown, provenance?: ...}`
- `{state: not_applicable, provenance?: ...}`
- absent key = **missing**, distinct from the other three states.

Known facts **require** a nonempty source ID and source locator. The model ID
must match `CanonicalModel.model_id`; each profile ID/kind must match one
canonical element; no duplicate records. Canonical element names and cable
labels are never used to infer values.

The versioned calculation contour accepts existing canonical types:
`bus`, `circuit_breaker`, `disconnector`, `transformer_2w`, and
the formerly WS-8-synthetic `external_grid`, `line`, `load`.
This is **not** an edit to the accepted `electrical-v1` profile.
`bus` is the explicit balanced calculation node; its exact
`nominal_voltage_v` is a canonical fact. Transformer HV/LV rated
voltages come from their **terminal-scoped** canonical values. Exact nominal
voltage cannot be derived from `voltage_class`.

`line` includes `construction=overhead|cable`; this maps to the existing
Gate-D `LineParameters.line_type=line|cable` without altering that DTO.
The line impedance fields below are the **positive-sequence** per-length
quantities for balanced studies. Zero-sequence values remain independent
optional source facts, never extrapolated from positive-sequence data.

## SI parameter catalog

| Kind | Mandatory known facts | Optional facts |
|---|---|---|
| external_grid | voltage_pu; angle_deg; short_circuit_power_max_va; rx_max | zero_sequence_r_over_x_max; zero_sequence_x_over_x_max |
| line | construction; length_m; resistance_ohm_per_m; reactance_ohm_per_m; capacitance_f_per_m; max_current_a; end_temperature_c | zero_sequence_resistance_ohm_per_m; zero_sequence_reactance_ohm_per_m; zero_sequence_capacitance_f_per_m |
| transformer_2w | rated_power_va; short_circuit_voltage_percent; short_circuit_resistance_percent; iron_loss_w; no_load_current_percent; phase_shift_deg | vector_group; five independent zero_sequence_* parameters |
| load | active_power_w; reactive_power_var | none |

Fields encode units as `_v`, `_va`, `_w`, `_var`, `_m`,
`_ohm_per_m`, `_f_per_m`, `_a`, `_deg`,
`_percent`, `_pu` or dimensionless ratios. No hidden kV/MW/km or
percentage-to-per-unit conversion is performed in the domain layer.
The existing backend adapter handles backend-specific conversions.

For this v1 boundary **all listed mandatory values are explicit**, including
values which the spike DTO happens to default (source voltage, phase shift,
reactive load, iron loss, etc.). The currently accepted DTO also requires a
nonzero source SC power for its input validation, including power flow:
the profile therefore requires this explicit fact for both study types, rather
than passing a fabricated default. This can be relaxed only through a separate
versioned Gate-D DTO/adapter decision.

## Topology / switching

- Direct canonical bus-to-equipment terminal connection is a bounded current
  Gate-D adapter prerequisite, not a universal canonical topology rule.
- Bus and switchgear exact voltages must match attached terminals; a line
  cannot bridge unequal nominal bus voltages; transformers may bridge ratings
  solely through explicit HV/LV terminal facts.
- `switch_allows_primary_conduction` is the accepted source for breaker/
  disconnector state: `closed` is conductive for fixed devices, and only
  `closed + withdrawable_position=working` for withdrawable ones. The
  materializer preserves canonical switch facts, not a parallel solver state.
- `inactive_equipment_ids` is a separate explicit scenario overlay;
  disabling a bus remains unsupported in the existing Gate-D spike DTO.

## Study capability / fail-closed decisions

- `power_flow` and `short_circuit_3ph` materialize; the latter validates
  explicit source short-circuit power/X:R. No numerical solve occurs here.
- `short_circuit_2ph` returns `unsupported_sequence_study` until independent
  negative-sequence semantics and backend qualifications exist.
- `short_circuit_1ph` reports missing independently sourced zero-sequence
  data when applicable and **always** returns
  `unsupported_phase_neutral_topology` under v1: the mere presence of zero
  values or winding connection labels is insufficient evidence of a qualified
  earthing/neutral current-return path.
- No vector group, neutral availability, earthing system, phase connections,
  tap positions, cable nameplate values or zero-sequence impedances are
  guessed. Known zero-sequence values are retained and projected into
  optional Gate-D fields; unknown/not-applicable ones stay `None`.
- Unsupported canonical kinds and non-direct terminal topology fail closed,
  rather than being silently ignored or simplified.

The WS-8 spike may experimentally calculate 2ph/1ph faults; it does **not**
certify those paths as qualified by this new production domain.

## Determinism / linkage / provenance

`materialize_study(model, profile, study_type=...)` yields
`MaterializedStudy(solver_input, normalized_json, fingerprint)`.
Normalization sorts canonical objects/connections/IDs and profile records,
and encodes the full canonical model + SI DTO + **complete fact states and
provenance**. The 64-hex SHA-256 is over canonical UTF-8 JSON payload
without the fingerprint member, then added as `fingerprint_sha256`.
Changing provenance changes fingerprint intentionally; source auditability
must not be lost. Same semantic record ordering leads to identical output.

The fingerprint is an **input identity**, not numerical solver-result
provenance and not a backend-specific topology fingerprint.

## Terminology

Verified against `src/energologic/terminology/registry-v1.json`:
`system.source` (источник), `system.load` (нагрузка),
`line.electric_line` (линия электропередачи),
`line.cable_line` (кабельная линия электропередачи),
`line.overhead_line` (воздушная линия электропередачи),
`topology.node` (узел), `bus.busbar` (сборная шина),
`transformer.power` (силовой трансформатор),
`switchgear.circuit_breaker` (выключатель) and
`switchgear.disconnector` (разъединитель).
No new independent terminology concept was invented in this item.
The code identifier `external_grid` denotes the external supply **kind**,
not a claim of a new normalized RU equipment noun.

## Explicit follow-ups

`PHASE-NEUTRAL-TOPOLOGY-001` (phase, neutral and earthing identity);
sequence/fault capability qualification for 2ph and 1ph studies;
`SOLVER-RUNTIME-HOST-001`;
`SITE-SOLVER-ACCEPTANCE-001`;
`SWITCH-FLOW-RESULTS-001` when current attribution is needed;
`OPENDSS-ADAPTER-001` only after phase-neutral qualification.

## Verification

See `docs/evidence/ELECTRICAL-CALCULATION-DOMAIN-001.md`.
