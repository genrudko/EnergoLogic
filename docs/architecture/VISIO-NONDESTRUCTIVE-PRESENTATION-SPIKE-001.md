# P0-B — Visio non-destructive operational presentation spike

**Issue:** #43 `VISIO-NONDESTRUCTIVE-PRESENTATION-SPIKE-001`
**Status:** candidate/experimental; **NOT live-qualified**.
**Baseline:** EnergoLogic main with PR #12, #32, #34, #36, #42 merged, Visio Editor V364 API 0.3.64.

## Product boundary

EnergoLogic is a local engineering/operational helper, not industrial SCADA. Operative/simulation/replay diagram coloring, values and alarms must be an **ephemeral presentation** bound by canonical identities and qualified topology. Source of truth remains canonical model, never Visio color or ShapeSheet. Original user VSDM must not be changed by viewing, replay or testing.

## Primary Microsoft desktop Visio API candidates

- [Window.GetViewRect](https://learn.microsoft.com/en-us/office/vba/api/visio.window.getviewrect) returns visible rectangle in Visio page coordinates. Microsoft explicitly notes ruler/page-tabs can affect it.
- [Window.GetWindowRect](https://learn.microsoft.com/en-us/office/vba/api/visio.window.getwindowrect) returns drawing/window client bounds in pixels **relative to its owner window** (e.g. MDICLIENT), not guaranteed to be screen coordinates. Window/monitor origin requires separate host composition.
- [Windows.ViewChanged](https://learn.microsoft.com/en-us/office/vba/api/visio.windows.viewchanged) fires when Visio drawing zoom/scroll changes; implement invalidation of a generation-bound coordinate snapshot and force redraw only when coherent data are available.
- [ShapeView.addOverlay](https://learn.microsoft.com/en-us/javascript/api/visio/visio.shapeview?view=visio-js-1.1) belongs to the Visio JavaScript/Web API surface. **Do not assume it is available in desktop Visio 2010 COM**.

These document **candidate primitives**, not tested availability on Visio 2010, 32-bit, current-host window handle details, live relative coordinate geometry, DPI, or multiple windows. No P0-B interactive desktop overlay acceptance is claimed.

## Strategies to compare

| Strategy | Key benefit | Risk / acceptance decision |
|---|---|---|
| **A. Existing V364 modeless panel** | Read-only state/time/measurements; no need to alter document/ShapeSheet; graceful fallback | Does not visually recolor conductors. **Default safe fallback** until B passes. |
| **B. Owned transient Win32/WinForms layer bound to document drawing viewport** | True transient color/annotation overlay and read-only hit-tested context; can be removed without changing file | Requires robust viewport HWND/client-origin, visual transform across zoom/pan, selection, DPI, scrollbars/page-tabs, window transitions, focus and click-through; only **experimental candidate**. |
| **C. Disposable dedicated display copy** | Conventional Visio rendering can be used on an explicit isolated file | Save/reopen/Undo/cleanup risk; never mutate original; useful as debug fallback but **not preferred operational runtime**. |
| **D. Write dynamic ShapeSheet colors into original** | Easy implementation | **Rejected** for runtime: persistent document pollution and unacceptable replay/Undo semantics. |

### Technology recommendation at start of spike

Research **B** in isolation while preserving **A** as a functional baseline. Do **not** select B for production without real visual Win16.x acceptance plus capability fallback and older-version matrix. Visio 2010/2013/2016/2019/2021 x86/x64 remain PENDING LIVE. An installed Visio 16.x pass cannot automatically qualify historic versions.

## Initial pure geometry contract

The experimental implementation `frontends/visio/viewport_spike.py` defines immutable:

- `VisioDrawingViewport`: qualified document/page/window identity, view generation, page rect and **drawing-client-local** pixel dimensions. Page and anchors must share explicitly tagged `visio_internal` coordinate unit.
- `VisioPageAnchor`: same identity/generation/unit plus an explicit page point, already obtained from qualified Visio coordinates.
- `project_point`: bounded page→client coordinate conversion and offscreen suppression.
- `project_segment`: accepted conductor segment with clipping to viewport bounds. It **does not reconstruct electrical Glue/topology or supply source states**.

The transformation reverses Visio page Y (bottom-up) to Windows client pixel Y (top-down) as a *provisional mapping*. Actual pixel-perfect mapping remains **unqualified** until measured on the running desktop window. The proof deliberately does not calculate window screen origin or claim hi-DPI correctness: that belongs to the host viewport collector/overlay owner, not the solver or canonical model.

Fail closed on invalid/nonfinite geometry, unknown units, stale generation, mismatched document/page/window or missing identity. A `Windows.ViewChanged`, page/active-document switch, mode exit, resize, monitor change, or lost window must invalidate the host snapshot and hide the overlay until a valid sample arrives.

## Actual geometry caveat exposed by user's 2026-10-08 log

A screen overlay cannot independently derive `scaleX = clientWidth/viewWidth` and `scaleY = clientHeight/viewHeight` from `WindowHandle32.GetClientRect` and `Visio.GetViewRect`. The latter spans **page-coordinate visible drawing space**, the former may include Visio UI chrome. Real 1471×903 host with either 20.205×12.050 or 14.888×8.879 page view implied **877.277 drawable height, 25.723 excess pixels** at both zoom levels. Independent X/Y scales introduce **2.932% vertical distortion**.

The new desktop probe first surveys native child HWND geometry (read-only) for an unambiguous canvas-like child; otherwise it exposes a clearly labelled **estimated** equal-split inset, not an accepted production transform. All overlay coordinates use the **same page-unit→pixel scale**, and the journal includes the actual drawing-screen candidate, source, insets and child rectangles. The production choice must require measured canvas origin, not a hard-coded ruler/tab offset or a guessed 50/50 distribution.

## Next strictly bounded Windows live experiment

1. Use the **separate** `EnergoLogic_Protection_Live_Test_20261008.vsdm`, never the single-page working CLEAN file; verify document/page identity and unchanged original file.
2. Implement/qualify a *read-only* viewport probe in managed V364 development bridge which returns exact window/doc/page identity, GetViewRect, GetWindowRect, actual drawing client HWND bounds, DPI awareness and event sequence. No new pages or shape writes.
3. Acquire host probe results at two zoom levels, two scroll positions, different window sizes and selection; compare with independently observed anchors (V-1-35 shape 66 is a candidate marker, not an electrical canonical binding).
4. Render **transient graphics only**, not ShapeSheet, with event-driven invalidation. Test click-through/focus, scrolling, DPI, multiple windows, document switches and topmost behavior; measure drift and redraw latency.
5. Capture before/after hash of original .vsdm and shape/page/state readback; verify zero persistent mutations and no new Visio pages, with closed overlay process. No field commands.
6. If native non-destructive overlay cannot be made robust with permitted APIs, formally select **A** as accepted fallback and consider only explicit isolated-file mode for further experiments.

## Exit gates

- [x] Required target API references and legacy-web exclusion documented.
- [x] Pure transform contract and deterministic negative tests supplied; **14/14** passed locally.
- [x] Current-host read-only page setup of separate Visio test copy: A3 420 × 297 mm, no content changes.
- [ ] Actual viewport collector reading GetViewRect/GetWindowRect on current installed Visio.
- [ ] Native ephemeral overlay drawn and removed without file mutation, pan/zoom/DPI behavior independently verified.
- [ ] Compatibility/printing/focus/Undo/cleanup evidence, no false claims of 2010 live qualification.
- [ ] Owner acceptance and Ready/Merge as separate explicit command.

Do not confuse a passing geometry unit suite with accepted native integration.
