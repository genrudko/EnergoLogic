from __future__ import annotations

from dataclasses import replace
import unittest

from energologic.core import fingerprint
from energologic.frontends.visio import (
    VisioGeometry,
    VisioGlueSnapshot,
    VisioMappingError,
    VisioPageSnapshot,
    VisioShapeSnapshot,
    build_render_plan,
    capture_page_snapshot,
)


U35 = "INDEX(10,Prop.u.Format)"


def live_slice() -> VisioPageSnapshot:
    return VisioPageSnapshot(
        page_name="MCP-v2",
        shapes=(
            VisioShapeSnapshot(
                101,
                "Шина10",
                "1 С 35 кВ",
                {"u": U35},
                geometry=VisioGeometry(2.5591, 10.0394, 8.2677, 0.0),
            ),
            VisioShapeSnapshot(
                103,
                "Шина10",
                "2",
                parent_shape_id=101,
                geometry=VisioGeometry(1.7717, 0.0, 0.0591, 0.0591),
            ),
            VisioShapeSnapshot(
                66,
                "Выкатная тележка выключателя",
                "В-1-35",
                {"u": U35},
                geometry=VisioGeometry(4.3307, 9.4341, 1.1516, 0.0),
            ),
            VisioShapeSnapshot(
                69,
                "ТТ",
                "ТТ\nВ-1-35",
                {"u": U35},
                geometry=VisioGeometry(4.3307, 8.5630, 0.5906, 0.0),
            ),
            VisioShapeSnapshot(
                117,
                "ТТ",
                "ТТ НП\nВ-1-35",
                {"u": U35},
                geometry=VisioGeometry(4.3307, 7.4311, 1.6732, 0.0),
            ),
            VisioShapeSnapshot(
                119,
                "Связь с объектом2",
                "В-1",
                {"u": U35},
                geometry=VisioGeometry(4.3307, 6.2992, 0.0, 0.5906),
            ),
        ),
        connections=(
            VisioGlueSnapshot(66, "BeginX", 103, "Connections.2.X"),
            VisioGlueSnapshot(69, "BeginX", 66, "Connections.2.X"),
            VisioGlueSnapshot(117, "BeginX", 69, "Connections.2.X"),
            VisioGlueSnapshot(119, "BeginX", 117, "Connections.2.X"),
        ),
    )


def snapshot_from_plan(plan) -> VisioPageSnapshot:
    ordered = sorted(plan.shapes, key=lambda shape: -shape.y_mm)
    ids = {
        shape.element_id: 900 + index * 17
        for index, shape in enumerate(reversed(ordered))
    }
    shapes = tuple(
        VisioShapeSnapshot(
            shape_id=ids[shape.element_id],
            master_name=shape.master_name,
            text=shape.text,
            shape_data=shape.shape_data,
            geometry=VisioGeometry(
                shape.x_mm / 25.4, shape.y_mm / 25.4, 0.123, 0.456
            ),
        )
        for shape in ordered
    )
    connections = []
    for upper, lower in zip(ordered, ordered[1:]):
        target_cell = (
            "Connections.1.X" if upper.kind == "bus" else "Connections.2.X"
        )
        connections.append(
            VisioGlueSnapshot(
                from_shape_id=ids[lower.element_id],
                from_cell="BeginX",
                to_shape_id=ids[upper.element_id],
                to_cell=target_cell,
            )
        )
    return VisioPageSnapshot(plan.page_name, shapes, tuple(connections))


class VisioMappingTests(unittest.TestCase):
    def test_live_shape_slice_maps_bus_child_to_parent_bus(self):
        result = capture_page_snapshot(live_slice(), model_id="kru35:v1-cell")
        self.assertEqual(len(result.model.elements), 5)
        self.assertEqual(len(result.model.connections), 4)
        self.assertEqual(len(result.bindings), 5)
        self.assertNotIn(103, {binding.shape_id for binding in result.bindings})
        self.assertEqual(
            {element.kind for element in result.model.elements},
            {"bus", "circuit_breaker", "current_transformer", "external_link"},
        )
        self.assertTrue(
            all(
                element.attributes["nominal_voltage_kv"] == 35
                for element in result.model.elements
            )
        )

    def test_geometry_changes_do_not_change_canonical_fingerprint(self):
        original = live_slice()
        moved = replace(
            original,
            shapes=tuple(
                replace(
                    shape,
                    geometry=VisioGeometry(
                        shape.geometry.pin_x + 100.0,
                        shape.geometry.pin_y - 50.0,
                        shape.geometry.width * 3.0 + 1.0,
                        shape.geometry.height * 2.0 + 1.0,
                    ),
                )
                for shape in original.shapes
            ),
        )
        a = capture_page_snapshot(original, model_id="kru35:v1-cell").model
        b = capture_page_snapshot(moved, model_id="kru35:v1-cell").model
        self.assertEqual(fingerprint(a), fingerprint(b))

    def test_electrical_shape_data_change_changes_fingerprint(self):
        original = live_slice()
        changed_shapes = list(original.shapes)
        breaker_index = next(
            i for i, shape in enumerate(changed_shapes) if shape.shape_id == 66
        )
        changed_shapes[breaker_index] = replace(
            changed_shapes[breaker_index],
            shape_data={"u": "INDEX(9,Prop.u.Format)"},
        )
        changed = replace(original, shapes=tuple(changed_shapes))
        a = capture_page_snapshot(original, model_id="kru35:v1-cell").model
        b = capture_page_snapshot(changed, model_id="kru35:v1-cell").model
        self.assertNotEqual(fingerprint(a), fingerprint(b))
        breaker = next(
            element for element in b.elements if element.kind == "circuit_breaker"
        )
        self.assertEqual(breaker.attributes["nominal_voltage_kv"], 60)

    def test_render_plan_round_trip_preserves_fingerprint(self):
        captured = capture_page_snapshot(
            live_slice(), model_id="kru35:v1-cell"
        ).model
        plan = build_render_plan(captured, page_name="EnergoLogic-V1")
        ordered = sorted(plan.shapes, key=lambda shape: -shape.y_mm)
        self.assertEqual(
            [shape.kind for shape in ordered],
            [
                "bus",
                "circuit_breaker",
                "current_transformer",
                "current_transformer",
                "external_link",
            ],
        )
        self.assertEqual(
            [shape.stencil_name for shape in ordered],
            [
                "Шины.vss",
                "Коммутационные аппараты.vss",
                "Трансформаторы.vss",
                "Трансформаторы.vss",
                "Линии, заземление.vss",
            ],
        )
        self.assertEqual(len(plan.connections), 4)
        self.assertTrue(
            all(connection.source_endpoint == "begin" for connection in plan.connections)
        )
        self.assertTrue(
            all(connection.target_connection_row == 2 for connection in plan.connections)
        )
        self.assertEqual(plan.connections[0].target_child_user_nt, 1)
        self.assertTrue(
            all(
                connection.target_child_user_nt is None
                for connection in plan.connections[1:]
            )
        )
        recaptured = capture_page_snapshot(
            snapshot_from_plan(plan), model_id="kru35:v1-cell"
        ).model
        self.assertEqual(fingerprint(captured), fingerprint(recaptured))

    def test_unknown_master_fails_closed(self):
        snapshot = VisioPageSnapshot(
            "x",
            (VisioShapeSnapshot(1, "Unknown", "X", {"u": U35}),),
            (),
        )
        with self.assertRaisesRegex(VisioMappingError, "unsupported_master"):
            capture_page_snapshot(snapshot, model_id="x")

    def test_ambiguous_semantic_identity_fails_closed(self):
        snapshot = VisioPageSnapshot(
            "x",
            (
                VisioShapeSnapshot(1, "ТТ", "ТТ X", {"u": U35}),
                VisioShapeSnapshot(2, "ТТ", "  ТТ   X  ", {"u": U35}),
            ),
            (),
        )
        with self.assertRaisesRegex(VisioMappingError, "ambiguous_identity"):
            capture_page_snapshot(snapshot, model_id="x")

    def test_visio_shape_ids_do_not_enter_canonical_identity(self):
        first = live_slice()
        remap = {shape.shape_id: shape.shape_id + 1000 for shape in first.shapes}
        second = VisioPageSnapshot(
            first.page_name,
            tuple(
                replace(
                    shape,
                    shape_id=remap[shape.shape_id],
                    parent_shape_id=(
                        remap[shape.parent_shape_id]
                        if shape.parent_shape_id
                        else None
                    ),
                )
                for shape in first.shapes
            ),
            tuple(
                replace(
                    connection,
                    from_shape_id=remap[connection.from_shape_id],
                    to_shape_id=remap[connection.to_shape_id],
                )
                for connection in first.connections
            ),
        )
        a = capture_page_snapshot(first, model_id="kru35:v1-cell").model
        b = capture_page_snapshot(second, model_id="kru35:v1-cell").model
        self.assertEqual(fingerprint(a), fingerprint(b))


if __name__ == "__main__":
    unittest.main()
