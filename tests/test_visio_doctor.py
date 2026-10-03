from __future__ import annotations

import unittest

from energologic.frontends.visio import (
    VisioConnectionPoint,
    VisioEndpointProbe,
    VisioGeometry,
    VisioGlueSnapshot,
    VisioPageSnapshot,
    VisioShapeSnapshot,
    diagnose_endpoint_glue,
    diagnose_page_structure,
    diagnose_scheme,
)


def inch(mm: float) -> float:
    return mm / 25.4


def base_snapshot(
    *,
    duplicate_identity: bool = False,
    bad_pitch: bool = False,
) -> VisioPageSnapshot:
    second_x = 151.0 if bad_pitch else 150.0
    second_id = '"cell:a"' if duplicate_identity else '"cell:b"'
    return VisioPageSnapshot(
        page_name="Doctor",
        shapes=(
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
                geometry=VisioGeometry(inch(second_x), inch(255.0)),
            ),
            VisioShapeSnapshot(
                66,
                "Выкатная тележка выключателя",
                "В-1-35",
                user_cells={"EnergoLogicCellId": '"cell:a"'},
                geometry=VisioGeometry(inch(110.0), inch(239.625)),
            ),
            VisioShapeSnapshot(
                138,
                "Выкатная тележка выключателя",
                "В-2-35",
                user_cells={"EnergoLogicCellId": second_id},
                geometry=VisioGeometry(inch(second_x), inch(239.625)),
            ),
        ),
        connections=(
            VisioGlueSnapshot(66, "BeginX", 103, "Connections.2.X"),
            VisioGlueSnapshot(138, "BeginX", 105, "Connections.2.X"),
        ),
    )


class SchemeDoctorTests(unittest.TestCase):
    def test_clean_page_has_no_structural_issues(self):
        self.assertEqual(
            diagnose_page_structure(
                base_snapshot(),
                expected_pitch_mm=40.0,
            ),
            (),
        )

    def test_duplicate_cell_identity_is_reported_only_across_bus_anchors(self):
        issues = diagnose_page_structure(
            base_snapshot(duplicate_identity=True),
            expected_pitch_mm=40.0,
        )
        self.assertEqual(
            {issue.code for issue in issues},
            {"duplicate_cell_identity"},
        )
        self.assertIn("66,138", issues[0].message)

    def test_bus_pitch_mismatch_is_reported(self):
        issues = diagnose_page_structure(
            base_snapshot(bad_pitch=True),
            expected_pitch_mm=40.0,
            pitch_tolerance_mm=0.25,
        )
        self.assertIn(
            "bus_pitch_mismatch",
            {issue.code for issue in issues},
        )

    def test_visual_touch_without_native_glue_is_an_error(self):
        issues = diagnose_endpoint_glue(
            VisioEndpointProbe(
                66,
                "begin",
                150.0,
                254.25,
                False,
            ),
            (
                VisioConnectionPoint(105, 2, 150.0, 254.25),
            ),
            tolerance_mm=0.5,
        )
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "visual_touch_without_glue")

    def test_real_glue_suppresses_geometry_warning(self):
        self.assertEqual(
            diagnose_endpoint_glue(
                VisioEndpointProbe(
                    66,
                    "begin",
                    150.0,
                    254.25,
                    True,
                ),
                (
                    VisioConnectionPoint(105, 2, 150.0, 254.25),
                ),
            ),
            (),
        )

    def test_ambiguous_geometric_candidates_fail_closed(self):
        issues = diagnose_endpoint_glue(
            VisioEndpointProbe(
                66,
                "begin",
                150.0,
                254.25,
                False,
            ),
            (
                VisioConnectionPoint(105, 1, 150.0, 254.5),
                VisioConnectionPoint(105, 2, 150.0, 254.25),
            ),
            tolerance_mm=0.5,
        )
        self.assertEqual(len(issues), 1)
        self.assertEqual(
            issues[0].code,
            "ambiguous_visual_touch_without_glue",
        )

    def test_combined_scheme_diagnostics_are_deterministic(self):
        issues = diagnose_scheme(
            base_snapshot(duplicate_identity=True, bad_pitch=True),
            endpoint_probes=(
                VisioEndpointProbe(66, "begin", 150.0, 254.25, False),
            ),
            connection_points=(
                VisioConnectionPoint(105, 2, 150.0, 254.25),
            ),
            expected_pitch_mm=40.0,
        )
        self.assertEqual(
            tuple(issue.code for issue in issues),
            tuple(sorted(issue.code for issue in issues)),
        )
        self.assertEqual(
            {issue.code for issue in issues},
            {
                "bus_pitch_mismatch",
                "duplicate_cell_identity",
                "visual_touch_without_glue",
            },
        )


if __name__ == "__main__":
    unittest.main()
