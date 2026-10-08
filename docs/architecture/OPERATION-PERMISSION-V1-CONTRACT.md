# Operation Permission v1 — model-bound switching evidence

**Work item:** OPERATION-PERMISSION-CONTRACT-001 · Issue #33 · WS-6, WS-10 precursor. **Status:** Draft, not merged.

## Scope and authority

This is a **headless, deterministic evidence verification adapter for simulation**. It does **not** implement an earthing switch, mechanical/electrical interlocks, dispatcher workflow, site Rules Engine, normative validation or authorization for live substation operations. A provenance reference is structurally checked, not authenticated or independently qualified.

Canonical English identifiers: `OperationPermissionEvidence`, `PermissionAssertion`, `PermissionDecision`; user-facing Russian terms: **разрешение оперативного переключения**, **блокировка операции**, **недостаточно данных**, **источник подтверждения**, **межблокировка** (interlock). Do not interpret `permitted` as physical switching clearance.

## Input / binding

`OperationPermissionEvidence` requires:
- nonempty `policy_id`; exact `model_fingerprint`;
- exact `operation_id`, `element_id`, `operation_type` (`switch_state` or `withdrawable_position`) and `target_value`;
- nonempty collection of assertions, each a distinct nonempty `requirement_id`, `outcome=pass|fail|unknown`, and nonempty `source_ref`.

The model fingerprint is compared to both `fingerprint(model)` and the preceding operational snapshot. No fallback matching, fuzzy attribute search, guessing source identity or site facts.

## Result / gate

`evaluate_operation_permission` yields `OperationPermissionResult`:
- **PERMITTED:** all distinct supplied assertions are `pass`, bound to the same model and operation, with source references. This verifies completeness of *submitted claims*, not electrical safety.
- **BLOCKED:** one or more assertions are explicit `fail`.
- **UNKNOWN:** missing/invalid evidence, empty collection, stale model, mismatched target, duplicate requirement, missing provenance, unknown outcome or invalid operational state.

In BLOCKED or UNKNOWN, adapter `permission_evidence_validator(evidence)` returns `OperationBlock` messages to the existing `execute_switching_operation(validators=...)` pre-mutation barrier. Nonempty blocks yield `SwitchingOperationStatus.BLOCKED`, unchanged model/fingerprint and no events. Message ordering is independent of the input assertion ordering.

**Important compatibility boundary:** the accepted `execute_switching_operation` API keeps validators **optional**. Callers that do not pass this adapter are not automatically permission-gated. Its existing `NO_CHANGE` fast path bypasses validators, performs no mutation and emits no event; `NO_CHANGE` must not be treated as an authorization or physical-dispatch success. Enforcing mandatory site-authoritative gates in every execution path is a separate guarded work item.

## Dependencies / future work

Upstream: canonical model and fingerprint, switching-state-v1, WS-6 operational snapshot/timeline. Downstream: future earthing semantics; mechanical/electrical/logical interlock evaluators; source registry + qualified rules; site-specific bindings. No direct dependency on the unmerged electrical-calculation domain PR #32.

## Acceptance

Synthetic two-source switching fixture: explicit all-pass operation succeeds; absent, malformed, stale, contradictory, unknown or duplicate assertions fail closed before mutation; deterministic ordering; withdrawable operation has distinct binding; pre-state invalid denied; no-change is not permission; full prior regression preserved.
