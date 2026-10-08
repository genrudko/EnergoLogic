# Evidence: PRODUCT-SCOPE-AND-OPERATIONAL-UX-ARCHITECTURE-001

**Дата:** 2026-10-08. **Issue #41.** **Base:** `main@f92f89b`. **Статус:** docs-only Draft, acceptance не заявлен.

## Наблюдаемые основания

1. Репозиторий `genrudko/EnergoLogic`, `README.md`, `docs/PROJECT-STATUS.md`, `docs/roadmap.md`, `docs/architecture/CANONICAL-PRODUCT-ARCHITECTURE.md`, `OPERATIONAL-SIMULATION-CONTRACT.md`, `EXECUTOR-GUIDE.md` прочитаны. `main` на момент начала work item = `f92f89b5939a2f4aa798a295389daf5f2b3db185`.
2. GitHub PR #12 (Visio V364) — **merged** в `main@f92f89b`. GitHub PR #32 (electrical domain), #34 (permission), #36 (integrated protection loop) — Draft/unmerged. PR #38 (VTD MCP projection) — Draft/unmerged, **base #36**, не `main`. Ошибочно считать эти capabilities принятыми нельзя.
3. Пользовательский приоритет и область применения явно сформулированы в проектной беседе: offline/standalone local engineering/operational helper, не промышленная SCADA; динамическая схема должна обеспечивать качество и достоверность инженерного представления.
4. Референсы российских производителей (проверены публичные описания, 2026-10-08):
   - [ЭПА / NPT Expert](https://www.epsa-spb.ru/scada_npt_expert/), [модуль бланков](https://epsa-spb.ru/modul-podderzhki-avtomatizirovannykh-blankov-pereklyucheniy/), [руководство NPT Expert (2022)](https://npt.spb.ru/f/rukovodstvo_po_ekspluatacii_scada_npt_expert.pdf).
   - [Прософт-Системы / Redkit SCADA 2.0](https://prosoftsystems.ru/catalog/show/programmnyj-kompleks-redkit-scada).
   - [Монитор Электрик / СК-11](https://monitel.ru/), [EMS/DMS](https://monitel.ru/applications/ems-and-dms/), [тренажёры](https://monitel.ru/applications/trenazhery/).
5. Состояния от принятых WS-6 и WS-9B не являются автоматически показаниями реальной телеметрии. `unknown`/stale и терминальные состояния добавлены в **target design**, без заявления о существующей implementation.
6. Исторический случай WS-0: пользовательская схема была заполнена множеством тестовых страниц; пользователь самостоятельно очистил сохранённую копию до одной страницы. В новый процесс внесён обязательный cleanup/evidence gate. **Никакие документы Visio в этом work item не изменялись.**

## Проверки документации

Ожидаемые локальные проверки перед коммитом:
- `git diff --check`, корректность ссылок на локальные .md и наличие файлов;
- все ссылки README/architecture/roadmap/PROJECT-STATUS/EXECUTOR-GUIDE ведут к добавленным документам;
- `PYTHONPATH=src python3 -m unittest discover -s tests -q` на неизменённом коде;
- отсутствуют runtime изменения, и нет Ready/Merge сторонних PR.

Заполнять только фактически наблюдаемыми результатами. CI run/head SHA и Draft PR number добавить после создания.

## Проверено локально на ветке #41 (2026-10-08)

- `main` зафиксирован как `f92f89b`. Проверка GitHub PR #12: **merged=true**, merge SHA `f92f89b`; старые противоречивые записи исправлены.
- Проверка текущих PR: #32, #34, #36, stacked #38 — **Draft/unmerged**, статусы не объявлены accepted.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -q`: **280 tests, 7 skipped, 0 failures** (код `main` не менялся).
- Проверены **57 Markdown-файлов** `README.md` и `docs/**`: **0 отсутствующих относительных ссылок**.
- `git diff --check`: PASS; изменения ограничены Markdown, runtime/Visio/solvers не затронуты.
- GitHub PR/CI результаты и конечный commit будут зафиксированы в PR после публикации; до того **CI не заявлен**.

## Известные границы

Design-reference != vendor interoperability; конкретные палитры и нормативные запреты должны проходить собственные site/normative acceptance. Динамическая мнемосхема, event replay и АПВ **не появляются** только потому, что документы написаны. Не выполнять field control, автоматические переключения и печать «разрешено к производству» без квалифицированных оснований.
