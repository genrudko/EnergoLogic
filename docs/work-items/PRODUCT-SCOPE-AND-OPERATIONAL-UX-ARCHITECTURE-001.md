# PRODUCT-SCOPE-AND-OPERATIONAL-UX-ARCHITECTURE-001

**Issue:** #41 · **Branch:** `architecture/product-scope-and-operational-ux-001` · **Base:** `main@f92f89b` · **Тип:** documentation-only canonical architecture decision · **Статус:** Draft / на приёмке владельца.

## Решение пользователя

EnergoLogic — standalone/offline инженерно-оперативная программа «для себя и своих» на базе Visio. Пользователи: начальники смен, диспетчеры, ДЭМ, инженеры оперативной работы. Сценарии: электрические схемы/ГОСТ, электрические расчёты, моделирование РЗА/АПВ, расчёт последствий переключений, бланки и разбор аварий. Русский UI, английский code/API. Полнота функций — да; промышленная SCADA/телемеханика и фактическое управление устройствами — нет.

**Основные референсы** ЭПА/NPT Expert, Прософт-Системы/REDKIT SCADA, Монитор Электрик/СК-11: перенять функциональные идеи и культуру индикации/оперативных процессов, не копировать чужой код/графику и не строить их серверную инфраструктуру.

## Deliverables

1. `docs/architecture/PRODUCT-BOUNDARY-AND-WORKSPACE-MODES.md` — продуктовые рамки, mode/source orthogonality, user workflows.
2. `docs/architecture/OPERATIONAL-STATE-AND-PRESENTATION-CONTRACT.md` — визуализация, энергизация, неизмеренное U, quality, события, replay, АПВ как deferred contract.
3. `docs/architecture/RUSSIAN-SCADA-DESIGN-BENCHMARK.md` — traceable российских референсов и принципы выборочного заимствования, vendor information ≠ standard.
4. `docs/architecture/LOCAL-WORKBENCH-IMPLEMENTATION-PROGRAM.md` — реализация по независимым P0/P1 пакетам, dependencies/acceptance/gates.
5. Ссылки и контекст в `README.md`, `CANONICAL-PRODUCT-ARCHITECTURE.md`, `roadmap.md`, `PROJECT-STATUS.md`, `EXECUTOR-GUIDE.md`.
6. `docs/evidence/PRODUCT-SCOPE-AND-OPERATIONAL-UX-ARCHITECTURE-001.md` — доказательства действительного изменения docs/внутренней проверки и точные ограничения.

## Non-goals

Нет новых Python/Visio/MCP runtime/solver feature в этом PR. Нет автоматического создания страниц Visio, изменения рабочего чертежа, merge/Ready других PR, заимствования проприетарных ресурсов SCADA, реального field control. Отдельные issues #39 (UX/event replay) и #40 (АПВ) остаются разработкой будущих функций.

## Acceptance

- [x] В пользовательской формулировке продукт = engineering helper, не full SCADA; согласован Windows10/11, Visio2010-latest, offline/standalone.
- [x] Единая каноническая модель, четыре режима и независимая классификация источника состояния.
- [x] Чёткое отличие topology energized, фактического U, nominal voltage и неизвестного/недостоверного состояния.
- [x] Терминально-ориентированная раскраска, множественные источники, safety/earthing отдельно, условная палитра с legend.
- [x] Контракт событий, времени, запрос vs подтверждение, учебного APV и replay.
- [x] UI/Visio non-destructive compatibility spike установлен как gate, не подразумеваемый existing feature.
- [x] Фактический GitHub state обновлён: #32/#34/#36 merged; PR #38 Draft/unmerged. Слияния были отдельно разрешены владельцем, в рамках подготовки к P0-B.
- [x] Headless independent work packages, изолированные fixture, cleanup/Undo, конкретная пользовательская приёмка.
- [x] GitHub CI на начальном head `0f1d95f`: run #37760718835 — 6/6 SUCCESS; после evidence-only commit проверить latest head отдельно.
- [ ] Owner acceptance архитектуры и продуктовых приоритетов — ожидается.
- [ ] Owner-approved Ready/Merge — **только отдельной явной командой**.

## Next implementation action after owner acceptance

Начать **P0-B Visio overlay feasibility spike** + **P0-C presentation DTO** + **P0-D scenario replay** параллельно, в отдельных bounded work items, не раздувая Issue #39 монолитно и не объявляя APV готовой.
