# EnergoLogic Visio Editor V364

## Purpose

V364 is the accepted editor/runtime baseline for the Visio engineering frontend. The editor replaces repetitive CAD-like shape manipulation with engineering-oriented commands while preserving native Visio/VTD topology and canonical-model boundaries.

## Engineering vocabulary

The editor works around explicit concepts:

- CELL;
- EQUIPMENT;
- TERMINAL;
- BUS;
- ANCHOR;
- CONNECTION.

A cell is not defined only by its bounding box or one connected component. Electrical core membership, visual/projected members and the engineering anchor are separate concepts.

## Live-qualified functional baseline

### Cell/topology operations

The accepted Visio line includes:

- Select Cell;
- Renumber Cell;
- Duplicate Cell Left/Right;
- Move Cell Left/Right;
- topology-safe Cell Pitch measure/distribute;
- Replace Equipment;
- Insert Equipment into Existing Connection;
- Extend / Trim Bus;
- Reconnect Begin / End;
- Repair Glue;
- Scheme Doctor / Visual Diagnostics.

### Selection and base-point operations

- Copy selected Left/Right;
- Duplicate Selected;
- Copy/Paste with Base Point;
- Move with Base Point;
- Exact Offset.

Selection-scoped operations preserve only relationships that belong to the selected subgraph. They do not invent external electrical attachment or clone managed cell identity blindly.

### Geometry helpers

- Coordinates;
- Smart Nudge presets;
- Align X / Align Y;
- Distribute selection X / Y;
- Measure distance/pitch;
- Snap selection to 5 mm grid.

Final V364 regression rechecked Coordinates, Nudge, Exact Offset, Snap, Align, Distribute X, Measure Distance, Duplicate Selected, Base Move and Base Copy on disposable pages.

### Native Visio UX

- EnergoLogic RibbonX surface;
- context-sensitive Visio right-click commands;
- Russian labels/help/feedback;
- built-in Office icons where applicable;
- modeless parameter panel;
- legacy toolbar hidden;
- explicit diagnostics/result dialogs.

## Electrical connectivity rule

Electrical attachment exists only when supported by one of the qualified representations:

1. native Visio Glue / `Page.Connects` / endpoint formulas;
2. canonical `terminal ↔ node` mapping;
3. a qualified importer reconstruction later persisted to the canonical model.

**Same coordinates are not a connection.**

Repair/Doctor may use geometry to find candidates, but automatic repair must fail closed on ambiguity.

## Cell anchor and bus pitch

For the accepted KRU-35 fixture, cell movement/distribution is based on explicit native bus slot order and engineering anchor position.

Do not derive left/right order as `User.nt ± 1`: native terminal identity and visible physical order are different concepts and may be non-monotonic.

A target slot must exist and be unambiguous. Occupied/ambiguous targets fail closed.

## Identity handling

Managed duplicated cells use instance metadata (`User.EnergoLogicCellId`) when explicit managed identity is required.

Rules:

- VTD masters are not modified to inject instance identity;
- source identity is not blindly cloned to a new logical cell;
- user-visible numbering and canonical identity are separate concerns;
- old/unmanaged diagrams remain importable through fallback mapping rules until migrated.

## Transaction architecture

V364 uses an external topology helper for compound topology-sensitive mutations. The helper owns geometry mutation, Glue restoration/verification and one native `Application` UndoScope in a single COM process.

See [`TOPOLOGY-UNDO.md`](TOPOLOGY-UNDO.md).

## Final V364 smoke

On a disposable duplicate of the accepted KRU-35 page:

- real cell anchor shape 155 moved slot 3 → 4;
- exact horizontal delta: +40.00 mm;
- restored Glue edges: 3;
- verified connections: 8;
- page shape count: 44 → 44;
- fragile 1-D shape geometry remained internally consistent.

The final smoke page was deleted after acceptance.

## What V364 does not mean

V364 does not make Visio the canonical model, solver or Rules Engine.

It also does not imply physical LIVE PASS for every historical Visio version. Cross-version qualification is tracked separately.
