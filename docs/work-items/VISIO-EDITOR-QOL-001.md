# VISIO-EDITOR-QOL-001

Status: Functional implementation accepted live; owner review/merge pending  
Issue: #11

## Цель

Сделать Visio удобным инженерным frontend'ом EnergoLogic: сократить ручные copy/paste/move/align/glue/rename операции и заменить их предметными командами.

Visio остаётся редактором и средством визуализации. Каноническая электрическая модель остаётся source of truth.

## Архитектурные правила

QoL-слой оперирует понятиями:

- CELL;
- EQUIPMENT;
- TERMINAL;
- BUS;
- ANCHOR;
- CONNECTION.

Электрическая связь существует только как реальный Glue и/или canonical terminal↔node mapping. Геометрическое совпадение — только подсказка или кандидат для repair.

Bounding box не является единственным anchor. Для ячейки нужен предметный anchor/base point.

VTD masters массово не переписываются. Сначала adapter/QoL extension.

## План работ

### R0 — исследование ✅

Проверить по официальной документации и на реальном Visio:

- Selection / Duplicate / Copy-Paste / Move;
- units / coordinates;
- Groups / nested shapes;
- Glue / Connection Points / Connects;
- Snap / Guides / Layers;
- Align / Distribute;
- Undo scopes;
- Events;
- Ribbon / context menu;
- возможности текущего visio-bridge.

На реальной `MCP-v2` зафиксировать:

- состав полноценной ячейки;
- внутренние связи;
- внешний Glue к шине;
- cell pitch;
- координатную систему;
- устойчивый anchor;
- VTD groups / Actions / ShapeSheet.

### R1 — главный P0 benchmark ✅

Сделать первую рабочую команду:

- Duplicate Cell Right;
- Duplicate Cell Left.

Она должна:

1. определить состав ячейки;
2. сохранить внутренние Glue;
3. определить pitch;
4. создать копию без произвольного смещения;
5. сохранить вертикальную ось;
6. определить bus terminal;
7. сделать настоящий Glue к шине;
8. выдать новую identity;
9. проверить результат;
10. выделить новую ячейку;
11. откатываться одним Undo.

### R2 — остальные P0 ✅

- [x] Copy with Base Point — pure planner + exact bridge request; external electrical Glue и managed identity обрабатываются fail-closed;
- [x] Move with Base Point — pure planner для свободного selection + отдельный cell-aware Move Cell;
- [x] Exact Offset в мм — pure planner + bridge primitive + deterministic verification;
- [x] Auto Glue to Bus для квалифицированного cell anchor;
- [x] Repair Glue: Find → Preview → Fix — pure planner + live repair;
- [x] Electrical Align — exact PinX/PinY planner для свободных shapes; glued equipment generic Align намеренно блокирует;
- [x] Cell Pitch: measure / set / distribute — measure + deterministic distribution planner по реальным native bus slots;
- [x] минимальный Scheme Doctor для Glue/pitch/identity structural checks.

Copy/Move with Base Point, Exact Offset, Smart Nudge, Coordinates, Align X/Y, Select Cell, Renumber Cell, Measure Pitch и Cell Pitch distribute прошли live acceptance в реальном Visio. В v3.18 topology-safe distribute принят на TSN cell: bus anchor восстанавливается первым внешним COM-helper'ом, внутренние VTD Glue — после него; итоговый `244.End → 166/Connections.1` подтверждён native `Connects` и обеими ShapeSheet-формулами.

### R3 — P1 ✅

- [x] Logical Cell Membership / cell_id;
- [x] Select Cell;
- [x] Duplicate with Identity Reset;
- [x] safe Renumber Cell;
- [x] Replace Equipment;
- [x] Insert Equipment into Existing Connection;
- [x] Extend Bus;
- [x] Trim / Extend / Reconnect;
- [x] Smart Nudge;
- [x] Coordinates Panel;
- [x] Scheme Doctor;
- [x] Visual Diagnostics.

Live R3 acceptance включает штатное изменение VTD bus Shape Data `6 → 7 → 6` при неизменном pitch 40 мм и восстановление реального `244.End → 166/Connections.1` через `Reconnect End`.

### R4 — P2 ✅

- [x] native EnergoLogic RibbonX;
- [x] native Visio context menu;
- [x] keyboard access через Ribbon KeyTips без глобального Windows hook;
- [x] presets, включая 5-мм nudge и Cell Pitch 40 мм;
- [x] parameter panel открывается только по явной команде;
- [x] legacy toolbar скрыт и оставлен только как recovery path.

Live `ui_status` финального v3.45:
`Ribbon=loaded; ContextMenu=installed; ContextHosts=Drawing Page Selected,Drawing Object Selected; Panel=hidden; FallbackToolbar=hidden`.

## Transaction safety

Сложная пользовательская операция должна по возможности открывать один Visio Undo scope.

Если операция выполнилась частично, она не должна оставлять поломанный промежуточный результат.

Live-квалификация подтвердила rollback внутри открытого scope, но показала, что текущий внешний Automation bridge не добавляет успешно завершённые мутации в обычный пользовательский undo stack Visio. Это воспроизводится даже на одиночном `move_shape`, поэтому не является дефектом алгоритма Duplicate Cell.

Дополнительно подтверждено: отдельный VBA-host можно установить в изолированную macro-enabled `.vsdm` копию, но запуск его процедуры через внешний `Document.ExecuteLine` всё ещё не создаёт пользовательский Undo.

Дальнейшая квалификация показала более жёсткую границу:

- explicit `IVBUndoUnit` через внешний bridge добавляется, но ни физический Ctrl+Z, ни `Application.Undo()` не вызывают ожидаемый откат;
- classic COM add-in с Ribbon XML оказался небезопасным при startup-load и был полностью удалён после qualification crashes;
- отдельный command-bar-only COM add-in без `IRibbonExtensibility`, с `LoadBehavior=0`, стабильно подключается после старта Visio;
- его `CommandBarButton.Execute()` реально выполняет Duplicate внутри add-in (`44 → 52`), но последующий физический Ctrl+Z оставляет `52`;
- попытка физически кликнуть кнопку синхронно из активного bridge COM-вызова приводит к reentrancy deadlock.

One-user-Undo больше не блокирует завершение Editor UI: исследование зафиксировано как отдельный технический хвост. Topology blocker Cell Pitch закрыт live в v3.18; текущая работа возвращается к R3/R4 — пользовательскому функционалу и polish.

## Acceptance benchmark

На реальной `MCP-v2`:

Исходно есть корректная ячейка, подключённая к шине.

Пользователь выполняет `Duplicate Cell Right`.

Без ручной доводки:

- копия появляется точно справа;
- ось совпадает;
- pitch корректен;
- внутренние Glue сохранены;
- верхний terminal реально glued к шине;
- случайного смещения нет;
- identity новая;
- исходная ячейка не изменена;
- Scheme Doctor не показывает structural errors;
- один Ctrl+Z откатывает всё действие.

## Метрика успеха

Сравнить штатный workflow:

`copy → paste → move → align → repair connection → rename`

с:

`Duplicate Cell Right`

Цель — убрать ручные действия, а не просто добавить команды.

## Ограничения

Не смешивать с Planner / RZA / CIM / pandapower.

Merge и Ready for Review — только по явной команде владельца.

## Evidence

Подробный live evidence: `docs/evidence/VISIO-EDITOR-QOL-001.md`.

Текущее состояние:

- текущий live Editor: **v3.45** (`EnergoLogic.VisioEditorAddinV345`, API `0.3.45`);
- текущий managed bridge: **2026.10.04.145**; development-bridge HEAD `946c55441761f6e510bef5d6dc44c9e7373fde93`;
- focused development-bridge Visio suite: **89/89 PASS**;
- P0/R2 и topology-safe Cell Pitch подтверждены live;
- R3 принят live: Replace/Insert, bus editing `6 → 7 → 6`, Reconnect, diagnostics;
- R4 принят live: native RibbonX, Visio right-click submenu в contexts `9` и `75`, Ribbon KeyTips/presets, hidden fallback toolbar;
- реальный pitch шины: **40 мм**;
- TSN cell anchor `155` корректно раскрывается в 11 top-level members: `[155,158,160,162,166,182,240,242,244,249,250]`;
- финальная `Visual Diagnostics` на контрольной странице: **structural-проблем не найдено**;
- полный diagnostic scan в текущем COM path занимает около **31.2 с** — performance debt, не повод менять доказанную topology semantics;
- исходная `MCP-v2` после финальной acceptance по-прежнему содержит **52 shapes**;
- One-user Undo остаётся deferred technical debt;
- PR #12 остаётся **Draft**; Ready/merge только по явной команде владельца.
