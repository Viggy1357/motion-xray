"""Analysis-domain contracts: reps, metrics, coaching, and the full result.

These models carry the deterministic movement analysis (reps, metrics) kept
strictly separate from the LLM coaching text (AGENTS.md rule 2). A metric with
no value stores ``value=None`` plus a ``reason`` — never a fabricated number
(rule 3).
"""

from __future__ import annotations

from typing import Annotated, List, Literal, Optional, Self, Tuple

from pydantic import Field, model_validator

from .base import FiniteFloat, MXRModel, SCHEMA_VERSION
from .enums import CoachingStatus, CompletionStatus


class Rep(MXRModel):
    """A single detected repetition with its phase boundaries (seconds)."""

    id: str
    ordinal: Annotated[int, Field(ge=1)]
    side: Optional[str] = None
    start_s: FiniteFloat
    turnaround_start_s: Optional[FiniteFloat] = None
    turnaround_end_s: Optional[FiniteFloat] = None
    end_s: FiniteFloat
    completion_status: CompletionStatus
    scorable: bool
    excluded_reasons: List[str] = []

    @model_validator(mode="after")
    def valid_interval(self) -> Self:
        boundaries = [self.start_s]
        boundaries.extend(t for t in (self.turnaround_start_s, self.turnaround_end_s) if t is not None)
        boundaries.append(self.end_s)
        if self.start_s < 0 or self.end_s <= self.start_s or boundaries != sorted(boundaries):
            raise ValueError("rep boundaries must be ordered within a positive interval")
        if self.scorable and self.completion_status != CompletionStatus.COMPLETED:
            raise ValueError("only completed repetitions can be scorable")
        return self


class Metric(MXRModel):
    """One measured quantity for a rep.

    ``value`` is ``None`` when it could not be measured; ``reason`` then states
    why in machine-readable form. ``reference_interval`` is the acceptable
    ``(lower, upper)`` band used by scoring.
    """

    id: str
    rep_id: str
    side: Optional[str] = None
    value: Optional[FiniteFloat] = None
    unit: str
    dimensionality: str
    reference_interval: Optional[Tuple[FiniteFloat, FiniteFloat]] = None
    deviation: Optional[FiniteFloat] = None
    coverage: Optional[Annotated[FiniteFloat, Field(ge=0, le=1)]] = None
    quality_method: Optional[str] = None
    status: str
    reason: Optional[str] = None

    @model_validator(mode="after")
    def honest_measurement(self) -> Self:
        if self.value is None and (self.reason is None or not self.reason.strip()):
            raise ValueError("missing metric value requires a nonempty reason")
        if self.reference_interval is not None and self.reference_interval[0] > self.reference_interval[1]:
            raise ValueError("reference interval lower bound exceeds upper bound")
        return self


class CoachingResult(MXRModel):
    """LLM-generated coaching text, kept separate from deterministic metrics.

    When ``status`` is ``unavailable`` the narrative fields are empty rather
    than invented, honoring the never-fabricate rule.
    """

    status: CoachingStatus
    summary: Optional[str] = None
    observations: List[str] = []
    next_set_cue: Optional[str] = None
    limitations: List[str] = []


class AnalysisResult(MXRModel):
    """The complete rep-by-rep report for one analyzed video."""

    schema_version: Literal["0.2.0"] = SCHEMA_VERSION
    analysis_id: str
    exercise: str
    variant: Optional[str] = None
    reps: List[Rep] = []
    metrics: List[Metric] = []
    score: Optional[Annotated[FiniteFloat, Field(ge=0, le=100)]] = None
    best_rep_id: Optional[str] = None
    worst_rep_id: Optional[str] = None
    source_ids: List[str] = []
    coaching: Optional[CoachingResult] = None
    warnings: List[str] = []
    provenance: dict[str, str] = {}
