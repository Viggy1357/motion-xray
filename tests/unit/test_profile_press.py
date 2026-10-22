"""Analytic tests for the incline dumbbell press profile module.

All geometry is synthetic and analytic; no video, pose inference, or
reference calibration is involved or claimed. The 2D fixture is built in
isotropic pixel coordinates (uniform scale in x and y) and only then
normalized by the frame dimensions, so projected 2D angles exactly match
the 3D angles instead of being distorted by WIDTH/HEIGHT anisotropy.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from contracts.pose import JointObservation, PoseFrame
from movement.profile_press import PROFILE, TORSO_AXIS, observe

WIDTH = 640
HEIGHT = 480


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


def _press_joints(side, elbow_deg, upper_arm_deg):
    """Build analytic joints for one side.

    Shoulder at origin (3D) / pixel (320, 240) (2D). The interior elbow
    angle at the elbow vertex is exactly ``elbow_deg``: the forearm direction
    (elbow->wrist) is rotated by ``180 - elbow_deg`` from the upper-arm
    direction (shoulder->elbow), because the interior angle is measured
    between elbow->shoulder (the reversed upper arm) and elbow->wrist.
    The hip is placed so the interior upper-arm-torso angle at the shoulder
    vertex (between shoulder->elbow and shoulder->hip) is ``upper_arm_deg``.

    2D coordinates are constructed in pixels with a uniform 100px scale
    (isotropic: identical scale on both axes) and normalized by
    (WIDTH, HEIGHT) afterwards, so projected 2D angles are identical to the
    3D angles. The previous fixture scaled normalized x and y by different
    pixel sizes (640 vs 480), which distorted every projected angle.
    """
    shoulder = f"{side}_shoulder"
    elbow = f"{side}_elbow"
    wrist = f"{side}_wrist"
    hip = f"{side}_hip"

    forearm_turn = math.radians(180.0 - elbow_deg)
    torso_turn = math.radians(upper_arm_deg)

    # 3D: shoulder at origin, elbow along +x, wrist rotated so the interior
    # angle at the elbow is elbow_deg.
    s3 = (0.0, 0.0, 0.0)
    e3 = (1.0, 0.0, 0.0)
    w3 = (1.0 + math.cos(forearm_turn), math.sin(forearm_turn), 0.0)
    # Hip: shoulder->hip rotated by upper_arm_deg from shoulder->elbow (+x),
    # so the interior angle at the shoulder is exactly upper_arm_deg.
    h3 = (math.cos(torso_turn), math.sin(torso_turn), 0.0)

    # 2D: identical layout in isotropic pixel units, then normalized.
    scale = 100.0
    sx, sy = 320.0, 240.0

    def norm(px, py):
        return (px / WIDTH, py / HEIGHT)

    s2 = norm(sx, sy)
    e2 = norm(sx + scale, sy)
    w2 = norm(
        sx + scale + scale * math.cos(forearm_turn),
        sy + scale * math.sin(forearm_turn),
    )
    h2 = norm(
        sx + scale * math.cos(torso_turn),
        sy + scale * math.sin(torso_turn),
    )

    return {
        shoulder: _joint(xy=s2, xyz=s3),
        elbow: _joint(xy=e2, xyz=e3),
        wrist: _joint(xy=w2, xyz=w3),
        hip: _joint(xy=h2, xyz=h3),
    }


def test_profile_fields_and_config_match():
    assert PROFILE["exercise_id"] == "incline_chest_press"
    assert PROFILE["variant"] == "incline_dumbbell_bilateral"
    assert PROFILE["version"] == "press-measure-v1"
    assert PROFILE["signal_metric"] == "elbow_angle"
    assert PROFILE["signal_space"] == "estimated_3d"
    assert PROFILE["low_degrees"] == 100
    assert PROFILE["high_degrees"] == 150
    assert PROFILE["dwell_s"] == 0.1
    assert PROFILE["max_gap_s"] == 0.1
    assert set(PROFILE["metrics"]) == {
        "elbow_angle/projected_2d",
        "elbow_angle/estimated_3d",
        "upper_arm_torso_angle/projected_2d",
        "upper_arm_torso_angle/estimated_3d",
        "torso_axis_angle/projected_2d",
    }
    for meta in PROFILE["metrics"].values():
        assert meta["unit"] == "degrees"
        assert isinstance(meta["label"], str) and meta["label"]
    assert "bench_contact" in PROFILE["omitted_components"]
    assert "lumbar_arch" in PROFILE["omitted_components"]

    cfg_path = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "movement"
        / "movement"
        / "configs"
        / "press-measure-v1.json"
    )
    assert json.loads(cfg_path.read_text()) == PROFILE


def test_observe_analytic_angles():
    frame = _frame(_press_joints("left", elbow_deg=120.0, upper_arm_deg=60.0))
    obs = observe(frame, side="left", width=WIDTH, height=HEIGHT)
    assert len(obs) == 5
    assert [(o.metric, o.space) for o in obs] == [
        ("elbow_angle", "estimated_3d"),
        ("elbow_angle", "projected_2d"),
        ("upper_arm_torso_angle", "projected_2d"),
        ("upper_arm_torso_angle", "estimated_3d"),
        ("torso_axis_angle", "projected_2d"),
    ]
    assert obs[0].value == pytest.approx(120.0, abs=1e-6)
    assert obs[0].reason is None
    # Isotropic pixel geometry: projected 2D matches the 3D angle exactly.
    assert obs[1].value == pytest.approx(120.0, abs=1e-6)
    assert obs[2].value == pytest.approx(60.0, abs=1e-6)
    assert obs[3].value == pytest.approx(60.0, abs=1e-6)
    # Torso axis: hip is below-right of shoulder in image coords, so the
    # torso axis is tilted from image up; just require finite.
    assert obs[4].value is not None and math.isfinite(obs[4].value)
    assert all(o.side == "left" for o in obs)


def test_observe_missing_joint_reports_reason():
    joints = _press_joints("right", 120.0, 60.0)
    del joints["right_wrist"]
    obs = observe(_frame(joints), side="right", width=WIDTH, height=HEIGHT)
    assert len(obs) == 5
    assert obs[0].value is None and obs[0].reason == "missing_joint"
    assert obs[1].value is None and obs[1].reason == "missing_joint"
    # Upper-arm/torso and torso axis do not need the wrist.
    assert obs[2].value is not None
    assert obs[3].value is not None
    assert obs[4].value is not None


def test_observe_interpolated_joint_rejected():
    joints = _press_joints("left", 120.0, 60.0)
    prev = joints["left_elbow"]
    joints["left_elbow"] = _joint(
        xy=prev.xy, xyz=prev.xyz, interpolated=True, quality_method="linear"
    )
    obs = observe(_frame(joints), side="left", width=WIDTH, height=HEIGHT)
    assert obs[0].value is None and obs[0].reason == "interpolated_joint"
    assert obs[1].value is None and obs[1].reason == "interpolated_joint"
    assert obs[2].value is None and obs[2].reason == "interpolated_joint"
    assert obs[3].value is None and obs[3].reason == "interpolated_joint"
    assert obs[4].value is not None


def test_observe_invalid_joint_rejected():
    joints = _press_joints("left", 120.0, 60.0)
    prev = joints["left_hip"]
    joints["left_hip"] = _joint(xy=prev.xy, xyz=prev.xyz, valid=False)
    obs = observe(_frame(joints), side="left", width=WIDTH, height=HEIGHT)
    assert obs[0].value is not None
    assert obs[2].value is None and obs[2].reason == "invalid_joint"
    assert obs[3].value is None and obs[3].reason == "invalid_joint"
    assert obs[4].value is None and obs[4].reason == "invalid_joint"


def test_observe_missing_3d_coordinates():
    joints = _press_joints("left", 120.0, 60.0)
    prev = joints["left_wrist"]
    joints["left_wrist"] = _joint(xy=prev.xy, xyz=None)
    obs = observe(_frame(joints), side="left", width=WIDTH, height=HEIGHT)
    assert obs[0].value is None and obs[0].reason == "missing_coordinates"
    assert obs[1].value is not None


def test_observe_validates_dimensions_and_side():
    frame = _frame(_press_joints("left", 120.0, 60.0))
    with pytest.raises(ValueError):
        observe(frame, side="left", width=0, height=HEIGHT)
    with pytest.raises(ValueError):
        observe(frame, side="left", width=WIDTH, height=-1)
    with pytest.raises(ValueError):
        observe(frame, side="left", width=True, height=HEIGHT)
    with pytest.raises(ValueError):
        observe(frame, side="center", width=WIDTH, height=HEIGHT)


def test_torso_axis_constant_unverified():
    assert TORSO_AXIS.axis_id == "image_up_unverified"
    assert TORSO_AXIS.version == "press-measure-v1"
