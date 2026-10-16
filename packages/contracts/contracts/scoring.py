from __future__ import annotations

"""Scoring-domain contract: the auditable breakdown behind a displayed score.

The deterministic scoring formula (recorded for implementers in T-stage tasks)
is ``d = max(L - x, 0, x - U); s = 100 * max(0, 1 - d / T)`` where ``[L, U]``
is the reference interval and ``T`` the tolerance. This model stores the
inputs and outputs so a score is always explainable, and leaves scores
``None`` with ``missing_reasons`` when inputs are absent (AGENTS.md rule 3).
"""

from typing import List, Optional

from .base import FiniteFloat, MXRModel


class ScoreBreakdown(MXRModel):
    """Per-component inputs and the resulting raw/displayed scores."""

    profile_id: str
    profile_version: str
    reference_version: str
    component_values: dict[str, Optional[FiniteFloat]] = {}
    component_weights: dict[str, FiniteFloat] = {}
    raw_score: Optional[FiniteFloat] = None
    displayed_score: Optional[FiniteFloat] = None
    coverage: Optional[FiniteFloat] = None
    missing_reasons: List[str] = []
