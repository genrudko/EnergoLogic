# P0-B evidence — initial bounded viewport experiment

**Issue #43**, 2026-10-08, based on `main@80540e9120de35dd1fae8c9ce96780440b288818`.

## Source inspection / public API

- Visio Editor V364 `managed/visio/energologic_visio_editor_addin.cs` in development-bridge: existing WinForms/modeless panel tools; no existing accepted nonpersistent drawing viewport overlay.
- `managed/visio/VISIO_COMPATIBILITY_MATRIX.md` V364: installed desktop Visio16.x 64-bit LIVE PASS editor, Visio2010-current other SKUs/bitness **ARCH/PACKAGE PASS; PENDING LIVE**.
- Microsoft COM documentation: [GetViewRect](https://learn.microsoft.com/en-us/office/vba/api/visio.window.getviewrect), [GetWindowRect](https://learn.microsoft.com/en-us/office/vba/api/visio.window.getwindowrect), [Windows.ViewChanged](https://learn.microsoft.com/en-us/office/vba/api/visio.windows.viewchanged).
- Microsoft web-JavaScript [ShapeView.addOverlay](https://learn.microsoft.com/en-us/javascript/api/visio/visio.shapeview?view=visio-js-1.1): **NOT a Visio 2010 desktop COM fallback**.

## Read-only real Visio MCP observation

Production Master visio-bridge node `visio-workstation`:
- `list_open_documents` shows separate, manually saved `EnergoLogic_Protection_Live_Test_20261008.vsdm` with **1** page and existing scratch `Документ1`.
- `get_page_setup(doc_name=...Test..., page=MCP-v2)` returned PageWidth **420 mm** / **16.53543 IU**, PageHeight **297 mm** / **11.69291 IU**, PageScale/DrawingScale 1 mm. No mutation call made; shape/page state not changed.
- Existing MCP Visio tool catalog lacks a qualified `GetViewRect/GetWindowRect` collector and actual per-window client HWND+DPI API; therefore **no real viewport-to-pixel alignment has been measured**.

## Testable code

- `src/energologic/frontends/visio/viewport_spike.py`: only pure immutable transform and clipping; no COM/Win32/drawing instructions.
- `tests/test_visio_viewport_spike.py`: **14 unit tests PASS** on VPS, covering orientation assumption, pixel bounds, segment clipping, offscreen, zoom, scrolling with revision bump, stale/wrong doc/page/window, invalid dimensions/units, NaN/Inf and bool.
- Full existing+new test suite: **352 tests, 9 skipped, 0 failures**; compileall PASS. This is **headless**, not a Visio live overlay test.

## Explicit NOT YET PROVEN

- Whether the geometry formula matches desktop Visio16.x exactly once page tabs, rulers, DPI scaling, display scaling and owner-relative window rectangles are considered.
- Whether a transparent window overlay remains synchronized and click-through without disrupting Visio selection and Undo; whether it prints or must be deliberately hidden on print.
- Whether Visio2010 x86/x64 supplies all needed capabilities on actual hardware.
- Original user's VSDM hash-based immutability (requires authorized Windows filesystem access and actual native overlay test). Only read-only MCP tool results are available now.

The result is a **candidate geometry contract**, not an accepted Visio presentation runtime. Draft PR should remain Draft until real desktop test and owner acceptance.
