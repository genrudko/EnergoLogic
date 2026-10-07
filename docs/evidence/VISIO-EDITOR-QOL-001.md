# VISIO-EDITOR-QOL-001 — final V364 evidence

**Evidence date:** 2026-10-07
**Status:** live runtime baseline accepted; EnergoLogic PR #12 owner merge gate remains.

This document supersedes the previous running probe diary as the current evidence summary. Historical v3.x investigation remains in Git history.

## Source identity

### EnergoLogic

- repository: `genrudko/EnergoLogic`;
- work item: `VISIO-EDITOR-QOL-001`;
- Issue #11;
- Draft PR #12;
- branch: `visio/visio-editor-qol-001`.

### Live runtime / bridge

- repository: `genrudko/development-bridge`;
- branch: `feature/energologic-visio-qol-001`;
- accepted runtime commit: `5695108cf9602ab93ac8223fe0f90c4e7d658209`;
- documentation-only portable wording follow-up: `b0fd952`.

## Accepted runtime versions

- Editor: **V364**;
- ProgID: `EnergoLogic.VisioEditorAddinV364`;
- API: `0.3.64`;
- managed extension/package transport: `2026.10.06.213`.

V364 was compiled, registered and connected in the running Visio. The final status check reported the current ProgID connected with native UI available.

## Functional regression evidence

The final stabilization regression exercised live production APIs on disposable pages:

- Coordinates;
- Nudge Right/Left;
- Exact Offset forward/reverse;
- Snap to 5 mm grid;
- Align X;
- Align Y;
- Distribute Selection X;
- Measure Selection Distance;
- Duplicate Selected;
- Base Move;
- Base Copy.

Representative exact checks included snap to 60 × 40 mm and reversible offsets returning to the original coordinates.

The previously accepted cell/equipment operations from the same work item remain part of the V364 baseline: Select/Renumber/Duplicate/Move Cell, Cell Pitch, Replace/Insert Equipment, bus editing, reconnect, Repair Glue and Scheme Doctor.

## Native topology transaction evidence

### Root cause established

A real moved double-ended 1-D connector may lose one endpoint Glue implicitly during `Selection.Move`; normal Undo then cannot always reconstruct the original endpoint formula.

Explicit selective pre-detach of qualified managed double-ended endpoints, performed inside the same helper-owned native UndoScope, produces symmetric forward/Undo/Redo behavior.

Blanket detach was rejected because VTD elements may use non-standard endpoint formulas that generic Glue repair cannot safely recreate.

### Extra Undo-unit root cause

The editor wrapper previously reassigned `ActiveWindow.Page` even when the target page was already active. That same-page assignment could create a separate native Undo unit through Visio/VTD UI events.

Production wrapper now activates only when target document/page differs. Repeated `COMAddIns.Update()` was also removed from the hot path.

### Single real-cell Move

Accepted production path on an 11-member cell:

- forward movement: +40 mm;
- expected external/internal Glue restored;
- one native `Application.Undo()` restored exact baseline geometry/Glue;
- one native `Application.Redo()` restored exact forward state.

### Multi-step DistributePitch

Accepted production transaction with two MoveSteps:

- forward: two cells changed target slots in one helper scope;
- one native Undo compared 26 shapes × `PinX/BeginX/BeginY/EndX/EndY/Width` against the clean baseline;
- mismatch count: **0**;
- one Redo restored expected slot positions and Glue.

This is the accepted production transaction architecture documented in `docs/visio/TOPOLOGY-UNDO.md`.

## Final V364 smoke

Acceptance document:

`KRU-35_normal_scheme_v2_energologic_qol_host_v1.vsdm`

Canonical reusable acceptance page:

`UI-V318-Pitch-Acceptance`

Disposable final page:

`UI-FINAL-V364-SMOKE` (deleted after acceptance)

Observed result:

- shape 155 moved slot 3 → 4;
- dx: +40.00 mm;
- operation result: success;
- Glue restored: 3;
- connections checked: 8;
- shape count: 44 → 44;
- shape 155 Begin/End position consistent at target;
- shape 244 retained both Glue endpoints and zero-width vertical geometry.

## Cleanup / production-code evidence

Intermediate research paths were removed from production source:

- IVBUndo custom mutation classes/probes;
- cross-call UndoScope probes;
- bare Undo/Redo acceptance probes;
- OS Ctrl+Z acceptance worker/tools;
- helper probe-only Undo modes.

Read-only operational diagnostics useful for support remain.

## Tests

EnergoLogic PR #12 reconciliation branch:

- `PYTHONPATH=src python3 -m unittest discover -s tests -v` — **120/120 PASS**.

Development-bridge final focused Visio suite:

- **139 passed**;
- `python -W error -m py_compile managed/visio/visio_managed_extension.py` — PASS;
- `git diff --check` — PASS.

Full development-bridge repository run:

- 2507 passed, 1 failed;
- the only failure was proven pre-existing and unrelated: Coordinator UI test expected `poll-leader-v1` while its parent HEAD HTML already used `poll-leader-v2`;
- rerun with exactly that pre-existing test deselected: **2507 passed, 1 deselected in 110.30 s**.

The unrelated Coordinator file/test was not modified by the V364 baseline commit.

## Portable package evidence

`EnergoLogic-Visio-Editor-Kit-0.3.64.zip`

- size: 689,913 bytes;
- SHA-256: `3a584ee4bc1178809b1fe47bca42904446a2901d53c7eeb611bb2d4dcc820aff`;
- 23 manifest files;
- 10 project-owned/personal ГОСТ stencils;
- VTD third-party assets excluded.

The target installer validates prebuilt binaries and manifest; it does not compile.

Release dependency validation confirms no runtime assembly dependency on Office/Extensibility/Visual Studio Interop PIA.

## Compatibility boundary

Architectural/package target:

- Windows 10/11;
- Visio 2010+;
- x86/x64 where applicable.

Physical live evidence currently exists for the installed Visio 16.x host only. Historical SKU/bitness combinations remain WS-3 qualification tasks.

## Final conclusion

The Visio editor QoL/topology/packaging implementation is no longer an open research blocker. V364 is the accepted implementation baseline. Future Visio work should be either:

- compatibility/maintenance;
- rendering/integration for new EnergoLogic capabilities;
- a separately bounded new frontend feature.

Do not reopen rejected Undo/interop experiments without new contradictory evidence.
