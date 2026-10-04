# Protection Engine Contract — WS-9B foundation

Status: candidate contract in PROTECTION-ENGINE-FOUNDATION-001  
Issue: #25  
Draft PR: #26

## 1. Purpose

WS-9B turns validated protection settings plus explicit measured quantities into
deterministic protection state transitions and declarative output requests.

ProtectionSettingCard v1
+ measured-value snapshot
+ logical time
+ prior protection state
→ generic protection engine
→ pickup / reset / operate events
+ output requests
+ next protection state

The engine does not operate a breaker and does not mutate the canonical electrical
model.

## 2. Stacked dependency

This work item is stacked on WS-9A Draft PR #22 and consumes its public setting-card
contract.

It deliberately does not import:

- WS-6 operational runtime;
- WS-8 solver runtime;
- Visio/frontends;
- the unmerged WS-2 terminology runtime.

The runtime remains stdlib-only.

## 3. Qualified protection functions

The first engine contract qualifies one scalar-current, definite-time algorithm family
for these controlled function IDs:

- protection.overcurrent — МТЗ;
- protection.instantaneous_overcurrent — ТО;
- protection.earth_fault — токовая защита от замыканий на землю.

The semantic bindings are explicit:

| Function | Required measurement semantic | Required pickup semantic |
|---|---|---|
| overcurrent | phase_current | pickup_current |
| instantaneous overcurrent | phase_current | pickup_current |
| earth fault | residual_current | pickup_residual_current |

Delay semantic is operate_delay.

A current-valued input with the wrong semantic key is rejected even if its physical
unit happens to be amperes.

## 4. Settings completeness and lifecycle

Production execution is fail-closed by default.

compile_protection_program normally requires:

- settings_scope = full_configuration;
- lifecycle = approved or implemented.

WS-9A operational_summary and partial_configuration are not silently treated as
complete protection configurations.

For explicit engineering/unit-test work only, callers may use
allow_incomplete_settings=True.

Non-authoritative lifecycle states require a separate explicit override.

These overrides are visible API choices; they are not hidden defaults.

## 5. Measured-value snapshots

A snapshot contains:

- caller-supplied stable snapshot_id;
- caller-supplied logical time_s;
- zero or more normalized MeasuredQuantity values.

A measured quantity carries:

- stable WS-9A measurement-input ID;
- quantity kind;
- basis;
- normalized value;
- normalized unit.

Values use exact decimal text and decimal.Decimal.

The engine does not read wall-clock time.

### Basis preservation

The setting and measured value must have the same basis.

Examples:

- primary setting + primary measurement — allowed;
- primary setting + secondary measurement — rejected.

WS-9B performs no implicit CT/VT transformation.

### Canonical units

Runtime snapshots are already normalized data.

For current in the current foundation the canonical normalized unit is A.

A runtime value supplied as kA is rejected as not normalized even if it could be
mathematically converted.

## 6. Idealized definite-time semantics

This foundation implements an ideal logical algorithm, not the analogue/digital
tolerance envelope of a particular relay.

For each qualified stage:

pickup criterion = measured value >= configured pickup

When inactive:

- criterion false → remain inactive;
- criterion true → emit pickup and start the logical timer.

For a non-zero delay:

operate when logical_time - pickup_start >= operate_delay

For an explicitly configured zero delay:

- pickup and operate occur in the same engine step.

After operation:

- no repeated action request is emitted while the pickup criterion remains true;
- when measured value becomes lower than pickup, emit reset and return to inactive;
- a later pickup begins a new timing cycle.

### No invented hysteresis

The foundation does not invent:

- return/drop-off ratio;
- reset threshold;
- relay tolerance;
- overshoot;
- transient filtering;
- debounce;
- manufacturer-specific memory.

A separately configured reset characteristic is not interpreted by this bounded
algorithm yet. Such a parameter fails as unsupported instead of being guessed.

### Sampling semantics

The timer begins at the first supplied snapshot at which the pickup criterion is
observed.

The engine does not interpolate a threshold crossing between snapshots. The caller
owns sampling density and logical time.

## 7. Runtime state

Each compiled active stage has one of:

- inactive;
- picked_up;
- operated.

State records:

- function ID;
- stage ID;
- pickup timestamp when applicable;
- operation timestamp when applicable.

State is immutable and tied to the fingerprint of the exact setting card from which
the program was compiled.

Reusing state with another card fails closed.

Logical time is nondecreasing. Time reversal fails closed.

## 8. Output requests

Operation converts configured stage-level WS-9A actions into declarative requests.

A request includes:

- deterministic request ID;
- function ID;
- stage ID;
- configured action ID;
- action type;
- target kind/ID;
- logical time;
- cause.

Example:

trip requested → breaker:v-1-35

This means only that protection logic requested the configured action.

It does not mean:

- the breaker opened;
- WS-6 accepted an operation;
- an interlock permitted it;
- the network topology changed.

Function-level action semantics are intentionally not guessed in this foundation;
non-empty function-level actions fail program compilation.

## 9. Unsupported functions are explicit

The WS-9A synthetic card also contains protection.breaker_failure.

WS-9B foundation reports that function in unsupported_function_ids; it does not
silently ignore it as though it were simulated.

УРОВ requires, at minimum, an explicit contract for:

- initiation/start;
- protected breaker identity;
- breaker open/closed feedback;
- current/other reset criteria where applicable;
- timing;
- output targets.

The current WS-9A synthetic delay alone is insufficient to infer these semantics.

## 10. WS-6 / Gate E boundary

WS-6 owns operational topology and switching-operation event sequences.

WS-9B foundation owns protection algorithm state and output requests.

Neither imports the other.

Future Gate E should adapt:

WS-6 / WS-8 measured or event context
→ ProtectionSnapshot
→ ProtectionOutputRequest
→ operational adapter / validators
→ WS-6 switching operation

A trip request must remain distinct from successful breaker operation.

## 11. Normative design evidence

IEC currently lists IEC 60255-151:2009 as Valid with stability date 2028. Its
published scope covers over/under-current protection functions, measurement
characteristics and time-delay characteristics.

Rosstandart currently lists ГОСТ IEC 60255-151-2014 as Действует and describes the
same functional domain, including measurement and return-time characteristics.

This bounded engine does not claim to reproduce every tolerance, time curve or dynamic
performance requirement of those standards. It implements only the explicit ideal
definite-time semantics qualified by the tests in this work item.

## 12. Explicitly deferred

- УРОВ state machine;
- inverse-time curves;
- directional current protection;
- voltage restraint/control;
- distance protection;
- differential protection;
- arc protection;
- live WS-6 event consumption;
- WS-8 short-circuit/result feed;
- breaker mutation;
- real-time/asynchronous scheduling;
- relay/manufacturer tolerance models.
