"""P0-B geometry-only contract, not a claimed Visio live overlay acceptance."""
from __future__ import annotations

from dataclasses import replace
from math import inf, nan
import os
from pathlib import Path
import subprocess
import unittest

from energologic.frontends.visio.viewport_spike import (
    ClientPoint,
    VisioDrawingViewport,
    estimate_centered_client_region,
    calibrate_horizontal_bus,
    project_calibrated_point,
    VisioPageAnchor,
    VisioViewportError,
    project_point,
    project_segment,
)


class VisioViewportSpikeTests(unittest.TestCase):
    def setUp(self):
        self.view = VisioDrawingViewport(
            document_ref="doc:fixture",
            page_ref="page:fixture",
            window_ref="window:1",
            generation=7,
            left_page=1.0,
            top_page=11.0,
            width_page=10.0,
            height_page=10.0,
            client_width_px=1000,
            client_height_px=500,
        )

    def anchor(self, x: float, y: float) -> VisioPageAnchor:
        return VisioPageAnchor(
            document_ref=self.view.document_ref,
            page_ref=self.view.page_ref,
            window_ref=self.view.window_ref,
            generation=self.view.generation,
            x_page=x,
            y_page=y,
        )

    def test_top_left_and_bottom_right_are_client_bounds(self):
        self.assertEqual(project_point(self.view, self.anchor(1, 11)), ClientPoint(0, 0))
        self.assertEqual(project_point(self.view, self.anchor(11, 1)), ClientPoint(1000, 500))

    def test_visio_bottom_up_page_coordinates_are_explicitly_flipped(self):
        self.assertEqual(project_point(self.view, self.anchor(6, 6)), ClientPoint(500, 250))
        self.assertEqual(project_point(self.view, self.anchor(6, 10)), ClientPoint(500, 50))
        self.assertEqual(project_point(self.view, self.anchor(6, 2)), ClientPoint(500, 450))

    def test_off_screen_anchor_is_not_drawn(self):
        for p in [self.anchor(0, 6), self.anchor(12, 6), self.anchor(4, 12), self.anchor(4, 0)]:
            with self.subTest(anchor=p):
                self.assertIsNone(project_point(self.view, p))

    def test_scroll_invalidation_generates_new_projection(self):
        after = replace(self.view, generation=8, left_page=6)
        with self.assertRaises(VisioViewportError):
            project_point(after, self.anchor(6, 6))
        new = replace(self.anchor(6, 6), generation=8)
        self.assertEqual(project_point(after, new), ClientPoint(0, 250))

    def test_zoom_changes_scale_with_no_shape_mutation(self):
        narrower = replace(self.view, width_page=5)
        self.assertEqual(project_point(narrower, self.anchor(6, 6)), ClientPoint(1000, 250))
        self.assertEqual(project_point(self.view, self.anchor(6, 6)), ClientPoint(500, 250))

    def test_client_dimensions_are_independent_of_monitor_origin(self):
        taller = replace(self.view, client_width_px=500, client_height_px=1000)
        self.assertEqual(project_point(taller, self.anchor(6, 6)), ClientPoint(250, 500))

    def test_clipped_horizontal_conductor(self):
        result = project_segment(self.view, self.anchor(-4, 6), self.anchor(16, 6))
        self.assertIsNotNone(result)
        self.assertEqual(result.start, ClientPoint(0, 250))
        self.assertEqual(result.end, ClientPoint(1000, 250))

    def test_clipped_vertical_conductor(self):
        result = project_segment(self.view, self.anchor(6, 0), self.anchor(6, 12))
        self.assertIsNotNone(result)
        self.assertEqual(result.start, ClientPoint(500, 500))
        self.assertEqual(result.end, ClientPoint(500, 0))

    def test_segment_entirely_outside_window(self):
        self.assertIsNone(project_segment(self.view, self.anchor(-3, 4), self.anchor(-2, 8)))
        self.assertIsNone(project_segment(self.view, self.anchor(2, 14), self.anchor(3, 15)))

    def test_zero_length_point_segment_is_qualified(self):
        line = project_segment(self.view, self.anchor(6, 6), self.anchor(6, 6))
        self.assertEqual(line.start, line.end)
        self.assertEqual(line.start, ClientPoint(500, 250))

    def test_mismatched_document_page_and_window_rejected(self):
        for field, value in [
            ("document_ref", "doc:another"), ("page_ref", "page:another"),
            ("window_ref", "window:another"), ("page_unit", "mm"),
            ("generation", 8),
        ]:
            with self.subTest(field=field), self.assertRaises(VisioViewportError):
                project_point(self.view, replace(self.anchor(6, 6), **{field: value}))

    def test_user_log_finds_same_2572_pixel_chrome_at_two_zoom_levels(self):
        # 2026-10-08 user-provided read-only GetViewRect/ClientScreen.
        # A drawing view must have the same physical X/Y scale.
        cases = (
            (20.20528660071778, 12.05005610077602),
            (14.888106609805067, 8.878989119417499),
        )
        for width, height in cases:
            with self.subTest(width=width):
                view = replace(
                    self.view,
                    width_page=width, height_page=height,
                    client_width_px=1471, client_height_px=903,
                )
                estimate = estimate_centered_client_region(view)
                self.assertAlmostEqual(estimate.height_px, 877.2769659, places=5)
                self.assertAlmostEqual(estimate.excluded_height_px, 25.7230341, places=5)
                self.assertAlmostEqual(estimate.top_px, 12.86151705, places=5)
                self.assertAlmostEqual(
                    estimate.width_px / width,
                    estimate.height_px / height,
                    places=8,
                )

    def test_two_manual_bus_anchors_calibrate_scale_and_both_offsets(self):
        view = replace(
            self.view, left_page=0.64, top_page=11.925,
            width_page=14.888106609805071, height_page=8.878989119417497,
            client_width_px=1471, client_height_px=903,
        )
        bus_left = 65.0 / 25.4
        bus_width = 290.0 / 25.4
        bus_y = 255.0 / 25.4
        k = 98.8
        offset_x, offset_y = 15.0, 2.5
        left_px = offset_x + (bus_left - view.left_page) * k
        right_px = left_px + bus_width * k
        y_px = offset_y + (view.top_page - bus_y) * k
        fitted = calibrate_horizontal_bus(
            view, bus_start_page=bus_left, bus_y_page=bus_y,
            bus_width_page=bus_width,
            pointer_left=ClientPoint(left_px, y_px),
            pointer_right=ClientPoint(right_px, y_px),
        )
        def point(x, y, vp=view):
            return VisioPageAnchor(
                vp.document_ref, vp.page_ref, vp.window_ref,
                vp.generation, x, y,
            )
        self.assertAlmostEqual(fitted.offset_x_px, offset_x)
        self.assertAlmostEqual(fitted.offset_y_px, offset_y)
        p = project_calibrated_point(view, fitted, point(bus_left, bus_y))
        self.assertAlmostEqual(p.x_px, left_px)
        self.assertAlmostEqual(p.y_px, y_px)
        scrolled = replace(view, left_page=0.74, top_page=12.225, generation=8)
        p = project_calibrated_point(scrolled, fitted, point(bus_left, bus_y, scrolled))
        self.assertAlmostEqual(p.x_px, left_px - 0.10 * k, places=5)
        self.assertAlmostEqual(p.y_px, y_px + 0.30 * k, places=5)
        zoomed = replace(view, width_page=view.width_page / 1.2, generation=9)
        p = project_calibrated_point(zoomed, fitted, point(bus_left, bus_y, zoomed))
        self.assertAlmostEqual(p.x_px, offset_x + (bus_left - view.left_page) * k * 1.2, places=5)

    def test_two_point_calibration_fails_closed_on_unqualified_sample(self):
        params = dict(
            bus_start_page=2.5, bus_y_page=6, bus_width_page=2,
            pointer_left=ClientPoint(250, 300),
            pointer_right=ClientPoint(450, 300),
        )
        cal = calibrate_horizontal_bus(self.view, **params)
        invalid = [
            dict(pointer_left=ClientPoint(450, 300), pointer_right=ClientPoint(250, 300)),
            dict(pointer_right=ClientPoint(450, 330)),
            dict(bus_width_page=0),
            dict(pointer_right=ClientPoint(nan, 300)),
        ]
        for change in invalid:
            with self.subTest(change=change), self.assertRaises(VisioViewportError):
                calibrate_horizontal_bus(self.view, **dict(params, **change))
        with self.assertRaises(VisioViewportError):
            project_calibrated_point(replace(self.view, client_width_px=1500), cal, self.anchor(5, 6))
        with self.assertRaises(VisioViewportError):
            project_calibrated_point(
                replace(self.view, generation=9), cal,
                self.anchor(5, 6),
            )

    def test_centered_fit_rejects_impossible_client_aspect(self):
        too_short = replace(
            self.view, width_page=10, height_page=10,
            client_width_px=1471, client_height_px=903,
        )
        with self.assertRaises(VisioViewportError):
            estimate_centered_client_region(too_short)
        too_much_chrome = replace(
            self.view, width_page=10, height_page=10,
            client_width_px=1471, client_height_px=1800,
        )
        with self.assertRaises(VisioViewportError):
            estimate_centered_client_region(too_much_chrome)

    def test_invalid_viewport_geometry_fails_closed(self):
        for field, value in [
            ("width_page", 0), ("height_page", -1),
            ("client_width_px", nan), ("client_height_px", inf),
            ("left_page", nan), ("top_page", inf),
            ("width_page", True), ("client_height_px", "800"),
        ]:
            with self.subTest(field=field, value=value), self.assertRaises(VisioViewportError):
                replace(self.view, **{field: value})

    def test_invalid_viewport_identity_fails_closed(self):
        for field, value in [
            ("page_ref", ""), ("document_ref", " "), ("window_ref", None),
            ("generation", 0), ("generation", True), ("page_unit", "mm"),
        ]:
            with self.subTest(field=field), self.assertRaises(VisioViewportError):
                replace(self.view, **{field: value})

    def test_invalid_anchor_coordinate_rejected(self):
        for p in [self.anchor(nan, 6), self.anchor(6, inf), self.anchor("6", 6)]:
            with self.subTest(point=p), self.assertRaises(VisioViewportError):
                project_point(self.view, p)

    @unittest.skipUnless(os.name == "nt", "requires Windows PowerShell/.NET Framework")
    def test_native_probe_powershell_parses_and_embedded_csharp_compiles(self):
        validator = Path(__file__).resolve().parents[1] / "tools" / "p0b_probe_static_validate.ps1"
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-STA", "-ExecutionPolicy",
             "Bypass", "-File", str(validator)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
            check=False,
        )
        self.assertEqual(
            completed.returncode, 0,
            f"PowerShell/C# probe validation failed:\n{completed.stdout}\n{completed.stderr}",
        )
        self.assertIn("P0B_EMBEDDED_CSHARP_COMPILE_PASS", completed.stdout)


if __name__ == "__main__":
    unittest.main()
