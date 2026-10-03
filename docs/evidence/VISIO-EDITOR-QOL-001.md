# VISIO-EDITOR-QOL-001 — live evidence

## Контур проверки

Проверка выполнена на реальном Microsoft Visio через `visio-workstation` и MCP bridge.

Документ:

`KRU-35_normal_scheme_v2_energologic_transformer_v1.vsdx`

Исходная страница:

`MCP-v2`

Исходная страница не использовалась для разрушительных проб. Для мутаций создавались отдельные `QoL-*` страницы-копии.

## Реальная ячейка В-1-35

Полный копируемый состав квалифицированной ячейки:

- 66 — выкатная тележка выключателя `В-1-35`;
- 69 — ТТ;
- 71 — ОПН;
- 73 — ЗН;
- 113 — внутренняя ошиновка;
- 117 — ТТ НП;
- 119 — связь с объектом;
- 247 — служебная/проекционная фигура.

Электрическое Glue-ядро этой же ячейки уже полного визуального состава:

`66 → 69 → 117 → 119`

ОПН/ЗН связаны с внутренней ошиновкой отдельной Glue-компонентой. Фигура 247 электрического Glue не создаёт.

Вывод: CELL нельзя определять только как connected component. В QoL-модели электрическое ядро и визуальный состав ячейки должны быть разными понятиями.

## Anchor и шаг

Anchor квалифицированной ячейки — верхний коммутационный аппарат, реально glued к дочерней native-точке шины.

Для `В-1-35`:

- X anchor = 110.0 мм;
- native bus terminal = `Sheet.103`;
- видимое место шины = `2`;
- `User.nt = 1`;
- Glue = `BeginX → Connections.2.X`.

Для исходной соседней `В-2-35` X = 150.0 мм.

Измеренный pitch:

**40.0 мм**.

Важно: физический порядок мест нельзя выводить как `User.nt ± 1`. На этой же `Шина10` видимое место `1` имеет `User.nt=9`, место `2` — `nt=1`, место `3` — `nt=2`.

Поэтому:

- направление Left/Right определяется по явному номеру места шины;
- `User.nt` используется как native identity точки для Glue;
- неоднозначность должна приводить к fail-closed.

## Native Duplicate

На реальном Visio подтверждено:

1. `Selection.Duplicate()` через pywin32 может выполнить копирование, но вернуть `None`.
2. В этом случае новая selection доступна через `ActiveWindow.Selection`.
3. Visio сам добавляет UI-style paste offset примерно:
   - X: +12.6 мм;
   - Y: -12.6 мм.
4. После измерения и компенсации native offset итоговый сдвиг проверен как:
   - X: **+40.000 мм**;
   - Y: **0.000 мм**;
   - tolerance: 0.01 мм.

## Glue после Duplicate

Native Duplicate сам сохраняет внутренние Glue:

- ТТ → выключатель;
- ОПН → внутренняя ошиновка;
- ЗН → внутренняя ошиновка;
- ТТ НП → ТТ;
- связь с объектом → ТТ НП.

Внешний Glue к главной шине намеренно/фактически не сохраняется.

После явного Glue дубликата верхнего аппарата к `Sheet.105 / Connections.2.X` post-commit `get_connections` подтвердил:

- новый верхний аппарат → новая точка шины;
- все внутренние Glue новой ячейки сохранены.

Это желательное поведение для `Duplicate Cell`: внутреннюю структуру сохраняет native Visio, внешний terminal перепривязывается осознанно.

## Визуальная проверка

PNG рендер страницы после успешного прототипа показал новую ячейку в соседнем 40-мм месте без вертикального сдвига.

SHA-256 PNG evidence:

`627a3fc2b3b247ca4a8c012e91aed56dc90498e83804c2bf9c1b35533bff9652`

## Identity reset на копии

Для новой ячейки введён instance-only metadata row:

`User.EnergoLogicCellId`

Правила:

- строка добавляется только экземплярам фигур новой ячейки;
- VTD master не изменяется;
- исходная ячейка не получает новый ID;
- значение ограничено безопасным токеном 1..128 символов;
- native Duplicate может оставить прежние видимые подписи, но canonical import уже различает исходную и новую ячейку;
- пользовательский `Renumber Cell` остаётся отдельной операцией и не является источником canonical identity.

Live probe `cell:qol-v2-probe` подтвердил `User.EnergoLogicCellId` на всех 8 новых shape instances. У исходного shape 66 такой строки после операции нет.

Canonical mapping остаётся backward-compatible: старые фигуры без `EnergoLogicCellId` используют прежнюю text-derived identity; новые/управляемые фигуры включают explicit cell identity в material canonical element ID.

## Transaction rollback и пользовательский Undo

Внутренний rollback открытого UndoScope подтверждён: при ошибке внутри compound operation созданные фигуры удаляются целиком.

При этом отдельное требование «один пользовательский Ctrl+Z после успешно завершённой внешней Automation-команды» **не подтверждено и сейчас считается ограничением внешнего bridge path**.

Проверено:

- `Application.UndoEnabled = true`;
- `Document.UndoEnabled = true`;
- `CurrentScope = -1` вне операции;
- `Application.Undo()` после commit не меняет документ;
- штатная UI-команда `DoCmd(visCmdEditUndo)` после commit также не меняет документ;
- тот же эффект воспроизводится не только на Duplicate, но и на простом внешнем `move_shape` + 1 мм.

Вывод: проблема не специфична для `Duplicate Cell`. Мутации через текущий внешний Automation bridge не попадают в обычный пользовательский undo stack Visio.

Архитектурное следствие:

- внешний bridge остаётся executor/qualification backend;
- аварийный rollback compound operation сохраняется;
- требование «один Ctrl+Z» переносится в in-Visio command host: Ribbon/add-in/VBA host или custom Visio UndoUnit;
- это не должно блокировать детерминированный QoL planner и остальные P0-функции.

## Реализованный pure planner

EnergoLogic теперь разделяет:

- `VisioCellAnchor` — native привязка ячейки к шине;
- `VisioCell.electrical_core_shape_ids` — только Glue-топология;
- `VisioCell.member_shape_ids` — полный копируемый проекционный состав;
- `DuplicateCellPlan` — transport-neutral план Exact Offset + target bus terminal + identity reset requirement.

Fail-closed условия включают:

- отсутствующий/неоднозначный bus Glue;
- отсутствующий `User.nt`;
- отсутствующий/неоднозначный видимый slot;
- занятый target terminal;
- неоднозначную геометрическую границу ячейки;
- несовпадение явно указанного terminal с направлением Left/Right.

Геометрическое попадание фигуры в CELL никогда не создаёт электрическую связь.


## Exact Move Cell — live qualification

На отдельной странице `QoL-Move-Probe-32` исходная ячейка `В-1-35` была перенесена с видимого места 2 на место 3.

Итоговые координаты anchor:

- было: X = 110.0 мм;
- стало: X = 150.0 мм;
- точный сдвиг: **+40.0 мм**;
- вертикальный сдвиг: **0.0 мм**.

После операции:

- старый внешний Glue к `Sheet.103` отсутствует;
- новый внешний Glue: `shape 66 BeginX → Sheet.105 Connections.2.X`;
- внутренние Glue сохранены:
  - 69 → 66;
  - 71 → 113;
  - 73 → 113;
  - 117 → 69;
  - 119 → 117.

То есть Move Cell реализуется как предметная операция:

`detach old bus terminal → exact move whole cell → glue new bus terminal`

а не как ручное перетаскивание отдельных фигур.

## Repair Glue — live qualification

На отдельной странице `QoL-Glue-Repair` был намеренно создан опасный случай:

- endpoint верхнего аппарата оставлен **точно в тех же page coordinates**;
- native Glue к шине удалён.

Внешне схема при этом выглядит соединённой, но электрического `Connects` нет.

После Repair Glue выбран точный native candidate:

`Sheet.105 / Connections.2.X`

и post-check подтвердил настоящий:

`shape 66 BeginX → Sheet.105 Connections.2.X`.

Это live-доказательство инварианта проекта:

**геометрическое совпадение ≠ электрическая связь**.

## Scheme Doctor — минимальный детерминированный слой

Добавлен pure Scheme Doctor, который уже умеет детерминированно сообщать:

- `visual_touch_without_glue` — endpoint находится у единственной native connection point, но реального Glue нет;
- `ambiguous_visual_touch_without_glue` — рядом несколько кандидатов, автоисправление запрещено;
- `bus_pitch_mismatch` — геометрия native bus slots не соответствует заданному pitch;
- `duplicate_bus_slot`;
- `duplicate_bus_terminal_nt`;
- `duplicate_cell_identity` — один `EnergoLogicCellId` используется несколькими независимыми bus anchors;
- ошибки некорректной explicit identity.

Проверка отделена от исправления: Doctor только диагностирует; Repair Glue остаётся отдельным явным действием.

## Финальная проверка внешнего Ctrl+Z

После перехода Duplicate на штатную UI-команду Visio и отдельной отправки **реального Ctrl+Z** в корневое окно Visio:

- Ctrl+Z был физически отправлен успешно;
- `UndoEnabled = true`;
- документ до Ctrl+Z: 52 shapes;
- документ после одного Ctrl+Z: 52 shapes.

То есть ограничение внешнего Automation path подтверждено уже не только COM/API-командой Undo, но и настоящим клавиатурным Ctrl+Z.

Требование одного пользовательского Undo поэтому остаётся задачей для **in-Visio command host/custom UndoUnit** и не маскируется bridge-эмуляцией.
