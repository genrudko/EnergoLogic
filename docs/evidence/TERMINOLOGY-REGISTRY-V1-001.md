# TERMINOLOGY-REGISTRY-V1-001 — evidence and terminology decisions

Status: **Implementation complete in Draft; owner acceptance pending**  
Issue: **#17**  
Draft PR: **#18**  
Branch: `terminology/terminology-registry-v1-001`  
Base: `main@9edc59a0e83f17e94c50ca10f7feac320332b2a1`

## Repository boundary evidence

The WS-2 branch was created directly from `main`, not from
`visio/visio-editor-qol-001`.

No VISIO-EDITOR-QOL-001 implementation file is part of this work item.

## Implemented contract

- versioned machine-readable registry;
- versioned JSON Schema;
- deterministic stdlib-only runtime validation;
- stable concept ID + unique code identifier checks;
- scalar canonical RU/EN names;
- aliases and abbreviations separated from canonical terminology;
- deprecated/forbidden aliases with rationale;
- source edition/status + per-concept locator provenance;
- semantic binding collision protection;
- lookup by ID/code/term;
- ambiguity-safe domain-aware resolution;
- terminology lint, including ambiguous canonical strings;
- package-data delivery of the default registry.

Current registry: **41 concepts / 21 normative source records**.

## Corrected source-selection rule

The first implementation treated generic terminology vocabulary too much like a
global precedence table.

That is incorrect for scoped power equipment.

The corrected rule is:

> define the engineering scope first, then prefer the current authoritative source
> directly governing that scope; use IEV/GOST IEC to cross-check the international
> concept and translations.

A generic vocabulary entry must not collapse two distinct equipment classes or
override a more specific current product standard merely because it is an IEV entry.

## High-voltage breaker vs low-voltage automatic circuit-breaker

These are now separate concepts.

### High-voltage/power-system breaker

```text
concept: switchgear.circuit_breaker
domain: power.switchgear.high_voltage
RU: выключатель
EN: circuit-breaker
code: CircuitBreaker
semantic binding: energologic.element.kind = circuit_breaker
status: accepted
```

Evidence:

- ГОСТ Р 52565-2006: «Выключатели переменного тока на напряжения от 3 до 750 кВ»;
- English title: `Alternating-current circuit-breakers...`.

The existing semantic binding remains here because current EnergoLogic acceptance is
based on 35 kV switchgear.

### Low-voltage automatic circuit-breaker

```text
concept: switchgear.low_voltage_circuit_breaker
domain: power.switchgear.low_voltage
RU: автоматический выключатель
EN: circuit-breaker
code: LowVoltageCircuitBreaker
status: accepted
```

Evidence:

- ГОСТ IEC 60947-2-2021:
  «Аппаратура распределения и управления низковольтная. Часть 2.
  Автоматические выключатели»;
- English title: `Low-voltage switchgear and controlgear. Part 2. Circuit-breakers`;
- scope primarily covers circuits up to 1000 V AC / 1500 V DC.

No `energologic.element.kind` binding is assigned yet: the current canonical
electrical model has not accepted a separate LV breaker kind.

Because English uses `circuit-breaker` for both, English lookup without voltage
domain is intentionally ambiguous and fails closed.

## High-voltage earthing switch

The earlier proposal `заземляющий выключатель` was revised after checking the
directly applicable equipment standard.

Current registry:

```text
concept: switchgear.earthing_switch
domain: power.switchgear.high_voltage
RU: заземлитель
EN: earthing switch
code: EarthingSwitch
status: accepted
```

Primary evidence:

- ГОСТ Р 52726-2007 title:
  «Разъединители и заземлители переменного тока на напряжение свыше 1 кВ...»;
- clause 3.17 directly defines `заземлитель` as the contact switching apparatus
  used for earthing parts of a circuit.

Current supporting terminology is retained as aliases:

- `заземляющий выключатель` — ГОСТ IEC 60050-441-2015 / IEV 441-14-11;
- `выключатель заземления` — ГОСТ Р 57190-2016;
- `заземляющий разъединитель`, `заземляющий нож`, `нож заземления` —
  current ГОСТ 12.2.007.4-75 KRU/KSO safety terminology.

## Real Russian homonym: «заземлитель»

Two accepted concepts intentionally share Russian canonical `заземлитель`:

1. `switchgear.earthing_switch` — high-voltage switching apparatus;
2. `earthing.earth_electrode` — earth electrode.

This is not a data error. It is a real cross-domain terminology collision.

Consequences:

- concept ID/domain is authoritative;
- raw Russian string lookup returns both concepts;
- `resolve_unique()` requires sufficient domain context;
- lint without domain reports `ambiguous_term`;
- neither concept is silently deprecated merely to force string uniqueness.

## Other established decisions

| Concept | Registry decision | Evidence / locator | Lifecycle |
|---|---|---|---|
| disconnector | `разъединитель` / `disconnector` | ГОСТ IEC 60050-441-2015, 441-14-05 | accepted |
| load-break switch | `выключатель нагрузки` / `load-break switch` | ГОСТ 17717-79 plus current switchgear vocabulary | provisional — English preferred-form scope remains to be pinned |
| fuse | `плавкий предохранитель` / `fuse` | ГОСТ IEC 60050-441-2015, 441-18-01 | accepted |
| current transformer | `трансформатор тока` / `current transformer` | ГОСТ Р МЭК 61869-2-2015, 3.1.201 / IEV 321-02-01 | accepted |
| voltage transformer | `трансформатор напряжения` / `voltage transformer` | ГОСТ IEC 61869-3-2012, 3.1.301 / IEV 321-03-01 | accepted |
| power transformer | `силовой трансформатор` / `power transformer` | ГОСТ Р 52719-2007 | accepted |
| busbar | power-domain RU `сборная шина`; EN `busbar`; generic «шина» alias | ГОСТ Р 55190-2022, 3.1.44; supporting IEV 151-12-30 | provisional — wider non-KRU scope still needs explicit domain boundary |
| feeder bay / connection | `присоединение распределительного устройства` / `feeder bay` | ГОСТ 24291-90, term 34 / IEV 605-02-10 | accepted |
| bay / cell | `ячейка` / `bay` | ГОСТ 24291-90, term 35 / IEV 605-02-09 | accepted |
| terminal | `вывод` / `terminal` | ГОСТ IEC 60050-151-2014, 151-12-12 | accepted |
| switch state | `включенное положение` / `отключенное положение` | Приказ Минэнерго №757, ред. 06.07.2026; IEV 441-16-22/23 supporting | accepted for operational UI |
| switch operation | `включение` / `отключение` | Приказ Минэнерго №757, ред. 06.07.2026; IEV 441-16-08/09 supporting | accepted for operational UI |

## Existing canonical semantics preserved

Semantic bindings protect:

- `energologic.element.kind = circuit_breaker` → high-voltage breaker concept;
- `energologic.element.kind = disconnector`;
- `energologic.element.kind = current_transformer`;
- `energologic.element.kind = bus`;
- `energologic.switch_state = open`;
- `energologic.switch_state = closed`.

No existing `electrical-v1`, `switching-state-v1` or transformer behavior is
changed by adding the LV terminology concept.

## Remaining provisional entries

No owner choice is being requested for the breaker/earthing-switch terminology after
this correction.

Remaining `provisional` concepts are evidence or future-domain-contract gaps
(e.g. some line/protection/energization wording). They remain explicit rather than
being guessed in this work item.

## Verification

Primary command:

```bash
python -m unittest discover -s tests -v
```

Final CI evidence for the corrected head is recorded in PR #18 before acceptance.
