from __future__ import annotations

"""Deterministic movement-analysis primitives (SCAFFOLD — no real math).

These are the public signatures the pipeline depends on. Implementations are
deferred to TODO(T05); each raises :class:`NotImplementedError` so a caller can
never mistake an empty scaffold for a real measurement (AGENTS.md rule 3).
"""

from typing import Any, Sequence

from contracts.analysis import Metric, Rep
from contracts.pose import PoseSequence


def compute_angle(a: Any, b: Any, c: Any) -> float:
    """Return the angle at vertex ``b`` formed by points ``a``-``b``-``c``.

    Points are joint coordinates in a shared frame. The result is the planar
    (or 3D, when available) interior angle in degrees.
    """
    # TODO(T05): implement the deterministic angle computation.
    raise NotImplementedError("compute_angle is a scaffold stub — TODO(T05).")


def smooth_series(series: Sequence[float], window: int) -> list[float]:
    """Smooth a 1D ``series`` with a centered moving window of size ``window``.

    Used to denoise joint-angle time series before rep segmentation; must not
    introduce values across gaps that are longer than the allowed interpolation
    window (see skills/pose-pipeline quality gating).
    """
    # TODO(T05): implement the deterministic smoothing.
    raise NotImplementedError("smooth_series is a scaffold stub — TODO(T05).")


def segment_reps(pose: PoseSequence, exercise_spec: Any) -> list[Rep]:
    """Segment ``pose`` into repetitions per the ``exercise_spec``.

    Turnaround events must come from real samples, never from interpolated
    fillers. Ambiguous or low-coverage reps are marked partial/uncertain rather
    than dropped silently.
    """
    # TODO(T05): implement deterministic rep segmentation.
    raise NotImplementedError("segment_reps is a scaffold stub — TODO(T05).")


def compute_metrics(pose: PoseSequence, reps: Sequence[Rep]) -> list[Metric]:
    """Compute per-rep :class:`~contracts.analysis.Metric` values from ``pose``.

    A metric that cannot be measured is returned with ``value=None`` and a
    machine-readable ``reason``; it is never fabricated.
    """
    # TODO(T05): implement deterministic metric computation.
    raise NotImplementedError("compute_metrics is a scaffold stub — TODO(T05).")
