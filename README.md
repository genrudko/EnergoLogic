# EnergoLogic

EnergoLogic — инженерная платформа, в которой **каноническая электрическая модель является источником истины**, а пользовательские интерфейсы являются проекциями и адаптерами этой модели.

Текущий этап: `ELECTRICAL-DOMAIN-PROFILE-V1-001`.

## Базовые архитектурные инварианты

1. **Visio — первый frontend**, но не system of record.
2. **VSDX/ShapeSheet/COM не являются canonical source of truth**.
3. Каноническая schema и электрическая семантика разделены: schema задаёт структурный контракт, named domain profiles задают более строгие инженерные правила.
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

Явно выбираемый профиль `electrical-v1` формализует первый поддержанный доменный subset:

- `bus(node)`;
- `circuit_breaker(a,b)`;
- `current_transformer(a,b)`;
- `external_link(node)`.

Профиль проверяет:

- exact terminal contracts;
- каноническое `attributes.nominal_voltage_v`;
- nominal-voltage consistency;
- bounded terminal degree;
- duplicate electrical edges;
- intra-element external connections.

Напряжение хранится в **целых вольтах**, независимо от frontend display units. Например, Visio/VTD `35 kV` → canonical `35000 V`.

## Быстрый запуск

```bash
python -m pip install -e .

# Открытая структурная schema 0.1:
energologic validate examples/minimal.energologic.json

# Строгая электрическая семантика:
energologic validate examples/kru35-v1-cell.electrical-v1.json --profile electrical-v1

energologic canonicalize examples/minimal.energologic.json
energologic fingerprint examples/minimal.energologic.json

python -m unittest discover -s tests -v
```

## Структура

```text
src/energologic/core/          structural canonical model + deterministic runtime
src/energologic/domain/        explicit electrical semantic profiles
src/energologic/frontends/     frontend contracts/adapters
schema/                        external versioned structural contracts
examples/                      canonical-model fixtures
docs/architecture/             ADRs
docs/work-items/               work-item evidence
tests/                         acceptance/regression tests
```

## Текущая граница

`electrical-v1` намеренно **не** является полной таксономией оборудования.

Пока отдельно остаются:

- switching-state semantics;
- multi-voltage transformer semantics;
- Planner;
- РЗА/protection;
- CIM;
- pandapower и другие solver-интеграции.

Они должны добавляться отдельными work items с собственными контрактами и evidence.

## Процесс изменений

Рабочий процесс проекта:

**Issue → branch → Draft PR → implementation/tests/evidence → owner acceptance**

Merge и Ready for Review запрещены без явной команды владельца проекта.
