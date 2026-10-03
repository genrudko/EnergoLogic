# VISIO-EDITOR-QOL-001

Status: In progress  
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

### R1 — главный P0 benchmark — In progress

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

### R2 — остальные P0 — In progress

- [x] Copy with Base Point — pure planner + exact bridge request; external electrical Glue и managed identity обрабатываются fail-closed;
- [x] Move with Base Point — pure planner для свободного selection + отдельный cell-aware Move Cell;
- [x] Exact Offset в мм — pure planner + bridge primitive + deterministic verification;
- [x] Auto Glue to Bus для квалифицированного cell anchor;
- [x] Repair Glue: Find → Preview → Fix — pure planner + live repair;
- [x] Electrical Align — exact PinX/PinY planner для свободных shapes; glued equipment generic Align намеренно блокирует;
- [x] Cell Pitch: measure / set / distribute — measure + deterministic distribution planner по реальным native bus slots;
- [x] минимальный Scheme Doctor для Glue/pitch/identity structural checks.

Copy/Move with Base Point, Exact Offset, Smart Nudge, Coordinates, Align X/Y, Select Cell, Renumber Cell и измерение шага уже прошли live acceptance в реальном Visio. Cell Pitch distribute остаётся незакрытым только по topology-safety: геометрия 40 мм работает, но восстановление одного внутреннего VTD Glue edge ещё требует ремонта.

### R3 — P1

- Logical Cell Membership / cell_id;
- Select Cell;
- Duplicate with Identity Reset;
- safe Renumber Cell;
- Replace Equipment;
- Insert Equipment into Existing Connection;
- Extend Bus;
- Trim / Extend / Reconnect;
- Smart Nudge;
- Coordinates Panel;
- Scheme Doctor;
- Visual Diagnostics.

### R4 — P2

- EnergoLogic Ribbon/toolbar;
- context menu;
- keyboard shortcuts;
- presets.

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

One-user-Undo больше не блокирует завершение Editor UI: исследование зафиксировано как отдельный технический хвост. Текущий acceptance blocker — только topology-safe завершение Cell Pitch distribute на реальной VTD-ячейке.

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

- текущий live Editor: **v3.13** (`EnergoLogic.VisioEditorAddinV313`, API `0.3.13`);
- текущий managed bridge: **2026.10.03.111**; bridge branch HEAD `05a877e`;
- Coordinates, Copy/Move with Base Point, Exact Offset, Smart Nudge, Align X/Y, Select Cell, Renumber Cell, Duplicate/Move Cell, Repair Glue, Scheme Doctor и Measure Pitch — подтверждены live;
- реальный pitch шины: **40 мм**;
- TSN cell anchor `155` корректно раскрывается в 11 top-level members: `[155,158,160,162,166,182,240,242,244,249,250]`;
- Cell Pitch distribute в v3.13 разделён на geometry phase и explicit topology-completion phase с operation status;
- deliberate 10-second delay между phase 1 и phase 2 **не устраняет** дефект; гипотеза «VTD просто не успевает стабилизироваться» отвергнута;
- точный remaining failure: `244.End → 166/Connections.1`;
- после failure endpoint остаётся half-glued: `EndX = 190 mm`, а `EndY = PAR(PNT(ТСН2!Connections.1.X,ТСН2!Connections.1.Y))`;
- тот же edge на той же странице немедленно восстанавливается low-level `batch_glue_endpoints`, после чего `get_connections` подтверждает настоящий `244.EndX → 166/Connections.1.X`;
- следовательно, native `GlueTo` и connection point исправны; дефект локализован в C# add-in restoration/detach path, а не в тайминге;
- исходная `MCP-v2` не мутируется; acceptance выполняется только на disposable copies;
- Undo остаётся deferred technical debt и не должен снова вытеснять работу над пользовательским Editor;
- PR #12 остаётся **Draft**; Ready/merge только по явной команде владельца.
