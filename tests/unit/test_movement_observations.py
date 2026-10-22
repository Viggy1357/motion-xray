from __future__ import annotations

import math
from typing import Any

import pytest

from contracts.pose import JointObservation, PoseFrame
from movement.observations import angle_degrees, measure_frame


# ---------------------------------------------------------------------------
# Helpers for building PoseFrames without coupling to implementation details
# ---------------------------------------------------------------------------

def joint(
    xy: tuple[float, float] | None = None,
    xyz: tuple[float, float, float] | None = None,
    valid: bool = True,
    interpolated: bool = False,
    quality_method: str | None = None,
    native_quality: float | None = None,
) -> JointObservation:
    return JointObservation(
        xy=xy,
        xyz=xyz,
        valid=valid,
        interpolated=interpolated,
        quality_method=quality_method,
        native_quality=native_quality,
    )


def frame(
    frame_index: int = 7,
    timestamp_s: float = 1.25,
    **joints: JointObservation,
) -> PoseFrame:
    return PoseFrame(
        frame_index=frame_index,
        timestamp_s=timestamp_s,
        joints=joints,
    )


# ---------------------------------------------------------------------------
# angle_degrees
# ---------------------------------------------------------------------------


def test_angle_degrees_right_angle() -> None:
    assert angle_degrees((1.0, 0.0), (0.0, 0.0), (0.0, 1.0)) == pytest.approx(90.0)


def test_angle_degrees_straight_line() -> None:
    assert angle_degrees((1.0, 0.0), (0.0, 0.0), (-1.0, 0.0)) == pytest.approx(180.0)


def test_angle_degrees_acute_angle() -> None:
    # 60 degree angle via unit vectors
    assert angle_degrees((1.0, 0.0), (0.0, 0.0), (0.5, math.sqrt(3) / 2)) == pytest.approx(
        60.0, abs=1e-9
    )


def test_angle_degrees_3d() -> None:
    assert angle_degrees((1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 1.0, 0.0)) == pytest.approx(90.0)


def test_angle_degrees_translation_invariant() -> None:
    base = angle_degrees((1.0, 0.0), (0.0, 0.0), (0.0, 1.0))
    translated = angle_degrees((11.0, 10.0), (10.0, 10.0), (10.0, 11.0))
    assert base == pytest.approx(translated)


def test_angle_degrees_scale_invariant() -> None:
    base = angle_degrees((1.0, 0.0), (0.0, 0.0), (0.0, 1.0))
    huge = angle_degrees((1e150, 0.0), (0.0, 0.0), (0.0, 1e150))
    tiny = angle_degrees((1e-150, 0.0), (0.0, 0.0), (0.0, 1e-150))
    assert base == pytest.approx(huge)
    assert base == pytest.approx(tiny)


def test_angle_degrees_huge_numbers_no_overflow() -> None:
    # If implementation naively divides by magnitude, 1e200 can overflow when squared.
    result = angle_degrees((1e200, 0.0), (0.0, 0.0), (0.0, 1e200))
    assert result == pytest.approx(90.0)


def test_angle_degrees_degenerate_zero_vector_raises() -> None:
    with pytest.raises(ValueError):
        angle_degrees((0.0, 0.0), (0.0, 0.0), (1.0, 0.0))
    with pytest.raises(ValueError):
        angle_degrees((1.0, 0.0), (0.0, 0.0), (0.0, 0.0))
    with pytest.raises(ValueError):
        angle_degrees((1.0, 0.0), (1.0, 0.0), (2.0, 0.0))


def test_angle_degrees_rejects_non_numeric() -> None:
    with pytest.raises((TypeError, ValueError)):
        angle_degrees(("a", "b"), (0, 0), (1, 0))  # type: ignore[arg-type]


def test_angle_degrees_rejects_bool() -> None:
    with pytest.raises((TypeError, ValueError)):
        angle_degrees((True, False), (0, 0), (1, 0))  # type: ignore[arg-type]


def test_angle_degrees_rejects_mismatched_dimension() -> None:
    with pytest.raises((TypeError, ValueError)):
        angle_degrees((1.0, 0.0), (0.0, 0.0, 0.0), (0.0, 1.0))  # type: ignore[arg-type]


def test_angle_degrees_vector_norm_overflow() -> None:
    # 1e308 is near float max; squaring would overflow.
    result = angle_degrees((1e308, 0.0), (0.0, 0.0), (0.0, 1e308))
    assert result == pytest.approx(90.0)


def test_angle_degrees_opposite_endpoint_subtraction_overflow() -> None:
    # Points on opposite sides of the origin at huge magnitude.
    result = angle_degrees((1e308, 0.0), (0.0, 0.0), (-1e308, 0.0))
    assert result == pytest.approx(180.0)


def test_angle_degrees_tiny_numbers() -> None:
    result = angle_degrees((1e-300, 0.0), (0.0, 0.0), (0.0, 1e-300))
    assert result == pytest.approx(90.0)


# ---------------------------------------------------------------------------
# measure_frame: happy path geometry
# ---------------------------------------------------------------------------


def _left_frame() -> PoseFrame:
    # Simple left side skeleton in normalized coordinates.
    # shoulder at (0.25,0.25), elbow (0.25,0.5), wrist (0.45,0.5)
    # hip at (0.25,0.75)
    return frame(
        left_shoulder=joint(xy=(0.25, 0.25)),
        left_elbow=joint(xy=(0.25, 0.5)),
        left_wrist=joint(xy=(0.45, 0.5)),
        left_hip=joint(xy=(0.25, 0.75)),
    )


def test_measure_frame_returns_four_observations_fixed_order() -> None:
    f = _left_frame()
    obs = measure_frame(f, side="left", width=100, height=100)
    assert len(obs) == 4
    expected_keys = [
        ("elbow_angle", "projected_2d"),
        ("elbow_angle", "estimated_3d"),
        ("upper_arm_torso_angle", "projected_2d"),
        ("upper_arm_torso_angle", "estimated_3d"),
    ]
    for o, (metric, space) in zip(obs, expected_keys):
        assert o.metric == metric
        assert o.space == space


def test_measure_frame_preserves_frame_index_and_timestamp() -> None:
    f = frame(frame_index=42, timestamp_s=3.5)
    obs = measure_frame(f, side="left", width=100, height=100)
    for o in obs:
        assert o.frame_index == 42
        assert o.timestamp_s == pytest.approx(3.5)


def test_measure_frame_2d_scaling_rectangular_image() -> None:
    # Use a right angle at the elbow in normalized space.
    # shoulder (0.2,0.2), elbow (0.2,0.4), wrist (0.4,0.4)
    # In a 640x480 image the x step is 0.2*640=128, y step is 0.2*480=96.
    # The angle remains 90 degrees after independent axis scaling.
    f = frame(
        left_shoulder=joint(xy=(0.2, 0.2)),
        left_elbow=joint(xy=(0.2, 0.4)),
        left_wrist=joint(xy=(0.4, 0.4)),
        left_hip=joint(xy=(0.2, 0.6)),
    )
    obs = measure_frame(f, side="left", width=640, height=480)
    elbow_2d = obs[0]
    assert elbow_2d.value == pytest.approx(90.0, abs=1e-9)


def test_measure_frame_2d_not_square_aspect_changes_angle() -> None:
    # Non-square aspect: a-b points left after scaling, so the angle is the
    # supplement of the naive atan2 result.
    # shoulder (0,0), elbow (0.1,0), wrist (0.2,0.1)
    # normalized vectors: (0.1,0) and (0.1,0.1) -> angle = atan2(0.1,0.1)=45 deg
    # scaled 100x200: (10,0) and (10,20) -> angle = 180 - atan2(20,10) ~ 116.565 deg
    f = frame(
        left_shoulder=joint(xy=(0.0, 0.0)),
        left_elbow=joint(xy=(0.1, 0.0)),
        left_wrist=joint(xy=(0.2, 0.1)),
        left_hip=joint(xy=(0.0, 0.2)),
    )
    obs = measure_frame(f, side="left", width=100, height=200)
    expected = 180.0 - math.degrees(math.atan2(20.0, 10.0))
    assert obs[0].value == pytest.approx(expected, abs=1e-9)


def test_measure_frame_3d_known_geometry() -> None:
    # 3D right angle elbow, straight upper-arm/torso.
    f = frame(
        left_shoulder=joint(xyz=(0.0, 0.0, 0.0)),
        left_elbow=joint(xyz=(1.0, 0.0, 0.0)),
        left_wrist=joint(xyz=(1.0, 1.0, 0.0)),
        left_hip=joint(xyz=(-1.0, 0.0, 0.0)),
    )
    obs = measure_frame(f, side="left", width=100, height=100)
    assert obs[1].value == pytest.approx(90.0, abs=1e-9)  # elbow 3D
    assert obs[3].value == pytest.approx(180.0, abs=1e-9)  # upper_arm_torso 3D


# ---------------------------------------------------------------------------
# measure_frame: side handling
# ---------------------------------------------------------------------------


def test_measure_frame_right_side() -> None:
    f = frame(
        right_shoulder=joint(xy=(0.5, 0.25)),
        right_elbow=joint(xy=(0.5, 0.5)),
        right_wrist=joint(xy=(0.7, 0.5)),
        right_hip=joint(xy=(0.5, 0.75)),
    )
    obs = measure_frame(f, side="right", width=100, height=100)
    assert obs[0].metric == "elbow_angle"
    assert obs[0].value == pytest.approx(90.0, abs=1e-9)


def test_measure_frame_invalid_side_raises() -> None:
    f = _left_frame()
    with pytest.raises(ValueError):
        measure_frame(f, side="center", width=100, height=100)  # type: ignore[arg-type]


def test_measure_frame_opposite_side_missing_joints() -> None:
    # Only left joints present; asking for right should yield missing_joint.
    f = _left_frame()
    obs = measure_frame(f, side="right", width=100, height=100)
    for o in obs:
        assert o.value is None
        assert o.reason == "missing_joint"


# ---------------------------------------------------------------------------
# measure_frame: dimension validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "width,height",
    [
        (0, 100),
        (100, 0),
        (-1, 100),
        (100, -1),
        (100.5, 100),
        (100, True),
        (True, 100),
    ],
)
def test_measure_frame_rejects_bad_dimensions(width: Any, height: Any) -> None:
    f = _left_frame()
    with pytest.raises(ValueError):
        measure_frame(f, side="left", width=width, height=height)


# ---------------------------------------------------------------------------
# measure_frame: per-metric/space gating and reason precedence
# ---------------------------------------------------------------------------


def test_measure_frame_missing_joint_precedence() -> None:
    # No wrist at all -> elbow metrics missing_joint; upper-arm/torso unaffected.
    f = frame(
        left_shoulder=joint(xy=(0.25, 0.25)),
        left_elbow=joint(xy=(0.25, 0.5)),
        left_hip=joint(xy=(0.25, 0.75)),
    )
    obs = measure_frame(f, side="left", width=100, height=100)
    assert obs[0].reason == "missing_joint"
    assert obs[1].reason == "missing_joint"
    assert obs[2].value == pytest.approx(0.0, abs=1e-9)
    assert obs[3].reason == "missing_coordinates"


def test_measure_frame_invalid_joint_precedence() -> None:
    # Wrist invalid but present -> elbow invalid_joint before missing_coordinates.
    f = frame(
        left_shoulder=joint(xy=(0.25, 0.25)),
        left_elbow=joint(xy=(0.25, 0.5)),
        left_wrist=joint(xy=(0.45, 0.5), valid=False),
        left_hip=joint(xy=(0.25, 0.75)),
    )
    obs = measure_frame(f, side="left", width=100, height=100)
    assert obs[0].reason == "invalid_joint"
    assert obs[1].reason == "invalid_joint"


def test_measure_frame_interpolated_joint_refused() -> None:
    # Interpolated wrist must be refused for both 2D and 3D elbow metrics.
    f = frame(
        left_shoulder=joint(xy=(0.25, 0.25)),
        left_elbow=joint(xy=(0.25, 0.5)),
        left_wrist=joint(
            xy=(0.45, 0.5),
            interpolated=True,
            quality_method="linear",
        ),
        left_hip=joint(xy=(0.25, 0.75)),
    )
    obs = measure_frame(f, side="left", width=100, height=100)
    assert obs[0].reason == "interpolated_joint"
    assert obs[1].reason == "interpolated_joint"


def test_measure_frame_missing_coordinates_precedence() -> None:
    # 2D wrist coordinate is None (not missing entirely) -> missing_coordinates.
    f = frame(
        left_shoulder=joint(xy=(0.25, 0.25)),
        left_elbow=joint(xy=(0.25, 0.5)),
        left_wrist=joint(xy=None, xyz=(1.0, 1.0, 1.0)),
        left_hip=joint(xy=(0.25, 0.75)),
    )
    obs = measure_frame(f, side="left", width=100, height=100)
    assert obs[0].reason == "missing_coordinates"
    # Wrist has xyz; shoulder/elbow do not, so 3D remains unavailable.
    assert obs[1].reason == "missing_coordinates"


def test_measure_frame_degenerate_geometry() -> None:
    # Shoulder, elbow, wrist collinear with zero-length segment at elbow.
    f = frame(
        left_shoulder=joint(xy=(0.25, 0.25)),
        left_elbow=joint(xy=(0.25, 0.25)),
        left_wrist=joint(xy=(0.45, 0.5)),
        left_hip=joint(xy=(0.25, 0.75)),
    )
    obs = measure_frame(f, side="left", width=100, height=100)
    assert obs[0].reason == "degenerate_geometry"
    assert obs[1].reason == "missing_coordinates"


def test_measure_frame_reason_precedence_order() -> None:
    # Make shoulder invalid, elbow interpolated, wrist missing coordinates,
    # hip degenerate-ish. The precedence is checked independently per metric/space.
    # For elbow metric: shoulder invalid -> invalid_joint wins over elbow interpolated.
    f = frame(
        left_shoulder=joint(xy=(0.25, 0.25), valid=False),
        left_elbow=joint(xy=(0.25, 0.5), interpolated=True, quality_method="linear"),
        left_wrist=joint(xy=None, xyz=(1.0, 1.0, 1.0)),
        left_hip=joint(xy=(0.25, 0.75)),
    )
    obs = measure_frame(f, side="left", width=100, height=100)
    # Elbow metric requires shoulder, elbow, wrist. First failing in precedence:
    # shoulder is invalid -> invalid_joint.
    assert obs[0].reason == "invalid_joint"
    assert obs[1].reason == "invalid_joint"
    # Invalid shoulder takes priority even when interpolated elbow occurs first.
    assert obs[2].reason == "invalid_joint"
    assert obs[3].reason == "invalid_joint"


# ---------------------------------------------------------------------------
# measure_frame: per-metric separation (wrist occlusion should not affect torso)
# ---------------------------------------------------------------------------


def test_measure_frame_wrist_occlusion_does_not_affect_upper_arm_torso() -> None:
    f = frame(
        left_shoulder=joint(xy=(0.25, 0.25)),
        left_elbow=joint(xy=(0.25, 0.5)),
        left_wrist=joint(xy=None, xyz=(1.0, 1.0, 1.0)),  # occluded in 2D only
        left_hip=joint(xy=(0.25, 0.75)),
    )
    obs = measure_frame(f, side="left", width=100, height=100)
    assert obs[0].value is None
    assert obs[2].value == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# measure_frame: 2D vs 3D availability separation
# ---------------------------------------------------------------------------


def test_measure_frame_2d_available_3d_missing() -> None:
    f = frame(
        left_shoulder=joint(xy=(0.25, 0.25)),
        left_elbow=joint(xy=(0.25, 0.5)),
        left_wrist=joint(xy=(0.45, 0.5)),
        left_hip=joint(xy=(0.25, 0.75)),
    )
    obs = measure_frame(f, side="left", width=100, height=100)
    assert obs[0].value == pytest.approx(90.0, abs=1e-9)
    assert obs[1].reason == "missing_coordinates"


def test_measure_frame_3d_available_2d_missing() -> None:
    f = frame(
        left_shoulder=joint(xyz=(0.0, 0.0, 0.0)),
        left_elbow=joint(xyz=(1.0, 0.0, 0.0)),
        left_wrist=joint(xyz=(1.0, 1.0, 0.0)),
        left_hip=joint(xyz=(0.0, 0.0, 0.0)),
    )
    obs = measure_frame(f, side="left", width=100, height=100)
    assert obs[0].reason == "missing_coordinates"
    assert obs[1].value == pytest.approx(90.0, abs=1e-9)


# ---------------------------------------------------------------------------
# measure_frame: gaps preserved via timestamps, no smoothing/segmentation
# ---------------------------------------------------------------------------


def test_measure_frame_no_smoothing_across_frames() -> None:
    f1 = frame(frame_index=0, timestamp_s=0.0)
    f2 = frame(frame_index=1, timestamp_s=1.0)
    obs1 = measure_frame(f1, side="left", width=100, height=100)
    obs2 = measure_frame(f2, side="left", width=100, height=100)
    for o1, o2 in zip(obs1, obs2):
        assert o1.timestamp_s == 0.0
        assert o2.timestamp_s == 1.0


# ---------------------------------------------------------------------------
# measure_frame: determinism
# ---------------------------------------------------------------------------


def test_measure_frame_is_deterministic() -> None:
    f = _left_frame()
    obs_a = measure_frame(f, side="left", width=100, height=100)
    obs_b = measure_frame(f, side="left", width=100, height=100)
    assert obs_a == obs_b


# ---------------------------------------------------------------------------
# measure_frame: no confidence-derived or fabricated claims
# ---------------------------------------------------------------------------


def test_measure_frame_does_not_use_native_quality() -> None:
    f = frame(
        left_shoulder=joint(xy=(0.25, 0.25), native_quality=0.1),
        left_elbow=joint(xy=(0.25, 0.5), native_quality=0.1),
        left_wrist=joint(xy=(0.45, 0.5), native_quality=0.1),
        left_hip=joint(xy=(0.25, 0.75), native_quality=0.1),
    )
    obs = measure_frame(f, side="left", width=100, height=100)
    assert obs[0].value == pytest.approx(90.0, abs=1e-9)
