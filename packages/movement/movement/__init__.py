"""Motion X Ray movement — deterministic movement analysis.

Pure, deterministic processing kept strictly separate from any LLM output
(AGENTS.md rule 2). All computation operates on contract pose/analysis models;
a missing perception input yields an honest partial result, never a fabricated
angle or rep (rule 3).
"""

from __future__ import annotations

from .core import (
    compute_angle,
    compute_metrics,
    segment_reps,
    smooth_series,
)

__all__ = [
    "compute_angle",
    "smooth_series",
    "segment_reps",
    "compute_metrics",
]
