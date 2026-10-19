"""Scoring-domain contract: the auditable breakdown behind a displayed score.

The deterministic scoring formula (recorded for implementers in T-stage tasks)
is ``d = max(L - x, 0, x - U); s = 100 * max(0, 1 - d / T)`` where ``[L, U]``
is the reference interval and ``T`` the tolerance. This model stores the
inputs and outputs so a score is always explainable, and leaves scores
``None`` with ``missing_reasons`` when inputs are absent (AGENTS.md rule 3).
"""

from __future__ import annotations

from typing import Annotated, List, Optional, Self

from pydantic import Field, model_validator

from .base import FiniteFloat, MXRModel


class ScoreBreakdown(MXRModel):
    """Per-component inputs and the resulting raw/displayed scores."""

    profile_id: str
    profile_version: str
    reference_version: str
    component_values: dict[str, Optional[FiniteFloat]] = {}
    component_weights: dict[str, Annotated[FiniteFloat, Field(ge=0, le=1)]] = {}
    raw_score: Optional[Annotated[FiniteFloat, Field(ge=0, le=100)]] = None
    displayed_score: Optional[Annotated[FiniteFloat, Field(ge=0, le=100)]] = None
    coverage: Optional[Annotated[FiniteFloat, Field(ge=0, le=1)]] = None
    missing_reasons: List[str] = []

    @model_validator(mode="after")
    def valid_breakdown(self) -> Self:
        if self.component_weights and abs(sum(self.component_weights.values()) - 1.0) > 1e-9:
            raise ValueError("component weights must sum to one")
        if self.displayed_score is None and not any(reason.strip() for reason in self.missing_reasons):
            raise ValueError("missing displayed score requires a reason")
        return self
