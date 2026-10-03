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

- Copy with Base Point;
- [x] Move with Base Point / Move Cell to adjacent native slot;
- [x] Exact Offset в мм — bridge primitive + deterministic verification;
- [x] Auto Glue to Bus для квалифицированного cell anchor;
- [x] Repair Glue: Find → Preview → Fix — pure planner + live repair;
- Electrical Align;
- Cell Pitch: measure / set / distribute — measure already implemented;
- [x] минимальный Scheme Doctor для Glue/pitch/identity structural checks.

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

Live-квалификация подтвердила rollback внутри открытого scope, но показала, что текущий внешний Automation bridge не добавляет успешно завершённые мутации в обычный пользовательский undo stack Visio. Это воспроизводится даже на одиночном `move_shape`, поэтому не является дефектом алгоритма Duplicate Cell. Для финального требования «один Ctrl+Z» нужен in-Visio command host/custom UndoUnit.

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

- R0 исследование реального Visio/MCP-v2 — выполнено;
- exact native duplicate с компенсацией скрытого paste offset — подтверждён;
- pitch 40 мм — подтверждён;
- внутренние Glue после native Duplicate — подтверждены;
- явный Glue новой ячейки к следующей native bus terminal — подтверждён;
- визуальный результат — подтверждён PNG snapshot;
- fail-safe rollback при ошибке — подтверждён;
- pure CELL/ANCHOR/Duplicate plan — реализован и покрыт тестами;
- instance-only identity reset через `User.EnergoLogicCellId` — реализован и подтверждён live;
- пользовательский Renumber Cell — ещё не реализован;
- Move Cell Right + exact detach/re-glue — подтверждён live;
- Repair Glue на визуально совпадающем, но electrically disconnected endpoint — подтверждён live;
- минимальный Scheme Doctor — реализован;
- один пользовательский Ctrl+Z — требует in-Visio host/custom UndoUnit; внешний bridge этого не обеспечивает даже при реальной отправке Ctrl+Z.
