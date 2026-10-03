from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from energologic.core import CanonicalModel, Element, Terminal, load_model
from energologic.domain import (
    SwitchingStateError,
    read_switching_state,
    switch_allows_primary_conduction,
    validate_electrical_model,
    validate_switching_state_model,
)


ROOT = Path(__file__).resolve().parents[1]


def switch_element(
    element_id: str = "q",
    *,
    kind: str = "circuit_breaker",
    switch_state: object = "closed",
    mounting_type: object = "withdrawable",
    withdrawable_position: object = "working",
) -> Element:
    attributes: dict[str, object] = {
        "nominal_voltage_v": 35000,
        "switch_state": switch_state,
        "mounting_type": mounting_type,
    }
    if withdrawable_position is not None:
        attributes["withdrawable_position"] = withdrawable_position
    return Element(
        id=element_id,
        kind=kind,
        terminals=(Terminal("a"), Terminal("b")),
        attributes=attributes,
    )


def model_with(element: Element) -> CanonicalModel:
    return CanonicalModel("0.1", "test:switching", (element,), ())


class SwitchingStateTests(unittest.TestCase):
    def test_disconnector_is_supported_by_static_electrical_profile(self):
        element = switch_element(kind="disconnector")
        self.assertEqual(validate_electrical_model(model_with(element)), ())

    def test_closed_working_withdrawable_switch_conducts(self):
        element = switch_element()
        state = read_switching_state(element)
        self.assertEqual(state.switch_state, "closed")
        self.assertEqual(state.mounting_type, "withdrawable")
        self.assertEqual(state.withdrawable_position, "working")
        self.assertTrue(switch_allows_primary_conduction(element))

    def test_open_switch_does_not_conduct(self):
        self.assertFalse(
            switch_allows_primary_conduction(
                switch_element(switch_state="open")
            )
        )

    def test_closed_repair_or_control_position_does_not_conduct(self):
        for position in ("repair", "control"):
            with self.subTest(position=position):
                self.assertFalse(
                    switch_allows_primary_conduction(
                        switch_element(withdrawable_position=position)
                    )
                )

    def test_closed_fixed_switch_conducts_without_withdrawable_position(self):
        element = switch_element(
            mounting_type="fixed",
            withdrawable_position=None,
        )
        self.assertTrue(switch_allows_primary_conduction(element))
        self.assertEqual(validate_switching_state_model(model_with(element)), ())

    def test_fixed_switch_rejects_withdrawable_position(self):
        element = switch_element(
            mounting_type="fixed",
            withdrawable_position="working",
        )
        issues = validate_switching_state_model(model_with(element))
        self.assertIn(
            "unexpected_withdrawable_position",
            {issue.code for issue in issues},
        )
        with self.assertRaisesRegex(
            SwitchingStateError, "unexpected_withdrawable_position"
        ):
            switch_allows_primary_conduction(element)

    def test_withdrawable_switch_requires_known_position(self):
        for invalid in (None, "removed", 0, ["working"]):
            with self.subTest(invalid=invalid):
                element = switch_element(withdrawable_position=invalid)
                issues = validate_switching_state_model(model_with(element))
                self.assertIn(
                    "invalid_withdrawable_position",
                    {issue.code for issue in issues},
                )

    def test_switch_state_and_mounting_type_fail_closed_on_invalid_values(self):
        cases = (
            ("switch_state", {"switch_state": "unknown"}, "invalid_switch_state"),
            ("switch_state_type", {"switch_state": True}, "invalid_switch_state"),
            ("mounting", {"mounting_type": "plug-in"}, "invalid_mounting_type"),
            ("mounting_type", {"mounting_type": {}}, "invalid_mounting_type"),
        )
        for _, changes, code in cases:
            with self.subTest(changes=changes):
                element = switch_element()
                attributes = dict(element.attributes)
                attributes.update(changes)
                changed = replace(element, attributes=attributes)
                issues = validate_switching_state_model(model_with(changed))
                self.assertIn(code, {issue.code for issue in issues})

    def test_non_switching_elements_must_not_carry_switching_attributes(self):
        element = Element(
            id="ct",
            kind="current_transformer",
            terminals=(Terminal("a"), Terminal("b")),
            attributes={
                "nominal_voltage_v": 35000,
                "switch_state": "closed",
            },
        )
        issues = validate_switching_state_model(model_with(element))
        self.assertIn(
            "unexpected_switching_attribute",
            {issue.code for issue in issues},
        )

    def test_switching_example_is_profile_valid(self):
        model = load_model(
            ROOT / "examples" / "kru35-v1-cell.switching-state-v1.json"
        )
        self.assertEqual(validate_switching_state_model(model), ())

    def test_switching_validation_is_input_order_independent(self):
        breaker = switch_element("breaker", switch_state="bad")
        disconnector = switch_element(
            "disconnector",
            kind="disconnector",
            withdrawable_position="bad",
        )
        first = CanonicalModel(
            "0.1",
            "test:order",
            (breaker, disconnector),
            (),
        )
        second = replace(first, elements=tuple(reversed(first.elements)))
        self.assertEqual(
            validate_switching_state_model(first),
            validate_switching_state_model(second),
        )


if __name__ == "__main__":
    unittest.main()
