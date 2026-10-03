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
- R1: Duplicate Cell Right / Left — **in progress**: pure planner + exact duplicate + Glue + instance identity reset подтверждены; in-Visio one-Undo host и пользовательский command surface ещё нужны;
- R2: остальные P0 QoL-команды;
- R3: P1 cell/model diagnostics;
- R4: P2 Ribbon/context menu/shortcuts/presets.

Главный критерий первого релиза — реальный benchmark Duplicate Cell Right на MCP-v2.

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
