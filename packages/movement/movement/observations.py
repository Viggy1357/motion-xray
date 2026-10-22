"""Internal movement observations for pose-derived angles.

This module is intentionally narrow: it computes joint angles from a single
PoseFrame and reports why a value is missing. It does not smooth, segment,
infer sides, or claim anatomical correctness beyond the geometry requested.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Sequence

from contracts.pose import PoseFrame


@dataclass(frozen=True, slots=True)
class AngleObservation:
    """One angle measurement from a single frame.

    ``value`` is ``None`` when the geometry cannot be measured; ``reason``
    carries a deterministic, machine-readable cause.
    """

    frame_index: int
    timestamp_s: float
    side: Literal["left", "right"]
    metric: str
    space: Literal["projected_2d", "estimated_3d"]
    value: float | None
    reason: str | None


def _is_finite_number(value: object) -> bool:
    """Return True for finite, non-bool numeric scalars."""
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _validate_coords(coords: Sequence[float], dims: int) -> tuple[float, ...]:
    """Validate a coordinate sequence has exactly ``dims`` finite numbers."""
    if len(coords) != dims:
        raise ValueError(f"expected {dims} coordinates, got {len(coords)}")
    for c in coords:
        if not _is_finite_number(c):
            raise ValueError("coordinates must be finite non-bool numbers")
    return tuple(float(c) for c in coords)


def _sub(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(x - y for x, y in zip(a, b))


def _dot(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return math.fsum(x * y for x, y in zip(a, b))


def _unit_direction(
    a: tuple[float, ...], b: tuple[float, ...]
) -> tuple[float, ...]:
    """Return unit vector raw/s where raw = a - b.

    If any raw component is non-finite (e.g. overflow), rescale the endpoints
    by maxabs(a, b) before subtracting. Then scale raw by maxabs(raw), compute
    the Euclidean norm of the scaled vector, and divide. Never multiply the
    norm back by the scale. Finite endpoints divided by their common maximum
    lie in [-1, 1], so the rescued difference is finite in [-2, 2]. The common
    positive divisor preserves direction; close same-sign endpoints cannot
    overflow subtraction and therefore use the original difference.
    """
    raw = _sub(a, b)
    if not all(math.isfinite(x) for x in raw):
        scale = max(max(abs(x) for x in a), max(abs(x) for x in b))
        if scale == 0.0 or not math.isfinite(scale):
            raise ValueError("degenerate or non-finite vector")
        a_scaled = tuple(x / scale for x in a)
        b_scaled = tuple(x / scale for x in b)
        raw = _sub(a_scaled, b_scaled)
    s = max(abs(x) for x in raw)
    if s == 0.0:
        raise ValueError("degenerate zero-length vector")
    scaled = tuple(x / s for x in raw)
    n = math.sqrt(math.fsum(x * x for x in scaled))
    if n == 0.0:
        raise ValueError("degenerate zero-length vector")
    return tuple(x / n for x in scaled)


def angle_degrees(
    a: Sequence[float], b: Sequence[float], c: Sequence[float]
) -> float:
    """Interior angle at vertex ``b`` formed by points ``a-b-c``.

    Returns a value in ``[0.0, 180.0]``. Inputs must be 2D or 3D finite,
    non-bool coordinates. Degenerate vectors raise ``ValueError``.
    """
    dims = len(a)
    if dims not in (2, 3) or len(b) != dims or len(c) != dims:
        raise ValueError("only 2D or 3D coordinates are supported")
    a_t = _validate_coords(a, dims)
    b_t = _validate_coords(b, dims)
    c_t = _validate_coords(c, dims)

    v1 = _unit_direction(a_t, b_t)
    v2 = _unit_direction(c_t, b_t)
    clamped = max(-1.0, min(1.0, _dot(v1, v2)))
    return math.degrees(math.acos(clamped))


def _validate_dimensions(width: object, height: object) -> tuple[int, int]:
    """Reject non-positive, non-integer, or bool dimensions."""
    if isinstance(width, bool) or isinstance(height, bool):
        raise ValueError("width and height must be positive integers, got bool")
    if not isinstance(width, int) or not isinstance(height, int):
        raise ValueError("width and height must be positive integers")
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    return width, height


def _validate_side(side: object) -> Literal["left", "right"]:
    if side == "left":
        return "left"
    if side == "right":
        return "right"
    raise ValueError("side must be 'left' or 'right'")


def _joint_names(side: Literal["left", "right"]) -> tuple[str, str, str, str]:
    """Return (shoulder, elbow, wrist, hip) joint names for the given side."""
    prefix = side
    return (
        f"{prefix}_shoulder",
        f"{prefix}_elbow",
        f"{prefix}_wrist",
        f"{prefix}_hip",
    )


def _get_coords(
    frame: PoseFrame,
    joint: str,
    space: Literal["projected_2d", "estimated_3d"],
    width: int,
    height: int,
) -> tuple[float, ...] | None:
    """Extract validated coordinates for a joint, or None if unavailable."""
    obs = frame.joints.get(joint)
    if obs is None:
        return None
    if space == "projected_2d":
        if obs.xy is None:
            return None
        x, y = obs.xy
        return (x * width, y * height)
    else:
        if obs.xyz is None:
            return None
        return obs.xyz


def _check_joint_status(
    frame: PoseFrame,
    joint: str,
) -> str | None:
    """Return a deterministic reason string if a joint cannot be used."""
    obs = frame.joints.get(joint)
    if obs is None:
        return "missing_joint"
    if not obs.valid:
        return "invalid_joint"
    if obs.interpolated:
        return "interpolated_joint"
    return None


def _measure_angle(
    frame: PoseFrame,
    side: Literal["left", "right"],
    metric: str,
    space: Literal["projected_2d", "estimated_3d"],
    joints: Sequence[str],
    width: int,
    height: int,
) -> AngleObservation:
    """Measure one angle or report the highest-priority failure reason."""
    priority = {
        "missing_joint": 0,
        "invalid_joint": 1,
        "interpolated_joint": 2,
        "missing_coordinates": 3,
        "degenerate_geometry": 4,
    }
    best_reason: str | None = None
    for joint in joints:
        status = _check_joint_status(frame, joint)
        if status == "missing_joint":
            return _observation(frame, side, metric, space, None, "missing_joint")
        if status is not None and (
            best_reason is None or priority[status] < priority[best_reason]
        ):
            best_reason = status

    if best_reason is not None:
        return _observation(frame, side, metric, space, None, best_reason)

    coords: list[tuple[float, ...]] = []
    for joint in joints:
        c = _get_coords(frame, joint, space, width, height)
        if c is None:
            return _observation(
                frame, side, metric, space, None, "missing_coordinates"
            )
        coords.append(c)

    try:
        value = angle_degrees(coords[0], coords[1], coords[2])
    except ValueError:
        return _observation(frame, side, metric, space, None, "degenerate_geometry")

    return _observation(frame, side, metric, space, value, None)


def _observation(
    frame: PoseFrame,
    side: Literal["left", "right"],
    metric: str,
    space: Literal["projected_2d", "estimated_3d"],
    value: float | None,
    reason: str | None,
) -> AngleObservation:
    return AngleObservation(
        frame_index=frame.frame_index,
        timestamp_s=frame.timestamp_s,
        side=side,
        metric=metric,
        space=space,
        value=value,
        reason=reason,
    )


def measure_frame(
    frame: PoseFrame,
    *,
    side: Literal["left", "right"],
    width: int,
    height: int,
) -> tuple[AngleObservation, AngleObservation, AngleObservation, AngleObservation]:
    """Return four angle observations for ``side`` in a fixed order.

    Order:
        1. elbow_angle / projected_2d
        2. elbow_angle / estimated_3d
        3. upper_arm_torso_angle / projected_2d
        4. upper_arm_torso_angle / estimated_3d
    """
    side = _validate_side(side)
    width, height = _validate_dimensions(width, height)

    shoulder, elbow, wrist, hip = _joint_names(side)

    elbow_2d = _measure_angle(
        frame, side, "elbow_angle", "projected_2d", [shoulder, elbow, wrist], width, height
    )
    elbow_3d = _measure_angle(
        frame, side, "elbow_angle", "estimated_3d", [shoulder, elbow, wrist], width, height
    )
    upper_2d = _measure_angle(
        frame, side, "upper_arm_torso_angle", "projected_2d", [elbow, shoulder, hip], width, height
    )
    upper_3d = _measure_angle(
        frame, side, "upper_arm_torso_angle", "estimated_3d", [elbow, shoulder, hip], width, height
    )

    return (elbow_2d, elbow_3d, upper_2d, upper_3d)
