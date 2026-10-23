"""Explicitly configured local-review cycle candidates; not validated rep counts.

Reviewer notes (hm-gap01 repair): ``Cycle`` keeps exactly its original three
fields (start_s, bottom_s, end_s) so strict ``astuple`` comparisons stay
stable. Accepted missing-observation spans are additive diagnostics metadata
stored on ``CandidateResult.cycle_missing_spans``, aligned one entry per
cycle (empty tuple when none); this field is not public API. Gap bridging is
endpoint-capped: a run of None samples is bridged only when both bracketing
observed samples share one threshold band and their elapsed time fits within
missing_gap_s (+1e-9). Missing frames never count toward dwell: the plateau
candidate is cleared at the first None and dwell restarts at the next valid
sample. Failed bridges, implicit timestep jumps, and trailing gaps reset the
attempt; recorded spans always lie within their cycle's [start_s, end_s].
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

_EPS = 1e-9


@dataclass(frozen=True)
class ReviewConfig:
    version: str
    low_degrees: float
    high_degrees: float
    dwell_s: float
    max_gap_s: float
    missing_gap_s: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.version, str) or not self.version:
            raise ValueError("version must be a nonempty string")
        for name, value in (
            ("low_degrees", self.low_degrees),
            ("high_degrees", self.high_degrees),
            ("dwell_s", self.dwell_s),
            ("max_gap_s", self.max_gap_s),
            ("missing_gap_s", self.missing_gap_s),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be a finite number, got {value!r}")
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite, got {value}")
        if not 0.0 <= self.low_degrees < self.high_degrees <= 180.0:
            raise ValueError("thresholds must satisfy 0 <= low < high <= 180")
        if self.dwell_s <= 0.0 or self.max_gap_s <= 0.0:
            raise ValueError("dwell_s and max_gap_s must be positive")
        if not 0.0 <= self.missing_gap_s <= self.max_gap_s:
            raise ValueError("missing_gap_s must satisfy 0 <= missing_gap_s <= max_gap_s")


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
    # Additive diagnostics metadata (not public API): one entry per cycle,
    # each a tuple of accepted missing-observation spans within that cycle.
    cycle_missing_spans: tuple[tuple[tuple[float, float], ...], ...] = ()


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
    preserve only observed nonzero partial spans.

    Opt-in gap bridging (``missing_gap_s > 0``): once the initial HIGH is
    confirmed, a run of None samples is held pending instead of resetting.
    It is bridged only when the prior and next observed samples fall in the
    SAME threshold band (high >= high_degrees, low <= low_degrees, middle
    strictly between) and the elapsed time between those valid endpoints is
    <= missing_gap_s (+1e-9 epsilon). Missing observations never count toward
    dwell: the current plateau candidate is cleared at the first None and
    dwell restarts at the next valid sample. Accepted spans are recorded on
    ``CandidateResult.cycle_missing_spans`` (aligned one entry per cycle) and
    reset per cycle. Different bands, overlong spans, implicit timestep jumps
    > max_gap_s, trailing gaps, and gaps before the first confirmed HIGH are
    never bridged. Missing frames remain None; nothing is interpolated.
    """
    _validate_samples(samples)

    cycles: list[Cycle] = []
    cycle_spans: list[tuple[tuple[float, float], ...]] = []
    partials: list[tuple[float, float]] = []

    state = "waiting_initial_high"
    attempt_start: float | None = None  # first sample of current attempt
    first_high: float | None = None  # confirmed HIGH plateau start
    bottom: float | None = None  # confirmed LOW plateau start
    plateau_start: float | None = None  # current qualifying plateau candidate
    last_t: float | None = None
    last_band: str | None = None  # threshold band of last observed sample
    pending_gap_start: float | None = None  # last valid time before a None run
    pending_gap_band: str | None = None  # band of that last valid sample
    attempt_spans: list[tuple[float, float]] = []  # accepted gaps, this cycle

    def _band(a: float) -> str:
        if a >= config.high_degrees:
            return "high"
        if a <= config.low_degrees:
            return "low"
        return "mid"

    def _record_partial(end: float) -> None:
        if attempt_start is not None and end > attempt_start:
            partials.append((attempt_start, end))

    def _reset(end: float) -> None:
        nonlocal state, attempt_start, first_high, bottom, plateau_start
        nonlocal pending_gap_start, pending_gap_band, attempt_spans
        _record_partial(end)
        state = "waiting_initial_high"
        attempt_start = None
        first_high = None
        bottom = None
        plateau_start = None
        pending_gap_start = None
        pending_gap_band = None
        attempt_spans = []

    for t, a in samples:
        if last_t is not None and (t - last_t) > config.max_gap_s:
            _reset(last_t)
        if a is None:
            # Missing samples never count dwell: clear the plateau candidate
            # immediately, not only on resume.
            plateau_start = None
            if (
                config.missing_gap_s > 0.0
                and first_high is not None
                and pending_gap_start is None
                and last_t is not None
            ):
                pending_gap_start = last_t
                pending_gap_band = last_band
            elif pending_gap_start is None:
                _reset(t if last_t is None else last_t)
            last_t = t
            continue

        if pending_gap_start is not None:
            elapsed = t - pending_gap_start
            band = _band(a)
            if band == pending_gap_band and elapsed <= config.missing_gap_s + _EPS:
                attempt_spans.append((pending_gap_start, t))
                # Dwell restarts at this valid sample (plateau already cleared).
                plateau_start = None
            else:
                _reset(pending_gap_start)
            pending_gap_start = None
            pending_gap_band = None

        last_t = t
        last_band = _band(a)
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
                    cycle_spans.append(tuple(attempt_spans))
                    # Reuse confirmed return HIGH as next cycle's first HIGH.
                    first_high = end
                    attempt_start = end
                    bottom = None
                    plateau_start = None
                    attempt_spans = []
                    state = "waiting_low"
            else:
                # Low or intermediate: reset only the return dwell candidate.
                plateau_start = None

    if pending_gap_start is not None:
        # Trailing gap: never bridged; partial ends at the last valid sample.
        _reset(pending_gap_start)
    elif last_t is not None:
        _record_partial(last_t)

    return CandidateResult(
        cycles=tuple(cycles),
        partial_spans=tuple(partials),
        status="experimental",
        reason=None,
        cycle_missing_spans=tuple(cycle_spans),
    )
