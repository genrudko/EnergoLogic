# EnergoLogic — инструкция для исполнителей

Этот документ обязателен для любого человека/агента, который начинает новый work item или продолжает существующий.

## 1. Что прочитать перед работой

В таком порядке:

1. `README.md` — продукт и базовые инварианты;
2. `docs/PROJECT-STATUS.md` — что реально готово сейчас;
3. `docs/roadmap.md` — текущий порядок и зависимости;
4. `docs/architecture/CANONICAL-PRODUCT-ARCHITECTURE.md` — целевая архитектура;
5. relevant contract/ADR в `docs/architecture/`;
6. relevant work item в `docs/work-items/`;
7. relevant evidence в `docs/evidence/`;
8. только после этого — реализация и тесты.

Не использовать старый чат, старый PR body или historical checklist как более сильный source of truth, чем current repo state.

## 2. Перед созданием нового work item

Проверить:

- capability уже не реализована в `main`;
- нет открытой branch/PR с тем же bounded scope;
- определён upstream contract/gate;
- ясно, что является входом и выходом work item;
- перечислено out-of-scope;
- acceptance можно проверить детерминированно;
- terminology concepts либо уже есть в Registry, либо добавляются отдельным bounded изменением;
- site-specific данные не протекают в generic code.

Если upstream ещё не принят, разрешён prototype против versioned mock/fixture, но нельзя объявлять его production integration.

## 3. Mandatory process

```text
Issue
  ↓
dedicated branch
  ↓
Draft PR
  ↓
implementation + tests + evidence
  ↓
owner acceptance
  ↓
Ready/Merge только по явной команде владельца
```

Не создавать лишние issue/branch/PR, если существует подходящий активный work item.

## 4. Где что делать

| Область | Основной путь | Что туда относится |
|---|---|---|
| Structural canonical core | `src/energologic/core/` | decode/validate/canonicalize/fingerprint/base contracts |
| Electrical semantics | `src/energologic/domain/` | equipment/state/transformer/phase/parameter semantics |
| Operational runtime | `src/energologic/operational/` | energization, source tracing, switching operations/timeline |
| Solver boundary | `src/energologic/solvers/` | DTO/contracts/adapters/result normalization |
| Protection | `src/energologic/protection/` | settings import, protection runtime, breaker failure, future functions |
| Terminology | `src/energologic/terminology/` | Registry, lookup, lint/provenance |
| Frontends | `src/energologic/frontends/` | Visio and future projection adapters only |
| External contracts | `schema/` | versioned JSON/external schemas |
| Fixtures | `examples/`, `tests/fixtures/` | synthetic/golden deterministic inputs/outputs |
| Architecture | `docs/architecture/` | stable contracts/decisions, not progress diary |
| Work items | `docs/work-items/` | bounded scope + acceptance checklist |
| Evidence | `docs/evidence/` | observed verification/results/limitations |
| Visio runtime docs | `docs/visio/` | current V364 baseline, packaging, acceptance |

## 5. Dependency rules

### Core

`energologic.core` must not import domain, frontend, COM, solver or protection stacks.

### Domain

`energologic.domain` may depend on core. It must not become a wrapper around pandapower/Visio/protection implementation.

### Operational

Consumes canonical/domain semantics. It does not infer electrical quantities that belong to solver, nor protection actions that belong to protection engine.

### Solver

Public contract uses EnergoLogic IDs/types and normalized units. No pandapower/OpenDSS DataFrame/index/type leaks through public API.

### Protection

Consumes explicit settings + explicit measured quantities + logical time. It emits declarative requests. It does not silently mutate canonical switch state.

### Frontend / Visio

Frontend displays/edits projections. Geometry does not become electrical truth. Connectivity is canonical terminal↔node and/or qualified native Glue evidence.

## 6. Fail-closed rules

Never guess when missing data changes engineering meaning.

Examples:

- do not infer exact voltage from nearby label if source only provides voltage class;
- do not infer zero-sequence data from positive sequence;
- do not infer a protection setting/basis/target;
- do not infer a source from element name/geometry;
- do not infer electrical connection from visual contact;
- do not silently choose one ambiguous legacy symbol classification;
- do not silently switch solver backend after failure;
- do not mark unsupported Visio version as live-qualified.

## 7. Tests and evidence

Минимальный набор для каждого work item:

- unit tests for local semantics;
- fail-closed/adversarial cases;
- deterministic ordering/fingerprint where applicable;
- golden fixture for numerical/serialized output where useful;
- integration test at public contract boundaries;
- Linux/Windows CI if runtime is cross-platform;
- live Visio acceptance only when COM/Visio behavior is intrinsic;
- evidence document with exact commands/results/known limitations.

Do not replace observed evidence with wording such as «должно работать».

## 8. Documentation update rule

Every accepted work item updates, when applicable:

1. relevant architecture contract;
2. its `docs/work-items/...` status;
3. `docs/evidence/...`;
4. `docs/PROJECT-STATUS.md` if project state changed;
5. `docs/roadmap.md` if dependencies/order changed;
6. README only for user-visible high-level baseline changes.

Historical evidence is preserved. If a pre-merge checklist becomes stale after merge, mark it archival rather than rewriting observed history.

## 9. Visio-specific execution rules

Read `docs/visio/README.md` and `docs/visio/DEVELOPMENT-ACCEPTANCE.md` before any Visio work.

Key rules:

- production V364 runtime source currently lives in `genrudko/development-bridge`, branch `feature/energologic-visio-qol-001`;
- EnergoLogic repo owns canonical/domain/frontend contracts, pure planners/tests and product documentation;
- destructive acceptance uses disposable pages/copies; source/reference pages are preserved;
- use actual native Glue/Connects and ShapeSheet evidence; visual overlap is not connectivity;
- topology-sensitive compound mutations must preserve the accepted helper-owned single UndoScope architecture;
- do not reintroduce cross-call held UndoScope or `IVBUndoUnit` research paths without new evidence;
- current V364 target installation is prebuilt/offline; do not add target-side compiler/PIA requirements;
- third-party VTD files are not silently redistributed;
- physical compatibility claims require actual SKU/bitness acceptance.

A development-bridge runtime change is not fully reconciled until EnergoLogic Visio docs/evidence/version references are updated.

## 10. Site-specific work

Kochubeevskaya WPP is the principal real-world acceptance target, but its data are not generic defaults.

For site data always preserve:

- source/provenance;
- revision/date;
- source locator;
- uncertainty/unknown state;
- stable canonical IDs;
- separation between source-derived values and engineering assumptions.

Synthetic fixtures must be clearly labelled synthetic and must never be presented as real site settings/parameters.

## 11. Definition of done

A bounded item is not DONE merely because code exists.

DONE means:

- scope is implemented;
- public contract is explicit;
- tests/evidence pass;
- known limitations are documented;
- docs/status are reconciled;
- CI required by the item is green;
- owner acceptance/merge state is recorded correctly.
