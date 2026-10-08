from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from energologic.core import fingerprint, load_model
from energologic.operational import (
    SourceRef,
    SwitchStateOperation,
    SwitchingOperationStatus,
    WithdrawablePositionOperation,
    execute_switching_operation,
    simulate_operational_state,
)
from energologic.operational.permission import (
    OperationPermissionEvidence,
    PermissionAssertion,
    PermissionDecision,
    evaluate_operation_permission,
    permission_evidence_validator,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "ws6-operational-two-source.json"
SOURCES = (SourceRef("source:a", "node"), SourceRef("source:b", "node"))


class OperationPermissionTests(unittest.TestCase):
    def setUp(self):
        self.model = load_model(FIXTURE)
        self.operation = SwitchStateOperation("op:permission-test", "breaker:coupler", "closed")
        self.before = simulate_operational_state(self.model, SOURCES)

    def evidence(self, *assertions, operation=None):
        operation = operation or self.operation
        return OperationPermissionEvidence(
            policy_id="policy:synthetic-v1",
            model_fingerprint=fingerprint(self.model),
            operation_id=operation.operation_id,
            element_id=operation.element_id,
            operation_type="switch_state" if isinstance(operation, SwitchStateOperation) else "withdrawable_position",
            target_value=operation.target_state if isinstance(operation, SwitchStateOperation) else operation.target_position,
            assertions=tuple(assertions),
        )

    def assertion(self, key="interlock:synthetic", outcome="pass", source="fixture:permission-v1"):
        return PermissionAssertion(key, outcome, source)

    def evaluate(self, evidence):
        return evaluate_operation_permission(self.model, self.operation, self.before, evidence)

    def run_with(self, evidence):
        return execute_switching_operation(
            self.model,
            SOURCES,
            self.operation,
            validators=(permission_evidence_validator(evidence),),
        )

    def assert_blocked_and_unchanged(self, evidence, expected_code):
        result = self.run_with(evidence)
        self.assertEqual(result.status, SwitchingOperationStatus.BLOCKED)
        self.assertEqual(result.events, ())
        self.assertEqual(result.model_after, self.model)
        self.assertEqual(result.model_after_fingerprint, result.model_before_fingerprint)
        self.assertEqual(result.blocks[0].code, expected_code)

    def test_absent_evidence_denies_and_does_not_mutate(self):
        self.assertEqual(self.evaluate(None).decision, PermissionDecision.UNKNOWN)
        self.assert_blocked_and_unchanged(None, "permission_evidence_missing")

    def test_empty_requirement_set_denies(self):
        self.assert_blocked_and_unchanged(self.evidence(), "permission_requirements_missing")

    def test_explicit_pass_with_provenance_allows_synthetic_mutation(self):
        evidence = self.evidence(self.assertion())
        self.assertEqual(self.evaluate(evidence).decision, PermissionDecision.PERMITTED)
        result = self.run_with(evidence)
        self.assertEqual(result.status, SwitchingOperationStatus.SUCCESS)
        self.assertTrue(result.events)
        self.assertNotEqual(result.model_before_fingerprint, result.model_after_fingerprint)

    def test_failed_assertion_denies(self):
        evidence = self.evidence(self.assertion(outcome="fail"))
        self.assertEqual(self.evaluate(evidence).decision, PermissionDecision.BLOCKED)
        self.assert_blocked_and_unchanged(evidence, "permission_requirement_failed")

    def test_unknown_assertion_denies(self):
        evidence = self.evidence(self.assertion(outcome="unknown"))
        self.assertEqual(self.evaluate(evidence).decision, PermissionDecision.UNKNOWN)
        self.assert_blocked_and_unchanged(evidence, "permission_requirement_unknown")

    def test_missing_source_provenance_denies(self):
        self.assert_blocked_and_unchanged(
            self.evidence(self.assertion(source="  ")),
            "permission_invalid_assertion",
        )

    def test_invalid_outcome_denies(self):
        self.assert_blocked_and_unchanged(
            self.evidence(self.assertion(outcome="allowed?")),
            "permission_invalid_assertion",
        )

    def test_duplicate_requirements_deny_even_if_both_pass(self):
        evidence = self.evidence(self.assertion(), self.assertion(source="different-source"))
        self.assert_blocked_and_unchanged(evidence, "permission_duplicate_requirement")

    def test_stale_model_snapshot_denies(self):
        evidence = replace(self.evidence(self.assertion()), model_fingerprint="stale")
        self.assert_blocked_and_unchanged(evidence, "permission_binding_mismatch")

    def test_wrong_target_or_operation_identity_denies(self):
        source = self.evidence(self.assertion())
        for evidence in (
            replace(source, operation_id="op:wrong"),
            replace(source, element_id="breaker:wrong"),
            replace(source, target_value="open"),
            replace(source, operation_type="withdrawable_position"),
        ):
            with self.subTest(evidence=evidence):
                self.assert_blocked_and_unchanged(evidence, "permission_binding_mismatch")

    def test_policy_identifier_is_required(self):
        self.assert_blocked_and_unchanged(
            replace(self.evidence(self.assertion()), policy_id=""),
            "permission_invalid_policy",
        )

    def test_requirement_order_is_deterministic(self):
        a = self.assertion("z", "fail")
        b = self.assertion("a", "unknown")
        forward = self.evaluate(self.evidence(a, b))
        reverse = self.evaluate(self.evidence(b, a))
        self.assertEqual(forward, reverse)
        self.assertEqual(forward.decision, PermissionDecision.BLOCKED)
        self.assertEqual(forward.evaluated_requirements, ("a", "z"))

    def test_invalid_pre_operation_state_denies(self):
        from energologic.operational import OperationalStatus

        invalid_before = replace(self.before, status=OperationalStatus.INVALID_MODEL)
        decision = evaluate_operation_permission(
            self.model, self.operation, invalid_before, self.evidence(self.assertion())
        )
        self.assertEqual(decision.decision, PermissionDecision.UNKNOWN)
        self.assertEqual(decision.blocks[0].code, "permission_binding_mismatch")

    def test_no_change_result_is_not_a_permission_decision(self):
        # Existing operations API treats an unchanged state as a no-op before validators.
        # The no-op response must never be interpreted as authority to dispatch.
        op = SwitchStateOperation("op:nochange", "breaker:coupler", "open")
        result = execute_switching_operation(
            self.model, SOURCES, op, validators=(permission_evidence_validator(None),)
        )
        self.assertEqual(result.status, SwitchingOperationStatus.NO_CHANGE)
        self.assertEqual(result.events, ())
        self.assertEqual(result.model_after, self.model)

    def test_withdrawable_operation_binds_to_distinct_target(self):
        op = WithdrawablePositionOperation("op:withdraw", "breaker:transformer", "repair")
        evidence = self.evidence(self.assertion(), operation=op)
        result = execute_switching_operation(
            self.model, SOURCES, op, validators=(permission_evidence_validator(evidence),)
        )
        self.assertEqual(result.status, SwitchingOperationStatus.SUCCESS)
        denied = replace(evidence, target_value="control")
        result = execute_switching_operation(
            self.model, SOURCES, op, validators=(permission_evidence_validator(denied),)
        )
        self.assertEqual(result.status, SwitchingOperationStatus.BLOCKED)
        self.assertEqual(result.blocks[0].code, "permission_binding_mismatch")


if __name__ == "__main__":
    unittest.main()
