from __future__ import annotations

from dataclasses import replace
import unittest

from energologic.core import CanonicalModel, Element, Terminal, fingerprint
from energologic.domain import (
    VOLTAGE_CLASS_BELOW_3000_V,
    validate_electrical_model,
)
from energologic.frontends.visio import (
    VisioMappingError,
    VisioPageSnapshot,
    VisioShapeSnapshot,
    build_render_plan,
    capture_page_snapshot,
)


class VisioTransformerTests(unittest.TestCase):
    def tsn_snapshot(self) -> VisioPageSnapshot:
        return VisioPageSnapshot(
            page_name="MCP-v2",
            shapes=(
                VisioShapeSnapshot(
                    166,
                    "ТСН2",
                    "ТСН",
                    {
                        "u": "INDEX(10,Prop.u.Format)",
                        "u2": "INDEX(16,Prop.u2.Format)",
                        "s1": "INDEX(1,Prop.s1.Format)",
                        "s2": "INDEX(4,Prop.s2.Format)",
                        "p2": "INDEX(1,Prop.p2.Format)",
                        "c": "INDEX(1,Prop.c.Format)",
                    },
                ),
            ),
            connections=(),
        )

    def test_live_tsn2_shape_maps_without_inventing_400v(self):
        model = capture_page_snapshot(
            self.tsn_snapshot(),
            model_id="tsn2:live-like",
        ).model
        self.assertEqual(validate_electrical_model(model), ())

        self.assertEqual(len(model.elements), 1)
        transformer = model.elements[0]
        self.assertEqual(transformer.kind, "transformer_2w")
        self.assertNotIn("nominal_voltage_v", transformer.attributes)

        terminals = {terminal.id: terminal for terminal in transformer.terminals}
        self.assertEqual(
            terminals["hv"].attributes["nominal_voltage_v"],
            35000,
        )
        self.assertEqual(
            terminals["hv"].attributes["winding_connection"],
            "delta",
        )
        self.assertNotIn("nominal_voltage_v", terminals["lv"].attributes)
        self.assertEqual(
            terminals["lv"].attributes["voltage_class"],
            VOLTAGE_CLASS_BELOW_3000_V,
        )
        self.assertEqual(
            terminals["lv"].attributes["winding_connection"],
            "star",
        )

    def test_tsn2_render_round_trip_preserves_canonical_model(self):
        captured = capture_page_snapshot(
            self.tsn_snapshot(),
            model_id="tsn2:round-trip",
        ).model
        plan = build_render_plan(captured, page_name="Transformer-V1")

        self.assertEqual(len(plan.shapes), 1)
        shape = plan.shapes[0]
        self.assertEqual(shape.master_name, "ТСН2")
        self.assertEqual(shape.stencil_name, "Трансформаторы.vss")
        self.assertEqual(
            dict(shape.shape_data),
            {
                "u": "INDEX(10,Prop.u.Format)",
                "u2": "INDEX(16,Prop.u2.Format)",
                "s1": "INDEX(1,Prop.s1.Format)",
                "s2": "INDEX(4,Prop.s2.Format)",
                "p2": "INDEX(1,Prop.p2.Format)",
                "c": "INDEX(1,Prop.c.Format)",
            },
        )

        recaptured = capture_page_snapshot(
            VisioPageSnapshot(
                page_name="Transformer-V1",
                shapes=(
                    VisioShapeSnapshot(
                        900,
                        shape.master_name,
                        shape.text,
                        shape.shape_data,
                    ),
                ),
                connections=(),
            ),
            model_id="tsn2:round-trip",
        ).model
        self.assertEqual(fingerprint(captured), fingerprint(recaptured))

    def test_undefined_vtd_low_voltage_fails_closed(self):
        snapshot = self.tsn_snapshot()
        shape = replace(
            snapshot.shapes[0],
            shape_data={
                **snapshot.shapes[0].shape_data,
                "u2": "INDEX(17,Prop.u2.Format)",
            },
        )
        with self.assertRaisesRegex(
            VisioMappingError,
            "unsupported_voltage_class",
        ):
            capture_page_snapshot(
                replace(snapshot, shapes=(shape,)),
                model_id="x",
            )

    def test_undefined_winding_connection_fails_closed(self):
        snapshot = self.tsn_snapshot()
        shape = replace(
            snapshot.shapes[0],
            shape_data={
                **snapshot.shapes[0].shape_data,
                "s1": "INDEX(0,Prop.s1.Format)",
            },
        )
        with self.assertRaisesRegex(
            VisioMappingError,
            "unsupported_winding_connection",
        ):
            capture_page_snapshot(
                replace(snapshot, shapes=(shape,)),
                model_id="x",
            )

    def test_exact_400v_is_valid_canonical_data_but_not_lossless_vtd_projection(self):
        transformer = Element(
            id="transformer:exact-400v",
            kind="transformer_2w",
            name="ТСН",
            terminals=(
                Terminal(
                    "hv",
                    attributes={
                        "nominal_voltage_v": 35000,
                        "winding_connection": "delta",
                    },
                ),
                Terminal(
                    "lv",
                    attributes={
                        "nominal_voltage_v": 400,
                        "winding_connection": "star",
                    },
                ),
            ),
        )
        model = CanonicalModel(
            "0.1",
            "tsn2:exact-400v",
            (transformer,),
            (),
        )
        self.assertEqual(validate_electrical_model(model), ())
        with self.assertRaisesRegex(
            VisioMappingError,
            "unsupported_exact_voltage_projection",
        ):
            build_render_plan(model, page_name="Transformer-V1")


if __name__ == "__main__":
    unittest.main()
