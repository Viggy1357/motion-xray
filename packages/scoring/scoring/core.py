from __future__ import annotations

"""Deterministic scoring primitives (SCAFFOLD — no real math).

Scoring compares a user's measured metrics against an approved reference
interval ``[L, U]`` with tolerance ``T``. The per-metric score uses::

    d = max(L - x, 0, x - U); s = 100 * max(0, 1 - d/T)

where ``x`` is the measured value, ``L``/``U`` the reference interval bounds,
``d`` the signed-clamped deviation outside the band, and ``s`` the 0-100
score. Implementations are deferred to TODO(T07); each raises
:class:`NotImplementedError` so no caller mistakes a scaffold for a real score
(AGENTS.md rules 2 and 3 — scores are deterministic and never fabricated).
"""

from typing import Any, Sequence

from contracts.analysis import Metric
from contracts.scoring import ScoreBreakdown


def normalize_and_align(user: Any, reference: Any) -> Any:
    """Normalize and temporally align ``user`` samples to the ``reference``.

    Produces comparable, scale-consistent series before alignment; unknown
    world scale stays unknown and is reported as a ratio, not fabricated units.
    """
    # TODO(T07): implement deterministic normalization/alignment.
    raise NotImplementedError(
        "normalize_and_align is a scaffold stub — TODO(T07)."
    )


def dtw_align(user: Sequence[float], reference: Sequence[float]) -> Any:
    """Dynamic-time-warp align ``user`` to ``reference`` time series.

    Returns the alignment path used to compare phase-matched samples.
    """
    # TODO(T07): implement deterministic DTW alignment.
    raise NotImplementedError("dtw_align is a scaffold stub — TODO(T07).")


def score_rep(metrics: Sequence[Metric], reference: Any) -> ScoreBreakdown:
    """Score one rep's ``metrics`` against the ``reference`` profile.

    Applies the per-metric score ``d = max(L - x, 0, x - U);
    s = 100 * max(0, 1 - d/T)`` and records component values/weights plus any
    missing-coverage reasons in the :class:`~contracts.scoring.ScoreBreakdown`.
    A metric with no value lowers coverage rather than being invented.
    """
    # TODO(T07): implement the deterministic per-rep scoring formula.
    raise NotImplementedError("score_rep is a scaffold stub — TODO(T07).")


def score_set(rep_scores: Sequence[ScoreBreakdown], reference: Any) -> ScoreBreakdown:
    """Aggregate per-rep breakdowns into a single set-level score.

    Honors coverage: insufficient scorable reps yield an honest partial result
    with ``displayed_score=None`` and a reason, never a padded number.
    """
    # TODO(T07): implement deterministic set-level aggregation.
    raise NotImplementedError("score_set is a scaffold stub — TODO(T07).")
