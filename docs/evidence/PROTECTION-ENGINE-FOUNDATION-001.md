# PROTECTION-ENGINE-FOUNDATION-001 — evidence

Status: Draft qualification evidence  
Issue: #25  
Draft PR: #26  
Stacked base: WS-9A PR #22 head
2fc665a9be2e73fbeb059650a822c041791df11c

## Delivered runtime

src/energologic/protection/runtime.py adds:

- ProtectionProgram;
- MeasuredQuantity;
- ProtectionSnapshot;
- ProtectionRuntimeState;
- StageRuntimeState;
- ProtectionEngineEvent;
- ProtectionOutputRequest;
- deterministic compile/evaluate/fingerprint functions.

No wall-clock, async, WS-6, WS-8, frontend or Visio runtime is imported.

## Qualified algorithms

The first bounded engine qualifies:

- protection.overcurrent;
- protection.instantaneous_overcurrent;
- protection.earth_fault.

All are single-scalar-current, definite-time stage algorithms.

Explicit semantic contracts prevent a physically compatible but semantically wrong
input from being accepted:

- МТЗ/ТО require phase_current + pickup_current;
- earth-fault requires residual_current + pickup_residual_current;
- delay requires operate_delay.

## Fail-closed execution guards

The engine rejects by default:

- incomplete operational_summary / partial_configuration;
- draft/superseded/unknown setting lifecycle;
- null enabled state;
- missing or duplicate required algorithm parameters;
- function-level actions whose stage semantics are undefined;
- unsupported extra algorithm parameters;
- wrong measurement semantic;
- wrong pickup semantic;
- basis mismatch;
- non-normalized runtime unit;
- missing/duplicate measurement value;
- negative scalar operating quantity;
- logical-time reversal;
- runtime state for another setting-card fingerprint.

Explicit engineering overrides exist for incomplete/non-authoritative settings but are
never defaults.

## State-machine qualification

Regression tests demonstrate:

1. below pickup → inactive;
2. exact pickup threshold → pickup;
3. before definite-time delay → no operation;
4. exact delay boundary → operate;
5. configured zero delay → pickup + operate in one step;
6. operated stage emits its output requests once;
7. falling below pickup → reset;
8. later pickup starts a fresh timer;
9. earth-fault uses residual-current input;
10. action request preserves the configured target without mutating the setting card;
11. identical input/state produces identical request IDs and result fingerprint;
12. measurement tuple order does not change the result.

## Unsupported breaker failure

The inherited WS-9A synthetic card contains protection.breaker_failure.

It remains explicit in unsupported_function_ids.

No breaker-failure algorithm was inferred from its delay because the setting card does
not yet provide a complete start/feedback contract.

## Standards evidence

Verified on 2026-10-04:

- IEC Webstore: IEC 60255-151:2009, status Valid, stability date 2028;
- Rosstandart: ГОСТ IEC 60255-151-2014, status Действует.

These sources support treating overcurrent pickup/measurement/time behavior as a
defined functional domain.

The exact ideal threshold/reset state machine in this PR is an EnergoLogic bounded
simulation contract. It is not represented as a complete conformance model for every
IEC/GOST relay performance tolerance.

## CI checkpoints

- first runtime candidate 48afdb1e4d13727d3b965e1fd00f0722c393055b:
  CI 37215872927 — SUCCESS, 118 tests on representative job;
- fail-closed semantic/scope reinforcement through
  9227a21427235f1edf31be6652fa6bbd7a47a237:
  CI 37216082437 — SUCCESS, 124 tests on representative Ubuntu job.

Final documentation/head CI is recorded before owner acceptance.
