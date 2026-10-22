"""Deterministic per-rep measurements from explicit provisional window labels.

RepWindow labels are EXPLICIT VISUAL PROVISIONAL ANNOTATIONS, not independent
human ground truth or expert approval. Durations are annotation timing, not
proved true turnaround. No interpolation, gap filling, scoring, filtering,
or best-rep selection. Caller carries axis/provider/source-hash provenance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Sequence

from movement.observations import AngleObservation, _is_finite_number
from movement.posture import summarize_window

_Group = tuple[str, str]
_TORSO: _Group = ("torso_axis_angle", "projected_2d")
_ANGLES: tuple[_Group, ...] = (
    ("elbow_angle", "projected_2d"),
    ("elbow_angle", "estimated_3d"),
    ("upper_arm_torso_angle", "projected_2d"),
    ("upper_arm_torso_angle", "estimated_3d"),
)
_ALLOWED: frozenset[_Group] = frozenset((_TORSO, *_ANGLES))


@dataclass(frozen=True, slots=True)
class RepWindow:
    """Provisional annotated rep window; bottom is the annotated turnaround."""

    rep_id: str
    side: Literal["left", "right"]
    start_s: float
    bottom_s: float
    end_s: float

    def __post_init__(self) -> None:
        if not isinstance(self.rep_id, str) or not self.rep_id:
            raise ValueError("rep_id must be a non-empty string")
        if self.side not in ("left", "right"):
            raise ValueError("side must be 'left' or 'right'")
        for name in ("start_s", "bottom_s", "end_s"):
            if not _is_finite_number(getattr(self, name)):
                raise ValueError(f"{name} must be a finite non-bool number")
        if not (0.0 <= self.start_s < self.bottom_s < self.end_s):
            raise ValueError("require 0 <= start_s < bottom_s < end_s")


@dataclass(frozen=True, slots=True)
class Component:
    """One measured component; value is None iff reason is a non-empty string."""

    value: float | None
    reason: str | None
    unit: str
    actual_pts_s: float | None = None

    def __post_init__(self) -> None:
        if self.unit not in ("degrees", "seconds"):
            raise ValueError("unit must be 'degrees' or 'seconds'")
        if (self.value is None) != (self.reason is not None):
            raise ValueError("value is None iff reason is not None")
        if self.reason is not None and (
            not isinstance(self.reason, str) or not self.reason
        ):
            raise ValueError("reason must be a non-empty string when present")
        if self.value is not None and not _is_finite_number(self.value):
            raise ValueError("value must be finite and non-bool when present")
        if self.actual_pts_s is not None and not _is_finite_number(self.actual_pts_s):
            raise ValueError("actual_pts_s must be finite and non-bool when present")


def _missing(unit: str, reason: str = "missing_series") -> Component:
    return Component(value=None, reason=reason, unit=unit)


def _event(
    series: Sequence[AngleObservation], t: float, max_gap_s: float
) -> Component:
    """Nearest RAW sample to ``t`` within tolerance; tie picks earlier PTS.

    Never searches for the nearest valid sample: an invalid nearest sample
    keeps its original reason and its actual PTS.
    """
    best: AngleObservation | None = None
    best_d = math.inf
    for s in series:
        d = abs(s.timestamp_s - t)
        if d > max_gap_s:
            continue
        if d < best_d or (d == best_d and best is not None and s.timestamp_s < best.timestamp_s):
            best, best_d = s, d
    if best is None:
        return Component(None, "no_sample_in_tolerance", "degrees", None)
    if best.value is None:
        return Component(None, best.reason, "degrees", best.timestamp_s)
    return Component(best.value, None, "degrees", best.timestamp_s)


def _validate(
    samples: Sequence[AngleObservation], label: RepWindow
) -> dict[_Group, list[AngleObservation]]:
    groups: dict[_Group, list[AngleObservation]] = {g: [] for g in _ALLOWED}
    for s in samples:
        if not isinstance(s, AngleObservation):
            raise ValueError("samples must be AngleObservation instances")
        if s.side != label.side:
            raise ValueError("sample side must match label side")
        key = (s.metric, s.space)
        if key not in _ALLOWED:
            raise ValueError(f"unexpected metric/space group: {key}")
        if not _is_finite_number(s.timestamp_s) or s.timestamp_s < 0.0:
            raise ValueError("sample timestamps must be finite and non-negative")
        if (s.value is None) != (s.reason is not None):
            raise ValueError("value is None iff reason is not None")
        if s.reason is not None and (not isinstance(s.reason, str) or not s.reason):
            raise ValueError("reason must be a non-empty string when present")
        if s.value is not None and not _is_finite_number(s.value):
            raise ValueError("sample value must be finite and non-bool when present")
        group = groups[key]
        if group and s.timestamp_s <= group[-1].timestamp_s:
            raise ValueError("per-group PTS must be strictly increasing (no duplicates)")
        group.append(s)
    return groups


def measure_rep(
    samples: Sequence[AngleObservation],
    label: RepWindow,
    *,
    max_gap_s: float,
) -> dict[str, Component]:
    """Measure one labeled rep. Returns exactly 32 deterministic keys."""
    if not isinstance(label, RepWindow):
        raise ValueError("label must be a RepWindow")
    if not _is_finite_number(max_gap_s) or max_gap_s <= 0.0:
        raise ValueError("max_gap_s must be a finite positive non-bool number")
    gap = float(max_gap_s)
    groups = _validate(samples, label)

    out: dict[str, Component] = {
        "pull_duration_s": Component(label.bottom_s - label.start_s, None, "seconds"),
        "return_duration_s": Component(label.end_s - label.bottom_s, None, "seconds"),
    }

    for metric, space in _ANGLES:
        prefix = f"{metric}/{space}/"
        series = groups[(metric, space)]
        if not series:
            for suffix in ("start", "bottom", "end", "minimum", "maximum", "excursion"):
                out[prefix + suffix] = _missing("degrees")
            continue
        out[prefix + "start"] = _event(series, label.start_s, gap)
        out[prefix + "bottom"] = _event(series, label.bottom_s, gap)
        out[prefix + "end"] = _event(series, label.end_s, gap)
        full = summarize_window(
            series, start_s=label.start_s, end_s=label.end_s, max_gap_s=gap, circular=False
        )
        if full.reason is not None:
            for suffix in ("minimum", "maximum", "excursion"):
                out[prefix + suffix] = _missing("degrees", full.reason)
        else:
            out[prefix + "minimum"] = Component(full.minimum, None, "degrees")
            out[prefix + "maximum"] = Component(full.maximum, None, "degrees")
            out[prefix + "excursion"] = Component(full.excursion, None, "degrees")

    prefix = "torso_axis_angle/projected_2d/"
    series = groups[_TORSO]
    if not series:
        for suffix in ("start", "bottom", "end", "pull_change", "pull_excursion", "excursion"):
            out[prefix + suffix] = _missing("degrees")
        return out
    out[prefix + "start"] = _event(series, label.start_s, gap)
    out[prefix + "bottom"] = _event(series, label.bottom_s, gap)
    out[prefix + "end"] = _event(series, label.end_s, gap)
    full = summarize_window(
        series, start_s=label.start_s, end_s=label.end_s, max_gap_s=gap, circular=True
    )
    pull = summarize_window(
        series, start_s=label.start_s, end_s=label.bottom_s, max_gap_s=gap, circular=True
    )
    out[prefix + "excursion"] = (
        _missing("degrees", full.reason)
        if full.reason is not None
        else Component(full.excursion, None, "degrees")
    )
    out[prefix + "pull_excursion"] = (
        _missing("degrees", pull.reason)
        if pull.reason is not None
        else Component(pull.excursion, None, "degrees")
    )
    start_ev, bottom_ev = out[prefix + "start"], out[prefix + "bottom"]
    if pull.reason is not None:
        out[prefix + "pull_change"] = _missing("degrees", pull.reason)
    elif start_ev.value is None or bottom_ev.value is None:
        out[prefix + "pull_change"] = _missing("degrees", "invalid_boundary_event")
    else:
        arc = (bottom_ev.value - start_ev.value + 180.0) % 360.0 - 180.0
        if abs(arc) == 180.0:
            out[prefix + "pull_change"] = _missing("degrees", "ambiguous_rotation")
        else:
            out[prefix + "pull_change"] = Component(arc, None, "degrees")
    return out
