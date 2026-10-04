# EnergoLogic roadmap

## Уже завершено и находится в main

1. PROJECT-FOUNDATION-001
2. VISIO-CANONICAL-BRIDGE-001
3. ELECTRICAL-DOMAIN-PROFILE-V1-001
4. SWITCHING-STATE-SEMANTICS-001
5. TRANSFORMER-SEMANTICS-001

## Текущий этап

### VISIO-EDITOR-QOL-001 — EnergoLogic Visio UX

Приоритет: **сейчас**.

Задача этапа — сделать Visio удобным инженерным frontend'ом, не меняя принцип «canonical model = source of truth».

Порядок:

- R0: исследование API / bridge / реальной MCP-v2 — **done**;
- R1: Duplicate Cell Right / Left — **live-qualified core / polish remains**: exact duplicate, Glue, identity reset и реальный Editor UI работают; one-user-Undo вынесен в deferred technical debt и не блокирует продукт;
- R2: остальные P0 QoL-команды — **почти закрыты live**: Coordinates, Base Point copy/move, Exact Offset, Smart Nudge, Align X/Y, Select/Renumber Cell, Move Cell, Repair Glue, Scheme Doctor и Measure Pitch приняты live. Remaining blocker — topology-safe Cell Pitch distribute: v3.13 geometry phase работает, но C# restoration оставляет `244.End → 166/Connections.1` half-glued; 10-second delay не помогает, low-level `batch_glue_endpoints` тот же edge восстанавливает сразу;
- R3: P1 cell/model diagnostics / Replace & Insert Equipment / bus editing — после закрытия topology-safe pitch;
- R4: P2 Ribbon/context menu/shortcuts/presets.

Текущая точка релиза — довести уже работающий Editor v3.13 до topology-safe поведения и завершить пользовательский polish. Главный незакрытый acceptance case: Cell Pitch distribute на TSN cell с обязательной проверкой реального Glue.


## Canonical product target

Authoritative target architecture: `docs/architecture/CANONICAL-PRODUCT-ARCHITECTURE.md`.

EnergoLogic target scope now explicitly includes: Visio engineering frontend/mnemonic; canonical electrical model; operational switching simulation; switching forms/training; power-flow and short-circuit solver layer; protection/RZA including arc-fault protection; Russian normative + site-rule validation with provenance; legacy Visio migration; automatic scheme generation; self-contained offline deployment.

Cross-cutting requirements: Windows 10/11; desktop Visio 2010 through latest supported desktop/Microsoft 365 Visio; x86/x64 qualification as applicable; bundled runtimes/libraries; Russian UI with canonical Russian power-engineering terminology; English code/API identifiers using canonical international electrical terminology; controlled RU↔EN Terminology Registry.

Planned bounded workstreams after the current editor baseline: canonical architecture hardening → legacy Visio migration (Kochubeevskaya WPP as real acceptance case) → scheme generator → energized-network traversal → switching simulation/forms → electrical solver v1 (pandapower preferred initial adapter) → protection engine v1 → arc/advanced protection → Russian normative rules → compatibility/product hardening.

## Следующий основной архитектурный этап

После промежуточного Visio UX work item вернуться к:

### ENERGIZED-NETWORK-TRAVERSAL-001

Определение фактически запитанных участков сети на основе:

- canonical topology;
- состояния коммутационных аппаратов;
- положения выкатных частей;
- transformer hv/lv semantics.

Этот этап не начинать внутри VISIO-EDITOR-QOL-001.

## Дальнейшие отдельные направления

- grounding / earthing semantics;
- interlocks;
- transformer tap changer / RPN;
- three-winding transformers / autotransformers;
- RZA/protection;
- CIM;
- solver integrations / pandapower;
- Planner.

Каждое направление оформляется отдельным work item.
