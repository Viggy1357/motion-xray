"""Bodyweight squat single-frame feature module (squat-measure-v1).

Computes knee and hip joint angles plus a projected torso axis angle from one
PoseFrame. Every feature emits exactly one AngleObservation per call, even
when the geometry cannot be measured (``value=None`` with a deterministic
``reason``). No smoothing, segmentation, depth, or technique judgments are
made here; PROFILE band values are segmentation trial bounds only, not
technique tolerances or calibrated norms.
"""

from __future__ import annotations

from typing import Literal

from contracts.pose import PoseFrame
from movement.observations import (
    AngleObservation,
    _measure_angle,
    _validate_dimensions,
    _validate_side,
)
from movement.posture import ProjectionAxis, measure_torso_frame

# Image-space up axis. Camera orientation is provisional and unverified for
# this variant; no calibration claim is made.
SQUAT_TORSO_AXIS = ProjectionAxis(
    version="squat-measure-v1",
    axis_id="image_up_unverified",
    up_xy=(0.0, -1.0),
    positive_cross_sign=1,
)

PROFILE: dict = {
    "exercise_id": "squat",
    "variant": "bodyweight",
    "version": "squat-measure-v1",
    "signal_metric": "knee_angle",
    "signal_space": "estimated_3d",
    "low_degrees": 100.0,
    "high_degrees": 150.0,
    "dwell_s": 0.1,
    "max_gap_s": 0.1,
    "metrics": {
        "knee_angle": {
            "projected_2d": {"unit": "degrees", "label": "Knee angle (hip-knee-ankle), projected 2D"},
            "estimated_3d": {"unit": "degrees", "label": "Knee angle (hip-knee-ankle), estimated 3D"},
        },
        "hip_angle": {
            "projected_2d": {"unit": "degrees", "label": "Hip angle (shoulder-hip-knee), projected 2D"},
            "estimated_3d": {"unit": "degrees", "label": "Hip angle (shoulder-hip-knee), estimated 3D"},
        },
        "torso_axis_angle": {
            "projected_2d": {"unit": "degrees", "label": "Torso axis angle from image up, projected 2D"},
        },
    },
    "omitted_components": [
        "squat_depth_or_floor_parallel",
        "bar_position_or_contact",
        "lumbar_spine_flexion",
        "scapular_position",
        "muscle_activation",
        "foot_pressure_and_ankle_strategy",
    ],
}


def observe(
    frame: PoseFrame,
    *,
    side: Literal["left", "right"],
    width: int,
    height: int,
) -> list[AngleObservation]:
    """Return five observations for ``side`` in a fixed order.

    Order:
        1. knee_angle / projected_2d
        2. knee_angle / estimated_3d
        3. hip_angle / projected_2d
        4. hip_angle / estimated_3d
        5. torso_axis_angle / projected_2d
    """
    side = _validate_side(side)
    width, height = _validate_dimensions(width, height)

    shoulder = f"{side}_shoulder"
    hip = f"{side}_hip"
    knee = f"{side}_knee"
    ankle = f"{side}_ankle"

    knee_2d = _measure_angle(
        frame, side, "knee_angle", "projected_2d", [hip, knee, ankle], width, height
    )
    knee_3d = _measure_angle(
        frame, side, "knee_angle", "estimated_3d", [hip, knee, ankle], width, height
    )
    hip_2d = _measure_angle(
        frame, side, "hip_angle", "projected_2d", [shoulder, hip, knee], width, height
    )
    hip_3d = _measure_angle(
        frame, side, "hip_angle", "estimated_3d", [shoulder, hip, knee], width, height
    )
    torso_2d = measure_torso_frame(
        frame, side=side, width=width, height=height, axis=SQUAT_TORSO_AXIS
    )

    return [knee_2d, knee_3d, hip_2d, hip_3d, torso_2d]
