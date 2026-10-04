# Breaker-Failure Protection Contract — WS-9B foundation

Status: **candidate contract in BREAKER-FAILURE-FOUNDATION-001**  
Issue: **#29**  
Draft PR: **#30**

## 1. Purpose

This contract defines a deterministic circuit-breaker-failure / УРОВ state machine
without importing WS-6 runtime types and without assuming a vendor-specific logic
diagram.

The bounded flow is:

```text
WS-9A breaker-failure setting
+ explicit BreakerFailureBinding
+ deterministic runtime feedback
        ↓
breaker-failure state machine
        ↓
pickup / reset / operate events
+ declarative backup trip requests
```

The result is protection logic only. It does not operate any breaker.

## 2. Function meaning

IEC terminology defines circuit-breaker failure protection as protection intended to
clear a system fault by initiating tripping of other circuit-breakers if the
appropriate circuit-breaker fails to trip.

This foundation therefore treats the monitored failed breaker and the backup trip
targets as different identities.

Retrip of the monitored breaker is intentionally out of scope in this bounded item.

## 3. Explicit binding

The current WS-9A card contains the breaker-failure function, delay and output target,
but it does not contain enough site/runtime wiring information to define the complete
algorithm.

Therefore the integration boundary must provide a `BreakerFailureBinding`.

The binding contains:

- stable binding ID;
- breaker-failure function ID;
- monitored breaker stable ID;
- explicit failure-criterion mode;
- explicit start behavior;
- stable provenance/integration reference.

No criterion or start behavior has a default.

## 4. Failure criteria

Supported modes:

| Mode | Failure remains present when |
|---|---|
| `breaker_closed` | the monitored breaker closed-position feedback is true |
| `current_flow` | qualified current-flow feedback is true |
| `breaker_closed_or_current_flow` | either explicit feedback is true |
| `breaker_closed_and_current_flow` | both explicit feedbacks are true |

Inputs required by the selected mode are mandatory.

For an OR or AND mode, both feedback channels must be present. The engine does not
interpret an absent channel as false.

The current-flow input is already a qualified boolean runtime signal. This work item
does not invent a current threshold from the WS-9A card.

## 5. Start behavior

Supported modes:

### `maintained`

The external start must remain active throughout timing.

If start drops before operation, the state resets without a backup trip.

This models protection implementations where the initiating signal is required during
the delay.

### `latched`

Once timing has started, a later loss of the external start does not cancel timing.

The breaker-failure criterion must still remain present.

This mode exists because start-memory behavior is implementation-dependent. The engine
does not choose between maintained and latched semantics on its own.

## 6. Runtime input

A `BreakerFailureSnapshot` carries:

- caller-supplied snapshot ID;
- caller-supplied logical time;
- `start_active`;
- `breaker_closed` when required;
- `current_flow_present` when required.

No wall clock is read.

Logical time must be nondecreasing.

## 7. State machine

States:

- `inactive`;
- `timing`;
- `operated`.

### Inactive

- no start → remain inactive;
- start + failure criterion false → remain inactive;
- start + failure criterion true → emit pickup and begin timing;
- if configured delay is zero → emit pickup and operate in the same step.

### Timing

- failure criterion clears → reset;
- maintained start drops → reset;
- latched start may drop while criterion remains true;
- exact delay expiry while criterion remains true → operate.

### Operated

- configured backup requests are not emitted repeatedly;
- failure criterion remaining true → remain operated;
- failure criterion clearing → reset.

## 8. Settings consumed from WS-9A

The foundation requires:

- function concept `protection.breaker_failure`;
- exactly one explicit stage;
- exactly one stage delay;
- delay semantic key `breaker_failure_delay`;
- normalized seconds;
- basis `not_applicable`;
- explicit stage-level trip actions.

The foundation rejects rather than guesses:

- current pickup/threshold settings;
- function-level action semantics;
- multiple breaker-failure stages;
- vendor-specific retrip;
- vendor-specific second timer;
- non-trip backup actions.

## 9. Output contract

On operation, each qualified stage action becomes a deterministic
`ProtectionOutputRequest`.

The request preserves:

- function ID;
- stage ID;
- configured action ID;
- action type;
- target kind/ID;
- logical time;
- deterministic request ID;
- cause `breaker_failure_operated`.

A request means only that backup tripping was requested.

It does not mean that WS-6 accepted the operation or that the target breaker opened.

## 10. WS-6 boundary

Future Gate E integration should adapt explicit operational data to this runtime:

```text
protection trip/start event
+ monitored breaker feedback
+ optional qualified current-flow feedback
        ↓ adapter
BreakerFailureSnapshot
        ↓
breaker-failure runtime
        ↓
ProtectionOutputRequest
        ↓ operational adapter / validators
WS-6 switching operation
```

The breaker-failure package does not import `energologic.operational`.

## 11. Technical evidence for configurability

The generic contract intentionally avoids one hard-coded vendor scheme.

Examples from current/official manufacturer documentation demonstrate why:

- Siemens SIPROTEC breaker-failure functions can use a current criterion and breaker
  auxiliary-contact criterion, with specific start-hold behavior depending on the
  implementation;
- ABB Relion breaker-failure function inputs expose explicit START, breaker closed
  position and breaker-fault inputs.

Those examples support the need for explicit runtime binding, not a universal default
criterion.

## 12. Explicitly deferred

- retrip of the failed breaker;
- vendor-specific two-channel security;
- vendor-specific tBF1/tBF2 or staged breaker-failure schemes;
- derivation of current-flow feedback from raw current;
- Site Profile automatic binding;
- direct WS-6 event consumption;
- direct breaker mutation;
- asynchronous/wall-clock timing.
