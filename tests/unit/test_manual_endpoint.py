"""Offline unit tests for movement.manual_endpoint (pure stdlib)."""

from __future__ import annotations

import math
import unittest

from movement.manual_endpoint import (
    Measurement,
    Point,
    annotation_interval,
    measure_endpoint,
)

HASH = "a" * 64
HASH2 = "b" * 64
W, H = 640, 480
PTS = 10.0


def pt(x: float, y: float, pts: float = PTS, h: str = HASH) -> Point:
    return Point(x=x, y=y, frame_pts_s=pts, source_hash=h)


def call(**kw: object) -> dict[str, Measurement]:
    args: dict[str, object] = {
        "bar": pt(100.0, 100.0),
        "chest": pt(100.0, 150.0),
        "shoulder": pt(100.0, 120.0),
        "hip": pt(100.0, 220.0),
        "width": W,
        "height": H,
        "expected_source_sha256": HASH,
        "expected_frame_pts_s": PTS,
        "max_pts_delta_s": 0.04,
    }
    args.update(kw)
    return measure_endpoint(**args)  # type: ignore[arg-type]


class TestGeometry(unittest.TestCase):
    def test_normalized_values(self) -> None:
        out = call()
        self.assertAlmostEqual(out["bar_chest_vertical_norm"].value or 0.0, -0.5)
        self.assertAlmostEqual(out["bar_chest_euclidean_norm"].value or 0.0, 0.5)
        self.assertIsNone(out["bar_chest_vertical_norm"].reason)

    def test_scaling_invariance(self) -> None:
        out = call(
            bar=pt(200.0, 200.0),
            chest=pt(200.0, 300.0),
            shoulder=pt(200.0, 240.0),
            hip=pt(200.0, 440.0),
        )
        self.assertAlmostEqual(out["bar_chest_vertical_norm"].value or 0.0, -0.5)
        self.assertAlmostEqual(out["bar_chest_euclidean_norm"].value or 0.0, 0.5)

    def test_translation_invariance(self) -> None:
        out = call(
            bar=pt(300.0, 200.0),
            chest=pt(300.0, 250.0),
            shoulder=pt(300.0, 220.0),
            hip=pt(300.0, 320.0),
        )
        self.assertAlmostEqual(out["bar_chest_vertical_norm"].value or 0.0, -0.5)
        self.assertAlmostEqual(out["bar_chest_euclidean_norm"].value or 0.0, 0.5)

    def test_missing_point(self) -> None:
        out = call(bar=None)
        self.assertEqual(out["bar_chest_vertical_norm"].reason, "missing_coordinates")
        self.assertIsNone(out["bar_chest_euclidean_norm"].value)

    def test_degenerate_segment(self) -> None:
        out = call(shoulder=pt(50.0, 50.0), hip=pt(50.0, 50.0))
        self.assertEqual(out["bar_chest_vertical_norm"].reason, "degenerate_body_segment")


class TestProvenance(unittest.TestCase):
    def test_hash_mismatch(self) -> None:
        out = call(bar=pt(100.0, 100.0, h=HASH2))
        self.assertEqual(out["bar_chest_vertical_norm"].reason, "source_hash_mismatch")

    def test_expected_hash_mismatch(self) -> None:
        out = call(expected_source_sha256=HASH2)
        self.assertEqual(out["bar_chest_euclidean_norm"].reason, "source_hash_mismatch")

    def test_frame_pts_exceeds_allowance(self) -> None:
        out = call(bar=pt(100.0, 100.0, pts=PTS + 0.05))
        self.assertEqual(out["bar_chest_vertical_norm"].reason, "frame_pts_delta_exceeds_allowance")

    def test_within_allowance_ok(self) -> None:
        out = call(bar=pt(100.0, 100.0, pts=PTS + 0.03))
        self.assertIsNone(out["bar_chest_vertical_norm"].reason)

    def test_zero_allowance_exact_frame_valid(self) -> None:
        out = call(max_pts_delta_s=0.0)
        self.assertIsNone(out["bar_chest_vertical_norm"].reason)

    def test_zero_allowance_any_delta_fails(self) -> None:
        out = call(max_pts_delta_s=0.0, bar=pt(100.0, 100.0, pts=PTS + 1e-9))
        self.assertEqual(out["bar_chest_vertical_norm"].reason, "frame_pts_delta_exceeds_allowance")

    def test_out_of_bounds_exclusive(self) -> None:
        out = call(bar=pt(float(W), 100.0))
        self.assertEqual(out["bar_chest_vertical_norm"].reason, "point_out_of_image_bounds")
        out = call(bar=pt(-0.001, 100.0))
        self.assertEqual(out["bar_chest_vertical_norm"].reason, "point_out_of_image_bounds")
        out = call(bar=pt(100.0, float(H)))
        self.assertEqual(out["bar_chest_vertical_norm"].reason, "point_out_of_image_bounds")

    def test_contact_always_unavailable_even_zero_2d(self) -> None:
        out = call(bar=pt(100.0, 150.0))
        self.assertIsNone(out["bar_chest_contact"].value)
        self.assertEqual(out["bar_chest_contact"].reason, "contact_unavailable_depth_unobserved")


class TestValidation(unittest.TestCase):
    def test_bad_hash_format(self) -> None:
        with self.assertRaises(ValueError):
            pt(1.0, 1.0, h="A" * 64)
        with self.assertRaises(ValueError):
            pt(1.0, 1.0, h="a" * 63)
        with self.assertRaises(ValueError):
            call(expected_source_sha256="zz")

    def test_bool_nan_inf_rejected(self) -> None:
        for bad in (True, math.nan, math.inf):
            with self.assertRaises(ValueError):
                Point(x=bad, y=1.0, frame_pts_s=0.0, source_hash=HASH)  # type: ignore[arg-type]
            with self.assertRaises(ValueError):
                call(max_pts_delta_s=bad)
            with self.assertRaises(ValueError):
                call(expected_frame_pts_s=bad)
        with self.assertRaises(ValueError):
            call(width=True)
        with self.assertRaises(ValueError):
            call(width=0)
        with self.assertRaises(ValueError):
            call(max_pts_delta_s=-0.1)
        with self.assertRaises(ValueError):
            Measurement(value=math.nan, reason=None, unit="ratio")
        with self.assertRaises(ValueError):
            Measurement(value=None, reason=None, unit="ratio")


class TestAnnotationInterval(unittest.TestCase):
    def test_spread(self) -> None:
        m = annotation_interval([1.0, 4.5, 2.0])
        self.assertAlmostEqual(m.value or 0.0, 3.5)
        self.assertEqual(m.unit, "pixels")

    def test_invalid(self) -> None:
        for bad in ([1.0], "12", [1.0, math.nan], [1.0, True], None):
            with self.assertRaises(ValueError):
                annotation_interval(bad)


if __name__ == "__main__":
    unittest.main()
