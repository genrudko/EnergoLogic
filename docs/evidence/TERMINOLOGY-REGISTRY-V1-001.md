# TERMINOLOGY-REGISTRY-V1-001 — evidence and terminology decisions

Status: **Draft evidence**  
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
- terminology lint;
- package-data delivery of the default registry.

Initial registry: **40 concepts**, including an explicit `earth electrode` concept to
prove and safely handle the real «заземлитель» homonym.

## Normative decision matrix

| Concept | Registry decision | Evidence / locator | Status |
|---|---|---|---|
| circuit-breaker | RU `выключатель`; EN `circuit-breaker`; «автоматический выключатель» retained as alias | ГОСТ Р 52565-2006 title/scope vs ГОСТ IEC 60050-441-2015, 441-14-20 | provisional — domain policy needed |
| disconnector | `разъединитель` / `disconnector` | ГОСТ IEC 60050-441-2015, 441-14-05 | accepted |
| earthing switch | `заземляющий выключатель` / `earthing switch` | ГОСТ IEC 60050-441-2015, 441-14-11 | provisional while UI convention is owner-reviewed |
| legacy earthing-switch «заземлитель» | deprecated alias only | superseded ГОСТ Р МЭК 60050-441-2012, 441-14-11 | legacy |
| earth electrode | `заземлитель` / `earth electrode` | ГОСТ 24291-90, term 47 | accepted |
| fuse | `плавкий предохранитель` / `fuse` | ГОСТ IEC 60050-441-2015, 441-18-01 | accepted |
| current transformer | `трансформатор тока` / `current transformer` | ГОСТ Р МЭК 61869-2-2015, 3.1.201 / IEV 321-02-01 | accepted |
| voltage transformer | `трансформатор напряжения` / `voltage transformer` | ГОСТ IEC 61869-3-2012, 3.1.301 / IEV 321-03-01 | accepted |
| busbar | `шина` / `busbar`; «сборная шина» alias | ГОСТ IEC 60050-151-2014, 151-12-30 | provisional — UI policy needed |
| feeder bay / connection | `присоединение распределительного устройства` / `feeder bay` | ГОСТ 24291-90, term 34 / IEV 605-02-10 | accepted |
| bay / cell | `ячейка` / `bay` | ГОСТ 24291-90, term 35 / IEV 605-02-09 | accepted |
| terminal | `вывод` / `terminal` | ГОСТ IEC 60050-151-2014, 151-12-12 | accepted |
| switch closed/open state | `замкнутое положение` / `разомкнутое положение` | ГОСТ IEC 60050-441-2015, 441-16-22 / 441-16-23 | accepted |
| closing/opening operation | `замыкание` / `размыкание` | ГОСТ IEC 60050-441-2015, 441-16-08 / 441-16-09 | accepted |
| energized/de-energized | `под напряжением` / `обесточенный` | ГОСТ IEC 60050-651-2014, 651-01-14 / 651-01-15 | accepted within source scope |

## Important non-decisions

The registry deliberately keeps several entries `provisional` instead of hiding
unresolved scope questions.

1. **Circuit-breaker Russian UI term.** Current generic IEV-derived terminology says
   «автоматический выключатель», while current Russian HV equipment standard
   ГОСТ Р 52565-2006 consistently names 3–750 kV circuit-breakers «выключатели».
2. **Busbar UI wording.** IEV canonical is «шина»; power-station/operator usage often
   qualifies it as «сборная шина».
3. **Electric/cable line English naming.** ГОСТ 24291-90 and current IEV 151 use
   different scope-sensitive English forms; the project needs an explicit domain rule.
4. **Station-service transformer English canonical wording.** Russian equipment class
   is supported; English preferred form still needs a primary terminology source.
5. **RPA umbrella English term, instantaneous overcurrent and arc protection.**
   Russian usage is clear enough to model provisionally, but primary IEC preferred-term
   evidence is incomplete.
6. **UI inflection for switch commands/states.** Normative concept names are
   «замкнутое/разомкнутое положение» and «замыкание/размыкание». Conventional UI
   labels «Включен/Отключен» and «Включить/Отключить» are represented as aliases,
   pending presentation-policy approval.

## Existing canonical semantics preserved

Semantic bindings currently protect:

- `energologic.element.kind = circuit_breaker`;
- `energologic.element.kind = disconnector`;
- `energologic.element.kind = current_transformer`;
- `energologic.element.kind = bus`;
- `energologic.switch_state = open`;
- `energologic.switch_state = closed`.

A second terminology concept cannot claim one of those namespace/value pairs.

No existing `electrical-v1`, `switching-state-v1` or transformer behavior was
changed by this work item.

## Verification

Primary command:

```bash
python -m unittest discover -s tests -v
```

GitHub Actions matrix:

- Ubuntu latest / Python 3.11;
- Ubuntu latest / Python 3.12;
- Windows latest / Python 3.11;
- Windows latest / Python 3.12.

At the first registry+lint regression checkpoint (commit `2c97e95`), CI run
`37204111193` completed **SUCCESS**.

A final CI result for the documentation/final-validation head must be recorded before
owner acceptance.
