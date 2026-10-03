from __future__ import annotations

from dataclasses import replace
import unittest

from energologic.frontends.visio import (
    VisioConnectionPoint,
    VisioGeometry,
    VisioGlueSnapshot,
    VisioPageSnapshot,
    VisioQolError,
    VisioShapeSnapshot,
    build_duplicate_execution_request,
    build_glue_repair_execution_request,
    build_move_execution_request,
    discover_cell,
    discover_cell_anchor,
    find_glue_candidates,
    measure_cell_pitch,
    plan_duplicate_cell,
    plan_move_cell_to_adjacent_slot,
    plan_repair_glue,
)


MM = 25.4


def inch(mm: float) -> float:
    return mm / MM


def live_qol_snapshot(*, occupy_right_slot: bool = False) -> VisioPageSnapshot:
    shapes = [
        VisioShapeSnapshot(
            101,
            "Шина10",
            "1 С 35 кВ",
            geometry=VisioGeometry(inch(65.0), inch(255.0), inch(210.0), 0.0),
        ),
        # Real MCP-v2 edge behavior: the visible left slot is User.nt=9,
        # followed by slot 2 = nt=1 and slot 3 = nt=2.
        VisioShapeSnapshot(
            112,
            "",
            "1",
            user_cells={"nt": "9"},
            parent_shape_id=101,
            geometry=VisioGeometry(inch(70.0), inch(255.0), 0.0, 0.0),
        ),
        VisioShapeSnapshot(
            103,
            "",
            "2",
            user_cells={"nt": "1"},
            parent_shape_id=101,
            geometry=VisioGeometry(inch(110.0), inch(255.0), 0.0, 0.0),
        ),
        VisioShapeSnapshot(
            105,
            "",
            "3",
            user_cells={"nt": "2"},
            parent_shape_id=101,
            geometry=VisioGeometry(inch(150.0), inch(255.0), 0.0, 0.0),
        ),
        VisioShapeSnapshot(
            66,
            "Выкатная тележка выключателя",
            "В-1-35",
            geometry=VisioGeometry(inch(110.0), inch(239.625), inch(29.25), 0.0),
        ),
        VisioShapeSnapshot(
            69,
            "ТТ",
            "ТТ\nВ-1-35",
            geometry=VisioGeometry(inch(110.0), inch(217.5), inch(15.0), 0.0),
        ),
        VisioShapeSnapshot(
            71,
            "ОПН  с заземлением",
            "ОПН\nВ-1-35",
            geometry=VisioGeometry(inch(117.5), inch(202.5), inch(15.0), 0.0),
        ),
        VisioShapeSnapshot(
            73,
            "Заземляющий разъединитель",
            "ЗН В-1-35",
            geometry=VisioGeometry(inch(103.0), inch(202.5), inch(15.0), 0.0),
        ),
        VisioShapeSnapshot(
            113,
            "Ошиновка1",
            "",
            geometry=VisioGeometry(inch(110.25), inch(210.0), inch(14.5), 0.0),
        ),
        VisioShapeSnapshot(
            117,
            "ТТ",
            "ТТ НП\nВ-1-35",
            geometry=VisioGeometry(inch(110.0), inch(188.75), inch(42.5), 0.0),
        ),
        VisioShapeSnapshot(
            119,
            "Связь с объектом2",
            "В-1",
            geometry=VisioGeometry(inch(110.0), inch(160.0), 0.0, inch(15.0)),
        ),
        VisioShapeSnapshot(
            247,
            "",
            "",
            geometry=VisioGeometry(inch(110.0), inch(163.0), inch(4.0), inch(5.0)),
        ),
    ]
    connections = [
        VisioGlueSnapshot(66, "BeginX", 103, "Connections.2.X"),
        VisioGlueSnapshot(69, "BeginX", 66, "Connections.2.X"),
        VisioGlueSnapshot(71, "BeginX", 113, "Connections.2.X"),
        VisioGlueSnapshot(73, "BeginX", 113, "Connections.1.X"),
        VisioGlueSnapshot(117, "BeginX", 69, "Connections.2.X"),
        VisioGlueSnapshot(119, "BeginX", 117, "Connections.2.X"),
    ]
    if occupy_right_slot:
        shapes.append(
            VisioShapeSnapshot(
                138,
                "Выкатная тележка выключателя",
                "В-2-35",
                geometry=VisioGeometry(inch(150.0), inch(239.625), inch(29.25), 0.0),
            )
        )
        connections.append(
            VisioGlueSnapshot(138, "BeginX", 105, "Connections.2.X")
        )
    return VisioPageSnapshot("MCP-v2", tuple(shapes), tuple(connections))


class VisioQolTests(unittest.TestCase):
    def test_live_cell_anchor_uses_native_bus_terminal_metadata(self):
        anchor = discover_cell_anchor(live_qol_snapshot(), seed_shape_id=66)
        self.assertEqual(anchor.shape_id, 66)
        self.assertAlmostEqual(anchor.x_mm, 110.0, places=6)
        self.assertEqual(anchor.bus_shape_id, 101)
        self.assertEqual(anchor.bus_terminal_shape_id, 103)
        self.assertEqual(anchor.bus_terminal_nt, 1)
        self.assertEqual(anchor.bus_slot_index, 2)
        self.assertEqual(anchor.source_endpoint, "begin")
        self.assertEqual(anchor.target_connection_row, 2)

    def test_cell_discovery_keeps_glue_core_separate_from_visual_membership(self):
        cell = discover_cell(
            live_qol_snapshot(),
            seed_shape_id=66,
            pitch_mm=40.0,
        )
        self.assertEqual(
            cell.electrical_core_shape_ids,
            (66, 69, 117, 119),
        )
        self.assertEqual(
            cell.member_shape_ids,
            (66, 69, 71, 73, 113, 117, 119, 247),
        )

    def test_geometry_only_member_never_becomes_electrical_core(self):
        original = live_qol_snapshot()
        annotation = VisioShapeSnapshot(
            500,
            "Annotation",
            "note",
            geometry=VisioGeometry(inch(111.0), inch(200.0), inch(5.0), inch(2.0)),
        )
        snapshot = replace(original, shapes=original.shapes + (annotation,))
        cell = discover_cell(snapshot, seed_shape_id=66, pitch_mm=40.0)
        self.assertIn(500, cell.member_shape_ids)
        self.assertNotIn(500, cell.electrical_core_shape_ids)

    def test_measures_real_40_mm_pitch_between_same_bus_anchors(self):
        pitch = measure_cell_pitch(
            live_qol_snapshot(occupy_right_slot=True),
            first_seed_shape_id=66,
            second_seed_shape_id=138,
        )
        self.assertAlmostEqual(pitch, 40.0, places=6)

    def test_duplicate_right_uses_visible_next_slot_and_native_nt(self):
        plan = plan_duplicate_cell(
            live_qol_snapshot(),
            source_seed_shape_id=66,
            direction="right",
            pitch_mm=40.0,
            new_cell_id="cell:v2",
        )
        self.assertEqual(plan.shape_ids, (66, 69, 71, 73, 113, 117, 119, 247))
        self.assertEqual(plan.dx_mm, 40.0)
        self.assertEqual(plan.dy_mm, 0.0)
        self.assertEqual(plan.source_bus_slot_index, 2)
        self.assertEqual(plan.target_bus_slot_index, 3)
        self.assertEqual(plan.target_bus_terminal_shape_id, 105)
        self.assertEqual(plan.target_bus_terminal_nt, 2)
        self.assertEqual(plan.source_endpoint, "begin")
        self.assertEqual(plan.target_connection_row, 2)
        self.assertEqual(plan.new_cell_id, "cell:v2")
        self.assertTrue(plan.reset_identity)

    def test_execution_request_contains_no_hardcoded_runtime_ids(self):
        plan = plan_duplicate_cell(
            live_qol_snapshot(),
            source_seed_shape_id=66,
            direction="right",
            pitch_mm=40.0,
            new_cell_id="cell:v2",
        )
        request = build_duplicate_execution_request(plan)
        self.assertEqual(request.tool_name, "duplicate_shapes_exact")
        self.assertEqual(request.shape_ids_json, "[66,69,71,73,113,117,119,247]")
        self.assertEqual(request.dx_mm, 40.0)
        self.assertEqual(request.dy_mm, 0.0)
        self.assertEqual(
            request.glue_items_json,
            '[{"endpoint":"begin","source_shape_id":66,"target_connection_row":2,"target_shape_id":105}]',
        )
        self.assertEqual(request.new_cell_id, "cell:v2")
        self.assertTrue(request.identity_reset_required)
        self.assertEqual(
            request.arguments(),
            {
                "shape_ids_json": "[66,69,71,73,113,117,119,247]",
                "dx_mm": 40.0,
                "dy_mm": 0.0,
                "select_result": True,
                "glue_items_json": request.glue_items_json,
                "new_cell_id": "cell:v2",
            },
        )

    def test_duplicate_left_handles_real_nt_wrap_without_nt_minus_one_guess(self):
        plan = plan_duplicate_cell(
            live_qol_snapshot(),
            source_seed_shape_id=66,
            direction="left",
            pitch_mm=40.0,
            new_cell_id="cell:v2",
        )
        self.assertEqual(plan.dx_mm, -40.0)
        self.assertEqual(plan.source_bus_slot_index, 2)
        self.assertEqual(plan.target_bus_slot_index, 1)
        self.assertEqual(plan.target_bus_terminal_shape_id, 112)
        self.assertEqual(plan.target_bus_terminal_nt, 9)

    def test_occupied_target_terminal_fails_closed(self):
        with self.assertRaisesRegex(VisioQolError, "target_bus_terminal_occupied"):
            plan_duplicate_cell(
                live_qol_snapshot(occupy_right_slot=True),
                source_seed_shape_id=66,
                direction="right",
                pitch_mm=40.0,
                new_cell_id="cell:v2",
            )

    def test_explicit_terminal_must_match_requested_direction(self):
        with self.assertRaisesRegex(VisioQolError, "bus_terminal_direction_mismatch"):
            plan_duplicate_cell(
                live_qol_snapshot(),
                source_seed_shape_id=66,
                direction="right",
                pitch_mm=40.0,
                new_cell_id="cell:v2",
                target_bus_terminal_nt=9,
            )

    def test_ambiguous_visible_bus_slot_fails_closed(self):
        original = live_qol_snapshot()
        duplicate_slot = VisioShapeSnapshot(
            999,
            "",
            "3",
            user_cells={"nt": "7"},
            parent_shape_id=101,
        )
        snapshot = replace(original, shapes=original.shapes + (duplicate_slot,))
        with self.assertRaisesRegex(VisioQolError, "ambiguous_bus_slot"):
            plan_duplicate_cell(
                snapshot,
                source_seed_shape_id=66,
                direction="right",
                pitch_mm=40.0,
                new_cell_id="cell:v2",
            )

    def test_duplicate_requires_safe_explicit_new_cell_id(self):
        with self.assertRaisesRegex(VisioQolError, "invalid_energologic_cell_id"):
            plan_duplicate_cell(
                live_qol_snapshot(),
                source_seed_shape_id=66,
                direction="right",
                pitch_mm=40.0,
                new_cell_id='bad "formula"',
            )

    def test_cell_boundary_is_not_silently_assigned(self):
        original = live_qol_snapshot()
        boundary = VisioShapeSnapshot(
            998,
            "Annotation",
            "boundary",
            geometry=VisioGeometry(inch(130.0), inch(200.0), 0.0, 0.0),
        )
        snapshot = replace(original, shapes=original.shapes + (boundary,))
        with self.assertRaisesRegex(VisioQolError, "ambiguous_cell_boundary"):
            discover_cell(snapshot, seed_shape_id=66, pitch_mm=40.0)


    def test_move_right_uses_native_bus_terminal_geometry(self):
        plan = plan_move_cell_to_adjacent_slot(
            live_qol_snapshot(),
            source_seed_shape_id=66,
            direction="right",
            pitch_mm=40.0,
        )
        self.assertEqual(
            plan.shape_ids,
            (66, 69, 71, 73, 113, 117, 119, 247),
        )
        self.assertAlmostEqual(plan.dx_mm, 40.0, places=6)
        self.assertAlmostEqual(plan.dy_mm, 0.0, places=6)
        self.assertEqual(plan.source_bus_terminal_shape_id, 103)
        self.assertEqual(plan.source_bus_terminal_nt, 1)
        self.assertEqual(plan.target_bus_terminal_shape_id, 105)
        self.assertEqual(plan.target_bus_terminal_nt, 2)
        self.assertEqual(plan.source_bus_slot_index, 2)
        self.assertEqual(plan.target_bus_slot_index, 3)
        self.assertEqual(plan.source_endpoint, "begin")
        self.assertEqual(plan.target_connection_row, 2)

    def test_move_execution_request_detaches_and_reglues_same_anchor(self):
        plan = plan_move_cell_to_adjacent_slot(
            live_qol_snapshot(),
            source_seed_shape_id=66,
            direction="right",
            pitch_mm=40.0,
        )
        request = build_move_execution_request(plan)
        self.assertEqual(request.tool_name, "move_shapes_exact")
        self.assertEqual(
            request.shape_ids_json,
            "[66,69,71,73,113,117,119,247]",
        )
        self.assertAlmostEqual(request.dx_mm, 40.0, places=6)
        self.assertAlmostEqual(request.dy_mm, 0.0, places=6)
        self.assertEqual(
            request.detach_items_json,
            '[{"endpoint":"begin","expected_target_connection_row":2,'
            '"expected_target_shape_id":103,"shape_id":66}]',
        )
        self.assertEqual(
            request.glue_items_json,
            '[{"endpoint":"begin","shape_id":66,'
            '"target_connection_row":2,"target_shape_id":105}]',
        )
        self.assertEqual(
            request.arguments(),
            {
                "shape_ids_json": "[66,69,71,73,113,117,119,247]",
                "dx_mm": request.dx_mm,
                "dy_mm": request.dy_mm,
                "select_result": True,
                "detach_items_json": request.detach_items_json,
                "glue_items_json": request.glue_items_json,
            },
        )

    def test_move_left_uses_real_slot_order_not_nt_arithmetic(self):
        plan = plan_move_cell_to_adjacent_slot(
            live_qol_snapshot(),
            source_seed_shape_id=66,
            direction="left",
            pitch_mm=40.0,
        )
        self.assertAlmostEqual(plan.dx_mm, -40.0, places=6)
        self.assertEqual(plan.target_bus_slot_index, 1)
        self.assertEqual(plan.target_bus_terminal_shape_id, 112)
        self.assertEqual(plan.target_bus_terminal_nt, 9)

    def test_move_to_occupied_bus_terminal_fails_closed(self):
        with self.assertRaisesRegex(
            VisioQolError,
            "target_bus_terminal_occupied",
        ):
            plan_move_cell_to_adjacent_slot(
                live_qol_snapshot(occupy_right_slot=True),
                source_seed_shape_id=66,
                direction="right",
                pitch_mm=40.0,
            )

    def test_move_rejects_bus_geometry_that_breaks_declared_pitch(self):
        original = live_qol_snapshot()
        shapes = list(original.shapes)
        target_index = next(
            index
            for index, shape in enumerate(shapes)
            if shape.shape_id == 105
        )
        shapes[target_index] = replace(
            shapes[target_index],
            geometry=VisioGeometry(
                inch(151.0),
                inch(255.0),
                0.0,
                0.0,
            ),
        )
        snapshot = replace(original, shapes=tuple(shapes))
        with self.assertRaisesRegex(VisioQolError, "bus_pitch_mismatch"):
            plan_move_cell_to_adjacent_slot(
                snapshot,
                source_seed_shape_id=66,
                direction="right",
                pitch_mm=40.0,
            )



    def test_find_glue_candidates_uses_page_coordinates_not_visual_touching(self):
        points = (
            VisioConnectionPoint(105, 1, 150.0, 255.75),
            VisioConnectionPoint(105, 2, 150.0, 254.25),
        )
        candidates = find_glue_candidates(
            source_shape_id=66,
            source_endpoint="begin",
            source_x_mm=150.0,
            source_y_mm=254.25,
            connection_points=points,
            tolerance_mm=1.0,
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].target_shape_id, 105)
        self.assertEqual(candidates[0].target_connection_row, 2)
        self.assertAlmostEqual(candidates[0].distance_mm, 0.0, places=9)

    def test_repair_glue_auto_plan_requires_exactly_one_candidate(self):
        points = (
            VisioConnectionPoint(105, 1, 150.0, 255.75),
            VisioConnectionPoint(105, 2, 150.0, 254.25),
        )
        plan = plan_repair_glue(
            source_shape_id=66,
            source_endpoint="begin",
            source_x_mm=150.0,
            source_y_mm=254.25,
            connection_points=points,
            tolerance_mm=1.0,
        )
        self.assertEqual(plan.candidate.target_shape_id, 105)
        self.assertEqual(plan.candidate.target_connection_row, 2)

        with self.assertRaisesRegex(
            VisioQolError,
            "ambiguous_glue_candidate",
        ):
            plan_repair_glue(
                source_shape_id=66,
                source_endpoint="begin",
                source_x_mm=150.0,
                source_y_mm=254.25,
                connection_points=points,
                tolerance_mm=2.0,
            )

    def test_repair_glue_allows_explicit_preview_selection_when_ambiguous(self):
        points = (
            VisioConnectionPoint(105, 1, 150.0, 255.75),
            VisioConnectionPoint(105, 2, 150.0, 254.25),
        )
        plan = plan_repair_glue(
            source_shape_id=66,
            source_endpoint="begin",
            source_x_mm=150.0,
            source_y_mm=254.25,
            connection_points=points,
            tolerance_mm=2.0,
            selected_target_shape_id=105,
            selected_target_connection_row=2,
        )
        self.assertEqual(plan.candidate.target_connection_row, 2)
        self.assertAlmostEqual(plan.candidate.distance_mm, 0.0, places=9)

    def test_repair_glue_refuses_already_glued_endpoint(self):
        with self.assertRaisesRegex(VisioQolError, "endpoint_already_glued"):
            plan_repair_glue(
                source_shape_id=66,
                source_endpoint="begin",
                source_x_mm=150.0,
                source_y_mm=254.25,
                connection_points=(
                    VisioConnectionPoint(105, 2, 150.0, 254.25),
                ),
                source_is_already_glued=True,
            )

    def test_glue_repair_execution_request_is_explicit_native_glue(self):
        plan = plan_repair_glue(
            source_shape_id=66,
            source_endpoint="begin",
            source_x_mm=150.0,
            source_y_mm=254.25,
            connection_points=(
                VisioConnectionPoint(105, 2, 150.0, 254.25),
            ),
        )
        request = build_glue_repair_execution_request(plan)
        self.assertEqual(request.tool_name, "batch_glue_endpoints")
        self.assertEqual(
            request.items_json,
            '[{"endpoint":"begin","shape_id":66,'
            '"target_connection_row":2,"target_shape_id":105}]',
        )
        self.assertEqual(
            request.arguments(),
            {"items_json": request.items_json},
        )

    def test_repair_glue_reports_no_candidate_outside_tolerance(self):
        with self.assertRaisesRegex(VisioQolError, "no_glue_candidate"):
            plan_repair_glue(
                source_shape_id=66,
                source_endpoint="begin",
                source_x_mm=150.0,
                source_y_mm=250.0,
                connection_points=(
                    VisioConnectionPoint(105, 2, 150.0, 254.25),
                ),
                tolerance_mm=1.0,
            )



if __name__ == "__main__":
    unittest.main()
