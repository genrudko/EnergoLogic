# LEGACY-VISIO-INSPECTOR-001

Status: In progress  
Workstream: WS-4 — Legacy Visio Migration  
Issue: #13  
Draft PR: #16  
Branch: `migration/legacy-visio-inspector-001`  
Base: `main` @ `9edc59a0e83f17e94c50ca10f7feac320332b2a1`

## Цель

Создать read-only foundation: `Legacy Visio → structured inspection data` без миграции в canonical model, без замены фигур и без изменения исходного документа.

Главный будущий acceptance-case — существующая большая схема Кочубеевской ВЭС, созданная без EnergoLogic masters.

## Изоляция от WS-0

- работа не ведётся в `visio/visio-editor-qol-001`;
- EnergoLogic Editor / Cell Pitch / текущая Glue implementation не меняются;
- Glue repair не выполняется;
- canonical architecture и canonical electrical semantics не меняются;
- ветка создана непосредственно от `main`, а не от Draft PR #12.

## Архитектура Inspector

### Observable snapshot

`LegacyDocumentSnapshot` / `LegacyPageSnapshot` / `LegacyShapeSnapshot` содержат только наблюдаемые Visio-данные: document metadata, pages, shapes, parent/group relation, master identity, shape type, geometry/rotation, text, layers, ShapeSheet cells, connection points, Begin/End formulas и native `Page.Connects`.

Snapshot не является canonical electrical model.

### Deterministic inspection

`inspect_legacy_visio(snapshot)` — pure/read-only transformation. Она не мутирует snapshot, не создаёт canonical electrical entities, не меняет Glue и не регенерирует Visio.

### Read-only VSDX package source

`capture_vsdx_package(path)` реализует первый реальный source adapter без COM: VSDX открывается как OPC/ZIP package строго на чтение, XML разбирается стандартной библиотекой Python, а SHA-256 исходного файла проверяется до и после capture.

Из VSDX package source извлекаются:

- page metadata/dimensions;
- recursive/nested Shapes;
- Shape ID / Name / NameU / Type;
- Master Name/NameU и MasterShape ID;
- XForm geometry/rotation;
- raw ShapeSheet cells + Geometry rows;
- text;
- layer membership;
- connection-point rows;
- BeginX/BeginY/EndX/EndY formulas;
- native `<Connects>/<Connect>` relations.

Этот adapter покрывает VSDX. Старый binary `.vsd` и live COM остаются отдельными future collectors за тем же `LegacyVisioSnapshotSource` contract и не требуют изменения inspection/fingerprint layer.

## Fingerprinting

Family fingerprint не зависит от Shape ID и абсолютных PinX/PinY. Отдельно считаются:

1. `master_signature`;
2. `geometry_signature`;
3. `group_signature`;
4. `shapesheet_signature`;
5. `connection_point_signature`;
6. `text_pattern` — отдельно от geometry family.

Numeric Master/Shape IDs сохраняются в raw instance data, но не входят в stable family key. Для master identity приоритет имеет стабильный `Master.NameU`; display/localized `Master.Name` используется только как fallback и не должен раскалывать family после переименования. Geometry нормализуется по собственному bounding box, поэтому абсолютный перенос и uniform scaling не меняют family. Child geometry нормализуется относительно родителя. ShapeSheet formula structure нормализуется: literal numbers/strings маскируются, XForm исключён, Geometry анализируется отдельно.

Designation text не ломает family. Например, `QF-101` и `QF-202` имеют один `text_pattern = qf-#`.

## Topology evidence

Evidence precedence:

1. native `Page.Connects` / Glue → `exact_native`;
2. endpoint formulas;
3. connection points;
4. spatial proximity — только future fallback;
5. topology context — future classifier input.

Критический invariant: визуальное касание не является доказательством электрической связи. В текущей foundation `glue_graph.inferred_edges` остаётся пустым.

## Confidence vocabulary

- `exact_native`;
- `high_confidence`;
- `review_recommended`;
- `ambiguous`;
- `unknown`.

## Inspection report

Schema: `schema/legacy-visio-inspection-0.1.schema.json`.

Разделы: `document`, `pages`, `symbol_families`, `instances`, `text_designation_candidates`, `glue_graph`, `endpoint_formula_candidates`, `connection_point_inventory`, `ambiguous_unclassified`, `statistics`, `inspection_fingerprint`.

Формат нейтрален относительно будущего importer'а и не требует canonical-domain taxonomy.

## Synthetic acceptance

- одинаковый symbol в разных координатах и с разными Shape IDs → один family;
- разные normalized geometry → разные family;
- designation text variation не ломает family;
- groups/nested shapes сохраняются;
- native Glue получает `exact_native`;
- visual contact не создаёт inferred edge;
- Inspector не мутирует input;
- результат детерминирован.

## Out of scope

- replacement legacy shapes;
- canonical import;
- Scheme Generator / regeneration;
- source Visio editing;
- Glue repair;
- production spatial classifier;
- mapping `legacy family → CircuitBreaker/...`;
- изменение canonical architecture.

## Owner gate

PR остаётся Draft. Ready for Review и merge — только по явной команде владельца.
