from __future__ import annotations

import json
from pathlib import Path

import pytest

from movement.observations import AngleObservation
from movement.rep_observations import Component, RepWindow, measure_rep


def obs(
    metric: str,
    space: str,
    timestamp_s: float,
    value: float | None,
    reason: str | None = None,
    side: str = "left",
    frame_index: int = 0,
) -> AngleObservation:
    return AngleObservation(
        frame_index=frame_index,
        timestamp_s=timestamp_s,
        side=side,
        metric=metric,
        space=space,  # type: ignore[arg-type]
        value=value,
        reason=reason,
    )


def rep(start: float = 0.0, bottom: float = 0.5, end: float = 1.0, side: str = "left") -> RepWindow:
    return RepWindow(rep_id="r1", side=side, start_s=start, bottom_s=bottom, end_s=end)


def test_rep_window_validation() -> None:
    with pytest.raises(ValueError):
        RepWindow(rep_id="", side="left", start_s=0.0, bottom_s=0.5, end_s=1.0)
    with pytest.raises(ValueError):
        RepWindow(rep_id="r", side="left", start_s=0.0, bottom_s=0.0, end_s=1.0)
    with pytest.raises(ValueError):
        RepWindow(rep_id="r", side="left", start_s=0.0, bottom_s=0.5, end_s=0.5)
    with pytest.raises(ValueError):
        RepWindow(rep_id="r", side="left", start_s=True, bottom_s=0.5, end_s=1.0)  # type: ignore[arg-type]


def test_measure_rep_happy_path_fixture() -> None:
    fixture_path = Path(__file__).parent.parent / "fixtures" / "movement" / "rep-observations-v1.json"
    data = json.loads(fixture_path.read_text())
    assert data["version"] == "rep-observations-v1"
    samples = [AngleObservation(**o) for o in data["observations"]]
    label = RepWindow(**data["label"])
    result = measure_rep(samples, label, max_gap_s=data["max_gap_s"])
    assert len(result) == 32
    assert result["pull_duration_s"].value == pytest.approx(0.5, abs=1e-9)
    assert result["return_duration_s"].value == pytest.approx(0.5, abs=1e-9)
    assert result["torso_axis_angle/projected_2d/start"].value == pytest.approx(10.0, abs=1e-9)
    assert result["torso_axis_angle/projected_2d/bottom"].value == pytest.approx(30.0, abs=1e-9)
    assert result["torso_axis_angle/projected_2d/end"].value == pytest.approx(10.0, abs=1e-9)
    assert result["torso_axis_angle/projected_2d/pull_change"].value == pytest.approx(20.0, abs=1e-9)
    assert result["torso_axis_angle/projected_2d/pull_excursion"].value == pytest.approx(20.0, abs=1e-9)
    assert result["torso_axis_angle/projected_2d/excursion"].value == pytest.approx(20.0, abs=1e-9)
    assert result["elbow_angle/projected_2d/minimum"].value == pytest.approx(70.0, abs=1e-9)
    assert result["elbow_angle/projected_2d/maximum"].value == pytest.approx(160.0, abs=1e-9)
    assert result["elbow_angle/projected_2d/excursion"].value == pytest.approx(90.0, abs=1e-9)
    assert result["upper_arm_torso_angle/projected_2d/minimum"].value == pytest.approx(30.0, abs=1e-9)
    assert result["upper_arm_torso_angle/projected_2d/maximum"].value == pytest.approx(150.0, abs=1e-9)
    assert result["upper_arm_torso_angle/projected_2d/excursion"].value == pytest.approx(120.0, abs=1e-9)
    for key in result:
        if result[key].value is None:
            assert result[key].reason is not None


def test_measure_rep_missing_series_null_not_zero() -> None:
    samples = [
        obs("torso_axis_angle", "projected_2d", 0.0, 10.0),
        obs("torso_axis_angle", "projected_2d", 0.5, 30.0),
        obs("torso_axis_angle", "projected_2d", 1.0, 10.0),
    ]
    result = measure_rep(samples, rep(), max_gap_s=0.5)
    assert result["elbow_angle/projected_2d/start"].value is None
    assert result["elbow_angle/projected_2d/start"].reason == "missing_series"


def test_measure_rep_wrong_side_rejected() -> None:
    samples = [
        obs("torso_axis_angle", "projected_2d", 0.0, 10.0, side="right"),
        obs("torso_axis_angle", "projected_2d", 0.5, 30.0, side="right"),
        obs("torso_axis_angle", "projected_2d", 1.0, 10.0, side="right"),
    ]
    with pytest.raises(ValueError):
        measure_rep(samples, rep(side="left"), max_gap_s=0.5)


def test_measure_rep_duplicate_pts_rejected() -> None:
    samples = [
        obs("torso_axis_angle", "projected_2d", 0.0, 10.0),
        obs("torso_axis_angle", "projected_2d", 0.0, 30.0),
    ]
    with pytest.raises(ValueError):
        measure_rep(samples, rep(), max_gap_s=0.5)


def test_measure_rep_timestamps_not_increasing() -> None:
    samples = [
        obs("torso_axis_angle", "projected_2d", 0.5, 30.0),
        obs("torso_axis_angle", "projected_2d", 0.0, 10.0),
    ]
    with pytest.raises(ValueError):
        measure_rep(samples, rep(), max_gap_s=0.5)


def test_measure_rep_invalid_nearest_preserved() -> None:
    samples = [
        obs("elbow_angle", "projected_2d", 0.0, 160.0),
        obs("elbow_angle", "projected_2d", 0.5, None, reason="missing_joint"),
        obs("elbow_angle", "projected_2d", 1.0, 160.0),
    ]
    result = measure_rep(samples, rep(), max_gap_s=0.5)
    assert result["elbow_angle/projected_2d/bottom"].value is None
    assert result["elbow_angle/projected_2d/bottom"].reason == "missing_joint"
    assert result["elbow_angle/projected_2d/bottom"].actual_pts_s == pytest.approx(0.5, abs=1e-9)


def test_measure_rep_no_sample_in_tolerance() -> None:
    samples = [obs("elbow_angle", "projected_2d", 0.0, 160.0)]
    result = measure_rep(samples, rep(), max_gap_s=0.1)
    assert result["elbow_angle/projected_2d/bottom"].value is None
    assert result["elbow_angle/projected_2d/bottom"].reason == "no_sample_in_tolerance"
    assert result["elbow_angle/projected_2d/bottom"].actual_pts_s is None


def test_measure_rep_gap_bad_span_endpoints_raw() -> None:
    samples = [
        obs("elbow_angle", "projected_2d", 0.0, 160.0),
        obs("elbow_angle", "projected_2d", 1.0, 160.0),
    ]
    result = measure_rep(samples, rep(), max_gap_s=0.5)
    assert result["elbow_angle/projected_2d/start"].value == pytest.approx(160.0, abs=1e-9)
    assert result["elbow_angle/projected_2d/end"].value == pytest.approx(160.0, abs=1e-9)
    assert result["elbow_angle/projected_2d/minimum"].value is None
    assert result["elbow_angle/projected_2d/minimum"].reason == "timestamp_gap"


def test_measure_rep_partial_boundary() -> None:
    samples = [obs("elbow_angle", "projected_2d", 0.5, 70.0)]
    result = measure_rep(samples, rep(), max_gap_s=0.49)
    assert result["elbow_angle/projected_2d/bottom"].value == pytest.approx(70.0, abs=1e-9)
    assert result["elbow_angle/projected_2d/start"].value is None
    assert result["elbow_angle/projected_2d/start"].reason == "no_sample_in_tolerance"


def test_measure_rep_wrapped_torso_2_degrees() -> None:
    samples = [
        obs("torso_axis_angle", "projected_2d", 0.0, 179.0),
        obs("torso_axis_angle", "projected_2d", 0.5, -179.0),
        obs("torso_axis_angle", "projected_2d", 1.0, 179.0),
    ]
    result = measure_rep(samples, rep(), max_gap_s=0.5)
    assert result["torso_axis_angle/projected_2d/pull_change"].value == pytest.approx(2.0, abs=1e-9)
    assert result["torso_axis_angle/projected_2d/pull_excursion"].value == pytest.approx(2.0, abs=1e-9)


def test_measure_rep_ambiguous_180() -> None:
    samples = [
        obs("torso_axis_angle", "projected_2d", 0.0, 0.0),
        obs("torso_axis_angle", "projected_2d", 0.5, 180.0),
        obs("torso_axis_angle", "projected_2d", 1.0, 0.0),
    ]
    result = measure_rep(samples, rep(), max_gap_s=0.5)
    assert result["torso_axis_angle/projected_2d/pull_change"].value is None
    assert result["torso_axis_angle/projected_2d/pull_change"].reason == "ambiguous_rotation"


def test_measure_rep_no_source_mutation() -> None:
    samples = [
        obs("torso_axis_angle", "projected_2d", 0.0, 10.0),
        obs("torso_axis_angle", "projected_2d", 0.5, 30.0),
        obs("torso_axis_angle", "projected_2d", 1.0, 10.0),
    ]
    original = [o for o in samples]
    measure_rep(samples, rep(), max_gap_s=0.5)
    assert samples == original


def test_measure_rep_rejects_bool_and_non_finite_max_gap() -> None:
    samples = [obs("torso_axis_angle", "projected_2d", 0.0, 10.0)]
    with pytest.raises(ValueError):
        measure_rep(samples, rep(), max_gap_s=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        measure_rep(samples, rep(), max_gap_s=float("inf"))
    with pytest.raises(ValueError):
        measure_rep(samples, rep(), max_gap_s=0.0)


def test_measure_rep_rejects_unexpected_metric_or_space() -> None:
    samples = [obs("knee_angle", "projected_2d", 0.0, 10.0)]
    with pytest.raises(ValueError):
        measure_rep(samples, rep(), max_gap_s=0.5)
    samples2 = [obs("elbow_angle", "estimated_2d", 0.0, 10.0)]  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        measure_rep(samples2, rep(), max_gap_s=0.5)


def test_component_validation() -> None:
    with pytest.raises(ValueError):
        Component(value=None, reason=None, unit="degrees")
    with pytest.raises(ValueError):
        Component(value=10.0, reason="x", unit="degrees")
    with pytest.raises(ValueError):
        Component(value=float("inf"), reason=None, unit="degrees")
    with pytest.raises(ValueError):
        Component(value=10.0, reason=None, unit="radians")


def test_measure_rep_returns_exact_32_keys() -> None:
    samples = [
        obs("torso_axis_angle", "projected_2d", 0.0, 10.0),
        obs("elbow_angle", "projected_2d", 0.0, 160.0),
        obs("elbow_angle", "estimated_3d", 0.0, 160.0),
        obs("upper_arm_torso_angle", "projected_2d", 0.0, 150.0),
        obs("upper_arm_torso_angle", "estimated_3d", 0.0, 150.0),
    ]
    result = measure_rep(samples, rep(), max_gap_s=0.5)
    assert len(result) == 32
    assert set(result.keys()) == {
        "pull_duration_s",
        "return_duration_s",
        "torso_axis_angle/projected_2d/start",
        "torso_axis_angle/projected_2d/bottom",
        "torso_axis_angle/projected_2d/end",
        "torso_axis_angle/projected_2d/pull_change",
        "torso_axis_angle/projected_2d/pull_excursion",
        "torso_axis_angle/projected_2d/excursion",
        "elbow_angle/projected_2d/start",
        "elbow_angle/projected_2d/bottom",
        "elbow_angle/projected_2d/end",
        "elbow_angle/projected_2d/minimum",
        "elbow_angle/projected_2d/maximum",
        "elbow_angle/projected_2d/excursion",
        "elbow_angle/estimated_3d/start",
        "elbow_angle/estimated_3d/bottom",
        "elbow_angle/estimated_3d/end",
        "elbow_angle/estimated_3d/minimum",
        "elbow_angle/estimated_3d/maximum",
        "elbow_angle/estimated_3d/excursion",
        "upper_arm_torso_angle/projected_2d/start",
        "upper_arm_torso_angle/projected_2d/bottom",
        "upper_arm_torso_angle/projected_2d/end",
        "upper_arm_torso_angle/projected_2d/minimum",
        "upper_arm_torso_angle/projected_2d/maximum",
        "upper_arm_torso_angle/projected_2d/excursion",
        "upper_arm_torso_angle/estimated_3d/start",
        "upper_arm_torso_angle/estimated_3d/bottom",
        "upper_arm_torso_angle/estimated_3d/end",
        "upper_arm_torso_angle/estimated_3d/minimum",
        "upper_arm_torso_angle/estimated_3d/maximum",
        "upper_arm_torso_angle/estimated_3d/excursion",
    }
