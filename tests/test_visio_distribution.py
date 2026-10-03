from __future__ import annotations

import unittest

from energologic.frontends.visio import (
    VisioGeometry,
    VisioGlueSnapshot,
    VisioPageSnapshot,
    VisioQolError,
    VisioShapeSnapshot,
    build_distribution_execution_requests,
    plan_distribute_cells_on_bus,
)


def inch(mm: float) -> float:
    return mm / 25.4


def distribution_snapshot(
    *,
    middle_x_mm: float = 150.0,
    occupy_middle: bool = False,
) -> VisioPageSnapshot:
    shapes = [
        VisioShapeSnapshot(
            101,
            "Шина10",
            "1 С 35 кВ",
            geometry=VisioGeometry(inch(150.0), inch(255.0)),
        ),
        VisioShapeSnapshot(
            103,
            "",
            "2",
            user_cells={"nt": "1"},
            parent_shape_id=101,
            geometry=VisioGeometry(inch(110.0), inch(255.0)),
        ),
        VisioShapeSnapshot(
            105,
            "",
            "3",
            user_cells={"nt": "2"},
            parent_shape_id=101,
            geometry=VisioGeometry(inch(middle_x_mm), inch(255.0)),
        ),
        VisioShapeSnapshot(
            107,
            "",
            "4",
            user_cells={"nt": "3"},
            parent_shape_id=101,
            geometry=VisioGeometry(inch(190.0), inch(255.0)),
        ),
        VisioShapeSnapshot(
            66,
            "Выкатная тележка выключателя",
            "В-1-35",
            geometry=VisioGeometry(inch(110.0), inch(239.625)),
        ),
        VisioShapeSnapshot(
            138,
            "Выкатная тележка выключателя",
            "В-3-35",
            geometry=VisioGeometry(inch(190.0), inch(239.625)),
        ),
    ]
    connections = [
        VisioGlueSnapshot(66, "BeginX", 103, "Connections.2.X"),
        VisioGlueSnapshot(138, "BeginX", 107, "Connections.2.X"),
    ]
    if occupy_middle:
        shapes.append(
            VisioShapeSnapshot(
                999,
                "Выкатная тележка выключателя",
                "FOREIGN",
                geometry=VisioGeometry(inch(middle_x_mm), inch(239.625)),
            )
        )
        connections.append(
            VisioGlueSnapshot(999, "BeginX", 105, "Connections.2.X")
        )
    return VisioPageSnapshot(
        page_name="Distribution",
        shapes=tuple(shapes),
        connections=tuple(connections),
    )


class CellDistributionTests(unittest.TestCase):
    def test_distribute_cells_uses_real_native_bus_slots(self):
        plan = plan_distribute_cells_on_bus(
            distribution_snapshot(),
            seed_shape_ids=(66, 138),
            pitch_mm=40.0,
            start_slot_index=2,
        )
        self.assertEqual(plan.bus_shape_id, 101)
        self.assertEqual(plan.ordered_seed_shape_ids, (66, 138))
        self.assertEqual(plan.start_slot_index, 2)
        self.assertEqual(len(plan.moves), 1)

        move = plan.moves[0]
        self.assertEqual(move.source_cell.seed_shape_id, 138)
        self.assertEqual(move.source_bus_slot_index, 4)
        self.assertEqual(move.target_bus_slot_index, 3)
        self.assertEqual(move.target_bus_terminal_shape_id, 105)
        self.assertAlmostEqual(move.dx_mm, -40.0, places=6)
        self.assertAlmostEqual(move.dy_mm, 0.0, places=6)

    def test_distribution_builds_explicit_detach_reglue_request(self):
        plan = plan_distribute_cells_on_bus(
            distribution_snapshot(),
            seed_shape_ids=(66, 138),
            pitch_mm=40.0,
            start_slot_index=2,
        )
        requests = build_distribution_execution_requests(plan)
        self.assertEqual(len(requests), 1)
        request = requests[0]
        self.assertEqual(request.tool_name, "move_shapes_exact")
        self.assertEqual(request.shape_ids_json, "[138]")
        self.assertIn('"expected_target_shape_id":107', request.detach_items_json)
        self.assertIn('"target_shape_id":105', request.glue_items_json)

    def test_distribution_refuses_bus_geometry_that_cannot_support_pitch(self):
        with self.assertRaisesRegex(VisioQolError, "bus_pitch_mismatch"):
            plan_distribute_cells_on_bus(
                distribution_snapshot(middle_x_mm=152.0),
                seed_shape_ids=(66, 138),
                pitch_mm=40.0,
                start_slot_index=2,
            )

    def test_distribution_refuses_foreign_occupant(self):
        with self.assertRaisesRegex(
            VisioQolError,
            "target_bus_terminal_occupied",
        ):
            plan_distribute_cells_on_bus(
                distribution_snapshot(occupy_middle=True),
                seed_shape_ids=(66, 138),
                pitch_mm=40.0,
                start_slot_index=2,
            )

    def test_distribution_requires_at_least_two_cells(self):
        with self.assertRaisesRegex(VisioQolError, "insufficient_cells"):
            plan_distribute_cells_on_bus(
                distribution_snapshot(),
                seed_shape_ids=(66,),
                pitch_mm=40.0,
            )


if __name__ == "__main__":
    unittest.main()
