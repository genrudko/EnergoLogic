# TERMINOLOGY-REGISTRY-V1-001 — evidence and terminology decisions

Status: **Implementation complete in Draft; owner terminology decisions pending**  
Issue: **#17**  
Draft PR: **#18**  
Branch: `terminology/terminology-registry-v1-001`  
Base: `main@9edc59a0e83f17e94c50ca10f7feac320332b2a1`

## Repository boundary evidence

The WS-2 branch was created directly from `main`, not from
`visio/visio-editor-qol-001`.

The branch changes only terminology schema/runtime/data/tests/documentation and
package-data configuration. It does not modify VISIO-EDITOR-QOL-001 implementation
files.

## Implemented contract

- versioned machine-readable registry;
- versioned JSON Schema;
- deterministic stdlib-only runtime validation;
- stable concept ID + unique code identifier checks;
- exactly one scalar canonical RU term and one scalar canonical EN term per concept;
- aliases and abbreviations separated from canonical terminology;
- deprecated/forbidden aliases with explicit rationale;
- source edition/status + per-concept clause/term/IEV locator provenance;
- semantic-binding collision protection for already accepted EnergoLogic semantics;
- lookup by concept ID, code identifier and RU/EN wording;
- alias/abbreviation lookup with match-kind reporting;
- ambiguity-safe domain-aware resolution;
- terminology lint;
- package-data delivery of the default registry.

Initial registry: **40 concepts / 18 normative source records**.

## Normative decision matrix

| Concept | Registry decision | Evidence / locator | Lifecycle |
|---|---|---|---|
| circuit-breaker | RU `выключатель`; EN `circuit-breaker`; «автоматический выключатель» retained as alias | ГОСТ Р 52565-2006 title/scope vs ГОСТ IEC 60050-441-2015, 441-14-20 | **provisional** — current sources differ by scope |
| disconnector | `разъединитель` / `disconnector` | ГОСТ IEC 60050-441-2015, 441-14-05 | accepted |
| earthing switch | proposed RU `заземляющий выключатель`; EN `earthing switch`; «выключатель заземления» alias | ГОСТ IEC 60050-441-2015, 441-14-11 vs ГОСТ Р 57190-2016, 01-12-11 | **provisional** — two current Russian normative forms |
| legacy earthing-switch «заземлитель» | deprecated alias only | superseded ГОСТ Р МЭК 60050-441-2012, 441-14-11 | legacy compatibility only |
| earth electrode | `заземлитель` / `earth electrode` | ГОСТ 24291-90, term 47 / IEV 604-04-05 | accepted |
| load-break switch | `выключатель нагрузки` / `load-break switch` | ГОСТ 17717-79 plus current switchgear vocabulary | provisional — English preferred-form scope remains to be pinned |
| fuse | `плавкий предохранитель` / `fuse` | ГОСТ IEC 60050-441-2015, 441-18-01 | accepted |
| current transformer | `трансформатор тока` / `current transformer` | ГОСТ Р МЭК 61869-2-2015, 3.1.201 / IEV 321-02-01 | accepted |
| voltage transformer | `трансформатор напряжения` / `voltage transformer` | ГОСТ IEC 61869-3-2012, 3.1.301 / IEV 321-03-01 | accepted |
| power transformer | `силовой трансформатор` / `power transformer` | ГОСТ Р 52719-2007 | accepted |
| station-service transformer | `трансформатор собственных нужд` / `station service transformer` | ГОСТ Р 52719-2007 for Russian equipment class | provisional — primary international preferred-term evidence remains incomplete |
| busbar | power-domain RU `сборная шина`; EN `busbar`; generic «шина» alias | ГОСТ Р 55190-2022, 3.1.44; supporting IEV 151-12-30 | provisional — wider non-KRU scope still needs explicit domain boundary |
| busbar section | `секция шин` / `busbar section` | ГОСТ 24291-90, term 44 / IEV 605-02-08 | accepted |
| busbar system | `система сборных шин` / `busbars` | ГОСТ 24291-90, term 41 / IEV 605-02-02 | accepted |
| feeder bay / connection | `присоединение распределительного устройства` / `feeder bay` | ГОСТ 24291-90, term 34 / IEV 605-02-10 | accepted |
| bay / cell | `ячейка` / `bay` | ГОСТ 24291-90, term 35 / IEV 605-02-09 | accepted |
| terminal | `вывод` / `terminal` | ГОСТ IEC 60050-151-2014, 151-12-12 | accepted |
| short-circuit | `короткое замыкание` / `short-circuit` | ГОСТ IEC 60050-151-2014 | accepted |
| overcurrent protection | `максимальная токовая защита` / `overcurrent protection` | IEV 448-14-26 | accepted |
| earth-fault protection | `защита от замыканий на землю` / `earth-fault protection` | IEV 448-14-28 | accepted |
| switch state | RU operational `включенное положение` / `отключенное положение`; IEV mechanical forms remain aliases | Приказ Минэнерго России №757, ред. 06.07.2026; supporting IEV 441-16-22/23 | accepted for EnergoLogic operational UI |
| switch operation | RU operational `включение` / `отключение`; IEV `замыкание` / `размыкание` remain aliases | Приказ Минэнерго России №757, ред. 06.07.2026; supporting IEV 441-16-08/09 | accepted for EnergoLogic operational UI |
| energized / de-energized | `под напряжением` / `обесточенный` | ГОСТ IEC 60050-651-2014, 651-01-14/15 | **provisional** — source is live-working scoped; traversal predicate belongs to later operational semantics |

## Important architecture findings

### Text is not identity

The Russian string «заземлитель» is a real normative homonym across historical/current
contexts:

- current power-system terminology uses it for an `earth electrode`;
- a superseded switchgear vocabulary used it for an `earthing switch`.

Therefore canonical terms are not globally unique keys. `lookup()` may return
multiple concepts, while `resolve_unique()` fails closed unless domain qualification
removes the ambiguity.

### «Присоединение» is not generic `feeder`

ГОСТ 24291-90 distinguishes:

- `присоединение распределительного устройства` — `feeder bay`;
- `ячейка` — `bay`.

The registry keeps them as separate concepts instead of collapsing them into one
frontend convenience term.

### Physical terminal vs topology abstraction

For a physical electrical terminal the Russian canonical IEV term is `вывод`.
Literal `электрический терминал` is marked forbidden.

The canonical model's abstract graph concepts `ElectricalNode` and
`ElectricalConnection` remain provisional where terminology depends on the final
WS-1 topology contract; terminology work does not redefine that electrical semantics.

### Operational wording takes precedence in the Russian UI scope

For EnergoLogic's operational power-system UI, current Russian switching rules support
`включение/отключение` and `включенное/отключенное положение`.

The generic IEV mechanical concepts
`замыкание/размыкание` and
`замкнутое/разомкнутое положение` remain valid aliases/supporting terminology rather
than replacing the operational UI vocabulary.

## Owner decisions still required

Two current-source conflicts are intentionally not hidden:

1. **Circuit-breaker Russian canonical UI term**
   - current generic ГОСТ IEC 60050-441-2015: «автоматический выключатель»;
   - current Russian HV equipment ГОСТ Р 52565-2006 (3–750 kV): «выключатель».
   - current registry proposal for the EnergoLogic power/HV domain: **«выключатель»**;
     «автоматический выключатель» remains an alias.

2. **Earthing-switch Russian canonical UI term**
   - current ГОСТ IEC 60050-441-2015: **«заземляющий выключатель»**;
   - current ГОСТ Р 57190-2016: **«выключатель заземления»**.
   - current registry proposal: **«заземляющий выключатель»**;
     «выключатель заземления» remains an alias;
     historical «заземлитель» is deprecated for this concept because current
     power-system terminology also uses «заземлитель» for `earth electrode`.

Other provisional entries are evidence/domain-contract gaps rather than choices that
should be guessed in this PR. They can be tightened continuously in WS-2 without
changing accepted electrical semantics.

## Existing canonical semantics preserved

Semantic bindings protect:

- `energologic.element.kind = circuit_breaker`;
- `energologic.element.kind = disconnector`;
- `energologic.element.kind = current_transformer`;
- `energologic.element.kind = bus`;
- `energologic.switch_state = open`;
- `energologic.switch_state = closed`.

The validator rejects a second terminology concept claiming the same
namespace/value pair.

No existing `electrical-v1`, `switching-state-v1` or transformer behavior is
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

Implementation head `16b3ea6f73a8cd2a60c5e0ae950a8cb6329c88e8`:
CI run **37204617645 — SUCCESS**.

Earlier registry/lint checkpoint `2c97e95`:
CI run **37204111193 — SUCCESS**.
