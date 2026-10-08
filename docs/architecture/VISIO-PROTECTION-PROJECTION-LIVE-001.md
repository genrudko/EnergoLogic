# VISIO-PROTECTION-PROJECTION-LIVE-001 — bounded VTD action contract

**Issue #37.** Stacked on Integrated Protection Loop Draft PR #36; **not merged**. This is a gateway contract, not a live Visio MCP client implementation.

## Native VTD switching semantics

Accepted ADR 0005: `Actions.Row_1.Action = TRUE` means contacts **closed**, `FALSE` means **open**. The menu value `Положение Отключено` offers an opening action and therefore indicates *currently closed*, not currently open. Verify the consistency of both native value and menu before any action. `User.p` in the working position `рабочее` is separately required for the supported withdrawable breaker. Disabled or invisible actions are ineligible.

## Safe projection boundary

`apply_live_visio_projection(result, binding, gateway, execute=False)` is **dry-run by default**. The caller must supply:
- `IntegratedLoopResult.status == COMPLETED`, a successful simulated breaker operation and one exactly matching `VisioStateUpdate(switch_state=open)`, with fingerprint of the resulting canonical model;
- `LiveVisioBinding` explicitly naming canonical element ID, document basename and absolute Windows `.vsdm` path, page name, Visio shape ID, expected VTD breaker master name and a nonempty evidence provenance reference;
- a `VtdVisioGateway` which addresses those exact document/page/shape identifiers. No shape text/name-based guesses and no direct command to real equipment are permitted.

Prior to mutation: verify unique open document identity, exact full path, unique page, exact shape ID and VTD master name, and read native Action/Menu/withdrawable position. Recheck identity and closed state just before the action. Only when `execute=True` and all checks pass, invoke the existing `Actions.Row_1` **once** and read back. If already open: do not toggle; return `ALREADY_OPEN`. After an action attempt, communication failure or unexpected readback is `INDETERMINATE`, with **no automatic retry**. This cannot provide an atomic external transaction; it is a best-effort guarded single call.

## Observed live Visio VTD canary — 2026-10-08

Test performed through production Master MCP Visio Bridge, Windows node `visio-workstation`, on user-created CLEAN copy of WS0 scheme `KRU-35_EnergoLogic_CLEAN_WS0_20261008.vsdm`, dedicated keeper demo page `EnergoLogic-Switching-V1`, shape 1 (VTD `Выкатная тележка выключателя`, 35 kV). Initial native state Action TRUE (closed), menu `Положение Отключено`, working position. `trigger_shape_action(Row_1)` returned success; separate `get_vtd_state` yielded FALSE + `Положение Включено` (open). A second action returned TRUE and state was read back restored. This establishes real VTD action and readback through MCP, **not execution of this new Python adapter against Visio**, not simulation-triggered dispatch, and not an Undo/persistence test.

## WS-0 document cleanup — partial

The user manually created a new copy before cleanup, preserving the original 136-page file. Exactly 131 of 136 pages were verified service probes named `UI-*`/`QoL-*`. Retain five pages `Страница-1`, `MCP-v2`, `EnergoLogic-V1`, `EnergoLogic-Switching-V1`, `EnergoLogic-Transformer-V1`. 23 test pages were successfully deleted from CLEAN copy; subsequent deletion call was blocked by OpenAI safety checks and not retried using alternate means. Subsequent read-only check: CLEAN contains **113 pages (108 probes + five retained)**. User stated they saved the CLEAN file via Ctrl+S. Bridge in-place save is intentionally forbidden, and SaveAs failed even on a blank new document. No claim that CLEAN is completely cleaned; no further automated deletion should be attempted while blocked.

## Known non-qualifications / next acceptance gates

- Adapter currently has only one-off synthetic smoke checks (5/5); writing its dedicated persistent test suite was blocked. Its state is **provisional** until adversarial automated CI, not accepted for production.
- Gateway to actually invoke Master MCP from a Python adapter process remains to be implemented/qualified. An explicit manual test-map between a synthetic canonical breaker and the VTD demo symbol is not a verified site mapping or full canonical capture.
- VTD master can differ for fixed/disconnector apparatus; arbitrary unsupported masters must fail closed. Additional trusted document identity + shape binding and live Undo/Save acceptance remain required.
- No real CT mapping, protection settings approval, normative switching permission, SCADA/field controls, or physical switching is performed here.
