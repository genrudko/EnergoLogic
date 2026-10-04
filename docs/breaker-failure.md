# Breaker-failure / УРОВ runtime

The bounded WS-9B breaker-failure runtime lives in:

```text
src/energologic/protection/breaker_failure.py
```

It is stacked on the generic protection-engine foundation.

## Compile explicitly

A breaker-failure program requires both:

1. a validated WS-9A setting card;
2. an explicit integration binding.

Example:

```python
from energologic.protection import (
    BreakerFailureBinding,
    compile_breaker_failure_program,
)

binding = BreakerFailureBinding(
    binding_id="binding:feeder-1:bf",
    function_id="function:feeder-1:breaker-failure",
    monitored_breaker_id="breaker:feeder-1",
    criterion_mode="breaker_closed_or_current_flow",
    start_behavior="maintained",
    provenance_ref="site-profile:feeder-1:bf",
)

program = compile_breaker_failure_program(card, binding)
```

Production compilation remains fail-closed for incomplete/non-authoritative setting
cards, just like the generic protection engine.

## Feed explicit runtime feedback

```python
from energologic.protection import (
    evaluate_breaker_failure_step,
    make_breaker_failure_snapshot,
)

snapshot = make_breaker_failure_snapshot(
    snapshot_id="bf:1",
    time_s="0",
    start_active=True,
    breaker_closed=True,
    current_flow_present=True,
)

result = evaluate_breaker_failure_step(program, snapshot)
```

The caller owns logical time and feedback qualification.

## Do not guess criterion wiring

Use only a criterion mode justified by actual device/site configuration.

Do not infer:

- current-flow criterion because a current measurement exists;
- breaker-position criterion because WS-6 knows the switch state;
- OR/AND combination from common industry practice;
- maintained/latched start behavior from the word УРОВ.

Those decisions belong to explicit configuration/provenance.

## Output remains declarative

A returned trip request must pass through the future Gate E operational adapter.

Do not directly mutate the breaker from the breaker-failure runtime.

## Extending to vendor logic

A later vendor-specific or generalized extension needs explicit evidence for:

- retrip;
- two-channel start;
- current thresholds;
- second timers;
- blocking;
- per-phase logic;
- different reset criteria.

Until such settings are represented and sourced, leave them unsupported.
