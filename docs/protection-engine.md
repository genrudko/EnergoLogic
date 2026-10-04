# Protection engine foundation

The generic WS-9B runtime lives in:

src/energologic/protection/runtime.py

It consumes WS-9A ProtectionSettingCard objects.

## Compile a program

Production compilation is intentionally strict.

Example:

from energologic.protection import compile_protection_program

program = compile_protection_program(card)

By default the card must claim full_configuration and must be approved or implemented.

For bounded synthetic/engineering work with an explicitly incomplete setting source:

program = compile_protection_program(
    card,
    function_ids=["function:test:mtz"],
    allow_incomplete_settings=True,
)

Do not enable this override implicitly in production integration.

## Feed a measured snapshot

Use make_measured_quantity and make_snapshot.

Logical time is caller supplied. The engine does not use the system clock.

Pass the previous immutable runtime state into evaluate_protection_step to continue
definite-time timing.

At the exact configured delay boundary the stage operates.

## Output is a request, not an operation

A trip request is not permission to mutate a breaker directly.

Future Gate E integration must pass it through the operational action/validation
boundary.

## Adding another function to this engine

Do not merely add a concept ID to SUPPORTED_CONCEPT_IDS.

A new function needs an explicit bounded contract for:

1. measurement semantic(s);
2. parameter semantic(s);
3. quantity/basis rules;
4. pickup condition;
5. reset condition;
6. timer/memory behavior;
7. output semantics;
8. exact threshold tests;
9. invalid/ambiguous-setting tests;
10. deterministic state transitions.

If any of these are unknown, leave the function unsupported.

## Adding УРОВ

The current setting card contains a breaker-failure delay and output association, but
that is not enough to define the algorithm.

A later item must add explicit external inputs for initiation and breaker/current
feedback before protection.breaker_failure can be moved into the supported set.
