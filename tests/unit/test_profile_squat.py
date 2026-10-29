"""Analytic tests for the bodyweight squat profile module.

The module PROFILE is squat-measure-v2 (adds the opt-in ``missing_gap_s``
policy). The historical squat-measure-v1 JSON config is preserved unchanged
on disk and pinned here as an immutable comparison of the unchanged
geometry/threshold fields; no v1 coverage was deleted.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from contracts.pose import JointObservation, PoseFrame
from movement.profile_squat import PROFILE, observe

WIDTH = 100
HEIGHT = 100

CONFIG_DIR = (
    Path(__file__).resolve().parents[2]
    / "packages"
    / "movement"
    / "movement"
    / "configs"
)


def _joint(xy=None, xyz=None, valid=True, interpolated=False):
    return JointObservation(
        xy=xy,
        xyz=xyz,
        valid=valid,
        interpolated=interpolated,
        quality_method="linear" if interpolated else None,
    )


def _frame(joints, index=0, ts=0.0):
    return PoseFrame(frame_index=index, timestamp_s=ts, joints=joints)


def _standing_joints(side):
    """Straight vertical line: hip (0.5,0.5), knee (0.5,0.7), ankle (0.5,0.9),
    shoulder (0.5,0.3). All angles 180 degrees; torso aligned with image up."""
    p = side
    return {
        f"{p}_shoulder": _joint(xy=(0.5, 0.3), xyz=(0.0, 0.4, 0.0)),
        f"{p}_hip": _joint(xy=(0.5, 0.5), xyz=(0.0, 0.0, 0.0)),
        f"{p}_knee": _joint(xy=(0.5, 0.7), xyz=(0.0, -0.4, 0.0)),
        f"{p}_ankle": _joint(xy=(0.5, 0.9), xyz=(0.0, -0.8, 0.0)),
    }


def _right_angle_joints(side):
    """L-shaped pose with both knee and hip interior angles of 90 degrees.

    Knee: hip directly above knee, ankle directly right of knee, so the
    interior angle at the knee is 90 deg.
    Hip: the hip angle is measured at the hip vertex between hip->shoulder
    and hip->knee. hip->knee points straight down, so the shoulder is
    placed directly left of the hip (hip->shoulder horizontal) to make the
    interior angle exactly 90 deg. A shoulder directly above the hip (the
    previous fixture) is collinear with hip->knee and yields 180 deg, not
    90 deg; that was a fixture geometry error.
    Because the shoulder is lateral to the hip, the torso axis is tilted
    from image up and is only required to be finite.
    """
    p = side
    return {
        f"{p}_shoulder": _joint(xy=(0.3, 0.5), xyz=(-0.4, 0.4, 0.0)),
        f"{p}_hip": _joint(xy=(0.5, 0.5), xyz=(0.0, 0.4, 0.0)),
        f"{p}_knee": _joint(xy=(0.5, 0.7), xyz=(0.0, 0.0, 0.0)),
        f"{p}_ankle": _joint(xy=(0.7, 0.7), xyz=(0.4, 0.0, 0.0)),
    }


def test_profile_config_matches_json():
    cfg = json.loads((CONFIG_DIR / "squat-measure-v2.json").read_text())
    assert cfg == PROFILE


def test_historical_v1_config_preserved_immutable():
    # The v1 JSON is retained unchanged as historical record: same geometry
    # and segmentation thresholds, and it never gained the v2 gap policy.
    v1 = json.loads((CONFIG_DIR / "squat-measure-v1.json").read_text())
    assert v1["version"] == "squat-measure-v1"
    assert "missing_gap_s" not in v1
    for key in (
        "exercise_id",
        "variant",
        "signal_metric",
        "signal_space",
        "low_degrees",
        "high_degrees",
        "dwell_s",
        "max_gap_s",
        "metrics",
        "omitted_components",
    ):
        assert v1[key] == PROFILE[key]


def test_profile_constants():
    assert PROFILE["exercise_id"] == "squat"
    assert PROFILE["variant"] == "bodyweight"
    assert PROFILE["version"] == "squat-measure-v2"
    assert PROFILE["signal_metric"] == "knee_angle"
    assert PROFILE["signal_space"] == "estimated_3d"
    assert PROFILE["low_degrees"] == 100.0
    assert PROFILE["high_degrees"] == 150.0
    assert PROFILE["dwell_s"] == 0.1
    assert PROFILE["max_gap_s"] == 0.1
    assert PROFILE["missing_gap_s"] == 0.1


def test_straight_line_angles_180():
    obs = observe(_frame(_standing_joints("left")), side="left", width=WIDTH, height=HEIGHT)
    assert len(obs) == 5
    assert [o.metric for o in obs] == [
        "knee_angle", "knee_angle", "hip_angle", "hip_angle", "torso_axis_angle",
    ]
    assert [o.space for o in obs] == [
        "projected_2d", "estimated_3d", "projected_2d", "estimated_3d", "projected_2d",
    ]
    for o in obs[:4]:
        assert o.reason is None
        assert o.value == pytest.approx(180.0)
    assert obs[4].reason is None
    assert obs[4].value == pytest.approx(0.0)


def test_right_angle_geometry():
    obs = observe(_frame(_right_angle_joints("right")), side="right", width=WIDTH, height=HEIGHT)
    assert obs[0].value == pytest.approx(90.0)
    assert obs[1].value == pytest.approx(90.0)
    assert obs[2].value == pytest.approx(90.0)
    assert obs[3].value == pytest.approx(90.0)
    # Torso is horizontal in this fixture, so the axis angle is not 0;
    # require a finite measurement instead.
    assert obs[4].reason is None
    assert obs[4].value is not None and math.isfinite(obs[4].value)


def test_missing_joint_reports_reason_all_features():
    joints = _standing_joints("left")
    del joints["left_knee"]
    obs = observe(_frame(joints), side="left", width=WIDTH, height=HEIGHT)
    assert len(obs) == 5
    for o in obs[:4]:
        assert o.value is None
        assert o.reason == "missing_joint"
    # torso only needs shoulder+hip, still measurable
    assert obs[5 - 1].value == pytest.approx(0.0)


def test_invalid_joint_rejected():
    joints = _standing_joints("left")
    joints["left_hip"] = _joint(xy=(0.5, 0.5), xyz=(0.0, 0.0, 0.0), valid=False)
    obs = observe(_frame(joints), side="left", width=WIDTH, height=HEIGHT)
    for o in obs:
        assert o.value is None
        assert o.reason == "invalid_joint"


def test_interpolated_joint_rejected():
    joints = _standing_joints("left")
    joints["left_ankle"] = _joint(xy=(0.5, 0.9), xyz=(0.0, -0.8, 0.0), interpolated=True)
    obs = observe(_frame(joints), side="left", width=WIDTH, height=HEIGHT)
    assert obs[0].value is None and obs[0].reason == "interpolated_joint"
    assert obs[1].value is None and obs[1].reason == "interpolated_joint"
    # hip/torso features do not use the ankle
    assert obs[2].value == pytest.approx(180.0)
    assert obs[3].value == pytest.approx(180.0)
    assert obs[4].value == pytest.approx(0.0)


def test_missing_3d_coordinates_only_3d_features_none():
    joints = _standing_joints("left")
    joints["left_knee"] = _joint(xy=(0.5, 0.7))
    obs = observe(_frame(joints), side="left", width=WIDTH, height=HEIGHT)
    assert obs[0].value == pytest.approx(180.0)
    assert obs[1].value is None and obs[1].reason == "missing_coordinates"
    assert obs[2].value == pytest.approx(180.0)
    assert obs[3].value is None and obs[3].reason == "missing_coordinates"
    assert obs[4].value == pytest.approx(0.0)


def test_degenerate_geometry():
    joints = _standing_joints("left")
    joints["left_knee"] = _joint(xy=(0.5, 0.5), xyz=(0.0, 0.0, 0.0))
    obs = observe(_frame(joints), side="left", width=WIDTH, height=HEIGHT)
    assert obs[0].value is None and obs[0].reason == "degenerate_geometry"
    assert obs[1].value is None and obs[1].reason == "degenerate_geometry"


def test_no_arm_joints_required():
    # Squat features must never substitute elbow/arm geometry.
    joints = _standing_joints("left")
    assert not any("elbow" in j or "wrist" in j for j in joints)
    obs = observe(_frame(joints), side="left", width=WIDTH, height=HEIGHT)
    assert all(o.reason is None for o in obs)


def test_frame_metadata_propagated():
    obs = observe(
        _frame(_standing_joints("left"), index=7, ts=1.25),
        side="left", width=WIDTH, height=HEIGHT,
    )
    for o in obs:
        assert o.frame_index == 7
        assert o.timestamp_s == pytest.approx(1.25)
        assert o.side == "left"


def test_invalid_side_and_dimensions_rejected():
    frame = _frame(_standing_joints("left"))
    with pytest.raises(ValueError):
        observe(frame, side="both", width=WIDTH, height=HEIGHT)
    with pytest.raises(ValueError):
        observe(frame, side="left", width=0, height=HEIGHT)
    with pytest.raises(ValueError):
        observe(frame, side="left", width=WIDTH, height=-1)
    with pytest.raises(ValueError):
        observe(frame, side="left", width=True, height=HEIGHT)


def test_observed_zero_angle():
    # Folded leg: ankle coincident direction with hip from knee -> 0 degrees.
    p = "left"
    joints = {
        f"{p}_shoulder": _joint(xy=(0.5, 0.3), xyz=(0.0, 0.4, 0.0)),
        f"{p}_hip": _joint(xy=(0.5, 0.5), xyz=(0.0, 0.0, 0.0)),
        f"{p}_knee": _joint(xy=(0.5, 0.7), xyz=(0.0, -0.4, 0.0)),
        f"{p}_ankle": _joint(xy=(0.5, 0.55), xyz=(0.0, -0.1, 0.0)),
    }
    obs = observe(_frame(joints), side="left", width=WIDTH, height=HEIGHT)
    assert obs[0].reason is None
    assert obs[0].value == pytest.approx(0.0)
    assert math.isfinite(obs[0].value)
