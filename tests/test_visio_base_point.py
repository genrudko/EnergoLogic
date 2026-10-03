from __future__ import annotations

import unittest

from energologic.frontends.visio import (
    VisioGeometry,
    VisioGlueSnapshot,
    VisioPageSnapshot,
    VisioQolError,
    VisioShapeSnapshot,
    build_base_point_copy_execution_request,
    build_base_point_move_execution_request,
    plan_copy_with_base_point,
    plan_exact_offset,
    plan_move_with_base_point,
)


def snapshot(
    *,
    external_glue: bool = False,
    managed_id: str | None = None,
    second_managed_id: str | None = None,
) -> VisioPageSnapshot:
    first_user = {}
    second_user = {}
    if managed_id is not None:
        first_user["EnergoLogicCellId"] = f'"{managed_id}"'
    if second_managed_id is not None:
        second_user["EnergoLogicCellId"] = f'"{second_managed_id}"'

    connections = [VisioGlueSnapshot(10, "EndX", 11, "BeginX")]
    shapes = [
        VisioShapeSnapshot(
            10,
            "A",
            "A",
            user_cells=first_user,
            geometry=VisioGeometry(1.0, 2.0),
        ),
        VisioShapeSnapshot(
            11,
            "B",
            "B",
            user_cells=second_user,
            geometry=VisioGeometry(2.0, 2.0),
        ),
    ]
    if external_glue:
        shapes.append(
            VisioShapeSnapshot(
                20,
                "Bus",
                "Bus",
                geometry=VisioGeometry(3.0, 2.0),
            )
        )
        connections.append(
            VisioGlueSnapshot(11, "EndX", 20, "Connections.1.X")
        )
    return VisioPageSnapshot(
        page_name="BasePoint",
        shapes=tuple(shapes),
        connections=tuple(connections),
    )


class BasePointQolTests(unittest.TestCase):
    def test_copy_uses_exact_base_to_target_delta(self):
        plan = plan_copy_with_base_point(
            snapshot(),
            shape_ids=(10, 11),
            base_x_mm=100.0,
            base_y_mm=50.0,
            target_x_mm=225.0,
            target_y_mm=50.0,
        )
        self.assertEqual(plan.operation, "copy")
        self.assertAlmostEqual(plan.dx_mm, 125.0)
        self.assertAlmostEqual(plan.dy_mm, 0.0)
        request = build_base_point_copy_execution_request(plan)
        self.assertEqual(request.tool_name, "duplicate_shapes_exact")
        self.assertEqual(request.shape_ids_json, "[10,11]")
        self.assertAlmostEqual(request.dx_mm, 125.0)
        self.assertEqual(request.glue_items_json, "[]")
        self.assertFalse(request.identity_reset_required)

    def test_move_uses_exact_base_to_target_delta(self):
        plan = plan_move_with_base_point(
            snapshot(),
            shape_ids=(10, 11),
            base_x_mm=100.0,
            base_y_mm=50.0,
            target_x_mm=90.0,
            target_y_mm=55.0,
        )
        self.assertEqual(plan.operation, "move")
        self.assertAlmostEqual(plan.dx_mm, -10.0)
        self.assertAlmostEqual(plan.dy_mm, 5.0)
        request = build_base_point_move_execution_request(plan)
        self.assertEqual(request.tool_name, "move_shapes_exact")
        self.assertEqual(request.detach_items_json, "[]")
        self.assertEqual(request.glue_items_json, "[]")

    def test_exact_offset_is_millimetre_move_without_point_math(self):
        plan = plan_exact_offset(
            snapshot(),
            shape_ids=(10, 11),
            dx_mm=10.0,
            dy_mm=-5.0,
        )
        self.assertEqual(plan.operation, "move")
        self.assertAlmostEqual(plan.dx_mm, 10.0)
        self.assertAlmostEqual(plan.dy_mm, -5.0)

    def test_generic_base_point_operations_refuse_external_electrical_glue(self):
        for planner in (plan_copy_with_base_point, plan_move_with_base_point):
            with self.subTest(planner=planner.__name__):
                kwargs = dict(
                    snapshot=snapshot(external_glue=True),
                    shape_ids=(10, 11),
                    base_x_mm=0.0,
                    base_y_mm=0.0,
                    target_x_mm=10.0,
                    target_y_mm=0.0,
                )
                if planner is plan_copy_with_base_point:
                    kwargs["new_cell_id"] = ""
                with self.assertRaisesRegex(
                    VisioQolError,
                    "external_glue_requires_cell_operation",
                ):
                    planner(**kwargs)

    def test_copy_of_managed_selection_requires_new_identity(self):
        with self.assertRaisesRegex(
            VisioQolError,
            "identity_reset_required",
        ):
            plan_copy_with_base_point(
                snapshot(managed_id="cell:old"),
                shape_ids=(10, 11),
                base_x_mm=0.0,
                base_y_mm=0.0,
                target_x_mm=40.0,
                target_y_mm=0.0,
            )

        plan = plan_copy_with_base_point(
            snapshot(managed_id="cell:old"),
            shape_ids=(10, 11),
            base_x_mm=0.0,
            base_y_mm=0.0,
            target_x_mm=40.0,
            target_y_mm=0.0,
            new_cell_id="cell:new",
        )
        self.assertTrue(plan.reset_identity)
        self.assertEqual(plan.new_cell_id, "cell:new")
        request = build_base_point_copy_execution_request(plan)
        self.assertTrue(request.identity_reset_required)
        self.assertEqual(request.new_cell_id, "cell:new")

    def test_copy_refuses_multiple_managed_cell_identities(self):
        with self.assertRaisesRegex(
            VisioQolError,
            "multiple_cell_identities",
        ):
            plan_copy_with_base_point(
                snapshot(
                    managed_id="cell:a",
                    second_managed_id="cell:b",
                ),
                shape_ids=(10, 11),
                base_x_mm=0.0,
                base_y_mm=0.0,
                target_x_mm=40.0,
                target_y_mm=0.0,
                new_cell_id="cell:c",
            )

    def test_zero_offset_fails_closed(self):
        with self.assertRaisesRegex(VisioQolError, "zero_offset"):
            plan_exact_offset(
                snapshot(),
                shape_ids=(10, 11),
                dx_mm=0.0,
                dy_mm=0.0,
            )


if __name__ == "__main__":
    unittest.main()
