"""Local experimental angle-pattern agreement, never a valid technique score."""

from __future__ import annotations

import math
from typing import Sequence

VERSION = "lat-review-angle-agreement-v1"

Sample = tuple[float, float | None, float | None]


def _num(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    try:
        v = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} must be finite") from exc
    if not math.isfinite(v):
        raise ValueError(f"{name} must be finite")
    return v


def _validate_angle(value: float | None, name: str) -> None:
    if value is None:
        return
    v = _num(value, name)
    if v < 0.0 or v > 180.0:
        raise ValueError(f"{name} must be in [0, 180]")


def _validate_samples(samples: Sequence[Sample], name: str) -> None:
    if not samples:
        raise ValueError(f"{name} must be non-empty")
    prev: float | None = None
    for i, row in enumerate(samples):
        if not isinstance(row, tuple) or len(row) != 3:
            raise ValueError(f"{name} row {i} must be a 3-tuple")
        t, elbow, upper = row
        tv = _num(t, f"{name}[{i}].time_s")
        if tv < 0.0:
            raise ValueError(f"{name}[{i}].time_s must be >= 0")
        _validate_angle(elbow, f"{name}[{i}].elbow_angle_deg")
        _validate_angle(upper, f"{name}[{i}].upper_arm_torso_angle_deg")
        if prev is not None and tv <= prev:
            raise ValueError(f"{name} timestamps must strictly increase")
        prev = tv


def _validate_cycle(cycle: tuple[float, float, float], name: str) -> None:
    if not isinstance(cycle, tuple) or len(cycle) != 3:
        raise ValueError(f"{name} must be a 3-tuple")
    start = _num(cycle[0], f"{name}.start")
    bottom = _num(cycle[1], f"{name}.bottom")
    end = _num(cycle[2], f"{name}.end")
    if not (0 <= start < bottom < end):
        raise ValueError(f"{name} must satisfy start < bottom < end")


def _validate_max_gap(value: float) -> None:
    if _num(value, "max_gap_s") <= 0.0:
        raise ValueError("max_gap_s must be positive")


def _validate_points(value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("points_per_phase must be int 2..501")
    if value < 2 or value > 501:
        raise ValueError("points_per_phase must be int 2..501")


def _coverage_ok(
    samples: Sequence[Sample], start: float, end: float, max_gap_s: float
) -> bool:
    """Every raw sample inside [start, end] must have both features, and no
    observation interval intersecting [start, end] may exceed max_gap_s."""
    prev_t: float | None = None
    for t, elbow, upper in samples:
        if start <= t <= end and (elbow is None or upper is None):
            return False
        if prev_t is not None and t > start and prev_t < end:
            if t - prev_t > max_gap_s:
                return False
        prev_t = t
    return True


def _phase_grid(start: float, end: float, points: int) -> list[float]:
    step = (end - start) / (points - 1)
    grid = [start + i * step for i in range(points)]
    grid[0] = start
    grid[-1] = end
    return grid


def _sample_value(
    t: float, samples: Sequence[Sample], max_gap_s: float, idx: int
) -> float | None:
    left: Sample | None = None
    right: Sample | None = None
    for s in samples:
        if s[0] == t:
            return s[idx]
        if s[0] < t:
            left = s
        elif s[0] > t and right is None:
            right = s
    if left is None or right is None:
        return None
    lv = left[idx]
    rv = right[idx]
    if lv is None or rv is None:
        return None
    if right[0] - left[0] > max_gap_s:
        return None
    frac = (t - left[0]) / (right[0] - left[0])
    return lv + frac * (rv - lv)


def _resample(
    grid: list[float], samples: Sequence[Sample], max_gap_s: float
) -> tuple[list[float], list[float]] | None:
    elbow: list[float] = []
    upper: list[float] = []
    for t in grid:
        e = _sample_value(t, samples, max_gap_s, 1)
        u = _sample_value(t, samples, max_gap_s, 2)
        if e is None or u is None:
            return None
        elbow.append(e)
        upper.append(u)
    return elbow, upper


def _durations(
    user_cycle: tuple[float, float, float],
    reference_cycle: tuple[float, float, float],
) -> dict:
    return {
        "user_pull_duration_s": user_cycle[1] - user_cycle[0],
        "user_return_duration_s": user_cycle[2] - user_cycle[1],
        "reference_pull_duration_s": reference_cycle[1] - reference_cycle[0],
        "reference_return_duration_s": reference_cycle[2] - reference_cycle[1],
    }


def _unavailable(
    user_cycle: tuple[float, float, float],
    reference_cycle: tuple[float, float, float],
) -> dict:
    return {
        "status": "unavailable",
        "experimental_agreement_score": None,
        "authoritative": False,
        "valid_technique_score": None,
        "score_label": "Unvalidated angle-pattern agreement; not technique correctness",
        "algorithm_version": VERSION,
        "normalization_degrees": 180,
        "per_feature_weights": {"elbow": 0.5, "upper_arm_torso": 0.5},
        "elbow_mae_degrees": None,
        "upper_arm_torso_mae_degrees": None,
        "mean_mae_degrees": None,
        "user_time_pairs": [],
        "reference_time_pairs": [],
        "grid_point_count": 0,
        "reason": "insufficient_observations",
        **_durations(user_cycle, reference_cycle),
    }


def compare_review_cycles(
    user: Sequence[Sample],
    user_cycle: tuple[float, float, float],
    reference: Sequence[Sample],
    reference_cycle: tuple[float, float, float],
    *,
    max_gap_s: float,
    points_per_phase: int = 21,
) -> dict:
    """Experimental local phase-normalized angle-pattern agreement.

    Samples are (time_s, elbow_interior_deg, upper_arm_torso_interior_deg).
    Caller is responsible for recording any side/view differences; this
    module cannot certify them. No DTW, no extrapolation, no correctness or
    calibration claim.
    """
    _validate_samples(user, "user")
    _validate_samples(reference, "reference")
    _validate_cycle(user_cycle, "user_cycle")
    _validate_cycle(reference_cycle, "reference_cycle")
    _validate_max_gap(max_gap_s)
    _validate_points(points_per_phase)

    us, ue = user_cycle[0], user_cycle[2]
    rs, re = reference_cycle[0], reference_cycle[2]
    if not (
        _coverage_ok(user, us, ue, max_gap_s)
        and _coverage_ok(reference, rs, re, max_gap_s)
    ):
        return _unavailable(user_cycle, reference_cycle)

    u_grid = _phase_grid(us, user_cycle[1], points_per_phase) + _phase_grid(
        user_cycle[1], ue, points_per_phase
    )[1:]
    r_grid = _phase_grid(rs, reference_cycle[1], points_per_phase) + _phase_grid(
        reference_cycle[1], re, points_per_phase
    )[1:]

    u_res = _resample(u_grid, user, max_gap_s)
    r_res = _resample(r_grid, reference, max_gap_s)
    if u_res is None or r_res is None:
        return _unavailable(user_cycle, reference_cycle)
    u_elbow, u_upper = u_res
    r_elbow, r_upper = r_res

    n = len(u_grid)
    elbow_mae = sum(abs(u_elbow[i] - r_elbow[i]) for i in range(n)) / n
    upper_mae = sum(abs(u_upper[i] - r_upper[i]) for i in range(n)) / n
    mean_mae = 0.5 * elbow_mae + 0.5 * upper_mae
    score = min(100.0, max(0.0, 100.0 * (1.0 - mean_mae / 180.0)))

    pairs = list(zip(u_grid, r_grid))
    return {
        "status": "experimental",
        "experimental_agreement_score": score,
        "authoritative": False,
        "valid_technique_score": None,
        "score_label": "Unvalidated angle-pattern agreement; not technique correctness",
        "algorithm_version": VERSION,
        "normalization_degrees": 180,
        "per_feature_weights": {"elbow": 0.5, "upper_arm_torso": 0.5},
        "elbow_mae_degrees": elbow_mae,
        "upper_arm_torso_mae_degrees": upper_mae,
        "mean_mae_degrees": mean_mae,
        "user_time_pairs": pairs,
        "reference_time_pairs": pairs,
        "grid_point_count": n,
        "reason": None,
        **_durations(user_cycle, reference_cycle),
    }
