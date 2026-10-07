# EnergoLogic roadmap

**Актуальность:** 2026-10-07.
Фактическое состояние: `docs/PROJECT-STATUS.md`.
Целевая архитектура: `docs/architecture/CANONICAL-PRODUCT-ARCHITECTURE.md`.

Roadmap организован по зависимостям, а не как одна последовательная очередь. Несвязанные bounded work items должны идти параллельно.

## 0. Текущий repository checkpoint — закрыть Visio reconciliation

### VISIO-EDITOR-QOL-001 / PR #12

Runtime implementation доведён до **V364 / API 0.3.64** и live-принят. Текущая задача PR #12 — привести EnergoLogic documentation/evidence к этому baseline и убрать старые v3.49/v3.18/Undo-ограничения из текущего статуса.

После этой reconciliation:

- PR остаётся Draft;
- Ready/Merge — только по явной команде владельца;
- Visio Editor перестаёт быть critical-path research item;
- дальнейшая работа с Visio идёт как compatibility/maintenance либо как frontend integration для новых product capabilities.

## 1. Ближайший главный milestone — Integrated Protection Loop

Следующий новый bounded integration work item должен замкнуть уже существующие foundation-слои без их переопределения.

Целевая цепочка:

```text
Canonical model + switching state
        ↓
Operational Runtime (WS-6)
        ↓
Solver study / short-circuit result (WS-8)
        ↓
Gate-E measured quantities adapter
        ↓
Protection Engine (WS-9B)
        ↓
ProtectionOutputRequest
        ↓
explicit breaker-operation adapter
        ↓
WS-6 switching operation + event timeline
        ↓
new energization/source attribution
        ↓
Visio state projection
```

### Acceptance v1

На synthetic canonical network:

1. задать исходное состояние и explicit source;
2. инициировать квалифицированный fault study;
3. получить deterministic solver result;
4. преобразовать только квалифицированную измеряемую величину в ProtectionSnapshot;
5. получить pickup/operate и trip request;
6. отдельно выполнить breaker operation через operational adapter;
7. подтвердить изменение topology/energization;
8. получить единый детерминированный event trace;
9. отобразить результат в Visio без превращения Visio в source of truth.

Критический инвариант: `trip requested` и `breaker opened` остаются разными событиями.

## 2. Параллельные P0/P1 направления

### A. ELECTRICAL-CALCULATION-DOMAIN-001 — P0

Уже назначенный WS-1/WS-8 follow-up из solver decisions.

Нужно определить `electrical-calculation-v1`:

- source/external network;
- line/cable;
- load;
- solver-neutral transformer/equipment parameters;
- sequence data + provenance;
- validation;
- materialization into Gate-D solver input.

Без этого WS-8 остаётся qualified spike, а не production calculation layer.

### B. Legacy Visio → Canonical Import — P0/P1

Продолжение `LEGACY-VISIO-INSPECTOR-001`:

```text
inspection/fingerprint
    ↓
family classification
    ↓
legacy family → canonical concept mapping
    ↓
connectivity reconstruction
    ↓
confidence/review
    ↓
Canonical Site Model
```

Главный fixture — существующая схема Кочубеевской ВЭС.

Inspector foundation нельзя выдавать за полный migrator.

### C. Earthing + Interlocks + Operation Permission — P0/P1

WS-6 уже умеет switching timeline, но сознательно не знает реальных safety/interlock rules.

Порядок:

1. earthing-switch / earthing topology semantics;
2. canonical operation-permission/interlock contract;
3. generic electrical/mechanical/logical interlocks;
4. site-specific bindings;
5. позже — provenance-bearing RU Rules Engine.

### D. SOLVER-RUNTIME-HOST-001 — P1

Production solver должен работать out-of-process:

- bundled pinned x64 Python/solver runtime;
- version/capability handshake;
- local versioned IPC;
- timeout/cancel/restart;
- offline deployment;
- x86/x64 Visio independence.

Это отдельный runtime/packaging контур; он не должен менять canonical/Gate-D contracts.

## 3. Следующий слой после первого integrated loop

### WS-5 Scheme Generator

Старт production integration после устойчивых Gate A + Gate C:

- bus/bay/cell templates;
- deterministic pitch/layout;
- equipment placement;
- Glue generation;
- numbering/labels;
- regeneration from canonical model.

Layout/template research можно вести раньше, но generated Visio не должен создавать собственную электрическую истину.

### WS-11 Kochubeevskaya Site Digital Twin

Собрать versioned site profile:

- accepted topology;
- equipment inventory/parameters;
- protection setting cards;
- actual protection bindings/matrices;
- local interlocks/rules;
- legacy symbol mappings;
- solver golden/reference cases;
- switching/training scenarios.

Site data должны оставаться отделены от generic product code.

### SITE-SOLVER-ACCEPTANCE-001

Квалифицировать расчёты на реальном site profile по reference hierarchy из solver decisions: hand/reference calculations → authoritative source calculations → second solver → engineering invariants → explicit tolerances/goldens.

## 4. Operational UX / Rules / Training

После появления earthing/interlock/rules foundation:

### WS-10 Russian Rules Engine

- Gate F rules/provenance contract;
- versioned federal/industry rules;
- site-specific rules;
- machine-readable applicability;
- source-attributed decisions;
- объяснение причины запрета/предупреждения.

### WS-7 Switching Forms & Training

- initial/target state;
- step model;
- execution against WS-6;
- rule/interlock validation;
- required checks;
- scoring/explanations;
- training scenarios.

## 5. Protection expansion

Foundation already covers definite-time МТЗ/ТО/токовую ЗЗ and explicit breaker-failure logic.

Further work must be bounded by function and evidence:

1. solver/operational measured-value integration;
2. actual breaker execution boundary;
3. inverse-time characteristics where required;
4. directional OC/EF;
5. voltage/frequency and negative-sequence functions;
6. differential protection;
7. distance protection;
8. reclosing/ATS/other automation where site scope requires;
9. WS-9C arc-fault protection: optical/current supervision, zones, trip matrices, breaker-failure escalation.

Do not implement a vendor/site-specific protection behavior from guesses.

## 6. Phase-domain / OpenDSS expansion

Not required for the first balanced production slice.

Sequence:

1. `PHASE-NEUTRAL-TOPOLOGY-001`;
2. explicit phase/neutral/earthing canonical semantics;
3. only then `OPENDSS-ADAPTER-001` for unbalance/neutral/harmonics/QSTS use cases.

## 7. Compatibility / packaging — continuous

Visio V364 packaging baseline is ready for current host. Remaining live qualification:

- Visio 2010;
- 2013;
- 2016;
- 2019;
- 2021;
- current Microsoft 365 / LTSC representative variants;
- x86/x64 where applicable.

Do not claim LIVE PASS for an unavailable SKU. Keep `ARCH/PACKAGE PASS` distinct from physical runtime acceptance.

Product-wide standalone work later additionally bundles solver/runtime dependencies; target users must not install Python/pip/pandapower/OpenDSS manually.

## 8. Dependency view

```text
                         ┌─ ELECTRICAL-CALCULATION-DOMAIN-001 ─┐
                         ├─ Legacy→Canonical Import              │
V364 reconciliation ─────┤─ Earthing / Interlocks               │
                         └─ SOLVER-RUNTIME-HOST-001              │
                                      │                          │
                                      └──────────────┬───────────┘
                                                     ▼
                                      Integrated Protection Loop
                                                     │
                        ┌────────────────────────────┼───────────────────────────┐
                        ▼                            ▼                           ▼
                  Scheme Generator          Kochubeevskaya Site          Rules/Training
                        │                     Digital Twin                     │
                        └────────────────────────────┼───────────────────────────┘
                                                     ▼
                                          Site-realistic acceptance
                                                     │
                                      ┌──────────────┴──────────────┐
                                      ▼                             ▼
                              Advanced Protection           Phase/OpenDSS studies
```

Стрелки отражают зависимости интеграции, а не обязательный календарный порядок.

## 9. Правила планирования

1. Один bounded work item — одна branch и Draft PR.
2. Перед стартом читать `PROJECT-STATUS`, этот roadmap и relevant architecture contract.
3. Не создавать новый layer внутри чужого work item «заодно».
4. Mocks/golden fixtures разрешены до готовности upstream, но contract version должен быть явным.
5. Incompatible contracts fail closed.
6. Headless logic не должно зависеть от Visio, если Visio не intrinsic к функции.
7. Terminology/provenance/packaging — continuous streams, а не финальная уборка.
8. Owner контролирует Ready/Merge.
