"""Frozen analytic expectations independent of perception/calibration."""

import json
import math
from decimal import Decimal, localcontext
from pathlib import Path

import pytest

from movement.observations import angle_degrees


def test_raw_angle_v1_regression() -> None:
    fixture = Path(__file__).parents[1] / "fixtures/movement/raw-angle-v1.json"
    cases = json.loads(fixture.read_text())
    assert cases["version"] == "raw-angle-v1"
    for case in cases["angles"]:
        first = angle_degrees(case["a"], case["b"], case["c"])
        assert first == pytest.approx(case["degrees"], abs=2e-6)
        assert angle_degrees(case["a"], case["b"], case["c"]) == first


def test_unrepresentable_integer_is_rejected() -> None:
    with pytest.raises(ValueError):
        angle_degrees((10**1000, 1), (0, 0), (1, 1))


@pytest.mark.parametrize("a,b,c", [
    ((1e308, 1e308), (-1e308, -1e308), (-1e308, 1e308)),
    ((1e308, 1e-300), (-1e308, 0.0), (1e308, -1e308)),
    ((1e308, 1e308), (math.nextafter(1e308, 0), 1e308), (1e308, 0.0)),
    ((1e-300, 1e-300), (0.0, 0.0), (-1e-300, 1e-300)),
])
def test_high_precision_direction_oracle(a, b, c) -> None:
    # Independent high-precision arithmetic, with no float rescaling algorithm.
    with localcontext() as context:
        context.prec = 700
        u = [Decimal(x) - Decimal(y) for x, y in zip(a, b)]
        v = [Decimal(x) - Decimal(y) for x, y in zip(c, b)]
        dot = sum(x*y for x, y in zip(u, v))
        norms = (sum(x*x for x in u) * sum(x*x for x in v)).sqrt()
        expected = math.degrees(math.acos(max(-1.0, min(1.0, float(dot/norms)))))
    assert angle_degrees(a, b, c) == pytest.approx(expected, abs=2e-6)


def test_present_degenerate_3d_is_unavailable() -> None:
    from contracts.pose import JointObservation, PoseFrame
    from movement.observations import measure_frame

    frame = PoseFrame(frame_index=1, timestamp_s=0.1, joints={
        "left_shoulder": JointObservation(xyz=(0, 0, 0), valid=True, interpolated=False),
        "left_elbow": JointObservation(xyz=(0, 0, 0), valid=True, interpolated=False),
        "left_wrist": JointObservation(xyz=(1, 0, 0), valid=True, interpolated=False),
    })
    observations = measure_frame(frame, side="left", width=464, height=832)
    assert observations[1].value is None
    assert observations[1].reason == "degenerate_geometry"
