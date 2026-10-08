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

## User-run isolated Windows overlay canary (2026-10-08 extension)

The current production Visio Bridge has **no allowed read-only tool for GetViewRect/GetWindowRect or native HWND geometry**, while Desktop Commander shows **no online Windows desktop device**. We therefore cannot directly execute local WinForms graphics from the cloud through an authorized connector; we did **not** attempt to use blocked managed-extension update operations.

A standalone local diagnostic prototype is supplied in `tools/p0b_live_overlay_probe.ps1`:

- Windows PowerShell 5.1 / STA; connects to existing `Visio.Application` via COM ROT, never starts or saves a Visio document.
- Restricts itself to *exact* user-saved test document name `EnergoLogic_Protection_Live_Test_20261008.vsdm`, page `MCP-v2`, breaker shape 66 and bus shape 101. If another page/window/document is selected, overlay hides.
- Reads `GetViewRect`, `GetWindowRect`, `WindowHandle32`, Win32 `GetClientRect`/`ClientToScreen` and optional window DPI, projects just a **magenta bus segment + cyan breaker marker**, with clearly labeled **TEST ONLY / NOT TELEMETRY**. Existing Visio symbols and colors remain unchanged. Hides if another application is foreground.
- Renders in a borderless click-through/no-activate transient WinForms overlay and supplies a separate Stop controller; closes/removes overlay when the controller exits; writes bounded read-only geometry samples to local `%TEMP%` JSONL.
- `tools/p0b_probe_static_validate.ps1` checks PowerShell syntax and compiles the embedded C# **without starting Visio**. A Windows-only unittest exercises this validator in GitHub Windows CI. This is a static compilation gate, **not live visual/zoom/scroll acceptance**.
- **No change** to existing development-bridge V364 add-in or the user's saved documents. User must run the probe in their interactive Windows session; it is not yet installed or exercised there.

## Screenshot-driven live findings and repair candidate (2026-10-08)

Owner ran initial Windows probe on the isolated `MCP-v2` test Visio copy and provided a screenshot: visible cyan breaker marker approximately aligned with V-1-35, magenta conductor badly shifted to the left and slightly above the real brown bus, yellow `ТЕСТОВЫЙ СЛОЙ — НЕ ТЕЛЕМЕТРИЯ` drawn over Visio upper ruler; overlay visibly flickered. This **fails** full P0-B live visual acceptance (though it confirms the temporary WinForms overlay actually appears over desktop Visio).

Independent **read-only** Visio Bridge shape 101 `Шина10` ShapeSheet: `PinX=65 mm`, `PinY=255 mm`, `Width=290 mm`, `LocPinX=0 mm`, `LocPinY=0 mm`, `Angle=0 deg`. Initial probe erroneously assumed `PinX` equals conductor **center** and applied `PinX ± Width/2`, displacing the projected bus by 145 mm. Visio's shape pin references local `LocPin`, hence proper unrotated line endpoints `(PinX-LocPinX, PinY-LocPinY)` and `(PinX-LocPinX+Width, PinY-LocPinY)` (provided `LocPinY=0`). Source fixed accordingly; unsupported non-zero angle now rejected. This is independent of actual topology/energized coloring.

Yellow overlay text was incorrectly painted at its local screen `(18,10)` location, coinciding with the drawing's ruler. It is removed from the transient overlay; explanatory label remains in external controller only. Timer previously invalidated a full transparent window every 400ms even with no geometry changes; now redraw only if bounds/points changed beyond tolerance. These changes are **candidates pending user's repeat screenshot and log**, not proof flicker is completely resolved.

Windows CI static validator guards `LocPinX` use and absence of former width/2 and yellow C# label; current state must be checked against updated head and latest CI before any success assertion.

## Live geometry journal follow-up (2026-10-08, supplied by owner)

The user supplied **23** read-only JSONL entries from the second desktop overlay run, including scroll/zoom variations. The doc/page identity stayed `EnergoLogic_Protection_Live_Test_20261008.vsdm` / `MCP-v2`. Representative samples:

| State | Visio `GetViewRect` [page IU] | Windows host client [px] | Page units→pixel X/Y |
|---|---|---|---|
| Initial viewport | `[-1.040495,12.570304,20.205287,12.050056]` | `1471 × 903` | `72.803` vs `74.937` |
| Zoomed viewport | `[1.616245,11.728140,14.888107,8.878989]` | `1471 × 903` | `98.804` vs `101.701` |

In **both** zoom states, the drawing height implied by uniform X/Y scale is `1471 × view_height / view_width = 877.276966 px`. The host HWND client contains **25.723034 px more vertical extent**. The old probe incorrectly scaled drawing Y across all `903` client pixels; the distortion is a systematic **+2.932145%**, not pixel noise or Visio shape geometry. Horizontal/vertical scroll values in the source log update consistently at the same zoom. `client_screen=(489,1619,...)` is **not enough** to diagnose monitor placement as an error: multi-monitor virtual desktop origins may differ from a cropped screenshot.

Microsoft explicitly documents that `GetViewRect` is affected by rulers/page tabs; `GetWindowRect` and `WindowHandle32` are different host/window contracts. We therefore **must not hardcode a 26 px correction**, nor assume that all 25.723 px are at the top or bottom.

**Candidate fix in this PR (unqualified live):**

- Enumerate child HWNDs **read-only** under the selected Visio drawing window and consider a single large, fully contained candidate whose aspect ratio is substantially closer to `GetViewRect` than the host. Use the child's actual client screen rectangle when unique.
- When no unique candidate qualifies, the isolated demo uses a **marked diagnostic fallback**: uniform X/Y scale based on view width, with excess height distributed equally above/below the estimated drawing region. This assumption is *not* a Visio specification and may still be wrong for a particular ruler/scrollbar layout.
- Journal fields `viewport_source`, `drawing_screen`, `candidate_count`, `child_rects`, `scale_x_y`, `excluded_client_height` distinguish native-candidate vs estimated fallback and allow the next test to identify actual chrome offsets.
- The pure `estimate_centered_client_region` is explicitly experimental and unit tested on both logged zoom states (plus impossible aspect/unsupported chrome rejection). No baseline colors or ShapeSheet mutations.

**Gate remains OPEN:** alignment requires a new interactive screenshot and journal confirming exact native child-viewport or testing an estimated fallback. Fewer render artifacts/CI successes do not substitute for native Visio acceptance.

## Explicit NOT YET PROVEN

- Whether the geometry formula matches desktop Visio16.x exactly once page tabs, rulers, DPI scaling, display scaling and owner-relative window rectangles are considered.
- Whether a transparent window overlay remains synchronized and click-through without disrupting Visio selection and Undo; whether it prints or must be deliberately hidden on print.
- Whether Visio2010 x86/x64 supplies all needed capabilities on actual hardware.
- Original user's VSDM hash-based immutability (requires authorized Windows filesystem access and actual native overlay test). Only read-only MCP tool results are available now.

The result is a **candidate geometry contract**, not an accepted Visio presentation runtime. Draft PR should remain Draft until real desktop test and owner acceptance.
