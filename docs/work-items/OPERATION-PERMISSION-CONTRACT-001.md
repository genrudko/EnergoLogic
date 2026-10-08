# OPERATION-PERMISSION-CONTRACT-001

**Issue:** #33
**Branch:** `domain/operation-permission-contract-001`
**State:** Draft candidate; owner acceptance pending; never Ready/Merge without explicit instruction.

## Objective

Create a deterministic, source-attributed *structural* permission-evidence contract and adapter for the existing simulated switching validator hook. Establish fail-closed behavior on missing/invalid evidence without embedding unverified operational interlocks or normative rules.

## Included

- `src/energologic/operational/permission.py`: frozen evidence/assertion/result DTOs, explicit three-state decision and fail-closed evaluator.
- `permission_evidence_validator`: explicit adapter to existing `OperationValidator`, not an implicit runtime behavior change.
- Public exports via `energologic.operational`; no solver/frontend/COM imports.
- Synthetic positive/negative/order/staleness/identity tests and current evidence.
- Architecture contract `docs/architecture/OPERATION-PERMISSION-V1-CONTRACT.md`.

## Excluded / gated later

- Earthing-switch modeling/topology and energized earth behavior.
- Site-specific Kochubeevskaya interlocking rules and actual switching permission.
- Russian normative source evaluation and authenticated provenance verification.
- Automatic live dispatch, physical isolation proof, protection-to-breaker actuation.
- Mandatory gate for all switching consumers and changed legacy no-op semantics.
- Changes to unrelated PR #32 calculation domain.

## Acceptance

- Exact model/operation/evidence binding; no optimistic defaults.
- Unknown/missing/stale/duplicate/unproven claims prevent simulated state mutation.
- Explicit pass with sourced synthetic assertions can drive an existing operation, but is NOT site safety certification.
- Deterministic order and no events after a blocked attempt.
- Base test suite remains green; CI on Linux/Windows must be verified before merge.

## Review gate

PR remains Draft pending external review, qualified policy provenance and owner acceptance. Unsupported normative or site claims cannot be introduced to make tests pass.
