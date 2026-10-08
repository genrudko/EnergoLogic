# Программа реализации локального инженерно-оперативного рабочего места EnergoLogic

**Дата архитектурного планирования:** 2026-10-08. **Status:** proposed delivery program (Issue #41), not execution approval or declaration of completion.

## Принцип

Строим **не SCADA**, а автономный Visio-центричный engineering workbench для рисования схем, расчётов, проверки оперативных переключений, РЗА/АПВ и разбора ситуаций. Перенимаем *UX и дисциплину данных*, но не серверную АСУ ТП. Базовые инварианты: одна canonical электрическая модель, русская терминология, Windows 10/11 + Visio 2010—latest, offline standalone packaging, тестируемое headless ядро. Смотри [Product Boundary](PRODUCT-BOUNDARY-AND-WORKSPACE-MODES.md) и [Presentation Contract](OPERATIONAL-STATE-AND-PRESENTATION-CONTRACT.md).

## Актуальные upstream boundaries (не считать merged)

- `main` на 2026-10-08: `f92f89b`, WS-0 V364, WS-6, WS-8, WS-9 foundation accepted; статус смотреть по GitHub и `PROJECT-STATUS`.
- **Draft PR #32**: `ELECTRICAL-CALCULATION-DOMAIN-001` — производственный electrical domain, отдельная приёмка.
- **Draft PR #34**: `OPERATION-PERMISSION-CONTRACT-001` — модель evidence/permission, но не реальные сертифицированные interlocks.
- **Draft PR #36**: `INTEGRATED-PROTECTION-LOOP-001` — headless квалифицированный 3-фазный КЗ→MTЗ→simulated breaker→Visio intent; CI green, **не реальная Visio интеграция**.
- **Stacked Draft PR #38**, base #36: native VTD read-verify-action-read Python callback boundary с разрешающими проверками; real VTD canary выполнялся **отдельно**, не via нового adapter; общая автоматическая live acceptance не пройдена.
- **Issue #39**: индикация/события/replay; **Issue #40**: АПВ. Имеющиеся вопросы не автоматически «закрыты» этой архитектурной программой.

Если контракт upstream не accepted/merged, новый downstream item работает против *явно версионированной fixture/mock*, фиксирует это в документации и не заявляет полную интеграцию. Не стартовать новые параллельные PR, дублирующие существующие #32/#34/#36/#38/#39/#40.

## Работа пакетами (DAG + параллельные пути)

| Пакет | Приоритет | Что выходит | Зависимости и точки принятия |
|---|---|---|---|
| **P0-A — Product/UX decision** (эта работа) | P0 | Назначение, 4 режима, source-of-data ось, contract, benchmark, roadmap | Независим, **docs-only** |
| **P0-B — Visio non-destructive presentation spike** | P0 | Честное решение о технологии overlay/rendering и Undo, сравнение Visio 2010/16, offline feasibility | V364 + единственная disposable fixture; параллельно P0-C |
| **P0-C — Presentation Data Contract v1** | P0 | `PresentationSnapshot/Delta`, value origin/quality, voltage class, terminal colors/unknown, deterministic pure Python tests | WS-6 accepted; PR #36 типизированный adapter/fixture пока не merged; без COM |
| **P0-D — Scenario/Event Store v1** | P0 | isolated scenario, deterministic time/event cursor/replay/Reset, provenance, snapshot persistence/export | WS-6 event timeline accepted; P0-C types согласованы; параллельно P0-B |
| **P0-E — Operative UI v1** (#39) | P0 | Visio Ribbon/panel, выбор источника/режима/палитры, legenda, fault/energized overlay, device card, alarms/event list/replay | P0-B + P0-C + P0-D; визуализацию считать завершённой только live acceptance |
| **P0-F — Calculation/protection → UI** | P0 | карты U/I/P/Q по qualified solver, protection pickup/trip/actual model change, timeline; stale/unsupported cases | PR #32/#36 contract acceptance + P0-C/D/E; gateway #38 integration, site mapping |
| **P1-A — Switching Forms v1** (WS-7) | P1 | модель и печать бланка, проверки исходных условий, step outcomes/reasons, протокол | WS-6 accepted, permission/interlock contracts (#34 + earthing), P0-D; UI после P0-E |
| **P1-B — АПВ v1** (#40) | P1 | deterministic state machine armed/blocked/deadtime/close requested/confirmed/success/fault persistent/lockout | WS-9B + breaker feedback + explicit settings/permission + P0-D; UI after P0-E |
| **P1-C — Site acceptance** | P1 | квалифицированный профиль реального объекта/эталонные расчёты/зависимости, бланки и сценарии | WS-4 site model import, #32 site solver, P0-F + P1-A/B по применимости |
| **P1-D — Offline packaging/compatibility** | P1 | bundled Windows runtime, Visio version/capability matrix, offline installer, project portability | способен идти отдельно от P0-B/C/D, final acceptance with P0-E/F |
| **P2 — Optional advanced** | P2 | COMTRADE import, расширенные РЗА, местные импортеры сигналов, развитые тренды, анализ восстановления питания | только если оправдано рабочими сценариями, с отдельным issue и доказательствами |

### Рекомендуемая первая параллельная волна

```text
        P0-A (this docs PR)
                |
        +-------+----------+-----------------+
        |                  |                 |
  P0-B Visio spike   P0-C Presentation   P0-D scenario timeline
        |                  |                 |
        +------------------+-----------------+
                           |
                      P0-E UI #39
                           |
    +----------------------+---------------------------+
    |                      |                           |
 P0-F solver/RZA      P1-A switching forms       P1-B APV #40
    |                      |                           |
    +----------------------+---------------------------+
                           |
                    P1-C site acceptance
    P1-D packaging/compatibility runs in parallel
```

**Causality:** P0-D может начать event persistence на WS-6 одновременно с P0-C, но интеграцию presentation snapshot делать после согласования DTO. Нельзя делать P1-B зависимым от UI: APV headless state machine самостоятельный, UI лишь его проекция. P1-A не должен обходить required permissions, даже если UI готов.

## P0-B: решающий Visio technology spike

Нельзя закладывать в roadmap «просто наложим слой» как доказанный факт. Рассмотреть и экспериментально сравнить:

1. **Modeless panel + read-only projected values**, без перекрашивания графики — самый безопасный первичный fallback для любой поддерживаемой версии Visio.
2. **Нативный непостоянный визуальный overlay поверх Visio window** — идеальный UX, но провести proof для scrolling/zoom, страниц, выделения, DPI, нескольких окон, печати и 2010 x86/x64.
3. **Документно-временная проекция в отдельной копии** — fallback исключительно при подтверждённом восстановлении документа/Undo и без загрязнения оригинала; требуется различать рабочий оригинал и disposable копию.

На вход: immutable `PresentationSnapshot`; на выход: `ViewProjection`, с `canonical_id`, `page/shape`, рендер-эффектами и возможностью сброса. Оригинальные `.vsdm` в `simulation/replay` не должны получать persistent shape changes. Native action toggles не годятся как механизм `seek`: повторный вызов может изменить положение в противоположную сторону. Для сложных VTD/ГОСТ мастеров нужен read-only квалифицированный binding и safe capability fallback.

**Выход P0-B:** таблица возможностей по API/битности/версии Visio, протокол сравнения стратегий, запись выбранного метода с risks/fallback/known limitations. Только после этого разрешается production overlay integration.

## P0-C/P0-D: нижний слой индикаторов

1. `TerminalStateSample`: tri-state топологической запитанности по каждой стороне аппарата, `source_refs[]`, профиль и provenance.
2. `ElectricalQuantitySample`: explicit unit, type, scope, phase/sequence, solver provenance, age/quality; незаполненное — `unknown`, не `0`.
3. `ScenarioSnapshot`: замороженный canonical/operational/measurement state, logical time, event references, idempotent hash/revision.
4. `EventRecord`: cause chain, request versus confirmation, protection, warnings, APV, numbering; стабильная replay time axis.
5. `PresentationSnapshot/Delta`: данные для Visio HMI, тестируемые без Windows, отдельная voltage/color palette profile. Нет UI-specific значений внутри solver или domain.

Golden fixture v1: две секции 35 кВ с двумя источниками и секционным выключателем, измерения в обеих точках, отключение линии при аварии, альтернативный источник, недостоверный сигнал, заземлитель как отдельная пометка, отказ операции. Фиксировать точные topology/protection fingerprints и набор ожидаемых color tokens/source badges/event IDs; значения расчётов только когда проверены solver.

## MVP вертикальная приёмка для человека (не только CI)

В изолированной Visio схеме КРУ-35 кВ:

1. Выбрать `Моделирование`, явно увидеть «Источник: расчёт/сценарий», источник данных и benchmark/fixture.
2. Исходно одна секция запитана — цвет класса по выбранной палитре; другая секция получает питание от указанного альтернативного источника или обозначается неизвестной, если данных нет.
3. Запустить synthetic qualified 3φ-КЗ; получить рассчитанный Iкз и pickup/operate c timestamps и provenance. Где напряжение не рассчитано — `Нет данных`.
4. Trip requested — отдельная запись; только после simulated position confirmation аппарат отображается открытым и меняется source attribution/color затронутых терминалов.
5. Просмотр карточки выбранного выключателя: причина, время, до/после, параметры, качество, source attribution с обеих сторон.
6. `Пауза/Шаг/Reset` полностью воспроизводят ту же цепочку без изменения оригинального файла и без обратных native toggle side effects.
7. При выключенном/stale solver, unknown topology, запрещённой операции — предупреждение и no false deenergized; ни одна неисполненная команда не становится «выключатель отключён».
8. **АПВ не имитировать** пока state machine #40 не принят. После него отдельные golden сценарии: successful, persistent-fault unsuccessful, blocked/lockout.
9. Закончить сеанс без новых страниц/постоянных меток, подтвердить исходный документ/контакты и Undo. Проверить, что печать и editing baseline не изменились.
10. Провести хотя бы один реальный live Visio acceptance на доступном Windows и тесты headless + матрицу поддерживаемых версий по доступности. Недоступная версия = `NOT QUALIFIED`, не PASS.

## Порог качества и ограничения времени

- Не измерять прогресс числом Draft PR, классов или пройденных unittest. Приёмка — рабочий сценарий диспетчера, инженерный результат, отсутствие артефактов в документах.
- Каждый item имеет bounded вход/выход, versioned contracts, risks, тесты, evidence; исходный test fixture изолирован от пользовательских рабочих схем.
- Все hard dependencies на user-provided normative/site data фиксировать явно. Не превращать недоказанную логику блокировок/АПВ в «одобренные операции».
- Производственные лицензии, реальный SCADA deployment, realtime historian, промышленные протоколы, серверные кластеры **не являются gate** этой программы.

## Связанные задачи / governance

- Issue #39 — simulation indication + event replay (P0-E, P0-C/D staged separately to avoid monolith PR).
- Issue #40 — APV state machine (P1-B).
- PR #32 — electrical calculation domain; PR #34 — operation permission; PR #36 — integrated protection headless; PR #38 — stacked Visio gateway. **Ни один не считать merged без проверки GitHub.**
- Один bounded work item → Issue → branch → Draft PR → CI/live evidence → owner acceptance → merge **только по явной команде**.

Решение owner по составу P0 волн и acceptance оформляется отдельно; сам план **не даёт права** менять рабочий Visio или автоматически управлять электрическими аппаратами.
