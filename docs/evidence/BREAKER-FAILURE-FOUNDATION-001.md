# BREAKER-FAILURE-FOUNDATION-001 — evidence

Status: **Draft qualification evidence**  
Issue: **#29**  
Draft PR: **#30**  
Stacked base: WS-9B engine foundation PR #26 head
`6de4d5937ba0aa56fcf25f2c20643aff64ce9147`

## Delivered runtime

New module:

`src/energologic/protection/breaker_failure.py`

Public contract includes:

- `BreakerFailureBinding`;
- `BreakerFailureProgram`;
- `BreakerFailureSnapshot`;
- `BreakerFailureRuntimeState`;
- `BreakerFailureEvent`;
- `BreakerFailureStepResult`;
- compile/evaluate/fingerprint helpers.

The module reuses the declarative `ProtectionOutputRequest` contract from the generic
WS-9B engine.

## Functional definition

IEC 60050-448:1995, IEV 448-11-18 is the terminology source for
`circuit-breaker failure protection`.

The same definition is cited in IEC 63438:2024, clause 3.35: the protection clears a
system fault by initiating tripping of other circuit-breaker(s) if the appropriate
circuit-breaker fails to trip.

This supports two foundation rules:

1. the monitored breaker and backup trip targets are explicit identities;
2. retrip of the monitored breaker is not silently treated as the same generic
   behavior as backup tripping of other breakers.

## Manufacturer evidence for explicit criterion binding

Official Siemens SIPROTEC documentation demonstrates implementations using:

- a current criterion;
- breaker auxiliary-contact criterion;
- implementation-specific combinations/start behavior.

Official ABB Relion parameter documentation exposes separate breaker-failure inputs
including START and breaker closed-position/fault status.

Therefore this generic runtime does not choose a universal current/position
combination. The integration binding must select it explicitly.

Sources reviewed:

- IEC 60050-448:1995 / IEV 448-11-18;
- IEC 63438:2024, 3.35;
- Siemens SIPROTEC 7UM61 / breaker-failure protection manual section;
- Siemens SIPROTEC 7ST6 / circuit-breaker-failure protection section;
- ABB Relion RE615 CCBRBRF1 parameter documentation.

## Russian operational context

PUE 3.2.18 describes УРОВ as acting on breakers adjacent to the failed breaker when
the breaker of a faulted element fails.

This is supplementary system-design context. The runtime contract is not presented as
a full implementation of all Russian network-specific УРОВ requirements.

## Qualified state-machine behavior

Tests cover:

- no-start idle state without unnecessary feedback requirements;
- breaker-position criterion;
- current-flow criterion;
- OR criterion;
- AND criterion;
- missing required feedback fail-closed;
- maintained-start reset;
- latched-start continuation;
- criterion clearing before delay;
- exact delay-boundary operation;
- zero-delay operation;
- one-shot backup request emission;
- reset after failure criterion clears;
- time reversal rejection;
- state/program fingerprint mismatch;
- monitored-breaker retrip rejection;
- unsupported current-threshold parameter rejection;
- unsupported multi-stage breaker-failure scheme rejection;
- disabled-function no-op;
- deterministic requests/result fingerprint.

## Intentional limitations

The current WS-9A synthetic card contains only a breaker-failure delay and one backup
trip association.

Accordingly this foundation does not infer:

- a current pickup threshold;
- breaker-position source;
- start source;
- site wiring;
- retrip;
- two-channel start security;
- two independent delay stages.

Those require explicit later settings/bindings.

## Initial verification

Implementation candidate:

`d1d449e1b334a1b530be2fd62423f5201f0b4519`

GitHub Actions run **37218116201 — SUCCESS**.

Representative Ubuntu job ran **151 tests — OK**.

Documentation-reconciled head `dfa0604a7bbd7395632800988141ec69ba5b32b5`: CI **37218303079 — SUCCESS** on Ubuntu/Windows × Python 3.11/3.12; representative Ubuntu job ran **151 tests — OK**.
