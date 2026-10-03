# EnergoLogic

EnergoLogic — инженерная платформа, в которой **каноническая электрическая модель является источником истины**, а пользовательские интерфейсы являются проекциями и адаптерами этой модели.

Текущий этап: `PROJECT-FOUNDATION-001`.

## Базовые архитектурные инварианты

1. **Visio — первый frontend**, потому что он уже даёт зрелую графическую среду и существующие электротехнические библиотеки.
2. **VSDX/ShapeSheet/COM не являются canonical source of truth**. Электрическая семантика хранится в versioned canonical model.
3. **Критический runtime детерминирован**: одинаковая модель даёт одинаковое каноническое представление, fingerprint и набор ошибок.
4. **LLM/агенты не участвуют в критической электрической логике**. Они могут помогать оператору или разработке, но не определяют корректность модели.
5. Core не зависит от Visio, COM и будущих solver/integration подсистем.

## Что реализовано в foundation baseline

- минимальная canonical-model schema `0.1`;
- Python core без runtime-зависимостей;
- структурное декодирование, семантическая валидация и канонизация;
- стабильный SHA-256 fingerprint модели;
- узкий контракт первого frontend — Visio;
- CLI для `validate`, `canonicalize`, `fingerprint`;
- unit tests и CI на Linux/Windows;
- ADR с архитектурными границами.

## Быстрый запуск

```bash
python -m pip install -e .
energologic validate examples/minimal.energologic.json
energologic canonicalize examples/minimal.energologic.json
energologic fingerprint examples/minimal.energologic.json
python -m unittest discover -s tests -v
```

## Структура

```text
src/energologic/core/          canonical model + deterministic runtime
src/energologic/frontends/    frontend contracts/adapters
schema/                        external versioned model contracts
examples/                      small canonical-model fixtures
docs/architecture/             ADR
docs/work-items/               work-item evidence
tests/                         acceptance/regression tests
```

## Граница текущего этапа

`PROJECT-FOUNDATION-001` **не** реализует Planner, РЗА, CIM, pandapower/solver integration и полноценную Visio COM-автоматизацию. Эти направления должны подключаться позже через отдельные work items, не протекая в core без явного архитектурного решения.

## Процесс изменений

Рабочий процесс проекта: **Issue → branch → Draft PR → implementation/tests/evidence → acceptance**.

Merge запрещён без явной команды владельца проекта.
