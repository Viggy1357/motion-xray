"""Explicitly configured local-review cycle candidates; not validated rep counts."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ReviewConfig:
    version: str
    low_degrees: float
    high_degrees: float
    dwell_s: float
    max_gap_s: float

    def __post_init__(self) -> None:
        if not isinstance(self.version, str) or not self.version:
            raise ValueError("version must be a nonempty string")
        for name, value in (
            ("low_degrees", self.low_degrees),
            ("high_degrees", self.high_degrees),
            ("dwell_s", self.dwell_s),
            ("max_gap_s", self.max_gap_s),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be a finite number, got {value!r}")
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite, got {value}")
        if not 0.0 <= self.low_degrees < self.high_degrees <= 180.0:
            raise ValueError("thresholds must satisfy 0 <= low < high <= 180")
        if self.dwell_s <= 0.0 or self.max_gap_s <= 0.0:
            raise ValueError("dwell_s and max_gap_s must be positive")


@dataclass(frozen=True)
class Cycle:
    start_s: float
    bottom_s: float
    end_s: float


@dataclass(frozen=True)
class CandidateResult:
    cycles: tuple[Cycle, ...]
    partial_spans: tuple[tuple[float, float], ...]
    status: str = "experimental"
    reason: str | None = None


def _validate_samples(samples: Sequence[tuple[float, float | None]]) -> None:
    prev: float | None = None
    for t, a in samples:
        if isinstance(t, bool) or not isinstance(t, (int, float)):
            raise ValueError("timestamps must be finite numbers")
        if not math.isfinite(t) or t < 0.0:
            raise ValueError("timestamps must be finite and nonnegative")
        if prev is not None and t <= prev:
            raise ValueError("timestamps must be strictly increasing")
        prev = t
        if a is None:
            continue
        if isinstance(a, bool) or not isinstance(a, (int, float)):
            raise ValueError("angles must be None or finite numbers")
        if not math.isfinite(a) or a < 0.0 or a > 180.0:
            raise ValueError("angles must be finite and in [0, 180]")


def find_cycles(
    samples: Sequence[tuple[float, float | None]], config: ReviewConfig
) -> CandidateResult:
    """Detect HIGH-LOW-HIGH cycle candidates from observed samples (experimental).

    Three explicit states: waiting_initial_high, waiting_low, waiting_return.
    ``plateau_start`` is the start of the *current* qualifying threshold
    plateau only (nullable); it never outlives a phase change. A plateau is
    confirmed only when observed elapsed time >= dwell_s. Intermediate angles
    reset only the current dwell candidate, never the phase or confirmed
    anchors. On a confirmed return HIGH the cycle is appended as
    Cycle(first_high, bottom, return_plateau_start) and that return plateau
    start is reused as the already-confirmed first HIGH of the next cycle.

    ``bottom_s`` is the LOW-threshold plateau entry time, not the kinematic
    extremum. Missing angles or gaps > max_gap_s reset the active attempt and
    preserve only observed nonzero partial spans; missing intervals are never
    bridged.
    """
    _validate_samples(samples)

    cycles: list[Cycle] = []
    partials: list[tuple[float, float]] = []

    state = "waiting_initial_high"
    attempt_start: float | None = None  # first sample of current attempt
    first_high: float | None = None  # confirmed HIGH plateau start
    bottom: float | None = None  # confirmed LOW plateau start
    plateau_start: float | None = None  # current qualifying plateau candidate
    last_t: float | None = None

    def _record_partial(end: float) -> None:
        if attempt_start is not None and end > attempt_start:
            partials.append((attempt_start, end))

    def _reset(end: float) -> None:
        nonlocal state, attempt_start, first_high, bottom, plateau_start
        _record_partial(end)
        state = "waiting_initial_high"
        attempt_start = None
        first_high = None
        bottom = None
        plateau_start = None

    for t, a in samples:
        if last_t is not None and (t - last_t) > config.max_gap_s:
            _reset(last_t)
        if a is None:
            _reset(t if last_t is None else last_t)
            last_t = t
            continue
        last_t = t
        if attempt_start is None:
            attempt_start = t

        high = a >= config.high_degrees
        low = a <= config.low_degrees

        if state == "waiting_initial_high":
            if high:
                if plateau_start is None:
                    plateau_start = t
                    if attempt_start is None:
                        attempt_start = t
                if t - plateau_start >= config.dwell_s:
                    first_high = plateau_start
                    if attempt_start < first_high:
                        partials.append((attempt_start, first_high))
                    attempt_start = first_high
                    plateau_start = None
                    state = "waiting_low"
            else:
                plateau_start = None

        elif state == "waiting_low":
            if low:
                if plateau_start is None:
                    plateau_start = t
                if t - plateau_start >= config.dwell_s:
                    bottom = plateau_start
                    plateau_start = None
                    state = "waiting_return"
            elif high:
                plateau_start = None
            else:
                plateau_start = None

        else:  # waiting_return
            if high:
                if plateau_start is None:
                    plateau_start = t
                if t - plateau_start >= config.dwell_s:
                    end = plateau_start
                    assert first_high is not None and bottom is not None
                    cycles.append(Cycle(start_s=first_high, bottom_s=bottom, end_s=end))
                    # Reuse confirmed return HIGH as next cycle's first HIGH.
                    first_high = end
                    attempt_start = end
                    bottom = None
                    plateau_start = None
                    state = "waiting_low"
            else:
                # Low or intermediate: reset only the return dwell candidate.
                plateau_start = None

    if last_t is not None:
        _record_partial(last_t)

    return CandidateResult(
        cycles=tuple(cycles),
        partial_spans=tuple(partials),
        status="experimental",
        reason=None,
    )
