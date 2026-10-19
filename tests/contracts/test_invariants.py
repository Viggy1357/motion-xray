"""Reject misleading measurements at the public contract boundary."""

import pytest
from pydantic import ValidationError

from contracts.analysis import Metric, Rep
from contracts.pose import JointObservation
from contracts.scoring import ScoreBreakdown


@pytest.mark.parametrize("value,reason", [(None, None), (None, ""), (None, " "), (float("nan"), None), (float("inf"), None)])
def test_missing_or_nonfinite_measurement_rejected(value, reason):
    with pytest.raises(ValidationError):
        Metric(id="m1", rep_id="r1", value=value, reason=reason, unit="deg", dimensionality="3d", status="missing")


def test_measured_zero_is_distinct_from_missing():
    measured = Metric(id="m1", rep_id="r1", value=0, unit="deg", dimensionality="3d", status="ok")
    missing = Metric(id="m2", rep_id="r1", reason="insufficient_visibility", unit="deg", dimensionality="3d", status="missing")
    assert measured.value == 0 and measured.reason is None
    assert missing.value is None and missing.reason == "insufficient_visibility"


@pytest.mark.parametrize("change", [
    {"start_s": -1}, {"end_s": 0}, {"end_s": -1}, {"ordinal": 0},
    {"turnaround_start_s": 3}, {"turnaround_start_s": 1.5, "turnaround_end_s": 1},
    {"completion_status": "partial"},
])
def test_invalid_rep_rejected(change):
    data = dict(id="r1", ordinal=1, start_s=0, end_s=2, completion_status="completed", scorable=True)
    with pytest.raises(ValidationError):
        Rep(**(data | change))


@pytest.mark.parametrize("coverage", [-0.01, 1.01])
def test_metric_coverage_is_bounded(coverage):
    with pytest.raises(ValidationError):
        Metric(id="m1", rep_id="r1", value=0, unit="deg", dimensionality="3d", status="ok", coverage=coverage)


@pytest.mark.parametrize("change", [
    {"displayed_score": -1}, {"displayed_score": 101}, {"coverage": 1.01},
    {"component_weights": {"rom": 0.5}}, {"displayed_score": None},
])
def test_invalid_score_rejected(change):
    data = dict(profile_id="p1", profile_version="1", reference_version="1", raw_score=0, displayed_score=0)
    with pytest.raises(ValidationError):
        ScoreBreakdown(**(data | change))


def test_missing_score_preserves_reason():
    result = ScoreBreakdown(profile_id="p1", profile_version="1", reference_version="1", missing_reasons=["reference_unavailable"])
    assert result.displayed_score is None
    assert result.missing_reasons == ["reference_unavailable"]


def test_valid_joint_requires_coordinates():
    with pytest.raises(ValidationError):
        JointObservation(valid=True, interpolated=False)
    # Off-image coordinates remain valid observations rather than being clipped.
    assert JointObservation(valid=True, interpolated=False, xy=(-0.1, 1.2)).xy == (-0.1, 1.2)
