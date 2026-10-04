# OPERATIONAL-SIMULATION-FOUNDATION-001 — Qualification Evidence

Status: **implementation candidate**
Issue: #19
Branch: `operational/operational-simulation-foundation-001`
Draft PR: #20

## 1. Isolation

Branch base:

`main@9edc59a0e83f17e94c50ca10f7feac320332b2a1`

The implementation is headless and has no Visio/COM or solver dependency.

## 2. Synthetic fixture

Fixture:

`examples/ws6-operational-two-source.json`

It contains:

- explicit Source A boundary;
- source-A disconnector;
- source-A current transformer;
- Bus A;
- bus-coupler circuit breaker;
- Bus B;
- source-B disconnector;
- explicit Source B boundary;
- withdrawable transformer breaker;
- 35/0.4 kV two-winding transformer;
- LV external boundary.

The fixture uses only already accepted `electrical-v1` element kinds and
accepted switching-state attributes.

Canonical model fingerprint:

`7bcab86c2aeb7d71fe6962ceb5b3b94005e0878b9c44e8d034cd91235792358d`

## 3. State A — coupler open

Active sources:

- `source:a:node`;
- `source:b:node`.

Observed:

| Terminal | Source attribution |
|---|---|
| `bus:a:node` | Source A |
| `breaker:coupler:a` | Source A |
| `breaker:coupler:b` | Source B |
| `bus:b:node` | Source B |
| `external:lv:node` | Source B |

This proves the terminal-first invariant: both sides of an open breaker can be
energized simultaneously from different sources without creating a conducting
path through the breaker.

Effective conductive-topology fingerprint:

`964bb8198db030c1e0a9198dafbf55aa36aa9d953043a0e15f15dbd69543ad6d`

## 4. State B — coupler closed

Only:

`breaker:coupler.switch_state: open → closed`

changes.

Observed:

| Terminal | Source attribution |
|---|---|
| `bus:a:node` | Source A + Source B |
| `bus:b:node` | Source A + Source B |
| `external:lv:node` | Source A + Source B |

Effective conductive-topology fingerprint:

`fb5a94eaf599cc8575cc2dffc5bf918d32e1d97faaee4ecbbcc2625160af1fad`

The before/after operational delta contains **17 changed terminal states/source
attributions** and reports `topology_changed = true`.

## 5. Loss of Source B path

With the coupler open and only
`disconnector:source-b.switch_state` changed to `open`:

- source-B-side terminal `a` remains energized from Source B;
- terminal `b` is de-energized;
- Bus B becomes de-energized;
- transformer HV/LV become de-energized;
- LV external boundary becomes de-energized.

This demonstrates true isolation across an open switching device.

## 6. Withdrawable breaker semantics

For `breaker:transformer`:

- closed + working conducts;
- closed + repair does not conduct;
- closed + control does not conduct.

In repair/control, the bus-side terminal may remain energized while the
transformer-side terminal and transformer remain de-energized.

The runtime reuses the already accepted
`switch_allows_primary_conduction()` predicate.

## 7. Transformer traversal

With Source B available and the transformer breaker conducting:

- transformer HV is energized;
- transformer LV is energized;
- LV external boundary is energized from Source B.

This is topological energization only. No numerical voltage/power-flow result is
claimed.

## 8. Failure behavior

Qualified fail-closed cases:

- nonexistent source endpoint → `invalid_source`;
- invalid canonical switching state → `invalid_model`;
- operational delta with changed canonical terminal set →
  `incompatible_models`;
- operational delta from a non-success result →
  `incompatible_models`.

An empty source set is intentionally valid and yields an all-deenergized state.

## 9. Determinism

Reversing element order, connection order and source input order produces the
same:

- terminal states;
- element summaries;
- effective conductive-topology fingerprint.

Duplicate source refs are normalized away.

## 10. Local verification

Commands:

```text
python3 -m compileall -q src tests
PYTHONPATH=src python3 -m unittest tests.test_operational_simulation -v
PYTHONPATH=src python3 -m unittest discover -s tests -v
git diff --check
```

Current local result:

- focused WS-6 suite: **13/13 PASS**;
- full repository suite: **84/84 PASS**;
- static operational-layer dependency guard: PASS;
- `git diff --check`: PASS.

Final GitHub CI result is recorded after the implementation candidate is pushed.

## 11. Known limitations

This foundation intentionally does not yet model:

- earthing;
- grounding switches;
- interlocks;
- safe/unsafe operation decisions;
- event chronology;
- load flow or voltage magnitude;
- protection/RZA;
- phase-domain neutral behavior.

It also does not infer whether an `external_link` is a source. Active sources
are explicit runtime boundary conditions.
