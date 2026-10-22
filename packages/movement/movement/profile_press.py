"""Incline dumbbell bilateral chest press frame feature module.

Produces five angle observations per frame in a stable order. The signal
metric is the estimated_3d elbow angle: high (extended) at the top of the
press, low at the bottom, high again on completion. The torso axis angle is
camera-plane descriptive only: the bench is inclined, so an upright torso
axis is NOT the goal and no upright band is applied. Bench contact, wrist
rotation, dumbbell path, lumbar arch, and bench inclination cannot be
measured reliably from body keypoints and are omitted.

All segmentation thresholds live in PROFILE / the versioned JSON config;
there are no hidden thresholds here. Config values are segmentation trial
values only, not technique tolerances. No reference-video calibration has
been performed; see docs/measurement/PRESS-reference-packet.json (status:
pending actual measurement).
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

PROFILE: dict = {
    "exercise_id": "incline_chest_press",
    "variant": "incline_dumbbell_bilateral",
    "version": "press-measure-v1",
    "signal_metric": "elbow_angle",
    "signal_space": "estimated_3d",
    "low_degrees": 100,
    "high_degrees": 150,
    "dwell_s": 0.1,
    "max_gap_s": 0.1,
    "metrics": {
        "elbow_angle/projected_2d": {
            "unit": "degrees",
            "label": "Elbow angle (camera plane)",
        },
        "elbow_angle/estimated_3d": {
            "unit": "degrees",
            "label": "Elbow angle (estimated 3D)",
        },
        "upper_arm_torso_angle/projected_2d": {
            "unit": "degrees",
            "label": "Upper arm to torso angle (camera plane)",
        },
        "upper_arm_torso_angle/estimated_3d": {
            "unit": "degrees",
            "label": "Upper arm to torso angle (estimated 3D)",
        },
        "torso_axis_angle/projected_2d": {
            "unit": "degrees",
            "label": "Torso axis angle relative to image up (camera plane, descriptive only; bench inclined)",
        },
    },
    "omitted_components": [
        "bench_contact",
        "wrist_rotation",
        "dumbbell_path",
        "lumbar_arch",
        "bench_inclination",
    ],
}

# Camera-plane axis: image up is (0, -1) in pixel coordinates. This axis is
# unverified against any calibrated reference; torso axis output is
# descriptive only and all camera-angle context is provisional.
TORSO_AXIS = ProjectionAxis(
    version="press-measure-v1",
    axis_id="image_up_unverified",
    up_xy=(0.0, -1.0),
    positive_cross_sign=1,
)


def observe(
    frame: PoseFrame,
    *,
    side: Literal["left", "right"],
    width: int,
    height: int,
) -> list[AngleObservation]:
    """Return five observations for ``side`` in a stable order.

    Order:
        1. elbow_angle / estimated_3d (signal metric)
        2. elbow_angle / projected_2d
        3. upper_arm_torso_angle / projected_2d
        4. upper_arm_torso_angle / estimated_3d
        5. torso_axis_angle / projected_2d (descriptive only)

    Every feature produces exactly one entry even when missing, with a
    deterministic reason from the shared measurement helpers.
    """
    side = _validate_side(side)
    width, height = _validate_dimensions(width, height)

    elbow_2d, elbow_3d, upper_2d, upper_3d = measure_frame(
        frame, side=side, width=width, height=height
    )
    torso = measure_torso_frame(
        frame, side=side, width=width, height=height, axis=TORSO_AXIS
    )
    return [elbow_3d, elbow_2d, upper_2d, upper_3d, torso]
