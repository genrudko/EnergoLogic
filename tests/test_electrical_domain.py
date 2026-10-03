from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from energologic.core import (
    CanonicalModel,
    Connection,
    Element,
    Endpoint,
    Terminal,
    load_model,
    validate_model,
)
from energologic.domain import validate_electrical_model


ROOT = Path(__file__).resolve().parents[1]


def _element(
    element_id: str,
    kind: str,
    terminals: tuple[str, ...],
    *,
    voltage: object = 35000,
    include_voltage: bool = True,
) -> Element:
    attributes = {"nominal_voltage_v": voltage} if include_voltage else {}
    return Element(
        id=element_id,
        kind=kind,
        terminals=tuple(Terminal(id=terminal_id) for terminal_id in terminals),
        attributes=attributes,
    )


def _valid_model() -> CanonicalModel:
    elements = (
        _element("bus", "bus", ("node",)),
        _element("breaker", "circuit_breaker", ("a", "b")),
        _element("ct", "current_transformer", ("a", "b")),
        _element("external", "external_link", ("node",)),
    )
    connections = (
        Connection(
            "c1",
            (Endpoint("bus", "node"), Endpoint("breaker", "a")),
        ),
        Connection(
            "c2",
            (Endpoint("breaker", "b"), Endpoint("ct", "a")),
        ),
        Connection(
            "c3",
            (Endpoint("ct", "b"), Endpoint("external", "node")),
        ),
    )
    return CanonicalModel("0.1", "test:electrical-v1", elements, connections)


class ElectricalDomainTests(unittest.TestCase):
    def test_valid_profile_model_has_no_issues(self):
        self.assertEqual(validate_electrical_model(_valid_model()), ())

    def test_repository_example_is_profile_valid(self):
        model = load_model(ROOT / "examples" / "kru35-v1-cell.electrical-v1.json")
        self.assertEqual(validate_electrical_model(model), ())

    def test_structural_validation_remains_open_for_unknown_kind(self):
        model = CanonicalModel(
            "0.1",
            "test:open-structural",
            (
                Element(
                    id="future",
                    kind="future_device",
                    terminals=(Terminal("x"),),
                    attributes={"anything": "allowed structurally"},
                ),
            ),
            (),
        )
        self.assertEqual(validate_model(model), ())
        issues = validate_electrical_model(model)
        self.assertEqual([issue.code for issue in issues], ["unsupported_element_kind"])

    def test_exact_terminal_contract_is_enforced(self):
        model = _valid_model()
        bad_bus = replace(
            model.elements[0],
            terminals=(Terminal("t1"),),
        )
        bad = replace(model, elements=(bad_bus,) + model.elements[1:])
        codes = {issue.code for issue in validate_electrical_model(bad)}
        self.assertIn("invalid_terminal_contract", codes)

    def test_nominal_voltage_is_required_in_integer_volts(self):
        model = _valid_model()
        breaker = model.elements[1]
        missing = replace(
            model,
            elements=(
                model.elements[0],
                replace(breaker, attributes={}),
                *model.elements[2:],
            ),
        )
        self.assertIn(
            "missing_nominal_voltage",
            {issue.code for issue in validate_electrical_model(missing)},
        )

        for invalid in (True, 35000.0, 0, -1):
            with self.subTest(invalid=invalid):
                changed = replace(
                    model,
                    elements=(
                        model.elements[0],
                        replace(
                            breaker,
                            attributes={"nominal_voltage_v": invalid},
                        ),
                        *model.elements[2:],
                    ),
                )
                self.assertIn(
                    "invalid_nominal_voltage",
                    {issue.code for issue in validate_electrical_model(changed)},
                )

    def test_voltage_mismatch_is_rejected(self):
        model = _valid_model()
        breaker = replace(
            model.elements[1],
            attributes={"nominal_voltage_v": 10000},
        )
        changed = replace(
            model,
            elements=(model.elements[0], breaker, *model.elements[2:]),
        )
        issues = validate_electrical_model(changed)
        mismatch = [issue for issue in issues if issue.code == "nominal_voltage_mismatch"]
        self.assertGreaterEqual(len(mismatch), 1)
        self.assertTrue(any("35000 V" in issue.message for issue in mismatch))
        self.assertTrue(any("10000 V" in issue.message for issue in mismatch))

    def test_bounded_terminal_cannot_branch(self):
        model = CanonicalModel(
            "0.1",
            "test:degree",
            (
                _element("bus-1", "bus", ("node",)),
                _element("bus-2", "bus", ("node",)),
                _element("breaker", "circuit_breaker", ("a", "b")),
            ),
            (
                Connection(
                    "c1",
                    (Endpoint("bus-1", "node"), Endpoint("breaker", "a")),
                ),
                Connection(
                    "c2",
                    (Endpoint("bus-2", "node"), Endpoint("breaker", "a")),
                ),
            ),
        )
        issues = validate_electrical_model(model)
        exceeded = [issue for issue in issues if issue.code == "terminal_degree_exceeded"]
        self.assertEqual(len(exceeded), 1)
        self.assertIn("breaker", exceeded[0].path)
        self.assertIn("terminal degree 2", exceeded[0].message)

    def test_duplicate_electrical_edge_is_rejected(self):
        model = CanonicalModel(
            "0.1",
            "test:duplicate-edge",
            (
                _element("bus", "bus", ("node",)),
                _element("breaker", "circuit_breaker", ("a", "b")),
            ),
            (
                Connection(
                    "c1",
                    (Endpoint("bus", "node"), Endpoint("breaker", "a")),
                ),
                Connection(
                    "c2",
                    (Endpoint("breaker", "a"), Endpoint("bus", "node")),
                ),
            ),
        )
        issues = validate_electrical_model(model)
        duplicate = [
            issue for issue in issues if issue.code == "duplicate_electrical_connection"
        ]
        self.assertEqual(len(duplicate), 1)
        self.assertIn("c1, c2", duplicate[0].message)

    def test_external_topology_cannot_short_element_to_itself(self):
        model = CanonicalModel(
            "0.1",
            "test:intra",
            (_element("breaker", "circuit_breaker", ("a", "b")),),
            (
                Connection(
                    "c1",
                    (Endpoint("breaker", "a"), Endpoint("breaker", "b")),
                ),
            ),
        )
        issues = validate_electrical_model(model)
        self.assertIn(
            "intra_element_connection",
            {issue.code for issue in issues},
        )

    def test_issue_order_is_input_order_independent(self):
        model = _valid_model()
        bad_breaker = replace(
            model.elements[1],
            attributes={"nominal_voltage_v": 10000},
        )
        bad = replace(
            model,
            elements=(model.elements[0], bad_breaker, *model.elements[2:]),
            connections=model.connections
            + (
                Connection(
                    "c4",
                    (Endpoint("bus", "node"), Endpoint("breaker", "a")),
                ),
            ),
        )
        reordered = replace(
            bad,
            elements=tuple(reversed(bad.elements)),
            connections=tuple(reversed(bad.connections)),
        )
        self.assertEqual(
            validate_electrical_model(bad),
            validate_electrical_model(reordered),
        )


if __name__ == "__main__":
    unittest.main()
