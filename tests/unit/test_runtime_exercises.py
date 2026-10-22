"""Offline analytic tests for the generic exercise runtime and assessment."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from contracts.enums import CompletionStatus
from movement import runtime_exercises as rt

SHA = "a" * 64
VARIANTS = {
    "dumbbell_curl": "standing_both_arms",
    "squat": "bodyweight",
    "incline_chest_press": "incline_dumbbell_bilateral",
}
SIGNAL = {
    "dumbbell_curl": ("elbow_angle", "estimated_3d"),
    "squat": ("knee_angle", "estimated_3d"),
    "incline_chest_press": ("elbow_angle", "estimated_3d"),
}
REPO_ROOT = Path(__file__).resolve().parents[2]


def _pattern(high=170.0, low=60.0):
    """H-L-H-L-H plateaus: 4 samples each at 0.05s spacing (0.15s dwell)."""
    seq = [high] * 4 + [low] * 4 + [high] * 4 + [low] * 4 + [high] * 4
    return [(0.05 * i, v) for i, v in enumerate(seq)]


PATTERN = _pattern()


def _load_cal():
    spec = importlib.util.spec_from_file_location(
        "calibrate_exercises", REPO_ROOT / "scripts" / "calibrate_exercises.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _obs(metric, space, value, t):
    return SimpleNamespace(
        metric=metric, space=space, value=value, unit="degrees",
        timestamp_s=t, side=None, reason=None if value is not None else "missing_geometry",
    )


def _install(monkeypatch, exercise, pattern=None, fixed=20.0):
    profile = rt._PROFILES[exercise].PROFILE
    groups = rt._groups(profile)
    sig_m, sig_s = SIGNAL[exercise]
    sig = dict(pattern if pattern is not None else PATTERN)

    def fake(mod, frame, side, width, height):
        t = frame.timestamp_s
        out = []
        for m, s, _ in groups:
            o = _obs(m, s, sig.get(t) if (m, s) == (sig_m, sig_s) else fixed, t)
            o.side = side
            out.append(o)
        return out

    monkeypatch.setattr(rt, "_observe_profile", fake)
    monkeypatch.setattr(rt, "_load_profile_config", lambda p: p)
    times = sorted(sig)
    return [SimpleNamespace(frame_index=i, timestamp_s=t) for i, t in enumerate(times)]


def _build(frames, exercise):
    return rt.build_exercise_report(
        frames, analysis_id="t1", exercise_id=exercise, variant=VARIANTS[exercise],
        width=640, height=480, pose_sha256=SHA, processing_version="pv1",
    )


@pytest.mark.parametrize("exercise", list(VARIANTS))
def test_two_cycles_detected(monkeypatch, exercise):
    frames = _install(monkeypatch, exercise)
    report = _build(frames, exercise)
    assert report.detected_rep_count == 2
    completed = [r for r in report.reps if r.completion_status == CompletionStatus.COMPLETED]
    assert len(completed) == 2
    ids = {m.id for m in report.metrics}
    assert "lower_phase_duration_s" in ids and "return_phase_duration_s" in ids
    for key in rt.COMPARISON_KEYS[exercise]:
        assert key in ids
    if exercise == "squat":
        assert any(m.id.startswith("knee_angle") for m in report.metrics)
        assert any(m.id.startswith("hip_angle") for m in report.metrics)
        assert not any(m.id.startswith("elbow_angle") for m in report.metrics)
    else:
        assert any(m.id.startswith("elbow_angle") for m in report.metrics)
        assert not any(m.id.startswith("knee_angle") for m in report.metrics)
    # metric side matches the selected rep side; keys unique per rep
    for r in report.reps:
        rep_metrics = [m for m in report.metrics if m.rep_id == r.id]
        assert all(m.side == r.side for m in rep_metrics)
        assert len({m.id for m in rep_metrics}) == len(rep_metrics)
    assert report.prototype_assessment.status == "unavailable"
    assert "reference_calibration_pending" in report.prototype_assessment.missing_reasons


def test_knee_signal_distinct_from_elbow(monkeypatch):
    frames = _install(monkeypatch, "squat")
    report = _build(frames, "squat")
    assert report.provenance["automatic_window_origin"] == "find_cycles:estimated_3d_knee_angle_signal"


def test_unknown_exercise_profile_rejected():
    with pytest.raises(ValueError):
        rt.build_exercise_report(
            [], analysis_id="t", exercise_id="lat_pulldown", variant="x",
            width=640, height=480, pose_sha256=SHA, processing_version="pv1",
        )


def test_null_signal_unavailable(monkeypatch):
    pattern = [(0.05 * i, None) for i in range(20)]
    frames = _install(monkeypatch, "dumbbell_curl", pattern=pattern)
    report = _build(frames, "dumbbell_curl")
    assert report.detected_rep_count is None
    assert report.detected_rep_count_unavailable_reason == "insufficient_valid_signal_samples"


def test_null_group_metrics_missing_with_reason(monkeypatch):
    frames = _install(monkeypatch, "squat", fixed=None)
    report = _build(frames, "squat")
    torso = [m for m in report.metrics if m.id == "torso_axis_angle/projected_2d/excursion"]
    assert torso
    assert all(m.value is None and m.status == "missing" for m in torso)
    assert all(m.reason == "no_valid_samples_in_window" for m in torso)
    assert all(m.coverage == 0.0 for m in torso)


def test_gap_not_bridged(monkeypatch):
    # 1.0s gap (> max_gap_s) inside the return phase breaks the cycle.
    pattern = [(0.05 * i, 170.0) for i in range(0, 4)] + [(0.05 * i, 60.0) for i in range(4, 8)]
    pattern += [(1.5 + 0.05 * i, 170.0) for i in range(0, 4)]
    frames = _install(monkeypatch, "dumbbell_curl", pattern=pattern)
    report = _build(frames, "dumbbell_curl")
    assert report.detected_rep_count == 0
    assert any(r.completion_status == CompletionStatus.PARTIAL for r in report.reps)


def test_bad_variant_rejected(monkeypatch):
    frames = _install(monkeypatch, "squat")
    with pytest.raises(ValueError):
        rt.build_exercise_report(
            frames, analysis_id="t", exercise_id="squat", variant="barbell_back",
            width=640, height=480, pose_sha256=SHA, processing_version="pv1",
        )


def _fake_config(exercise):
    bands = {}
    for k in rt.COMPARISON_KEYS[exercise]:
        bands[k] = {"lower": 0.0, "upper": 200.0, "valid_count": 3, "unit": "degrees"}
    return {
        "version": "exercise-reference-bands-v1",
        "author": False,
        "review": "unreviewed",
        "normalization_degrees": 30,
        "min_coverage": 0.8,
        "references": {
            exercise: {
                "primary": True, "reference_name": "fake-ref",
                "source_url": "file:///fake", "reference_id": "r1",
                "view_id": "front", "rep_count": 3, "valid_reference_cycles": 3,
                "bands": bands,
            }
        },
    }


@pytest.mark.parametrize("exercise", list(VARIANTS))
def test_assessment_with_fake_bands(monkeypatch, exercise):
    frames = _install(monkeypatch, exercise)
    report = _build(frames, exercise)
    assessed = rt.apply_reference_assessment(report, config=_fake_config(exercise))
    assert assessed.prototype_assessment.status == "partial"
    assert assessed.prototype_assessment.estimated_match == pytest.approx(100.0)
    assert assessed.score is None  # top-level technique score never produced
    assert assessed.prototype_assessment.policy_version == "exercise-reference-bands-v1"
    assert "view_unreviewed" in assessed.prototype_assessment.missing_reasons
    assert "view_unreviewed" in assessed.prototype_assessment.omitted_components
    prov = assessed.provenance
    assert prov["match_aggregation"] == "equal_metric_mean_per_cycle_then_cycle_mean"
    assert prov["match_normalization_degrees"] == "30"
    assert prov["match_coverage_threshold"] == "0.8"
    assert prov["matched_cycles"] == "2"
    assert prov["omitted_cycle_count"] == "0"
    assert prov["reference_name"] == "fake-ref"
    assert prov["reference_id"] == "r1"
    assert prov["reference_view_id"] == "front"
    assert prov["reference_rep_count"] == "3"
    assert prov["calibration_status"] == "unreviewed"
    assert prov["reference_band_basis"] == "observed_min_max_not_tolerance"
    assert prov["experimental_policy_version"] == "exercise-reference-bands-v1"
    assert len(prov["experimental_policy_hash"]) == 64
    assert prov["reference_source_url"] == "file:///fake"
    # original report untouched
    assert report.prototype_assessment.status == "unavailable"
    assert all(m.deviation is None for m in report.metrics)


def test_assessment_signed_deviation_below_band(monkeypatch):
    frames = _install(monkeypatch, "dumbbell_curl")
    report = _build(frames, "dumbbell_curl")
    cfg = _fake_config("dumbbell_curl")
    # torso excursion is constantly 0.0; band [5, 10] puts the value below.
    cfg["references"]["dumbbell_curl"]["bands"]["torso_axis_angle/projected_2d/excursion"] = {
        "lower": 5.0, "upper": 10.0, "valid_count": 2, "unit": "degrees",
    }
    assessed = rt.apply_reference_assessment(report, config=cfg)
    m = [m for m in assessed.metrics if m.id == "torso_axis_angle/projected_2d/excursion"][0]
    assert m.deviation == pytest.approx(-5.0)  # signed: negative below
    assert m.reference_interval == (5.0, 10.0)
    assert assessed.prototype_assessment.estimated_match < 100.0


def test_assessment_signed_deviation_above_band(monkeypatch):
    frames = _install(monkeypatch, "dumbbell_curl")
    report = _build(frames, "dumbbell_curl")
    cfg = _fake_config("dumbbell_curl")
    # elbow end is ~170 (high plateau); band [0, 0] puts the value above.
    cfg["references"]["dumbbell_curl"]["bands"]["elbow_angle/estimated_3d/end"] = {
        "lower": 0.0, "upper": 0.0, "valid_count": 2, "unit": "degrees",
    }
    assessed = rt.apply_reference_assessment(report, config=cfg)
    m = [m for m in assessed.metrics if m.id == "elbow_angle/estimated_3d/end"][0]
    assert m.deviation is not None and m.deviation > 0  # signed: positive above
    assert assessed.prototype_assessment.estimated_match < 100.0


def test_assessment_pending_without_config(monkeypatch):
    frames = _install(monkeypatch, "squat")
    report = _build(frames, "squat")
    monkeypatch.setattr(rt, "_load_baseline", lambda: None)
    assessed = rt.apply_reference_assessment(report)
    assert assessed.prototype_assessment.status == "unavailable"
    assert "reference_calibration_pending" in assessed.prototype_assessment.missing_reasons
    assert assessed.metrics  # measurements still returned


def test_assessment_rejects_invalid_baseline(monkeypatch):
    frames = _install(monkeypatch, "squat")
    report = _build(frames, "squat")
    for mutate in (
        lambda c: c.update(version="invalid-version"),
        lambda c: c.update(author=True),
        lambda c: c.update(review="reviewed"),
        lambda c: c.update(normalization_degrees=True),
        lambda c: c.update(normalization_degrees=-30),
        lambda c: c.update(min_coverage=0.5),
        lambda c: c["references"]["squat"].update(bands="bad"),
    ):
        cfg = _fake_config("squat")
        mutate(cfg)
        assessed = rt.apply_reference_assessment(report, config=cfg)
        assert assessed.prototype_assessment.status == "unavailable"


def test_assessment_rejects_low_valid_count(monkeypatch):
    frames = _install(monkeypatch, "squat")
    report = _build(frames, "squat")
    cfg = _fake_config("squat")
    cfg["references"]["squat"]["bands"]["knee_angle/estimated_3d/bottom"]["valid_count"] = 1
    assessed = rt.apply_reference_assessment(report, config=cfg)
    assert assessed.prototype_assessment.status == "unavailable"
    cfg = _fake_config("squat")
    cfg["references"]["squat"]["bands"]["knee_angle/estimated_3d/bottom"]["valid_count"] = True
    assessed = rt.apply_reference_assessment(report, config=cfg)
    assert assessed.prototype_assessment.status == "unavailable"
    cfg = _fake_config("squat")
    cfg["references"]["squat"]["bands"]["knee_angle/estimated_3d/bottom"]["valid_count"] = 99
    assessed = rt.apply_reference_assessment(report, config=cfg)
    assert assessed.prototype_assessment.status == "unavailable"


def test_determinism_and_idempotency(monkeypatch):
    frames = _install(monkeypatch, "incline_chest_press")
    a = _build(frames, "incline_chest_press")
    b = _build(frames, "incline_chest_press")
    assert a.model_dump() == b.model_dump()
    cfg = _fake_config("incline_chest_press")
    ca = rt.apply_reference_assessment(a, config=cfg)
    cb = rt.apply_reference_assessment(b, config=cfg)
    assert ca.model_dump() == cb.model_dump()
    # recipe + reference v1 assessment is idempotent
    ca2 = rt.apply_reference_assessment(ca, config=cfg)
    assert ca2.model_dump() == ca.model_dump()


def test_input_validation(monkeypatch):
    frames = _install(monkeypatch, "squat")
    with pytest.raises(ValueError):
        rt.build_exercise_report(
            frames, analysis_id="t", exercise_id="squat", variant=VARIANTS["squat"],
            width=0, height=480, pose_sha256=SHA, processing_version="pv1",
        )
    with pytest.raises(ValueError):
        rt.build_exercise_report(
            frames, analysis_id="t", exercise_id="squat", variant=VARIANTS["squat"],
            width=640, height=480, pose_sha256="zz", processing_version="pv1",
        )


def _manifest_entry(**over):
    entry = {
        "id": "r1", "exercise_id": "squat", "variant": "bodyweight",
        "pose_root": ".", "frames_artifact_key": "k", "pose_sha256": SHA,
        "width": 640, "height": 480, "processing_version": "pv1",
        "source_url": "file:///x", "view_id": "front", "primary": True,
    }
    entry.update(over)
    return entry


def test_cli_rejects_empty(monkeypatch, tmp_path):
    cal = _load_cal()
    monkeypatch.setattr(
        cal, "_measure_reference",
        lambda e: {"report": SimpleNamespace(detected_rep_count=0),
                   "values": {k: [] for k in rt.COMPARISON_KEYS[e["exercise_id"]]},
                   "usable_cycles": 0, "window_origin": "automatic_segmentation_signal_only",
                   "review_status": "unreviewed"},
    )
    manifest = tmp_path / "m.json"
    manifest.write_text(
        '{"references":[' + json_dumps(_manifest_entry(window_s=[1.0, 9.0])) + ']}'
    )
    with pytest.raises(ValueError):
        cal.build_config(manifest)
    manifest.write_text(
        '{"references":[' + json_dumps(_manifest_entry(primary=False)) + ']}'
    )
    with pytest.raises(ValueError):
        cal.build_config(manifest)


def json_dumps(obj):
    import json
    return json.dumps(obj)


def test_cli_bands_from_measured(monkeypatch, tmp_path):
    cal = _load_cal()
    frames = _install(monkeypatch, "squat")
    report = _build(frames, "squat")
    monkeypatch.setattr(cal, "read_pose_frames", lambda *a, **k: frames)
    monkeypatch.setattr(cal, "build_exercise_report", lambda *a, **k: report)
    manifest = tmp_path / "m.json"
    manifest.write_text('{"references":[' + json_dumps(_manifest_entry()) + ']}')
    cfg = cal.build_config(manifest)
    ref = cfg["references"]["squat"]
    assert ref["primary"] is True and ref["valid_reference_cycles"] == 2
    assert ref["window_origin"] == "automatic_segmentation_signal_only"
    assert ref["review_status"] == "unreviewed"
    assert ref["pose_sha256"] == SHA and ref["source_url"] == "file:///x"
    for k in rt.COMPARISON_KEYS["squat"]:
        band = ref["bands"][k]
        assert band["valid_count"] == 2 and band["lower"] <= band["upper"]
        assert band["unit"] == "degrees"
    out = tmp_path / "out" / "bands.json"
    monkeypatch.setattr(
        "sys.argv", ["calibrate", "--manifest", str(manifest), "--output", str(out)]
    )
    assert cal.main() == 0 and out.exists()


def test_cli_manual_rep_windows(monkeypatch, tmp_path):
    cal = _load_cal()
    frames = _install(monkeypatch, "squat")
    monkeypatch.setattr(cal, "read_pose_frames", lambda *a, **k: frames)
    windows = [
        {"start_s": 0.0, "bottom_s": 0.25, "end_s": 0.55, "side": "left",
         "origin": "visually_proposed_reference_window", "review_status": "unreviewed"},
        {"start_s": 0.40, "bottom_s": 0.65, "end_s": 0.95, "side": "left",
         "origin": "visually_proposed_reference_window", "review_status": "unreviewed"},
    ]
    manifest = tmp_path / "m.json"
    manifest.write_text(
        '{"references":[' + json_dumps(_manifest_entry(rep_windows=windows)) + ']}'
    )
    cfg = cal.build_config(manifest)
    ref = cfg["references"]["squat"]
    assert ref["valid_reference_cycles"] == 2
    assert ref["window_origin"] == "visually_proposed_reference_window"
    assert ref["review_status"] == "unreviewed"
    for k in rt.COMPARISON_KEYS["squat"]:
        band = ref["bands"][k]
        assert band["valid_count"] == 2 and band["lower"] <= band["upper"]
    # knee bottom band comes from the actual low plateaus (~60), never faked
    knee = ref["bands"]["knee_angle/estimated_3d/bottom"]
    assert knee["lower"] == pytest.approx(60.0)


def test_cli_rep_window_validation(monkeypatch, tmp_path):
    cal = _load_cal()
    frames = _install(monkeypatch, "squat")
    monkeypatch.setattr(cal, "read_pose_frames", lambda *a, **k: frames)
    good = {"start_s": 0.0, "bottom_s": 0.25, "end_s": 0.55, "side": "left",
            "origin": "visually_proposed_reference_window", "review_status": "unreviewed"}
    bad_windows = [
        dict(good, start_s=0.55),                       # not ordered
        dict(good, start_s=float("nan")),               # not finite
        dict(good, side="both"),                         # bad side
        dict(good, origin="ground_truth"),               # never ground truth
        dict(good, review_status="reviewed"),            # must stay unreviewed
        dict(good, end_s=99.0),                         # outside window_s
    ]
    for w in bad_windows:
        manifest = tmp_path / "m.json"
        entry = _manifest_entry(rep_windows=[w, good], window_s=[0.0, 1.0])
        manifest.write_text('{"references":[' + json_dumps(entry) + ']}')
        with pytest.raises(ValueError):
            cal.build_config(manifest)
