# EnergoLogic

EnergoLogic — инженерная платформа, в которой **каноническая электрическая модель является источником истины**, а пользовательские интерфейсы являются проекциями и адаптерами этой модели.

Текущий этап: `VISIO-EDITOR-QOL-001`.

## Базовые архитектурные инварианты

1. **Visio — первый frontend**, но не system of record.
2. **VSDX/ShapeSheet/COM не являются canonical source of truth**.
3. Каноническая schema, electrical profile и switching-state semantics разделены на явные детерминированные слои.
4. **Критический runtime детерминирован**: одинаковая модель даёт одинаковое каноническое представление, fingerprint и упорядоченный набор ошибок.
5. **LLM/агенты не участвуют в критической электрической логике**.
6. `energologic.core` не зависит от domain/frontend/solver слоёв; domain зависит только вниз от core.

## Реализованные слои

### Foundation

- canonical-model schema `0.1`;
- dependency-free Python core;
- decode / structural validate / canonicalize / fingerprint;
- CLI;
- Linux/Windows CI.

### Visio vertical slice

Квалифицирован детерминированный round-trip для native VTD/GOST фрагмента:

`bus → circuit breaker → CT → CT NP → external link`

Visio identity и geometry остаются projection-only.

### Electrical semantic profile v1

Явно выбираемый профиль `electrical-v1` формализует первый поддержанный статический subset:

- `bus(node)`;
- `circuit_breaker(a,b)`;
- `disconnector(a,b)`;
- `current_transformer(a,b)`;
- `external_link(node)`.

Профиль проверяет terminal contracts, `nominal_voltage_v`, voltage consistency, terminal degree и базовую топологическую целостность.

Напряжение хранится в **целых вольтах** независимо от frontend display units: Visio/VTD `35 kV` → canonical `35000 V`.

### Switching-state semantics v1

Профиль `switching-state-v1` добавляет к switchgear независимые факты:

- `switch_state = open | closed`;
- `mounting_type = fixed | withdrawable`;
- для выкатных аппаратов:
  `withdrawable_position = working | repair | control`.

Для поддержанных аппаратов реализован детерминированный локальный predicate проводимости:

- open → не проводит;
- closed + fixed → проводит;
- closed + withdrawable + working → проводит;
- closed + withdrawable + repair/control → не проводит.

Это **локальная семантика аппарата**, а не полный расчёт электрически связной/напряжённой сети.

Native VTD mapping квалифицирован на реальном Visio:

- `Actions.Row_1.Action TRUE/FALSE ↔ closed/open`;
- `User.p 0/1/2 ↔ working/repair/control`;
- breaker и `Разъединитель выдвижной`.

### Двухобмоточный трансформатор

Модель понимает `transformer_2w` как один аппарат с двумя сторонами:

- `hv` — высшее напряжение;
- `lv` — низшее напряжение.

Напряжение хранится **на конкретном выводе**. Оно может быть точным, например `35000 V`, либо классом, если исходный документ точнее не знает.

Для native VTD `ТСН2` квалифицировано:

- U1 = 35 кВ → `hv.nominal_voltage_v = 35000`;
- U2 = «ниже 3 кВ» → `lv.voltage_class = below_3000_v`;
- U1 = треугольник;
- U2 = звезда.

EnergoLogic намеренно **не угадывает 0,4 кВ** по соседней надписи: внутри самой VTD-фигуры такого точного значения нет.

Если точные 400 В известны из надёжного источника, canonical model их поддерживает и считает совместимыми с классом «ниже 3 кВ». Но текущий VTD master не может вернуть точные 400 В без потери точности, поэтому такая обратная проекция блокируется.

## Быстрый запуск

```bash
python -m pip install -e .

# Открытая структурная schema:
energologic validate examples/minimal.energologic.json

# Статическая электрическая семантика:
energologic validate examples/kru35-v1-cell.electrical-v1.json --profile electrical-v1

# Коммутационные состояния:
energologic validate examples/kru35-v1-cell.switching-state-v1.json --profile switching-state-v1

# Двухобмоточный трансформатор:
energologic validate examples/tsn2.transformer-v1.json --profile electrical-v1

energologic canonicalize examples/minimal.energologic.json
energologic fingerprint examples/minimal.energologic.json

python -m unittest discover -s tests -v
```

## Структура

```text
src/energologic/core/          structural canonical model + deterministic runtime
src/energologic/domain/        electrical and switching semantic profiles
src/energologic/frontends/     frontend contracts/adapters
schema/                        external versioned structural contracts
examples/                      canonical-model fixtures
docs/architecture/             ADRs
docs/work-items/               work-item evidence
tests/                         acceptance/regression tests
```

## EnergoLogic Visio UX

Текущий work item `VISIO-EDITOR-QOL-001` не меняет источник истины: Visio остаётся frontend'ом.

Цель — убрать ручную CAD-подобную рутину поверх Visio. Первый benchmark:

`Duplicate Cell Right / Left`

с точным pitch, сохранением внутренних Glue, автоматическим подключением к шине, новой identity и одним Undo.

План и приоритеты: `docs/roadmap.md`.

## Текущая граница

Пока отдельно остаются:

- grounding-switch / earthing semantics;
- interlocks;
- energized-network traversal;
- трёхобмоточные трансформаторы и автотрансформаторы;
- параметры трансформаторов для расчётов: мощность, uk%, потери, РПН;
- Planner;
- РЗА/protection;
- CIM;
- pandapower и другие solver-интеграции.

Они должны добавляться отдельными work items, а не протекать в уже квалифицированные контракты.

## Процесс изменений

Рабочий процесс проекта:

**Issue → branch → Draft PR → implementation/tests/evidence → owner acceptance**

Merge и Ready for Review запрещены без явной команды владельца проекта.
