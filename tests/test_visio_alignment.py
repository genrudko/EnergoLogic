from __future__ import annotations

import unittest

from energologic.frontends.visio import (
    VisioGeometry,
    VisioGlueSnapshot,
    VisioPageSnapshot,
    VisioQolError,
    VisioShapeSnapshot,
    build_alignment_execution_requests,
    plan_align_free_shapes,
)


def inch(mm: float) -> float:
    return mm / 25.4


def free_snapshot(*, glued: bool = False) -> VisioPageSnapshot:
    shapes = (
        VisioShapeSnapshot(
            10,
            "A",
            "A",
            geometry=VisioGeometry(inch(100.0), inch(50.0)),
        ),
        VisioShapeSnapshot(
            11,
            "B",
            "B",
            geometry=VisioGeometry(inch(106.0), inch(55.0)),
        ),
        VisioShapeSnapshot(
            20,
            "Bus",
            "Bus",
            geometry=VisioGeometry(inch(120.0), inch(55.0)),
        ),
    )
    connections = ()
    if glued:
        connections = (
            VisioGlueSnapshot(11, "BeginX", 20, "Connections.1.X"),
        )
    return VisioPageSnapshot(
        page_name="Align",
        shapes=shapes,
        connections=connections,
    )


class AlignmentTests(unittest.TestCase):
    def test_align_x_uses_reference_pin_not_bounding_box(self):
        plan = plan_align_free_shapes(
            free_snapshot(),
            shape_ids=(10, 11),
            axis="x",
            reference_shape_id=10,
        )
        self.assertEqual(plan.axis, "x")
        self.assertAlmostEqual(plan.target_mm, 100.0)
        self.assertEqual(len(plan.moves), 1)
        self.assertEqual(plan.moves[0].shape_id, 11)
        self.assertAlmostEqual(plan.moves[0].dx_mm, -6.0)
        self.assertAlmostEqual(plan.moves[0].dy_mm, 0.0)

    def test_align_y_can_use_explicit_engineering_coordinate(self):
        plan = plan_align_free_shapes(
            free_snapshot(),
            shape_ids=(10, 11),
            axis="y",
            target_mm=60.0,
        )
        self.assertEqual(
            [(move.shape_id, round(move.dy_mm, 6)) for move in plan.moves],
            [(10, 10.0), (11, 5.0)],
        )

    def test_alignment_builds_exact_move_requests(self):
        plan = plan_align_free_shapes(
            free_snapshot(),
            shape_ids=(10, 11),
            axis="x",
            reference_shape_id=10,
        )
        requests = build_alignment_execution_requests(plan)
        self.assertEqual(len(requests), 1)
        request = requests[0]
        self.assertEqual(request.tool_name, "move_shapes_exact")
        self.assertEqual(request.shape_ids_json, "[11]")
        self.assertAlmostEqual(request.dx_mm, -6.0)
        self.assertEqual(request.detach_items_json, "[]")
        self.assertEqual(request.glue_items_json, "[]")

    def test_alignment_refuses_to_move_glued_equipment(self):
        with self.assertRaisesRegex(
            VisioQolError,
            "glued_shape_requires_electrical_alignment",
        ):
            plan_align_free_shapes(
                free_snapshot(glued=True),
                shape_ids=(10, 11),
                axis="x",
                reference_shape_id=10,
            )

    def test_reference_must_be_selected(self):
        with self.assertRaisesRegex(VisioQolError, "reference_not_selected"):
            plan_align_free_shapes(
                free_snapshot(),
                shape_ids=(10, 11),
                axis="x",
                reference_shape_id=20,
            )

    def test_reference_and_explicit_target_are_mutually_exclusive(self):
        with self.assertRaisesRegex(
            VisioQolError,
            "ambiguous_alignment_target",
        ):
            plan_align_free_shapes(
                free_snapshot(),
                shape_ids=(10, 11),
                axis="x",
                reference_shape_id=10,
                target_mm=100.0,
            )


if __name__ == "__main__":
    unittest.main()
