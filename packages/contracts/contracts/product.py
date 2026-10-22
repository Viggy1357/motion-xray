"""Product-domain contracts: prototype reports, profiles, workouts, routines.

Additive module; the 0.2 analysis schema is untouched. The 0.3 prototype
report never invents a score: ``score`` is always ``None`` and any prototype
match estimate lives separately in ``prototype_assessment``.
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional, Self

from pydantic import Field, model_validator

from .analysis import AnalysisResult, CoachingResult, Metric, Rep
from .base import FiniteFloat, MXRModel, UTCDateTime

Str64 = Annotated[str, Field(min_length=1, max_length=64)]
Str128 = Annotated[str, Field(min_length=1, max_length=128)]
NonNegInt = Annotated[int, Field(ge=0, strict=True)]
LoadUnit = Literal["kg", "lb"]
ExerciseId = Literal["lat_pulldown", "dumbbell_curl", "squat", "incline_chest_press"]


class ReportQuality(MXRModel):
    expected_supporting_samples: NonNegInt
    valid_observed_samples: NonNegInt
    per_metric_coverage: dict[str, Annotated[FiniteFloat, Field(ge=0, le=1)]] = {}
    usable_reps: NonNegInt
    total_reps: NonNegInt
    missing_reasons: list[Annotated[str, Field(max_length=256)]] = []
    view_review: Literal["reviewed", "unreviewed", "incompatible"] = "unreviewed"

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.valid_observed_samples > self.expected_supporting_samples:
            raise ValueError("valid_observed_samples exceeds expected_supporting_samples")
        if self.usable_reps > self.total_reps:
            raise ValueError("usable_reps exceeds total_reps")
        if self.expected_supporting_samples == 0 and self.per_metric_coverage:
            raise ValueError("zero expected samples forbids nonempty coverage")
        return self


class PrototypeAssessment(MXRModel):
    status: Literal["matched", "partial", "unavailable"]
    policy_version: Optional[Str64] = None
    estimated_match: Optional[Annotated[FiniteFloat, Field(ge=0, le=100)]] = None
    included_components: list[Str64] = []
    omitted_components: list[Str64] = []
    missing_reasons: list[Annotated[str, Field(max_length=256)]] = []

    @model_validator(mode="after")
    def honest(self) -> Self:
        if self.estimated_match is not None:
            if self.status not in ("matched", "partial"):
                raise ValueError("estimated_match requires status matched/partial")
            if self.policy_version is None or not self.included_components:
                raise ValueError("estimated_match requires policy_version and included_components")
        if self.status == "unavailable":
            if self.estimated_match is not None:
                raise ValueError("unavailable status forbids estimated_match")
            if not self.missing_reasons:
                raise ValueError("unavailable status requires missing_reasons")
        return self


class PrototypeAnalysisResult(MXRModel):
    """0.3 prototype report; standalone, not a subclass of AnalysisResult."""

    schema_version: Literal["0.3.0"] = "0.3.0"
    analysis_id: Str128
    exercise: ExerciseId
    variant: Str64
    recipe_version: Str64
    analysis_scope: Literal["prototype_report"] = "prototype_report"
    reps: list[Rep] = []
    metrics: list[Metric] = []
    score: None = None
    detected_rep_count: Optional[NonNegInt] = None
    detected_rep_count_unavailable_reason: Optional[Annotated[str, Field(min_length=1, max_length=256)]] = None
    quality: ReportQuality
    prototype_assessment: PrototypeAssessment
    coaching: Optional[CoachingResult] = None
    warnings: list[Annotated[str, Field(max_length=256)]] = []
    provenance: dict[str, str] = {}

    @model_validator(mode="after")
    def consistent(self) -> Self:
        ids = [r.id for r in self.reps]
        if len(ids) != len(set(ids)):
            raise ValueError("rep ids must be unique")
        idset = set(ids)
        for m in self.metrics:
            if m.rep_id not in idset:
                raise ValueError("metric rep_id must reference an existing rep")
        if self.detected_rep_count is None:
            if not self.detected_rep_count_unavailable_reason:
                raise ValueError("null detected_rep_count requires an explicit reason")
        else:
            completed = sum(1 for r in self.reps if r.completion_status.value == "completed")
            if self.detected_rep_count != completed:
                raise ValueError("detected_rep_count must match completed reps")
        return self


def read_report(data: dict) -> AnalysisResult | PrototypeAnalysisResult:
    """Dispatch a raw report dict to the correct schema version."""
    version = data.get("schema_version")
    if version == "0.2.0":
        return AnalysisResult.model_validate(data)
    if version == "0.3.0":
        return PrototypeAnalysisResult.model_validate(data)
    raise ValueError(f"unknown report schema_version: {version!r}")


class PersonalProfile(MXRModel):
    display_name: Optional[Str64] = None
    preferred_load_unit: LoadUnit = "kg"
    created_at: UTCDateTime
    updated_at: UTCDateTime


class ProfilePatch(MXRModel):
    display_name: Optional[Str64] = None
    preferred_load_unit: Optional[LoadUnit] = None


class _LoadFields(MXRModel):
    load_value: Optional[FiniteFloat] = Field(default=None, ge=0)
    load_unit: Optional[LoadUnit] = None
    load_basis: Optional[Literal["total", "per_hand", "bodyweight"]] = None

    @model_validator(mode="after")
    def load_consistent(self) -> Self:
        if self.load_value is not None:
            if self.load_unit is None or self.load_basis is None:
                raise ValueError("load_value requires load_unit and load_basis")
            if self.load_basis == "bodyweight":
                raise ValueError("bodyweight basis forbids load_value")
        return self


class WorkoutSet(_LoadFields):
    id: Str128
    workout_id: Str128
    owner_id: Str128
    exercise_id: ExerciseId
    variant: Str64
    detected_rep_count: Optional[NonNegInt] = None
    logged_rep_count: Optional[NonNegInt] = None
    count_source: Literal["detected", "user", "manual"]
    notes: Optional[Annotated[str, Field(max_length=2000)]] = None
    analysis_id: Optional[Str128] = None
    performed_at: UTCDateTime
    created_at: UTCDateTime
    updated_at: UTCDateTime

    @model_validator(mode="after")
    def count_consistent(self) -> Self:
        if self.count_source == "detected":
            if self.analysis_id is None or self.detected_rep_count is None:
                raise ValueError("detected count_source requires analysis_id and detected_rep_count")
        return self


class SetCreate(_LoadFields):
    request_key: Str128
    exercise_id: ExerciseId
    variant: Str64
    logged_rep_count: Optional[NonNegInt] = None
    notes: Optional[Annotated[str, Field(max_length=2000)]] = None
    analysis_id: Optional[Str128] = None
    performed_at: UTCDateTime


class SetPatch(_LoadFields):
    logged_rep_count: Optional[NonNegInt] = None
    notes: Optional[Annotated[str, Field(max_length=2000)]] = None


class Workout(MXRModel):
    id: Str128
    owner_id: Str128
    name: Str128
    started_at: UTCDateTime
    created_at: UTCDateTime
    updated_at: UTCDateTime
    sets: list[WorkoutSet] = []


class WorkoutCreate(MXRModel):
    request_key: Str128
    name: Str128
    started_at: UTCDateTime


class RoutineExercise(MXRModel):
    exercise_id: ExerciseId
    variant: Str64
    planned_sets: Annotated[int, Field(ge=1, le=20, strict=True)]
    planned_reps: Optional[Annotated[int, Field(ge=1, le=100, strict=True)]] = None


class RoutineTemplate(MXRModel):
    id: Str128
    name: Str128
    exercises: list[RoutineExercise] = []


class ExerciseInfo(MXRModel):
    id: ExerciseId
    display_name: Str64
    variant: Str64
    supported_views: list[Str64] = []
    target_muscles: list[Str64] = []
    capabilities: list[Str64] = []
    reference_status: Literal["provisional", "unavailable"]
    profile_version: Optional[Str64] = None
