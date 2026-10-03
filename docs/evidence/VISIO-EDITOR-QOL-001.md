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


## Остальные P0 planners

После live-квалификации Duplicate/Move/Repair Glue добавлены детерминированные transport-neutral planners.

### Copy with Base Point

Поддерживается инженерный workflow:

`selection + base point + target point → exact dx/dy`.

Защитные правила:

- пустой/дублированный selection запрещён;
- child shapes нельзя случайно использовать вместо top-level engineering object;
- selection с внешним native Glue generic Copy не копирует молча — требуется предметный Duplicate Cell / Auto Glue;
- managed selection с `User.EnergoLogicCellId` требует явный новый `cell_id`;
- selection с несколькими managed cell identities блокируется.

Исполнение транслируется в уже квалифицированный `duplicate_shapes_exact`.

### Move with Base Point / Exact Offset

Для свободного selection поддержаны:

- base point → target point;
- прямой `dx_mm/dy_mm` Exact Offset.

Если selection имеет внешний electrical Glue, generic move блокируется и требует cell-aware detach/move/re-glue.

Для подключённых ячеек отдельный `MoveCellPlan` уже квалифицирован live.

### Electrical Align

Добавлен exact alignment по Visio reference point:

- axis X → `PinX`;
- axis Y → `PinY`;
- reference shape либо явная engineering coordinate.

Generic Align намеренно отказывается двигать shape, участвующий в native Glue. Для electrical equipment выравнивание должно выполняться через cell/bus-aware операцию, а не косметическим сдвигом.

### Cell Pitch distribute

Добавлен planner распределения выбранных ячеек по native bus slots.

Он:

- использует реальный slot order, а не `User.nt ± 1`;
- требует существующие native connection points;
- проверяет, что геометрия bus slots действительно поддерживает заданный pitch;
- блокирует занятые target slots;
- строит explicit MoveCell detach/move/re-glue requests;
- не создаёт фиктивные электрические точки ради красивой геометрии.

Live measure 40 мм уже подтверждён. Live apply/distribute ещё не квалифицирован.

## In-Visio host qualification

На рабочем Microsoft Visio подтверждено:

- `VBAEnabled = true`;
- macros target document enabled;
- VBE project доступен;
- COM Add-ins collection доступна.

Создана отдельная qualification copy:

`KRU-35_normal_scheme_v2_energologic_qol_host_v1.vsdm`.

В неё без изменения VTD stencil projects успешно установлен фиксированный модуль:

`EnergoLogicQolHost`.

Probe `UndoProbeDuplicate40` выполняет native Duplicate + exact Move внутри одного `BeginUndoScope/EndUndoScope`.

### Внешний ExecuteLine всё ещё не является user-context

При запуске VBA через внешний:

`Document.ExecuteLine("EnergoLogicQolHost.UndoProbeDuplicate40")`

операция реально выполнилась:

- shapes before: 44;
- after VBA duplicate: 52.

Но один физический `Ctrl+Z`, отправленный в корневое окно Visio, оставил:

- before Undo: 52;
- after Undo: 52.

Следовательно, перенос кода в VBA сам по себе проблему не решает. Критичен именно контекст запуска команды.

### Реальный Visio Macros UI

Добавлен bounded qualification path:

`Alt+F8 → fixed UndoProbeDuplicate40 → Run`.

Инструмент не принимает произвольное имя макроса или произвольные клавиши.

Версии `.36/.37` не дошли до запуска VBA из-за ошибок автоматизированного ввода фиксированного имени макроса. `.38` исправляет ввод прямыми ASCII virtual-key events с учётом Caps Lock и проходит bridge unit/contract tests.

Live qualification `.38` сейчас не завершена: после managed update running Visio add-in перестал публиковать `OpenAI Visio Live Application v4` в ROT. Windows node/agent остаётся online и tool catalog доступен, но любой Visio document call fail-closed с сообщением о missing live publication. Для продолжения требуется восстановить local Visio agent/add-in binding; Visio document restart не является частью planned recovery.

## Текущий CI

EnergoLogic head `742848bd355f39bef57986f92a73a527ebb1ed23`:

- CI run `37124461821`;
- conclusion: **success**.


## Продолжение квалификации user-context Undo

После VBA/Alt+F8 исследований были проверены дополнительные штатные механизмы Visio и Office.

### Explicit IVBUndoUnit

В отдельной qualification page был создан custom `IVBUndoUnit`, затем выполнен Duplicate:

- до операции: 44 shapes;
- после операции: 52 shapes;
- описание Undo unit: `EnergoLogic: Duplicate Cell`.

Однако:

- один физический `Ctrl+Z`: 52 → 52;
- прямой `Application.Undo()`: 52 → 52.

То есть само наличие external `AddUndoUnit` не делает transaction обычной пользовательской записью Undo для текущего bridge invocation context.

### Classic COM add-in + Ribbon

Был собран минимальный managed classic COM add-in.

Первая версия с самодельными COM interface declarations приводила к падению Visio. После ремонта add-in был переведён на реальные Microsoft interop assemblies:

- `Extensibility.IDTExtensibility2`;
- `Microsoft.Office.Core.IRibbonExtensibility`.

Manual `Connect=true` после старта Visio стал стабильным. Но startup-load с Ribbon customization в qualification contour оставался небезопасным: Visio завершался/терял live binding, и add-in был полностью удалён из HKCU перед дальнейшей работой.

Вывод: Ribbon startup probe не используется как production direction до отдельной полноценной packaging/runtime qualification.

### CommandBar-only add-in

Создан отдельный add-in:

`EnergoLogic.VisioQolCommandBarAddin`

Отличия:

- отдельный ProgID/CLSID;
- `LoadBehavior=0`;
- без `IRibbonExtensibility`;
- без Ribbon XML;
- только `IDTExtensibility2`;
- временная Office CommandBar `EnergoLogic QoL Probe`;
- кнопка `EnergoLogic Duplicate 40`.

Этот вариант стабильно зарегистрировался и подключился в работающий Visio:

- listed in `COMAddIns`: true;
- connected: true;
- command bar present/visible: true;
- button present/visible: true;
- Visio не падал.

Вызов штатного `CommandBarButton.Execute()` действительно зашёл в add-in callback и выполнил compound Duplicate:

- 44 → 52 shapes.

Но один физический `Ctrl+Z` после этого снова дал:

- 52 → 52.

Следовательно, программный `Execute()`, хотя callback выполняется внутри add-in, всё ещё инициирован внешним Automation call и не является достаточным user-context доказательством.

### Physical click и reentrancy

Следующая попытка физически кликнуть видимую CommandBar-кнопку мышью была сделана внутри того же synchronous bridge tool.

Результат:

- операция осталась в состоянии `claimed`;
- Windows node продолжил heartbeat;
- новый Visio command не может быть обработан;
- серверный `visio_call` истёк по timeout.

Это квалифицировано как reentrancy-deadlock pattern: нельзя держать активный Automation/COM вызов к Visio и одновременно пытаться породить физическое UI-событие, которое должно войти обратно в тот же Visio.

Такой synchronous physical-click path больше не использовать.

### Async physical UI probe

Bridge managed extension `.73` добавляет bounded detached helpers:

1. bridge выбирает фиксированный source selection и вычисляет координаты только нашей CommandBar-кнопки;
2. запускает локальный helper с фиксированной задержкой 1 сек;
3. bridge tool возвращается;
4. helper физически кликает кнопку после завершения внешнего COM-вызова;
5. отдельным read-only вызовом проверяется `44 → 52`;
6. второй detached helper аналогично отправляет один физический `Ctrl+Z` уже после возврата своего COM-вызова;
7. отдельным чтением проверяется ожидаемое `52 → 44`.

Helpers не принимают произвольные клавиши, команды или координаты от caller; координаты берутся только из фиксированной `EnergoLogic.Duplicate40.UndoProbe` CommandBarButton.

На момент фиксации evidence live async qualification ещё не выполнена: локальный `windows_visio_agent.py` остаётся заблокирован предыдущей synchronous physical-click операцией и требует один restart.

Bridge branch:

- managed extension `2026.10.03.73`;
- focused unit/contract suite: **39/39 PASS**.


## Editor v3.13 — end-of-session live topology checkpoint (2026-10-04)

Этот checkpoint является текущей точкой продолжения и supersede'ит старые operational notes про bridge `.73` / Undo blocker.

### Текущий runtime

- live add-in: `EnergoLogic.VisioEditorAddinV313`;
- API: `0.3.13`;
- managed Visio extension: `2026.10.03.111`;
- development-bridge branch HEAD: `05a877e` (`fix: complete editor topology in explicit second phase`);
- `visio-workstation` online;
- исходная `MCP-v2` сохранена неизменной.

К v3.13 live-приёмку уже прошли пользовательские команды:

- Coordinates;
- Copy with Base Point;
- Move with Base Point;
- Exact Offset;
- Smart Nudge;
- Align X/Y;
- Select Cell;
- Renumber Cell;
- Duplicate Cell Left/Right;
- Move Cell Left/Right;
- Repair Glue;
- Scheme Doctor;
- Measure Pitch.

TSN cell с anchor `155` корректно определяется как 11 top-level members:

`[155,158,160,162,166,182,240,242,244,249,250]`.

### Cell Pitch distribute: точная незакрытая проблема

v3.13 выполняет распределение в две фазы:

1. geometry phase перемещает ячейки и сохраняет pending topology plan;
2. `ApiCompletePendingTopology` отдельно восстанавливает и проверяет electrical Glue.

На disposable page `UI-V313-Pitch-Delay-Probe`:

- slot 3 был полностью освобождён;
- page shape count: **44**;
- `SelectCell(155)` подтвердил 11-member TSN cell;
- `MeasurePitch([66,155])` вернул **80 мм**;
- `DistributePitch(40)` успешно завершил geometry phase;
- pending token: `topology:106a58e76ead48a0b1053237e282eaff`.

Для проверки timing-гипотезы между phase 1 и phase 2 намеренно выдержано **10 секунд**.

Результат: phase 2 всё равно упал на том же внутреннем edge:

`shape 244 End → shape 166 / Connections.1`.

Диагностика после попытки восстановления:

- native target: none;
- formula target: none;
- `244.EndX FormulaU = 190 mm`.

Компенсация вернула геометрию назад, но также не смогла восстановить тот же edge; после compensation `EndX` оставался numeric `150 mm`.

**Вывод:** гипотеза «350 ms мало, VTD просто нужно дольше подождать» отвергнута. Проблема структурная в add-in Glue restoration path.

### Half-Glue — ключевое новое evidence

Сразу после failure на той же странице endpoint `244.End` оказался в несогласованном состоянии:

- `EndX FormulaU = "190 mm"`;
- `EndY FormulaU = "PAR(PNT(ТСН2!Connections.1.X,ТСН2!Connections.1.Y))"`.

То есть Y уже содержит VTD reference, а X остаётся обычной координатой — реального `Connects` для End endpoint нет.

После этого **без дополнительного ожидания** low-level bridge вызов:

`batch_glue_endpoints([{shape_id:244, endpoint:"end", target_shape_id:166, target_connection_row:1}])`

на той же странице успешно восстановил connection.

Authoritative `get_connections` после вызова подтвердил:

`244.EndX → 166/Connections.1.X`.

Одновременно существующий внутренний edge:

`244.BeginX → 242/Connections.2.X`

остался корректным.

Это разделяет гипотезы:

- native `GlueTo` работает;
- `ТСН2 / Connections.1` валиден;
- дополнительный settle delay не нужен для самого Glue;
- remaining defect находится именно в C# add-in path — `DetachEndpoint / GlueEndpointWithRetry / endpoint X/Y normalization`.

Особенно подозрительно, что `DetachEndpoint` записывает numeric значения и в X, и в Y, а `GlueEndpoint` вызывает `GlueTo` только на X cell. Следующая сессия должна сравнивать формулы X/Y до/после detach и каждой GlueTo-попытки, а не добавлять blind sleeps.

### Следующая точка продолжения

1. Не возвращаться к Undo research — это deferred technical debt.
2. Создать свежую disposable copy от `MCP-v2`.
3. Инструментировать `244.EndX/EndY` до detach, после detach и после каждого GlueTo.
4. Сравнить C# path с уже доказанным Python `batch_glue_endpoints`.
5. Исправить endpoint normalization / restore semantics.
6. Принимать Cell Pitch distribute только после реального post-check:
   - `244.EndX → 166/Connections.1.X`;
   - полный внутренний TSN topology сохранён;
   - внешний bus Glue корректен;
   - geometry = 40 мм.
7. После этого вернуться к общему UI/product polish.

PR #12 остаётся Draft; Ready/merge без явной команды владельца запрещены.
