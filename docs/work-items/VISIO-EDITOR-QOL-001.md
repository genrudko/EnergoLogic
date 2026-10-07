# VISIO-EDITOR-QOL-001 — EnergoLogic Visio UX

Status: **Runtime implementation accepted live as V364; EnergoLogic PR #12 reconciliation complete in branch; owner Ready/Merge pending**
Issue: #11
Draft PR: #12
EnergoLogic branch: `visio/visio-editor-qol-001`
Live runtime source: `genrudko/development-bridge@5695108cf9602ab93ac8223fe0f90c4e7d658209`

## Goal

Make Microsoft Visio a practical engineering frontend for EnergoLogic: replace repetitive manual copy/paste/move/align/glue/rename work with bounded engineering commands while preserving the invariant that the canonical electrical model remains source of truth.

## Final accepted baseline

- Editor **V364**;
- API `0.3.64`;
- ProgID `EnergoLogic.VisioEditorAddinV364`;
- managed extension/package transport `2026.10.06.213`;
- current-host live acceptance: Visio 16.x;
- Windows target: 10/11;
- architectural/package target: Visio 2010+ x86/x64 where applicable.

## Completed scope

### Editor / cell operations

- Select / Renumber Cell;
- Duplicate Cell Left / Right;
- Move Cell Left / Right;
- topology-safe Cell Pitch measure/distribute;
- Replace Equipment;
- Insert Equipment into Existing Connection;
- Extend/Trim Bus;
- Reconnect Begin/End;
- Repair Glue;
- Scheme Doctor / diagnostics.

### Selection / geometry QoL

- Duplicate Selected;
- copy selected left/right;
- Copy/Paste with Base Point;
- Move with Base Point;
- Exact Offset;
- Coordinates;
- Smart Nudge;
- Align X/Y;
- Distribute X/Y;
- Measure Distance/Pitch;
- Snap to 5 mm grid.

### Native UX

- RibbonX;
- context menu;
- Russian labels/help/feedback;
- modeless parameter panel;
- explicit diagnostic/result surfaces.

### Topology and transaction safety

Production topology-sensitive commands use an external helper that owns geometry mutation, Glue restoration/verification and a single native Visio UndoScope in one COM process.

Accepted live evidence includes exact one-step native Undo/Redo for:

- a real-cell production Move;
- multi-step Cell Pitch distribution containing two MoveSteps in one transaction.

Rejected research paths (`IVBUndoUnit` ShapeSheet mutation, cross-call held scopes, probe-only Undo tools) are not production architecture.

### Standalone package

Canonical package:

`EnergoLogic-Visio-Editor-Kit-0.3.64.zip`

- 689,913 bytes;
- SHA-256 `3a584ee4bc1178809b1fe47bca42904446a2901d53c7eeb611bb2d4dcc820aff`;
- prebuilt AnyCPU DLL/helper;
- manifest entries: 23;
- 10 personal ГОСТ stencils;
- third-party VTD excluded;
- target-side compiler/PIA/Visual Studio/Python/Internet not required.

## Final live smoke

On a disposable duplicate of `UI-V318-Pitch-Acceptance`:

- cell anchor 155: slot 3 → slot 4;
- dx = +40.00 mm;
- state = success;
- Glue restored = 3;
- connections verified = 8;
- shapes = 44 → 44;
- fragile 1-D geometry remained consistent.

Temporary V364/V362 finalization pages were deleted after acceptance. Historical older probe pages were intentionally not mass-deleted.

## Remaining scope that is NOT a blocker for closing this work item

### Cross-version live compatibility

Physical live qualification remains for historical Visio SKUs/bitnesses. This belongs to continuous WS-3 compatibility work and must not reopen the editor architecture unless evidence shows an incompatibility.

### Future product integration

Future simulation/result rendering, generator integration and site-specific UI are new work items. They consume the accepted frontend contract; they are not unfinished QoL scope.

## Explicit out of scope

- electrical solver implementation;
- protection/RZA algorithms;
- Rules Engine;
- full legacy canonical importer;
- Scheme Generator;
- Kochubeevskaya Site Profile;
- mass normalization/rewrite of VTD masters.

## Documentation

Current Visio documentation lives under `docs/visio/`.
Historical intermediate v3.x research remains available in Git history but is superseded by the V364 baseline/evidence.

## Governance

PR #12 remains **Draft**. Ready for Review and merge require explicit owner command.
