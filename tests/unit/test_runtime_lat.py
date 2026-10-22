"""Analytic tests for the deterministic lat runtime report."""

from __future__ import annotations

import math

import pytest

from contracts.pose import JointObservation, PoseFrame
from movement.runtime_lat import build_movement_report

HASH = "a" * 64
ANGLES = [
    140, 140, 140, 140, 120, 95, 95, 95, 95, 120,
    140, 140, 140, 140, 120, 95, 95, 95, 95, 120,
    140, 140, 140, 140,
]
KW = dict(
    analysis_id="ana-1", exercise_id="lat_pulldown", variant="cable_seated_bilateral",
    width=640, height=480, pose_sha256=HASH, processing_version="pose-v1",
)


def _joint(xy, xyz, valid=True):
    return JointObservation(xy=xy, xyz=xyz, valid=valid, interpolated=False)


def _frames(angles=ANGLES, invalid=(), drop_hip=False, left_invalid_even=False):
    frames = []
    for i, deg in enumerate(angles):
        th = math.radians(deg)
        wx, wy = math.sin(th), math.cos(th)
        joints = {}
        for s in ("left", "right"):
            valid = i not in invalid and not (s == "left" and left_invalid_even and i % 2 == 0)
            joints[f"{s}_shoulder"] = _joint((0.5, 0.3), (0.0, 1.0, 0.0))
            joints[f"{s}_elbow"] = _joint((0.5, 0.6), (0.0, 0.0, 0.0))
            joints[f"{s}_wrist"] = _joint((0.5 + 0.2 * wx, 0.6 - 0.2 * wy), (wx, wy, 0.0), valid)
            if not drop_hip:
                joints[f"{s}_hip"] = _joint((0.5, 0.9), (0.0, -1.0, 0.0))
        frames.append(PoseFrame(frame_index=i, timestamp_s=i * 0.05, joints=joints))
    return frames


def _metric(r, rep_id, key):
    return next(m for m in r.metrics if m.rep_id == rep_id and m.id == key)


def test_two_completed_cycles_count_and_timing():
    r = build_movement_report(_frames(), **KW)
    assert r.detected_rep_count == 2
    completed = [rep for rep in r.reps if rep.completion_status.value == "completed"]
    assert [rep.id for rep in completed] == ["rep-001", "rep-002"]
    assert completed[0].start_s == pytest.approx(0.0)
    assert completed[0].turnaround_start_s == pytest.approx(0.25)
    assert completed[0].end_s == pytest.approx(0.50)
    assert completed[1].start_s == pytest.approx(0.50)
    assert completed[1].end_s == pytest.approx(1.00)
    assert all(not rep.scorable for rep in r.reps)


def test_rom_and_observed_zero_torso():
    r = build_movement_report(_frames(), **KW)
    exc = _metric(r, "rep-001", "elbow_angle/estimated_3d/excursion")
    # Window [0.00, 0.50] observes 140..95 degrees; the fixed window-summary
    # arithmetic yields a 45-degree excursion for this analytic signal.
    assert exc.status == "observed" and exc.value == pytest.approx(45.0, abs=1e-6)
    assert exc.unit == "degrees" and exc.dimensionality == "estimated_3d"
    torso = _metric(r, "rep-001", "torso_axis_angle/projected_2d/excursion")
    assert torso.status == "observed" and torso.value == 0.0  # observed zero stays zero
    dur = _metric(r, "rep-001", "pull_duration_s")
    assert dur.value == pytest.approx(0.25) and dur.dimensionality == "temporal"
    assert dur.coverage == 1.0
    assert all(m.reference_interval is None and m.deviation is None for m in r.metrics)
    assert len([m for m in r.metrics if m.rep_id == "rep-001"]) == 32
    # Two completed cycles are usable; the trailing confirmed-HIGH fragment
    # (1.00..1.15, the reused return plateau that never descends again) is
    # retained as a partial entry, so total_reps counts all entries.
    assert r.quality.usable_reps == 2
    assert r.quality.total_reps == 3
    partial = [rep for rep in r.reps if rep.completion_status.value != "completed"]
    assert len(partial) == 1
    assert partial[0].start_s == pytest.approx(1.00)
    assert partial[0].end_s == pytest.approx(1.15)
    assert "incomplete_motion_span_not_counted" in partial[0].excluded_reasons
    assert r.quality.expected_supporting_samples == len(ANGLES)
    assert r.quality.valid_observed_samples == len(ANGLES)
    assert set(r.quality.per_metric_coverage) == {
        "elbow_angle/projected_2d", "elbow_angle/estimated_3d",
        "upper_arm_torso_angle/projected_2d", "upper_arm_torso_angle/estimated_3d",
        "torso_axis_angle/projected_2d",
    }


def test_repeat_dump_equality():
    a = build_movement_report(_frames(), **KW).model_dump_json()
    b = build_movement_report(_frames(), **KW).model_dump_json()
    assert a == b


def test_invalid_sample_resets_no_bridging():
    # Sample 7 (t=0.35) sits inside the first LOW plateau; its invalid angle
    # interrupts the first of the two cycles. The second cycle is unaffected
    # and must survive; the interrupted attempt is never bridged across the gap.
    r = build_movement_report(_frames(invalid={7}), **KW)
    assert r.detected_rep_count == 1
    completed = [rep for rep in r.reps if rep.completion_status.value == "completed"]
    assert len(completed) == 1
    # The surviving second cycle starts fresh at the next confirmed HIGH
    # plateau after the invalid sample, not by bridging over it.
    assert completed[0].start_s == pytest.approx(0.50)
    assert completed[0].turnaround_start_s == pytest.approx(0.75)
    assert completed[0].end_s == pytest.approx(1.00)
    partial = [rep for rep in r.reps if rep.completion_status.value != "completed"]
    assert partial, "expected retained partial motion fragments"
    assert all(
        "incomplete_motion_span_not_counted" in rep.excluded_reasons for rep in partial
    )
    # The interrupted first attempt ends at the last valid sample before the
    # gap; no rep span crosses the invalid sample at t=0.35.
    first_partial = min(partial, key=lambda rep: rep.start_s)
    assert first_partial.start_s == pytest.approx(0.0)
    assert first_partial.end_s == pytest.approx(0.30)
    assert all(
        not (rep.start_s < 7 * 0.05 < rep.end_s) for rep in r.reps
    ), "no span may bridge the invalid sample"
    assert not any(m.rep_id in {p.id for p in partial} for m in r.metrics)
    assert any(w.startswith("PARTIAL_MOTION") for w in r.warnings)
    assert r.quality.total_reps == len(r.reps)


def test_missing_torso_is_missing_not_zero():
    r = build_movement_report(_frames(drop_hip=True), **KW)
    torso = _metric(r, "rep-001", "torso_axis_angle/projected_2d/excursion")
    assert torso.value is None and torso.status == "missing"
    assert torso.reason and torso.reason != ""
    assert r.quality.usable_reps == 0


def test_side_tie_prefers_left():
    r = build_movement_report(_frames(), **KW)
    assert r.provenance["side"] == "left"
    assert all(rep.side == "left" for rep in r.reps)


def test_side_right_when_right_has_more_valid():
    r = build_movement_report(_frames(left_invalid_even=True), **KW)
    assert r.provenance["side"] == "right"


def test_empty_frames_count_unavailable():
    r = build_movement_report([], **KW)
    assert r.detected_rep_count is None
    assert r.detected_rep_count_unavailable_reason
    assert r.quality.expected_supporting_samples == 0
    assert r.quality.per_metric_coverage == {}


def test_other_contract_exercise_profile_unavailable():
    r = build_movement_report(_frames(), **{**KW, "exercise_id": "squat", "variant": "bodyweight"})
    assert r.detected_rep_count is None
    assert r.detected_rep_count_unavailable_reason == "exercise_profile_unavailable"
    assert r.reps == [] and r.metrics == []
    assert r.quality.expected_supporting_samples == 0
    assert r.quality.valid_observed_samples == 0
    assert r.quality.per_metric_coverage == {}
    assert r.quality.usable_reps == 0 and r.quality.total_reps == 0
    assert r.quality.missing_reasons == ["exercise_profile_unavailable"]
    # Generic unavailable recipe: no lat policy/axis/threshold provenance.
    assert r.recipe_version == "movement-unavailable-v1"
    assert "axis" not in r.provenance
    assert "config_sha256" not in r.provenance
    assert "segment_config_version" not in r.provenance
    assert "pipeline_version" not in r.provenance
    assert r.prototype_assessment.status == "unavailable"
    assert r.prototype_assessment.policy_version is None
    assert any(w.startswith("EXERCISE_PROFILE_UNAVAILABLE") for w in r.warnings)


def test_unknown_exercise_rejected():
    with pytest.raises(ValueError):
        build_movement_report(_frames(), **{**KW, "exercise_id": "lateral_raise"})
    with pytest.raises(ValueError):
        build_movement_report(_frames(), **{**KW, "exercise_id": "bench_press"})


def test_unsupported_lat_variant_rejected():
    with pytest.raises(ValueError):
        build_movement_report(_frames(), **{**KW, "variant": "wide_grip"})


def test_bad_frame_ordering_rejected():
    frames = _frames()
    frames[3], frames[5] = frames[5], frames[3]
    with pytest.raises(ValueError):
        build_movement_report(frames, **KW)


def test_bad_hash_and_dimensions_rejected():
    with pytest.raises(ValueError):
        build_movement_report(_frames(), **{**KW, "pose_sha256": "zz"})
    with pytest.raises(ValueError):
        build_movement_report(_frames(), **{**KW, "width": 0})
    with pytest.raises(ValueError):
        build_movement_report(_frames(), **{**KW, "width": True})
    with pytest.raises(ValueError):
        build_movement_report(_frames(), **{**KW, "height": 2000})
    with pytest.raises(ValueError):
        build_movement_report(_frames(), **{**KW, "processing_version": ""})


def test_no_scores_while_benchmark_pending():
    r = build_movement_report(_frames(), **KW)
    assert r.score is None
    pa = r.prototype_assessment
    assert pa.status == "unavailable" and pa.estimated_match is None
    assert pa.policy_version == "lat-component-policy-v1"
    assert set(pa.omitted_components) == {
        "torso_start", "torso_dynamic", "arm_rom", "shoulder_drive", "bar_endpoint"
    }
    assert {"reference_pending", "view_unreviewed", "bar_endpoint_unavailable"} <= set(
        pa.missing_reasons
    )
    assert r.coaching is not None and r.coaching.status.value == "unavailable"
    assert any(w.startswith("PROVISIONAL_CYCLE_CANDIDATES") for w in r.warnings)
    assert any(w.startswith("IMAGE_AXIS_NOT_GRAVITY") for w in r.warnings)
    prov = r.provenance
    assert prov["pose_sha256"] == HASH and prov["processing_version"] == "pose-v1"
    assert len(prov["config_sha256"]) == 64
    assert prov["segment_config_version"] == "lat-runtime-v1"
    assert prov["pipeline_version"] == "hm04-lat-v1"
    assert prov["axis"] == "image_up_unverified_not_gravity"
    assert prov["count_source"] == "automatic_segmentation_signal_only"
