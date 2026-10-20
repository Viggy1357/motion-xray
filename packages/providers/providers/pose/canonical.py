"""Canonical observed MP33 joints; estimated depth and visibility remain qualified."""

from __future__ import annotations

from typing import Any, Optional, Sequence
import math

from contracts.pose import JointObservation, PoseFrame


JOINT_INDICES: dict[str, int] = {
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
    "left_heel": 29,
    "right_heel": 30,
    "left_foot_index": 31,
    "right_foot_index": 32,
}


def _is_valid_numeric(value: Any) -> bool:
    """Check if value is a non-boolean int/float and finite."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    if isinstance(value, float):
        return math.isfinite(value)
    return True


def map_pose_frame(
    image_landmarks: Sequence[Any],
    world_landmarks: Sequence[Any],
    *,
    frame_index: int,
    timestamp_s: float,
    subject_track_id: Optional[str] = None,
    visibility_threshold: float = 0.6,
) -> PoseFrame:
    # Validate threshold
    if not _is_valid_numeric(visibility_threshold) or not (0 <= visibility_threshold <= 1):
        raise ValueError("visibility_threshold must be a float in [0,1]")
    if len(image_landmarks) not in (0, 33) or len(world_landmarks) not in (0, 33):
        raise ValueError("Landmark sequences must be length 0 or 33")

    joints = {}
    for name, idx in JOINT_INDICES.items():
        image = image_landmarks[idx] if image_landmarks else None
        world = world_landmarks[idx] if world_landmarks else None

        xy = None
        xyz = None
        native_quality = None
        valid = False

        if image:
            try:
                x, y = image.x, image.y
                if _is_valid_numeric(x) and _is_valid_numeric(y):
                    xy = (float(x), float(y))
                vis, pres = image.visibility, image.presence
                if _is_valid_numeric(vis) and _is_valid_numeric(pres) and 0 <= vis <= 1 and 0 <= pres <= 1:
                    native_quality = min(float(vis), float(pres))
            except (ValueError, TypeError, AttributeError):
                pass

        if world and xy is not None:
            try:
                x, y, z = world.x, world.y, world.z
                if all(_is_valid_numeric(v) for v in (x, y, z)):
                    xyz = (float(x), -float(y), -float(z))
            except (ValueError, TypeError, AttributeError):
                pass

        if xy is not None and xyz is not None and native_quality is not None and native_quality >= visibility_threshold:
            valid = True

        joints[name] = JointObservation(
            xy=xy,
            xyz=xyz,
            native_quality=native_quality,
            valid=valid,
            interpolated=False,
            quality_method="mp33-camera-v1;visibility_presence_proxy_not_3d_confidence"
        )

    # Derived joints
    for name, left_name, right_name in [
        ("pelvis", "left_hip", "right_hip"),
        ("shoulder_midpoint", "left_shoulder", "right_shoulder")
    ]:
        left, right = joints[left_name], joints[right_name]
        if left.valid and right.valid and left.xy and right.xy and left.xyz and right.xyz:
            xy = ((left.xy[0] + right.xy[0]) / 2, (left.xy[1] + right.xy[1]) / 2)
            xyz = (
                (left.xyz[0] + right.xyz[0]) / 2,
                (left.xyz[1] + right.xyz[1]) / 2,
                (left.xyz[2] + right.xyz[2]) / 2,
            )
            native_quality = min(left.native_quality or 0, right.native_quality or 0)
            method = "mp33-camera-v1;visibility_presence_proxy_not_3d_confidence;derived_paired_midpoint"
            joints[name] = JointObservation(
                xy=xy,
                xyz=xyz,
                native_quality=native_quality,
                valid=True,
                interpolated=False,
                quality_method=method
            )
        else:
            joints[name] = JointObservation(
                xy=None,
                xyz=None,
                native_quality=None,
                valid=False,
                interpolated=False,
                quality_method="mp33-camera-v1;derived_paired_midpoint_unavailable",
            )

    return PoseFrame(
        frame_index=frame_index,
        timestamp_s=timestamp_s,
        subject_track_id=subject_track_id,
        joints=joints
    )
