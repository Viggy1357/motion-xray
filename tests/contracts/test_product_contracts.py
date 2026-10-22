"""Offline tests for the additive product contracts (0.3 prototype report)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from contracts.analysis import AnalysisResult, Metric, Rep
from contracts.product import (
    ExerciseInfo,
    PrototypeAnalysisResult,
    PrototypeAssessment,
    ReportQuality,
    SetCreate,
    SetPatch,
    WorkoutSet,
    read_report,
)

NOW = datetime(2024, 1, 1, tzinfo=timezone.utc)


def rep(rid="r1", status="completed"):
    return Rep(id=rid, ordinal=1, start_s=0.0, end_s=1.0,
               completion_status=status, scorable=status == "completed")


def metric(rid="r1", value=1.0):
    return Metric(id="m1", rep_id=rid, value=value, unit="deg",
                  dimensionality="angle", status="ok")


def quality(**kw):
    base = dict(expected_supporting_samples=10, valid_observed_samples=8,
                usable_reps=1, total_reps=1)
    base.update(kw)
    return ReportQuality(**base)


def assessment(**kw):
    base = dict(status="matched", policy_version="p1", estimated_match=80.0,
                included_components=["depth"])
    base.update(kw)
    return PrototypeAssessment(**base)


def report(**kw):
    base = dict(analysis_id="a1", exercise="squat", variant="bodyweight",
                recipe_version="r1", reps=[rep()], metrics=[metric()],
                detected_rep_count=1, quality=quality(),
                prototype_assessment=assessment())
    base.update(kw)
    return PrototypeAnalysisResult(**base)


def test_valid_prototype_report_roundtrip():
    r = report()
    assert r.score is None and r.analysis_scope == "prototype_report"
    assert PrototypeAnalysisResult.model_validate(r.model_dump()) == r


def test_detected_count_none_requires_reason_and_zero_is_distinct():
    with pytest.raises(ValidationError):
        report(detected_rep_count=None)
    r = report(reps=[], metrics=[], detected_rep_count=0,
               quality=quality(usable_reps=0, total_reps=0))
    assert r.detected_rep_count == 0


def test_detected_count_must_match_completed_reps():
    with pytest.raises(ValidationError):
        report(detected_rep_count=2)
    r = report(reps=[rep("r1"), rep("r2", "partial")], detected_rep_count=1,
               quality=quality(usable_reps=1, total_reps=2))
    assert r.detected_rep_count == 1


def test_unique_rep_ids_and_metric_reference():
    with pytest.raises(ValidationError):
        report(reps=[rep("r1"), rep("r1")], detected_rep_count=2)
    with pytest.raises(ValidationError):
        report(metrics=[metric("nope")])


def test_quality_bounds_and_zero_expected_forbids_coverage():
    with pytest.raises(ValidationError):
        quality(valid_observed_samples=11)
    with pytest.raises(ValidationError):
        quality(usable_reps=2, total_reps=1)
    with pytest.raises(ValidationError):
        quality(expected_supporting_samples=0, valid_observed_samples=0,
                per_metric_coverage={"m": 0.5})
    with pytest.raises(ValidationError):
        quality(per_metric_coverage={"m": 1.5})


def test_assessment_score_policy_and_unavailable_rules():
    with pytest.raises(ValidationError):
        assessment(status="unavailable", estimated_match=None, missing_reasons=[])
    a = assessment(estimated_match=None)
    assert a.estimated_match is None
    with pytest.raises(ValidationError):
        assessment(policy_version=None)
    with pytest.raises(ValidationError):
        assessment(included_components=[])
    with pytest.raises(ValidationError):
        assessment(status="unavailable")
    with pytest.raises(ValidationError):
        assessment(status="unavailable", missing_reasons=["no ref"])
    u = assessment(status="unavailable", estimated_match=None,
                   policy_version=None, included_components=[],
                   missing_reasons=["no reference profile"])
    assert u.status == "unavailable"


def test_read_report_dispatch_and_unknown_rejected():
    old = AnalysisResult(analysis_id="a", exercise="squat")
    assert isinstance(read_report(old.model_dump()), AnalysisResult)
    assert isinstance(read_report(report().model_dump()), PrototypeAnalysisResult)
    with pytest.raises(ValueError):
        read_report({"schema_version": "9.9.9"})
    with pytest.raises(ValueError):
        read_report({})


def test_old_0_2_schema_unaffected():
    r = AnalysisResult(analysis_id="a", exercise="squat", score=55.0)
    assert r.schema_version == "0.2.0" and r.score == 55.0
    with pytest.raises(ValidationError):
        AnalysisResult(analysis_id="a", exercise="squat", score=float("nan"))


def test_workout_set_detected_source_requires_analysis():
    base = dict(id="s1", workout_id="w1", owner_id="o1", exercise_id="squat",
                variant="bw", count_source="detected", performed_at=NOW,
                created_at=NOW, updated_at=NOW)
    with pytest.raises(ValidationError):
        WorkoutSet(**base, detected_rep_count=5)
    s = WorkoutSet(**base, detected_rep_count=5, analysis_id="a1")
    assert s.detected_rep_count == 5


def test_load_value_requires_unit_basis_and_bodyweight_forbids_value():
    base = dict(request_key="k1", exercise_id="squat", variant="bw", performed_at=NOW)
    with pytest.raises(ValidationError):
        SetCreate(**base, load_value=20.0)
    with pytest.raises(ValidationError):
        SetCreate(**base, load_value=20.0, load_unit="kg", load_basis="bodyweight")
    with pytest.raises(ValidationError):
        SetCreate(**base, load_value=-1.0, load_unit="kg", load_basis="total")
    ok = SetCreate(**base, load_value=20.0, load_unit="kg", load_basis="total")
    assert ok.load_value == 20.0


def test_set_create_forbids_client_ownership_and_detected_fields():
    base = dict(request_key="k1", exercise_id="squat", variant="bw", performed_at=NOW)
    for bad in ("owner_id", "id", "detected_rep_count", "count_source"):
        with pytest.raises(ValidationError):
            SetCreate(**base, **{bad: "x" if bad != "detected_rep_count" else 3})


def test_set_patch_limited_fields_and_strict_ints():
    p = SetPatch(logged_rep_count=10, notes="ok")
    assert p.logged_rep_count == 10
    with pytest.raises(ValidationError):
        SetPatch(logged_rep_count=True)
    with pytest.raises(ValidationError):
        SetPatch(logged_rep_count=-1)
    with pytest.raises(ValidationError):
        SetPatch(exercise_id="squat")


def test_bool_and_nonfinite_rejected():
    with pytest.raises(ValidationError):
        quality(expected_supporting_samples=True)
    with pytest.raises(ValidationError):
        assessment(estimated_match=float("inf"))
    with pytest.raises(ValidationError):
        report(detected_rep_count=1.0)


def test_exercise_info_and_naive_datetime_rejected():
    info = ExerciseInfo(id="squat", display_name="Squat", variant="bw",
                        reference_status="provisional")
    assert info.reference_status == "provisional"
    with pytest.raises(ValidationError):
        SetCreate(request_key="k", exercise_id="squat", variant="bw",
                  performed_at=datetime(2024, 1, 1))
    with pytest.raises(ValidationError):
        SetCreate(request_key="k", exercise_id="bench", variant="bw", performed_at=NOW)
