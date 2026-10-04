from __future__ import annotations

from dataclasses import replace
import copy
import json
from pathlib import Path
import unittest

from energologic.frontends.visio.legacy_inspection import (
    CONFIDENCE_EXACT_NATIVE,
    LegacyConnectionPoint,
    LegacyDocumentSnapshot,
    LegacyGeometry,
    LegacyGlueSnapshot,
    LegacyPageSnapshot,
    LegacyShapeSheetCell,
    LegacyShapeSnapshot,
    inspect_legacy_visio,
    report_json,
)


def geometry_cells(points: tuple[tuple[float, float], ...]):
    cells = []
    for row, (x, y) in enumerate(points, start=1):
        cells.extend(
            (
                LegacyShapeSheetCell(
                    "Geometry1", str(row), "X", f"{x}", x
                ),
                LegacyShapeSheetCell(
                    "Geometry1", str(row), "Y", f"{y}", y
                ),
            )
        )
    return tuple(cells)


def breaker(
    shape_id: int,
    *,
    x: float,
    y: float,
    text: str,
    parent: int | None = None,
    variant: float = 1.0,
) -> LegacyShapeSnapshot:
    return LegacyShapeSnapshot(
        shape_id=shape_id,
        name=f"breaker-{shape_id}",
        name_u="LegacyBreaker",
        shape_type="Group" if parent is None else "Shape",
        master_name="Старый выключатель",
        master_name_u="LegacyCircuitBreaker",
        master_shape_id=777,
        parent_shape_id=parent,
        geometry=LegacyGeometry(x, y, 10.0 * variant, 20.0, 0.0),
        text=text,
        layers=("35 кВ",),
        cells=geometry_cells(
            (
                (0.0, 0.0),
                (5.0 * variant, 10.0),
                (10.0 * variant, 0.0),
            )
        )
        + (
            LegacyShapeSheetCell(
                "User", "Mode", "Value", "IF(Prop.State=1,1,0)", 1
            ),
            LegacyShapeSheetCell(
                "Prop", "Designation", "Value", f'"{text}"', text
            ),
        ),
        connection_points=(
            LegacyConnectionPoint(
                "1", 5.0 * variant, 0.0, "Width*0.5", "0"
            ),
            LegacyConnectionPoint(
                "2", 5.0 * variant, 20.0, "Width*0.5", "Height"
            ),
        ),
        begin_x_formula="PAR(PNT(Sheet.1!Connections.X1,Sheet.1!Connections.Y1))",
        end_x_formula="PAR(PNT(Sheet.2!Connections.X2,Sheet.2!Connections.Y2))",
    )


def report_for(*shapes: LegacyShapeSnapshot, connects=()):
    return inspect_legacy_visio(
        LegacyDocumentSnapshot(
            name="synthetic.vsdx",
            full_name=r"C:\fixtures\synthetic.vsdx",
            visio_version="16.0",
            read_only=True,
            pages=(
                LegacyPageSnapshot(
                    page_id=1,
                    name="Схема",
                    name_u="Page-1",
                    width=1000,
                    height=700,
                    shapes=tuple(shapes),
                    connects=tuple(connects),
                ),
            ),
            metadata={"fixture": True},
        )
    )


class LegacyVisioInspectorTests(unittest.TestCase):
    def test_same_symbol_different_shape_id_coordinates_and_text_same_family(self):
        first = breaker(10, x=100, y=100, text="QF-101")
        second = breaker(991, x=800, y=500, text="QF-202")
        report = report_for(first, second)

        self.assertEqual(report["statistics"]["symbol_family_count"], 1)
        family = report["symbol_families"][0]
        self.assertEqual(family["frequency"], 2)
        self.assertEqual(
            {item["family_id"] for item in report["instances"]},
            {family["family_id"]},
        )
        self.assertNotEqual(
            report["instances"][0]["text"],
            report["instances"][1]["text"],
        )

    def test_master_name_u_is_stable_identity_and_display_name_is_not(self):
        first = breaker(10, x=100, y=100, text="QF-101")
        second = replace(
            breaker(20, x=200, y=200, text="QF-202"),
            master_name="Переименованный отображаемый master",
        )
        report = report_for(first, second)
        self.assertEqual(report["statistics"]["symbol_family_count"], 1)

    def test_uniform_scale_preserves_symbol_family(self):
        first = breaker(10, x=100, y=100, text="QF-101")
        second = breaker(20, x=300, y=300, text="QF-202")
        second = replace(
            second,
            geometry=replace(
                second.geometry,
                width=second.geometry.width * 2,
                height=second.geometry.height * 2,
            ),
            cells=geometry_cells(((0, 0), (10, 20), (20, 0)))
            + tuple(cell for cell in second.cells if not cell.section.startswith("Geometry")),
            connection_points=(
                LegacyConnectionPoint("1", 10, 0, "Width*0.5", "0"),
                LegacyConnectionPoint("2", 10, 40, "Width*0.5", "Height"),
            ),
        )
        report = report_for(first, second)
        self.assertEqual(report["statistics"]["symbol_family_count"], 1)

    def test_different_geometry_does_not_collapse(self):
        first = breaker(10, x=100, y=100, text="QF-101")
        second = breaker(20, x=200, y=200, text="QF-102", variant=0.55)
        report = report_for(first, second)
        self.assertEqual(report["statistics"]["symbol_family_count"], 2)

    def test_text_variation_is_separate_signal(self):
        first = breaker(10, x=100, y=100, text="QF-101")
        second = breaker(20, x=200, y=200, text="QF-205")
        report = report_for(first, second)
        self.assertEqual(report["statistics"]["symbol_family_count"], 1)
        patterns = report["symbol_families"][0]["text_patterns"]
        self.assertEqual(patterns, ["qf-#"])
        self.assertTrue(
            all(
                item["separate_from_symbol_geometry"]
                for item in report["text_designation_candidates"]
            )
        )

    def test_groups_and_nested_shapes_affect_group_structure(self):
        child_a = LegacyShapeSnapshot(
            shape_id=2,
            parent_shape_id=1,
            shape_type="Shape",
            geometry=LegacyGeometry(102, 103, 2, 3, 0),
            cells=geometry_cells(((0, 0), (2, 3))),
        )
        child_b = LegacyShapeSnapshot(
            shape_id=3,
            parent_shape_id=2,
            shape_type="Shape",
            geometry=LegacyGeometry(102.5, 103.5, 1, 1, 0),
            cells=geometry_cells(((0, 0), (1, 1))),
        )
        group = LegacyShapeSnapshot(
            shape_id=1,
            shape_type="Group",
            master_name="GroupMaster",
            geometry=LegacyGeometry(100, 100, 10, 10, 0),
        )
        report = report_for(group, child_a, child_b)

        by_id = {item["shape_id"]: item for item in report["instances"]}
        self.assertEqual(by_id[1]["child_refs"], ["page:1/shape:2"])
        self.assertEqual(by_id[2]["parent_ref"], "page:1/shape:1")
        self.assertEqual(by_id[2]["child_refs"], ["page:1/shape:3"])
        self.assertEqual(by_id[3]["parent_ref"], "page:1/shape:2")
        self.assertEqual(report["statistics"]["nested_shape_count"], 2)

    def test_native_glue_graph_is_exact_and_not_inferred(self):
        top = breaker(10, x=100, y=200, text="QF-1")
        bottom = breaker(20, x=100, y=100, text="QF-2")
        report = report_for(
            top,
            bottom,
            connects=(LegacyGlueSnapshot(20, "EndX", 10, "Connections.1.X"),),
        )
        edge = report["glue_graph"]["edges"][0]
        self.assertEqual(edge["confidence"], CONFIDENCE_EXACT_NATIVE)
        self.assertFalse(edge["inferred"])
        self.assertIn("page.connects", edge["evidence"])
        self.assertEqual(report["glue_graph"]["inferred_edges"], [])
        self.assertFalse(
            report["glue_graph"]["policy"]["visual_contact_is_proof"]
        )

    def test_inspector_is_read_only_and_deterministic(self):
        source = LegacyDocumentSnapshot(
            name="readonly.vsdx",
            pages=(
                LegacyPageSnapshot(
                    page_id=1,
                    name="P",
                    shapes=(breaker(1, x=1, y=2, text="QF-1"),),
                ),
            ),
            metadata={"sentinel": "unchanged"},
        )
        before = copy.deepcopy(source)
        first = inspect_legacy_visio(source)
        second = inspect_legacy_visio(source)

        self.assertEqual(source, before)
        self.assertTrue(first["source_contract"]["read_only"])
        self.assertFalse(first["source_contract"]["mutates_source"])
        self.assertEqual(first["inspection_fingerprint"], second["inspection_fingerprint"])
        self.assertEqual(report_json(first), report_json(second))

    def test_report_exposes_shapesheet_and_frequency_statistics(self):
        first = breaker(10, x=100, y=100, text="QF-101")
        second = breaker(20, x=200, y=200, text="QF-202")
        report = report_for(first, second)
        instance = report["instances"][0]
        self.assertTrue(instance["shape_sheet_cells"])
        self.assertTrue(instance["normalized_geometry_rows"])
        self.assertEqual(
            report["statistics"]["master_frequency"]["LegacyCircuitBreaker"],
            2,
        )
        self.assertEqual(report["statistics"]["text_pattern_frequency"]["qf-#"], 2)

    def test_report_contract_matches_declared_schema_required_keys(self):
        report = report_for(breaker(1, x=0, y=0, text="QF-1"))
        schema = json.loads(
            Path("schema/legacy-visio-inspection-0.1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(set(schema["required"]).issubset(report))
        self.assertEqual(report["report_version"], "legacy-visio-inspection-0.1")

    def test_orphan_parent_is_reported_for_review(self):
        orphan = breaker(10, x=1, y=2, text="QF-1", parent=999)
        report = report_for(orphan)
        self.assertEqual(
            report["ambiguous_unclassified"][0]["reason"],
            "orphan_parent_shape",
        )

    def test_absolute_translation_does_not_change_family_fingerprint(self):
        original = breaker(10, x=100, y=100, text="QF-1")
        moved = replace(
            original,
            shape_id=700,
            geometry=replace(original.geometry, pin_x=900, pin_y=-50),
            text="QF-900",
        )
        a = report_for(original)["symbol_families"][0]["candidate_fingerprint"]
        b = report_for(moved)["symbol_families"][0]["candidate_fingerprint"]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
