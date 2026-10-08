# EnergoLogic

EnergoLogic — инженерная электротехническая платформа, в которой **каноническая электрическая модель является источником истины**, а Microsoft Visio, solver'ы, protection runtime и другие подсистемы являются проекциями/адаптерами этой модели.

**Актуальность архитектурного позиционирования:** 2026-10-08. Фактический статус интеграционных модулей — в `docs/PROJECT-STATUS.md` и GitHub PR.
Подробный фактический статус: [`docs/PROJECT-STATUS.md`](docs/PROJECT-STATUS.md).
Порядок дальнейшей разработки: [`docs/roadmap.md`](docs/roadmap.md).
Целевая архитектура: [`docs/architecture/CANONICAL-PRODUCT-ARCHITECTURE.md`](docs/architecture/CANONICAL-PRODUCT-ARCHITECTURE.md).

## Продуктовый контур (решение 2026-10-08)

**EnergoLogic — автономный инженерно-оперативный помощник**, а не замена промышленной SCADA. Пользователи: начальник смены, диспетчер, инженер по оперативной работе, ДЭМ. Задачи: редактор электрических схем в Visio, режимные расчёты/КЗ, РЗА и сценарии, анализ последствий переключений, бланки и учебные/ретроспективные разборы. Производственные серверы SCADA, непрерывная телемеханика и управление реальными выключателями **не являются частью базового продукта**.

Одна и та же инженерная схема должна использоваться в режимах **Редактирование**, **Оперативный просмотр**, **Моделирование** и **Ретроспектива**. Режим интерфейса и источник данных — **независимые понятия**. Топологическая запитанность не равна фактически измеренному напряжению; качество данных, происхождение расчётов и недоступные функции показываются явно.

Решение и архитектура:
- [Границы продукта и режимы работы](docs/architecture/PRODUCT-BOUNDARY-AND-WORKSPACE-MODES.md)
- [Модель состояния/событий/индикации](docs/architecture/OPERATIONAL-STATE-AND-PRESENTATION-CONTRACT.md)
- [Референсы российских SCADA и решения о заимствованиях](docs/architecture/RUSSIAN-SCADA-DESIGN-BENCHMARK.md)
- [Этапы, зависимости, параллельная реализация и критерии приёмки](docs/architecture/LOCAL-WORKBENCH-IMPLEMENTATION-PROGRAM.md)

## Архитектурные инварианты

1. **Canonical model = source of truth.** Visio, VSDX, ShapeSheet, COM, pandapower/OpenDSS и protection runtime не являются system of record.
2. **Visio — первый инженерный frontend**, редактор и мнемосхема, но не вычислительное ядро.
3. Critical electrical runtime должен быть детерминированным, fail-closed и тестируемым headless.
4. LLM/агенты не участвуют в критической электрической логике и не подменяют инженерные/нормативные факты.
5. Solver'ы подключаются через адаптеры; solver-specific schema не становится canonical schema.
6. Protection Engine отделён от solver'а: solver вычисляет физические величины, protection runtime — pickup/delay/reset/output requests.
7. Нормативная и site-specific логика должна быть отдельным versioned Rules layer с provenance.
8. Пользовательская терминология — каноническая русская; code/API/schema identifiers — каноническая английская электротехническая терминология.
9. Generic product code и данные конкретного объекта (в первую очередь Кочубеевской ВЭС) разделяются.
10. Production target — автономная offline-эксплуатация на Windows 10/11 при установленном поддерживаемом Microsoft Visio.

## Что уже находится в `main`

На 2026-10-07 приняты и merged следующие foundation-блоки:

- `PROJECT-FOUNDATION-001` — canonical schema/core/CLI/CI;
- `VISIO-CANONICAL-BRIDGE-001` — детерминированный Visio ↔ canonical vertical slice;
- `ELECTRICAL-DOMAIN-PROFILE-V1-001` — `electrical-v1`;
- `SWITCHING-STATE-SEMANTICS-001` — switch state / withdrawable position;
- `TRANSFORMER-SEMANTICS-001` — двухобмоточный трансформатор и terminal-scoped voltage;
- `TERMINOLOGY-REGISTRY-V1-001` — versioned RU↔EN terminology registry;
- `LEGACY-VISIO-INSPECTOR-001` — read-only VSDX inspection/fingerprinting foundation;
- `OPERATIONAL-SIMULATION-FOUNDATION-001` — energized traversal и source tracing;
- `SWITCHING-OPERATIONS-TIMELINE-001` — headless switching operations/event timeline;
- `ELECTRICAL-SOLVER-SPIKE-001` — solver-neutral boundary + qualified pandapower spike;
- `PROTECTION-SETTING-IMPORT-001` — source-neutral setting-card model/import;
- `PROTECTION-ENGINE-FOUNDATION-001` — deterministic МТЗ/ТО/ЗЗ foundation;
- `BREAKER-FAILURE-FOUNDATION-001` — explicit УРОВ/breaker-failure state machine.

Это **foundation-блоки**, а не заявление, что соответствующие продуктовые направления полностью завершены. Границы каждого направления перечислены в `docs/PROJECT-STATUS.md`.

## Visio Editor — текущий production baseline

`VISIO-EDITOR-QOL-001` доведён до live-принятого runtime baseline:

- **EnergoLogic Visio Editor V364**;
- API `0.3.64`;
- ProgID `EnergoLogic.VisioEditorAddinV364`;
- managed extension/package transport `2026.10.06.213`;
- native Ribbon/context menu/modeless panel;
- topology-safe cell/equipment/geometry operations;
- compound topology mutations в одном native Visio UndoScope;
- standalone/offline prebuilt AnyCPU package;
- live acceptance на установленном Visio 16.x.

Runtime implementation находится в `genrudko/development-bridge`, branch `feature/energologic-visio-qol-001`, commit `5695108cf9602ab93ac8223fe0f90c4e7d658209`.

Документация: [`docs/visio/README.md`](docs/visio/README.md).

PR #12 **merged** в `main` (`f92f89b`, проверено по GitHub 2026-10-08). V364 — текущий базовый редактор; отдельная совместимость Visio 2010–latest ещё требует матричных live-тестов.

## Главный следующий milestone

Следующая цель — не очередной изолированный foundation, а первый полноценный интеграционный vertical slice:

```text
Canonical topology/state
        ↓
Operational Runtime
        ↓
Solver Study / Short Circuit
        ↓
Qualified measured quantities
        ↓
Protection Engine
        ↓
Protection Output Request
        ↓
Breaker operation adapter
        ↓
Operational topology recalculation
        ↓
Visio state update
```

Acceptance-сценарий: **КЗ → расчёт → pickup/operate → trip request → отключение выключателя → новая topology/energization → отражение в Visio**.

Параллельно продолжаются bounded направления: production electrical-calculation domain, legacy→canonical migration, earthing/interlocks/rules, solver runtime host, site fixtures и advanced protection. Подробная зависимость и порядок — в [`docs/roadmap.md`](docs/roadmap.md).

## Структура репозитория

```text
src/energologic/core/          structural canonical model + deterministic runtime
src/energologic/domain/        electrical/switching/transformer semantics
src/energologic/operational/   energized traversal + switching timeline
src/energologic/solvers/       solver-neutral contracts + adapters
src/energologic/protection/    setting import + protection runtime + breaker failure
src/energologic/terminology/   controlled RU↔EN terminology registry
src/energologic/frontends/     frontend contracts/adapters, including Visio
schema/                        versioned external contracts
examples/                      canonical/synthetic fixtures
docs/architecture/             architecture contracts/ADRs
docs/work-items/               bounded work-item records
docs/evidence/                 acceptance/evidence records
docs/visio/                    current Visio baseline and development rules
tests/                         unit/integration/golden regressions
```

## Быстрый запуск core/test contour

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

Примеры profile-specific validation сохраняются в `examples/` и документации соответствующих контрактов.

## Процесс изменений

Каждое существенное изменение проходит:

**Issue → dedicated branch → Draft PR → implementation/tests/evidence → owner acceptance**

- Ready for Review и merge — **только по явной команде владельца**.
- Shared contracts меняются явно и версионируются.
- Исполнитель до начала работы обязан прочитать `docs/PROJECT-STATUS.md`, `docs/roadmap.md` и [`docs/EXECUTOR-GUIDE.md`](docs/EXECUTOR-GUIDE.md).
