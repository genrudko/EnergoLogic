# VISIO-NONDESTRUCTIVE-PRESENTATION-SPIKE-001 — P0-B

**Issue:** #43 · **Branch:** `spike/visio-nondestructive-presentation-001` · **Base:** main `80540e9` · **Status:** Draft experimental.

## Objective

Qualify how EnergoLogic can show **temporary calculated/simulated operational indication on desktop Visio 2010–current** without permanent modification of original VSDM/VSDX. No own full drawing editor, no SCADA integration, no operational control of physical devices.

## Existing contracts

- `PRODUCT-BOUNDARY-AND-WORKSPACE-MODES.md` — modes and local-only scope.
- `OPERATIONAL-STATE-AND-PRESENTATION-CONTRACT.md` — terminal/source color vs actual measured U, quality and provenance.
- `LOCAL-WORKBENCH-IMPLEMENTATION-PROGRAM.md` — P0-B, parallel with P0-C/P0-D.
- `VISIO_COMPATIBILITY_MATRIX.md` in development-bridge V364 — Win16.x live, Visio 2010–2021 versions pending.

## Delivered in this initial stage

- Microsoft desktop Visio read-only window API candidates and explicit JavaScript-Web exclusion; alternatives/fallbacks in [architecture spike](../architecture/VISIO-NONDESTRUCTIVE-PRESENTATION-SPIKE-001.md).
- Pure Python page-to-window client transform with exact document/page/window/view-generation identity and offscreen clipping.
- Unit tests for zoom/scroll/generation invalidation, no mutation, numeric invalidity, clipping, stale scope.

## Not yet complete

- Native managed V364/Visio COM collector for GetViewRect/GetWindowRect with HWND origin and DPI.
- Actual graphic overlay on Windows, pan/zoom/scroll, clicking, multiwindow/printing/Undo evidence.
- 2010+ live compatibility matrix; all unsupported versions remain unqualified.

## Acceptance

- [x] Source/candidate/fallback architecture documented.
- [x] Pure model and negative geometry tests locally green.
- [x] Separate test document identified and inspected read-only; source unchanged.
- [ ] Real Visio view and pixels measured via host.
- [ ] No persistent VSDM change demonstrated after transient graphics.
- [ ] Version/bitness capability matrix and window lifecycle evidence complete.
- [ ] Owner Ready/Merge approval separately explicit.

No production overlay is claimed merely because these deterministic tests pass.
