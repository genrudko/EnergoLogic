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
    fingerprint,
    load_model,
)
from energologic.domain import (
    VOLTAGE_CLASS_BELOW_3000_V,
    VoltageSpec,
    validate_electrical_model,
    voltage_spec_for_terminal,
    voltage_specs_compatible,
)


ROOT = Path(__file__).resolve().parents[1]


def transformer(
    *,
    hv_attributes: dict[str, object] | None = None,
    lv_attributes: dict[str, object] | None = None,
) -> Element:
    return Element(
        id="transformer:tsn",
        kind="transformer_2w",
        name="ТСН",
        terminals=(
            Terminal(
                "hv",
                attributes=hv_attributes
                or {
                    "nominal_voltage_v": 35000,
                    "winding_connection": "delta",
                },
            ),
            Terminal(
                "lv",
                attributes=lv_attributes
                or {
                    "voltage_class": VOLTAGE_CLASS_BELOW_3000_V,
                    "winding_connection": "star",
                },
            ),
        ),
    )


def endpoint_element(
    element_id: str,
    kind: str,
    terminal_id: str,
    voltage_v: int,
) -> Element:
    return Element(
        id=element_id,
        kind=kind,
        terminals=(Terminal(terminal_id),),
        attributes={"nominal_voltage_v": voltage_v},
    )


class TransformerSemanticsTests(unittest.TestCase):
    def test_repository_transformer_example_is_valid(self):
        model = load_model(ROOT / "examples" / "tsn2.transformer-v1.json")
        self.assertEqual(validate_electrical_model(model), ())
        self.assertEqual(
            fingerprint(model),
            "ae1156fe0898e6941109dd11af97a5fe3c6ec952657072b5b22cec5412c0f73b",
        )

    def test_transformer_uses_terminal_voltage_specs(self):
        element = transformer()
        hv = voltage_spec_for_terminal(element, "hv")
        lv = voltage_spec_for_terminal(element, "lv")
        self.assertEqual(hv, VoltageSpec(nominal_voltage_v=35000))
        self.assertEqual(
            lv,
            VoltageSpec(voltage_class=VOLTAGE_CLASS_BELOW_3000_V),
        )

    def test_exact_400v_is_compatible_with_below_3kv_class(self):
        self.assertTrue(
            voltage_specs_compatible(
                VoltageSpec(nominal_voltage_v=400),
                VoltageSpec(voltage_class=VOLTAGE_CLASS_BELOW_3000_V),
            )
        )
        self.assertTrue(
            voltage_specs_compatible(
                VoltageSpec(nominal_voltage_v=2999),
                VoltageSpec(voltage_class=VOLTAGE_CLASS_BELOW_3000_V),
            )
        )
        self.assertFalse(
            voltage_specs_compatible(
                VoltageSpec(nominal_voltage_v=3000),
                VoltageSpec(voltage_class=VOLTAGE_CLASS_BELOW_3000_V),
            )
        )

    def test_transformer_accepts_exact_low_voltage_when_known(self):
        element = transformer(
            lv_attributes={
                "nominal_voltage_v": 400,
                "winding_connection": "star",
            }
        )
        model = CanonicalModel("0.1", "test:exact-lv", (element,), ())
        self.assertEqual(validate_electrical_model(model), ())

    def test_connections_are_validated_against_specific_transformer_terminal(self):
        bus = endpoint_element("bus", "bus", "node", 35000)
        load = endpoint_element("load", "external_link", "node", 400)
        tx = transformer()
        model = CanonicalModel(
            "0.1",
            "test:terminal-voltage",
            (bus, tx, load),
            (
                Connection(
                    "hv",
                    (Endpoint("bus", "node"), Endpoint(tx.id, "hv")),
                ),
                Connection(
                    "lv",
                    (Endpoint(tx.id, "lv"), Endpoint("load", "node")),
                ),
            ),
        )
        self.assertEqual(validate_electrical_model(model), ())

    def test_6kv_connection_is_not_compatible_with_below_3kv_terminal(self):
        bus = endpoint_element("bus", "bus", "node", 35000)
        load = endpoint_element("load", "external_link", "node", 6000)
        tx = transformer()
        model = CanonicalModel(
            "0.1",
            "test:bad-lv",
            (bus, tx, load),
            (
                Connection(
                    "hv",
                    (Endpoint("bus", "node"), Endpoint(tx.id, "hv")),
                ),
                Connection(
                    "lv",
                    (Endpoint(tx.id, "lv"), Endpoint("load", "node")),
                ),
            ),
        )
        mismatches = [
            issue
            for issue in validate_electrical_model(model)
            if issue.code == "nominal_voltage_mismatch"
        ]
        self.assertEqual(len(mismatches), 1)
        self.assertIn("6000 V", mismatches[0].message)
        self.assertIn("class below_3000_v", mismatches[0].message)

    def test_transformer_requires_voltage_on_each_terminal(self):
        tx = transformer(
            lv_attributes={"winding_connection": "star"},
        )
        model = CanonicalModel("0.1", "test:missing-lv", (tx,), ())
        self.assertIn(
            "missing_terminal_voltage",
            {issue.code for issue in validate_electrical_model(model)},
        )

    def test_transformer_rejects_ambiguous_terminal_voltage(self):
        tx = transformer(
            lv_attributes={
                "nominal_voltage_v": 400,
                "voltage_class": VOLTAGE_CLASS_BELOW_3000_V,
                "winding_connection": "star",
            },
        )
        model = CanonicalModel("0.1", "test:ambiguous-lv", (tx,), ())
        self.assertIn(
            "ambiguous_terminal_voltage_spec",
            {issue.code for issue in validate_electrical_model(model)},
        )

    def test_transformer_rejects_unknown_voltage_class(self):
        tx = transformer(
            lv_attributes={
                "voltage_class": "low_voltage-ish",
                "winding_connection": "star",
            }
        )
        model = CanonicalModel("0.1", "test:bad-class", (tx,), ())
        self.assertIn(
            "invalid_terminal_voltage_class",
            {issue.code for issue in validate_electrical_model(model)},
        )

    def test_transformer_requires_known_winding_connection(self):
        tx = transformer(
            hv_attributes={
                "nominal_voltage_v": 35000,
                "winding_connection": "mystery",
            }
        )
        model = CanonicalModel("0.1", "test:bad-winding", (tx,), ())
        self.assertIn(
            "invalid_winding_connection",
            {issue.code for issue in validate_electrical_model(model)},
        )

    def test_transformer_rejects_definitely_reversed_hv_lv(self):
        tx = transformer(
            hv_attributes={
                "nominal_voltage_v": 400,
                "winding_connection": "delta",
            },
            lv_attributes={
                "nominal_voltage_v": 35000,
                "winding_connection": "star",
            },
        )
        model = CanonicalModel("0.1", "test:reversed-transformer", (tx,), ())
        issues = validate_electrical_model(model)
        self.assertIn(
            "invalid_transformer_voltage_order",
            {issue.code for issue in issues},
        )

    def test_below_3kv_hv_is_rejected_against_35kv_lv(self):
        tx = transformer(
            hv_attributes={
                "voltage_class": VOLTAGE_CLASS_BELOW_3000_V,
                "winding_connection": "delta",
            },
            lv_attributes={
                "nominal_voltage_v": 35000,
                "winding_connection": "star",
            },
        )
        model = CanonicalModel("0.1", "test:reversed-class", (tx,), ())
        self.assertIn(
            "invalid_transformer_voltage_order",
            {issue.code for issue in validate_electrical_model(model)},
        )

    def test_transformer_rejects_element_level_voltage_to_avoid_ambiguity(self):
        tx = replace(
            transformer(),
            attributes={"nominal_voltage_v": 35000},
        )
        model = CanonicalModel("0.1", "test:element-voltage", (tx,), ())
        self.assertIn(
            "unexpected_element_voltage_spec",
            {issue.code for issue in validate_electrical_model(model)},
        )


if __name__ == "__main__":
    unittest.main()
