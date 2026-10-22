"""Standing dumbbell curl (both arms) frame feature module.

Versioned profile ``curl-measure-v1``. This module only measures per-frame
geometry; it does not segment reps, calibrate against reference video, or
judge technique. ``low_degrees``/``high_degrees`` are segmentation trial
bounds only, not technique tolerances. No reference-video calibration has
been performed; all camera-angle context is provisional.
"""

from __future__ import annotations

from typing import Literal

from contracts.pose import PoseFrame
from movement.observations import (
    AngleObservation,
    _validate_dimensions,
    _validate_side,
    measure_frame,
)
from movement.posture import ProjectionAxis, measure_torso_frame

# Image-up axis for projected torso angle. The image vertical direction is
# unverified against any camera calibration; sign convention is provisional.
CURL_TORSO_AXIS_IMAGE_UP_UNVERIFIED = ProjectionAxis(
    version="curl-measure-v1",
    axis_id="image_up_unverified",
    up_xy=(0.0, -1.0),
    positive_cross_sign=1,
)

PROFILE: dict = {
    "exercise_id": "dumbbell_curl",
    "variant": "standing_both_arms",
    "version": "curl-measure-v1",
    "signal_metric": "elbow_angle",
    "signal_space": "estimated_3d",
    "low_degrees": 80.0,
    "high_degrees": 140.0,
    "dwell_s": 0.1,
    "max_gap_s": 0.1,
    "metrics": {
        "elbow_angle": {
            "projected_2d": {
                "unit": "degrees",
                "label": "Elbow flexion angle (projected 2D)",
            },
            "estimated_3d": {
                "unit": "degrees",
                "label": "Elbow flexion angle (estimated 3D)",
            },
        },
        "upper_arm_torso_angle": {
            "projected_2d": {
                "unit": "degrees",
                "label": "Upper arm to torso angle (projected 2D)",
            },
            "estimated_3d": {
                "unit": "degrees",
                "label": "Upper arm to torso angle (estimated 3D)",
            },
        },
        "torso_axis_angle": {
            "projected_2d": {
                "unit": "degrees",
                "label": "Torso axis angle vs image-up (projected 2D, unverified)",
            },
        },
    },
    "omitted_components": [
        "grip_and_wrist_position",
        "dumbbell_load_and_path",
        "scapular_position",
        "lumbar_spine_position",
        "muscle_activation",
        "tempo_and_external_cueing",
    ],
}


def observe(
    frame: PoseFrame,
    *,
    side: Literal["left", "right"],
    width: int,
    height: int,
) -> list[AngleObservation]:
    """Return five angle observations for ``side`` in a fixed order.

    Order:
        1. elbow_angle / projected_2d
        2. elbow_angle / estimated_3d
        3. upper_arm_torso_angle / projected_2d
        4. upper_arm_torso_angle / estimated_3d
        5. torso_axis_angle / projected_2d (image-up axis, unverified)

    Every feature produces exactly one entry, even when the geometry is
    missing; the reason field carries the deterministic cause.
    """
    side = _validate_side(side)
    width, height = _validate_dimensions(width, height)

    elbow_2d, elbow_3d, upper_2d, upper_3d = measure_frame(
        frame, side=side, width=width, height=height
    )
    torso_2d = measure_torso_frame(
        frame,
        side=side,
        width=width,
        height=height,
        axis=CURL_TORSO_AXIS_IMAGE_UP_UNVERIFIED,
    )
    return [elbow_2d, elbow_3d, upper_2d, upper_3d, torso_2d]
