"""Analytic tests for the standing dumbbell curl profile module.

All geometry is synthetic and analytic; no reference video or calibration
data is used. Bounds in PROFILE are segmentation trial values only.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from contracts.pose import JointObservation, PoseFrame
from movement import profile_curl
from movement.profile_curl import PROFILE, observe

WIDTH = 100
HEIGHT = 200


def _joint(xy=None, xyz=None, valid=True, interpolated=False, quality_method=None):
    return JointObservation(
        xy=xy,
        xyz=xyz,
        valid=valid,
        interpolated=interpolated,
        quality_method=quality_method,
    )


def _frame(joints, frame_index=0, timestamp_s=0.0):
    return PoseFrame(frame_index=frame_index, timestamp_s=timestamp_s, joints=joints)


def _analytic_frame(side: str) -> PoseFrame:
    """Right-angle elbow (90 deg) and vertical torso, consistently in 2D and 3D.

    Normalized xy: shoulder (0.5, 0.5), elbow (0.5, 0.7), wrist (0.7, 0.7),
    hip (0.5, 0.9). Pixel space: shoulder (50,100), elbow (50,140),
    wrist (70,140), hip (50,180). Elbow interior angle = 90 deg.
    Torso vector shoulder->hip = (0,+80) i.e. straight down in image coords,
    so the torso axis vs image-up (0,-1) is 0 deg in magnitude.

    The 3D coordinates encode the SAME geometry: elbow and hip both lie on
    the same ray below the shoulder (shoulder->elbow (0,1,0), shoulder->hip
    (0,2,0)), so the upper-arm vs torso interior angle at the shoulder is
    0 deg in BOTH projections. The previous fixture placed the 3D elbow at
    (0,-1,0) -- opposite the hip -- yielding 180 deg in 3D while the 2D
    projection yielded 0 deg; that inconsistency was a fixture error and is
    fixed here by making the 3D coordinates agree with the 2D layout.
    """
    joints = {
        f"{side}_shoulder": _joint(xy=(0.5, 0.5), xyz=(0.0, 0.0, 0.0)),
        f"{side}_elbow": _joint(xy=(0.5, 0.7), xyz=(0.0, 1.0, 0.0)),
        f"{side}_wrist": _joint(xy=(0.7, 0.7), xyz=(1.0, 1.0, 0.0)),
        f"{side}_hip": _joint(xy=(0.5, 0.9), xyz=(0.0, 2.0, 0.0)),
    }
    return _frame(joints)


def test_profile_fields():
    assert PROFILE["exercise_id"] == "dumbbell_curl"
    assert PROFILE["variant"] == "standing_both_arms"
    assert PROFILE["version"] == "curl-measure-v2"
    assert PROFILE["signal_metric"] == "elbow_angle"
    assert PROFILE["signal_space"] == "estimated_3d"
    assert PROFILE["low_degrees"] == 80.0
    assert PROFILE["high_degrees"] == 140.0
    assert PROFILE["dwell_s"] == 0.1
    assert PROFILE["max_gap_s"] == 0.1
    assert isinstance(PROFILE["omitted_components"], list)
    assert PROFILE["omitted_components"]


def test_config_json_matches_profile():
    cfg_path = (
        Path(profile_curl.__file__).parent / "configs" / "curl-measure-v2.json"
    )
    cfg = json.loads(cfg_path.read_text())
    assert cfg == PROFILE


def test_observe_analytic_angles_both_sides():
    for side in ("left", "right"):
        obs = observe(_analytic_frame(side), side=side, width=WIDTH, height=HEIGHT)
        assert len(obs) == 5
        assert [(o.metric, o.space) for o in obs] == [
            ("elbow_angle", "projected_2d"),
            ("elbow_angle", "estimated_3d"),
            ("upper_arm_torso_angle", "projected_2d"),
            ("upper_arm_torso_angle", "estimated_3d"),
            ("torso_axis_angle", "projected_2d"),
        ]
        assert all(o.side == side for o in obs)
        assert all(o.reason is None for o in obs)
        assert obs[0].value == pytest.approx(90.0)
        assert obs[1].value == pytest.approx(90.0)
        # Elbow and hip are both directly below the shoulder in BOTH the 2D
        # and 3D coordinates, so the upper-arm vs torso interior angle at
        # the shoulder is 0 deg in both spaces.
        assert obs[2].value == pytest.approx(0.0)
        assert obs[3].value == pytest.approx(0.0)
        assert obs[4].value == pytest.approx(0.0)


def test_observe_missing_joint_reports_reason():
    frame = _analytic_frame("left")
    del frame.joints["left_elbow"]
    obs = observe(frame, side="left", width=WIDTH, height=HEIGHT)
    assert len(obs) == 5
    for o in obs[:4]:
        assert o.value is None
        assert o.reason == "missing_joint"
    # torso axis only needs shoulder and hip, still measurable
    assert obs[4].value == pytest.approx(0.0)
    assert obs[4].reason is None


def test_observe_interpolated_joint_rejected():
    frame = _analytic_frame("right")
    frame.joints["right_wrist"] = _joint(
        xy=(0.7, 0.7),
        xyz=(1.0, 1.0, 0.0),
        interpolated=True,
        quality_method="linear",
    )
    obs = observe(frame, side="right", width=WIDTH, height=HEIGHT)
    assert obs[0].value is None and obs[0].reason == "interpolated_joint"
    assert obs[1].value is None and obs[1].reason == "interpolated_joint"
    # upper arm and torso do not use the wrist
    assert obs[2].reason is None
    assert obs[3].reason is None
    assert obs[4].reason is None


def test_observe_invalid_joint_rejected():
    frame = _analytic_frame("left")
    frame.joints["left_hip"] = _joint(valid=False)
    obs = observe(frame, side="left", width=WIDTH, height=HEIGHT)
    assert obs[0].reason is None
    assert obs[1].reason is None
    assert obs[2].value is None and obs[2].reason == "invalid_joint"
    assert obs[3].value is None and obs[3].reason == "invalid_joint"
    assert obs[4].value is None and obs[4].reason == "invalid_joint"


def test_observe_missing_coordinates():
    frame = _analytic_frame("left")
    frame.joints["left_wrist"] = _joint(xy=(0.7, 0.7), xyz=None)
    obs = observe(frame, side="left", width=WIDTH, height=HEIGHT)
    assert obs[0].reason is None
    assert obs[1].value is None and obs[1].reason == "missing_coordinates"


def test_observe_degenerate_geometry():
    frame = _analytic_frame("left")
    # elbow coincident with shoulder -> degenerate elbow angle
    frame.joints["left_elbow"] = _joint(xy=(0.5, 0.5), xyz=(0.0, 0.0, 0.0))
    obs = observe(frame, side="left", width=WIDTH, height=HEIGHT)
    assert obs[0].value is None and obs[0].reason == "degenerate_geometry"
    assert obs[1].value is None and obs[1].reason == "degenerate_geometry"


def test_observe_validates_side_and_dimensions():
    frame = _analytic_frame("left")
    with pytest.raises(ValueError):
        observe(frame, side="both", width=WIDTH, height=HEIGHT)
    with pytest.raises(ValueError):
        observe(frame, side="left", width=0, height=HEIGHT)
    with pytest.raises(ValueError):
        observe(frame, side="left", width=WIDTH, height=-1)
    with pytest.raises(ValueError):
        observe(frame, side="left", width=True, height=HEIGHT)


def test_observe_empty_frame_all_missing():
    frame = _frame({})
    obs = observe(frame, side="right", width=WIDTH, height=HEIGHT)
    assert len(obs) == 5
    assert all(o.value is None and o.reason == "missing_joint" for o in obs)


def test_frame_metadata_propagates():
    frame = _analytic_frame("left")
    frame = PoseFrame(frame_index=7, timestamp_s=0.25, joints=frame.joints)
    obs = observe(frame, side="left", width=WIDTH, height=HEIGHT)
    assert all(o.frame_index == 7 for o in obs)
    assert all(o.timestamp_s == pytest.approx(0.25) for o in obs)
