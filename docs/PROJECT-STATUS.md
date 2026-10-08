# EnergoLogic — фактическое состояние проекта

**Срез:** 2026-10-07
**Исторический срез:** `genrudko/EnergoLogic@734f64a` (2026-10-07). **Текущий проверенный main:** `f92f89b` (2026-10-08; PR #12 merged). Runtime Visio V364 baseline — `genrudko/development-bridge@5695108`. Перечень Draft и архитектурных изменений ниже обновлён отдельно.

## Актуализация архитектурного направления от 2026-10-08 (без фиктивного изменения статусов)

По решению владельца продукт окончательно определён как **локальный, автономный инженерно-оперативный помощник**, а **не промышленная SCADA**. Цель — схемы в Visio, расчёты, моделирование РЗА/оперативных переключений, бланки, разбор сценариев. Новый target UX: редактирование, оперативный просмотр, моделирование, ретроспектива; provenance/quality данных, динамическая мнемосхема и event replay. Это **план**, а не реализованные функции.

На момент проверки GitHub (2026-10-08): **Draft/unmerged** PR #32 `ELECTRICAL-CALCULATION-DOMAIN-001`, PR #34 `OPERATION-PERMISSION-CONTRACT-001`, PR #36 `INTEGRATED-PROTECTION-LOOP-001` (headless tested, без live Visio), **stacked Draft PR #38** `VISIO-PROTECTION-PROJECTION-LIVE-001` (MCP gateway contract, без законченного автоматического live Python→Visio теста). **Issue #39** индикация и event replay и **Issue #40** АПВ пока не implemented. Их результаты нельзя приписывать `main` до owner-controlled merge. Строки исходной статусной таблицы ниже сохраняют исторический срез 2026-10-07.

Стандарт: [Product Boundary](architecture/PRODUCT-BOUNDARY-AND-WORKSPACE-MODES.md), [Operational Presentation](architecture/OPERATIONAL-STATE-AND-PRESENTATION-CONTRACT.md), [Delivery Program](architecture/LOCAL-WORKBENCH-IMPLEMENTATION-PROGRAM.md).

Этот документ отвечает только на вопрос **«что реально готово сейчас»**. Целевой замысел находится в `docs/architecture/CANONICAL-PRODUCT-ARCHITECTURE.md`, а порядок дальнейшей работы — в `docs/roadmap.md`.

## Статусы

- **DONE / BASELINE** — bounded scope принят и merged либо, для V364, live-принят и документально reconciled в merged PR #12.
- **PARTIAL** — foundation/контракт существует, но продуктовая возможность ещё не замкнута end-to-end.
- **NOT IMPLEMENTED** — целевая возможность предусмотрена canonical plan, но production work item ещё не дал реализованный baseline.
- **CONTINUOUS** — поток не имеет одной конечной точки и развивается вместе с продуктом.

## Сводка по workstreams

| Поток | Статус | Уже есть | Ещё требуется |
|---|---|---|---|
| WS-0 Visio Editor | **DONE / merged PR #12** | V364, QoL, topology-safe operations, native Undo/Redo architecture, Ribbon/context/panel, standalone package | live matrix Visio 2010+ ведётся в WS-3; динамический оперативный слой — отдельный этап |
| WS-1 Canonical Domain & Contracts | **PARTIAL** | schema 0.1, stable canonical runtime, electrical-v1, switching-state-v1, transformer_2w | `electrical-calculation-v1`, phase/neutral/earthing domain, richer equipment/parameter model, Site Profile persistence |
| WS-2 Terminology & Normative Foundations | **PARTIAL / CONTINUOUS** | Terminology Registry v1 + provenance | расширение словаря; Normative Source Registry; executable rule provenance contract |
| WS-3 Compatibility & Packaging | **PARTIAL / CONTINUOUS** | Visio V364 offline prebuilt AnyCPU package; dual registry views; current Visio 16.x live pass | physical Visio 2010/2013/2016/2019/2021 x86/x64 qualification; bundled solver runtime host; product-wide installer/update strategy |
| WS-4 Legacy Visio Migration | **PARTIAL** | deterministic read-only VSDX inspector, symbol fingerprinting, native Glue evidence | family classification/mapping, canonical importer, ambiguity review, topology fallback, end-to-end Kochubeevskaya migration |
| WS-5 Scheme Generator | **NOT IMPLEMENTED** | editor/layout primitives usable as future backend | domain templates, bus/bay generation, deterministic layout, Glue generation, numbering, regeneration |
| WS-6 Operational Simulation | **PARTIAL** | energized traversal, multiple-source attribution, switching operations, deterministic timeline | earthing semantics, interlocks, operation permission/safety validation, integration with protection and rules |
| WS-7 Switching Forms & Training | **NOT IMPLEMENTED** | operational timeline can become execution backend | form/program schema, step validation, explanations, scoring/training workflow |
| WS-8 Electrical Solver | **PARTIAL** | solver-neutral contracts; pandapower spike; balanced AC power flow; IEC 60909 3φ/2φ/1φ-E spike qualification | production electrical domain, bundled worker/IPC, site data/goldens, current attribution, optional OpenDSS after phase-neutral domain |
| WS-9A Protection Settings | **DONE foundation** | versioned source-neutral setting card, JSON/tabular import, provenance, unit normalization | real site/vendor adapters and Kochubeevskaya cards |
| WS-9B Protection Engine | **PARTIAL** | МТЗ, ТО, токовая ЗЗ definite-time; declarative outputs; explicit УРОВ foundation | solver/operational integration, inverse/directional/distance/differential/voltage/frequency etc., actual breaker execution adapter |
| WS-9C Arc-fault Protection | **NOT IMPLEMENTED** | target architecture defined | optical/current supervision, zones, trip matrices, clearing sequence |
| WS-9D Advanced Protection | **NOT IMPLEMENTED** | generic engine boundary exists | directional, differential, distance, negative sequence, automation functions as bounded items |
| WS-10 Russian Rules Engine | **NOT IMPLEMENTED** | terminology/provenance principles exist | Gate F schema, executable federal/site rules, source-attributed decisions/explanations |
| WS-11 Site Digital Twin / Acceptance Fixtures | **NOT IMPLEMENTED as integrated profile** | Kochubeevskaya named as principal acceptance case; real Visio used for editor/inspection qualification | governed site model, equipment parameters, setting cards, topology snapshots, scenarios, solver/protection golden outcomes |

## Accepted/merged baselines in `main`

| Work item | Merge |
|---|---|
| PROJECT-FOUNDATION-001 | `8de6b81` — 2026-10-03 |
| VISIO-CANONICAL-BRIDGE-001 | `4105373` — 2026-10-03 |
| ELECTRICAL-DOMAIN-PROFILE-V1-001 | `936a66d` — 2026-10-03 |
| SWITCHING-STATE-SEMANTICS-001 | `182ff26` — 2026-10-03 |
| TRANSFORMER-SEMANTICS-001 | `9edc59a` — 2026-10-03 |
| LEGACY-VISIO-INSPECTOR-001 | `3e7043d` — 2026-10-04 |
| OPERATIONAL-SIMULATION-FOUNDATION-001 | `6dd5e60` — 2026-10-04 |
| PROTECTION-SETTING-IMPORT-001 | `92a62d7` — 2026-10-04 |
| ELECTRICAL-SOLVER-SPIKE-001 | `a5252e1` — 2026-10-04 |
| TERMINOLOGY-REGISTRY-V1-001 | `fee3b53` — 2026-10-04 |
| SWITCHING-OPERATIONS-TIMELINE-001 | `36198a6` — 2026-10-04 |
| PROTECTION-ENGINE-FOUNDATION-001 | `138f551` — 2026-10-04 |
| BREAKER-FAILURE-FOUNDATION-001 | `734f64a` — 2026-10-04 |

## Visio baseline / accepted into `main`

`VISIO-EDITOR-QOL-001` **merged PR #12**, runtime доведён до V364:

- development-bridge commit `5695108cf9602ab93ac8223fe0f90c4e7d658209`;
- Editor V364 / API 0.3.64;
- current-host live acceptance;
- one native Undo/Redo unit для topology-sensitive compound operations;
- prebuilt AnyCPU offline kit;
- target-side runtime PIA dependency отсутствует.

Это означает: **Visio Editor V364 baseline принят в `main` через PR #12**. Это не означает, что приняты все версии Visio либо готов оперативный presentation runtime.

## Что сейчас НЕ следует считать готовым

Следующие формулировки были бы преждевременными:

- «legacy Visio полностью мигрируется» — пока есть только inspector/fingerprinting foundation;
- «EnergoLogic уже рассчитывает любой реальный объект» — solver spike квалифицирован на synthetic/golden contour, production electrical domain/site acceptance ещё нужны;
- «РЗА полностью реализована» — реализованы bounded definite-time токовые функции и УРОВ foundation;
- «защита уже отключает выключатель» — engine пока выдаёт declarative output request, а successful breaker operation принадлежит будущей integration boundary;
- «есть российский Rules Engine» — executable rules layer ещё не реализован;
- «есть тренажёр/бланки переключений» — пока нет;
- «есть Scheme Generator» — пока нет;
- «Visio 2010 live-qualified» — V364 архитектурно/packaging-targeted для 2010+, но physical live pass есть только на установленном Visio 16.x.

## Главный интеграционный разрыв

Отдельные компоненты уже существуют, но пока не замкнуты в production loop:

```text
WS-6 operational state
        +
WS-8 solver result
        ↓
qualified measured-value adapter
        ↓
WS-9B protection runtime
        ↓
ProtectionOutputRequest
        ↓
breaker-operation integration
        ↓
WS-6 new state/timeline
        ↓
Visio renderer/state update
```

Headless-кандидат этого разрыва реализован в Draft PR #36, а Visio gateway-кандидат — в stacked Draft PR #38. Полное live-представление, event replay и пользовательская приёмка ещё не завершены; см. roadmap/Issue #39.
