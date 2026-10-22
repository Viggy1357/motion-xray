from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Sequence, TypeGuard

from contracts.pose import PoseFrame
from movement.observations import (
    AngleObservation,
    _check_joint_status,
    _get_coords,
    _is_finite_number,
    _observation,
    _validate_dimensions,
    _validate_side,
)

_STATUS_PRIORITY: dict[str, int] = {
    "missing_joint": 0,
    "invalid_joint": 1,
    "interpolated_joint": 2,
    "missing_coordinates": 3,
    "degenerate_geometry": 4,
}


@dataclass(frozen=True, slots=True)
class ProjectionAxis:
    version: str
    axis_id: str
    up_xy: tuple[float, float]
    positive_cross_sign: int

    def __post_init__(self) -> None:
        if not isinstance(self.version, str) or not self.version:
            raise ValueError("version must be a non-empty string")
        if not isinstance(self.axis_id, str) or not self.axis_id:
            raise ValueError("axis_id must be a non-empty string")
        if not isinstance(self.up_xy, (tuple, list)) or len(self.up_xy) != 2:
            raise ValueError("up_xy must be a tuple/list of exactly two coordinates")
        ux, uy = self.up_xy[0], self.up_xy[1]
        if not _is_finite_number(ux) or not _is_finite_number(uy):
            raise ValueError("up_xy coordinates must be finite non-bool numbers")
        if ux == 0.0 and uy == 0.0:
            raise ValueError("up_xy must be a non-zero vector")
        if not isinstance(self.positive_cross_sign, int) or isinstance(
            self.positive_cross_sign, bool
        ):
            raise ValueError("positive_cross_sign must be exactly +1 or -1")
        if self.positive_cross_sign not in (-1, 1):
            raise ValueError("positive_cross_sign must be exactly +1 or -1")
        object.__setattr__(self, "up_xy", (float(ux), float(uy)))


@dataclass(frozen=True, slots=True)
class WindowSummary:
    requested_start_s: float
    requested_end_s: float
    first_pts_s: float | None
    last_pts_s: float | None
    total_samples: int
    valid_samples: int
    minimum: float | None
    maximum: float | None
    excursion: float | None
    start_value: float | None
    end_value: float | None
    end_change: float | None
    reason: str | None


def _unit2d(v: tuple[float, float]) -> tuple[float, float]:
    x, y = v
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError("non-finite vector")
    s = max(abs(x), abs(y))
    if s == 0.0:
        raise ValueError("degenerate zero-length vector")
    sx, sy = x / s, y / s
    n = math.hypot(sx, sy)
    if n == 0.0 or not math.isfinite(n):
        raise ValueError("degenerate zero-length vector")
    return (sx / n, sy / n)


def _cross2d(a: tuple[float, float], b: tuple[float, float]) -> float:
    return a[0] * b[1] - a[1] * b[0]


def _signed_angle_degrees(
    from_vec: tuple[float, float],
    to_vec: tuple[float, float],
    positive_cross_sign: int,
) -> float:
    uf = _unit2d(from_vec)
    ut = _unit2d(to_vec)
    cross = _cross2d(uf, ut) * positive_cross_sign
    dot = uf[0] * ut[0] + uf[1] * ut[1]
    deg = math.degrees(math.atan2(cross, dot))
    if deg >= 180.0:
        deg -= 360.0
    if deg < -180.0:
        deg += 360.0
    return deg


def _robust_torso_vector(
    shoulder: tuple[float, float], hip: tuple[float, float]
) -> tuple[float, float]:
    scale = 1.0
    for _ in range(8):
        dx = shoulder[0] * scale - hip[0] * scale
        dy = shoulder[1] * scale - hip[1] * scale
        if math.isfinite(dx) and math.isfinite(dy):
            if dx == 0.0 and dy == 0.0:
                raise ValueError("degenerate zero-length torso vector")
            return (dx, dy)
        scale *= 0.5
    raise ValueError("torso vector subtraction overflowed irrecoverably")


def measure_torso_frame(
    frame: PoseFrame,
    *,
    side: Literal["left", "right"],
    width: int,
    height: int,
    axis: ProjectionAxis,
) -> AngleObservation:
    side = _validate_side(side)
    width, height = _validate_dimensions(width, height)
    if not isinstance(axis, ProjectionAxis):
        raise ValueError("axis must be a ProjectionAxis instance")

    shoulder = f"{side}_shoulder"
    hip = f"{side}_hip"

    best_status: str | None = None
    for joint in (shoulder, hip):
        status = _check_joint_status(frame, joint)
        if status is None:
            continue
        if best_status is None or _STATUS_PRIORITY.get(
            status, 99
        ) < _STATUS_PRIORITY.get(best_status, 99):
            best_status = status
    if best_status is not None:
        return _observation(
            frame, side, "torso_axis_angle", "projected_2d", None, best_status
        )

    shoulder_coords = _get_coords(frame, shoulder, "projected_2d", width, height)
    hip_coords = _get_coords(frame, hip, "projected_2d", width, height)
    if shoulder_coords is None or hip_coords is None:
        return _observation(
            frame, side, "torso_axis_angle", "projected_2d", None, "missing_coordinates"
        )

    try:
        torso = _robust_torso_vector(
            (shoulder_coords[0], shoulder_coords[1]),
            (hip_coords[0], hip_coords[1]),
        )
        value = _signed_angle_degrees(axis.up_xy, torso, axis.positive_cross_sign)
    except ValueError:
        return _observation(
            frame, side, "torso_axis_angle", "projected_2d", None, "degenerate_geometry"
        )

    return _observation(frame, side, "torso_axis_angle", "projected_2d", value, None)


def _unwrap_diff(a: float, b: float) -> float:
    diff = (b - a + 180.0) % 360.0 - 180.0
    if diff <= -180.0:
        diff += 360.0
    if abs(diff) == 180.0:
        raise ValueError("ambiguous 180 degree rotation")
    return diff


def _is_finite_float(obj: object) -> TypeGuard[float]:
    return _is_finite_number(obj)


def _validate_window_args(
    start_s: object, end_s: object, max_gap_s: object, circular: object
) -> tuple[float, float, float, bool]:
    if not _is_finite_float(start_s):
        raise ValueError("start_s must be a finite non-bool number")
    if not _is_finite_float(end_s):
        raise ValueError("end_s must be a finite non-bool number")
    if not _is_finite_float(max_gap_s):
        raise ValueError("max_gap_s must be a finite non-bool number")
    if not isinstance(circular, bool):
        raise ValueError("circular must be a bool")
    s, e, g = float(start_s), float(end_s), float(max_gap_s)
    if not (0.0 <= s < e):
        raise ValueError("require 0 <= start_s < end_s")
    if g <= 0.0:
        raise ValueError("max_gap_s must be positive")
    return s, e, g, bool(circular)


def _validate_sample(sample: AngleObservation) -> None:
    if not _is_finite_number(sample.timestamp_s) or sample.timestamp_s < 0.0:
        raise ValueError("sample timestamps must be finite and non-negative")
    if (sample.value is None) != (sample.reason is not None):
        raise ValueError("value is None iff reason is not None")
    if sample.reason is not None and (
        not isinstance(sample.reason, str) or not sample.reason
    ):
        raise ValueError("reason must be a non-empty string when present")
    if sample.value is not None and not _is_finite_number(sample.value):
        raise ValueError("sample value must be finite and non-bool when present")


def summarize_window(
    samples: Sequence[AngleObservation],
    *,
    start_s: float,
    end_s: float,
    max_gap_s: float,
    circular: bool,
) -> WindowSummary:
    start_s, end_s, max_gap_s, circular = _validate_window_args(
        start_s, end_s, max_gap_s, circular
    )

    if not samples:
        return WindowSummary(
            requested_start_s=start_s,
            requested_end_s=end_s,
            first_pts_s=None,
            last_pts_s=None,
            total_samples=0,
            valid_samples=0,
            minimum=None,
            maximum=None,
            excursion=None,
            start_value=None,
            end_value=None,
            end_change=None,
            reason="insufficient_samples",
        )

    prev_ts: float | None = None
    expected_side: Literal["left", "right"] | None = None
    expected_metric: str | None = None
    expected_space: Literal["projected_2d", "estimated_3d"] | None = None
    for sample in samples:
        _validate_sample(sample)
        if prev_ts is not None and sample.timestamp_s <= prev_ts:
            raise ValueError("sample timestamps must be strictly increasing")
        prev_ts = sample.timestamp_s
        if expected_side is None:
            expected_side = sample.side
            expected_metric = sample.metric
            expected_space = sample.space
        elif (
            sample.side != expected_side
            or sample.metric != expected_metric
            or sample.space != expected_space
        ):
            raise ValueError("samples must be homogeneous in side, metric, and space")

    selected: list[AngleObservation] = [
        s for s in samples if start_s <= s.timestamp_s <= end_s
    ]

    total = len(selected)
    valid = sum(1 for s in selected if s.value is not None)
    first_pts = selected[0].timestamp_s if selected else None
    last_pts = selected[-1].timestamp_s if selected else None

    if total < 2:
        return WindowSummary(
            requested_start_s=start_s,
            requested_end_s=end_s,
            first_pts_s=first_pts,
            last_pts_s=last_pts,
            total_samples=total,
            valid_samples=valid,
            minimum=None,
            maximum=None,
            excursion=None,
            start_value=None,
            end_value=None,
            end_change=None,
            reason="insufficient_samples",
        )

    assert first_pts is not None and last_pts is not None

    for s in selected:
        if s.value is None:
            return _invalid_summary(
                start_s, end_s, first_pts, last_pts, total, valid, "missing_observation"
            )

    if first_pts - start_s > max_gap_s or end_s - last_pts > max_gap_s:
        return _invalid_summary(
            start_s, end_s, first_pts, last_pts, total, valid, "partial_window"
        )
    for i in range(1, len(selected)):
        if selected[i].timestamp_s - selected[i - 1].timestamp_s > max_gap_s:
            return _invalid_summary(
                start_s, end_s, first_pts, last_pts, total, valid, "timestamp_gap"
            )

    values: list[float] = []
    for s in selected:
        if s.value is None:
            raise ValueError("unexpected None value after validation")
        values.append(s.value)

    if circular:
        try:
            unwrapped: list[float] = [values[0]]
            for i in range(1, len(values)):
                diff = _unwrap_diff(unwrapped[i - 1], values[i])
                unwrapped.append(unwrapped[i - 1] + diff)
        except ValueError:
            return _invalid_summary(
                start_s, end_s, first_pts, last_pts, total, valid, "ambiguous_rotation"
            )
        minimum = min(unwrapped)
        maximum = max(unwrapped)
        excursion = maximum - minimum
        start_value = unwrapped[0]
        end_value = unwrapped[-1]
    else:
        minimum = min(values)
        maximum = max(values)
        excursion = maximum - minimum
        start_value = values[0]
        end_value = values[-1]

    end_change = end_value - start_value

    return WindowSummary(
        requested_start_s=start_s,
        requested_end_s=end_s,
        first_pts_s=first_pts,
        last_pts_s=last_pts,
        total_samples=total,
        valid_samples=valid,
        minimum=minimum,
        maximum=maximum,
        excursion=excursion,
        start_value=start_value,
        end_value=end_value,
        end_change=end_change,
        reason=None,
    )


def _invalid_summary(
    requested_start_s: float,
    requested_end_s: float,
    first_pts_s: float | None,
    last_pts_s: float | None,
    total_samples: int,
    valid_samples: int,
    reason: str,
) -> WindowSummary:
    return WindowSummary(
        requested_start_s=requested_start_s,
        requested_end_s=requested_end_s,
        first_pts_s=first_pts_s,
        last_pts_s=last_pts_s,
        total_samples=total_samples,
        valid_samples=valid_samples,
        minimum=None,
        maximum=None,
        excursion=None,
        start_value=None,
        end_value=None,
        end_change=None,
        reason=reason,
    )
