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

Live native UX после v3.47-v3.49 дополнен контекстными ScreenTip/SuperTip, явным feedback диагностик, полной русской справкой, reusable base-point clipboard и контекстно-зависимым ПКМ-меню. `Align X/Y` повторно live-квалифицированы на v3.49.

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

- текущий live Editor: **v3.49** (`EnergoLogic.VisioEditorAddinV349`, API `0.3.49`);
- development-bridge functional HEAD: `bb342f472bc3760646998c51007e7ee6a066184f`;
- portable-kit HEAD: `d1f1282d9451c4c6949cb770db502501f294a007`;
- managed extension/package transport: **2026.10.06.153**;
- focused development-bridge Visio suite: **113/113 PASS**;
- P0/R2 и topology-safe Cell Pitch подтверждены live;
- R3 принят live: Replace/Insert, bus editing `6 → 7 → 6`, Reconnect, diagnostics;
- R4 принят live и дополнен: native RibbonX, русские labels/icons, ScreenTip/SuperTip, явные diagnostic results, Help, контекстный ПКМ;
- base-point workflow: отдельные «Копировать с базовой точкой» / «Вставить по базовой точке» / «Переместить по базовой точке», reusable clipboard;
- selected-object workflow принят live:
  - один выбранный shape копируется ровно один;
  - «Копировать выбранное ← / →» использует фактический pitch 40 мм;
  - внутренние связи выбранной группы сохраняются;
  - наружные связи ячейки на копию не переносятся;
  - неполная копия не наследует cell identity;
- геометрические helpers live-qualified:
  - Align X/Y;
  - distribute X/Y;
  - measure distance;
  - snap to 5 мм;
  - nudge 1/5 мм;
- текущая пользовательская `MCP-v2` содержит **68 shapes**; это пользовательское состояние документа. v3.49 acceptance выполнялась только на disposable page — исторические 52 shapes автоматически не восстанавливать;
- Visual Diagnostics сохраняет корректность, но полный scan остаётся около **31.2 с** — performance debt;
- One-user Undo остаётся deferred technical debt;
- offline portable kit **собран и CompileOnly-квалифицирован**:
  - ZIP `EnergoLogic-Visio-Editor-Kit-0.3.49.zip`;
  - size `564814` bytes;
  - SHA-256 `b455c9f95eaecd6ed67066715bd7d61eb9a2b3412e2b8eb5139b87bda139ff07`;
  - 10 личных ГОСТ-трафаретов;
  - third-party VTD files: не включены;
  - manifest + SHA-256 verification: включены;
- полная clean-second-PC / Visio-version matrix qualification остаётся отдельным WS-3 gate;
- PR #12 остаётся **Draft**; Ready/merge только по явной команде владельца.
