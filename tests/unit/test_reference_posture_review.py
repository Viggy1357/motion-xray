from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from contracts.pose import JointObservation, PoseFrame, PoseSequence
from providers.pose.artifacts import write_pose_frames

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "reference_posture_review", ROOT / "scripts" / "reference_posture_review.py")
rpr = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = rpr
spec.loader.exec_module(rpr)

AXIS = {"version": "camera-plane-axis-v1", "axis_id": "image_up_unverified",
        "up_xy": [0, -1], "positive_cross_sign": 1}


def _joint(x: float, y: float, valid: bool = True) -> JointObservation:
    if not valid:
        return JointObservation(valid=False, interpolated=False)
    return JointObservation(xy=(x, y), xyz=(x, y, 0.0), valid=True, interpolated=False)


def _make_pose_root(base: Path, bad_mid_wrist: bool = False) -> Path:
    root = base / "pose"
    root.mkdir(parents=True)
    frames = []
    for i, t in enumerate((0.0, 0.05, 0.1)):
        ok = not (bad_mid_wrist and i == 1)
        frames.append(PoseFrame(frame_index=i, timestamp_s=t, joints={
            "left_hip": _joint(0.5, 0.8), "left_shoulder": _joint(0.5, 0.5),
            "left_elbow": _joint(0.7, 0.5), "left_wrist": _joint(0.7, 0.3, ok)}))
    h = write_pose_frames(root, "tmp.jsonl", frames)
    (root / "tmp.jsonl").rename(root / f"{h}.jsonl")
    seq = PoseSequence(video_id="v", provider="synthetic", model_revision="r0",
                       native_skeleton="synthetic", joint_mapping_version="jm1",
                       sample_rate_hz=20.0, units="normalized",
                       coordinate_system="image_xy_down",
                       capabilities={"xy": True, "xyz": True},
                       quality_method="synthetic", frames_artifact_key=f"{h}.jsonl")
    (root / "manifest.json").write_text(seq.model_dump_json())
    return root


def _config(pose_root: Path, **over) -> dict:
    clip = {"id": "clip_a", "pose_root": str(pose_root), "side": "left", "width": 100,
            "height": 100, "axis": dict(AXIS), "windows_s": [[0.0, 0.1]],
            "sample_times_s": [0.05], "view_note": "synthetic"}
    clip.update(over.pop("clip", {}))
    cfg = {"version": "test-v1", "authoritative": False, "max_gap_s": 0.1,
           "clips": [clip]}
    cfg.update(over)
    return cfg


def _run(tmp_path: Path, cfg: dict, out_name: str = "out") -> Path:
    art = tmp_path / "artifacts"
    art.mkdir(exist_ok=True)
    cfg_path = art / "config.json"
    cfg_path.write_text(json.dumps(cfg))
    out = art / out_name
    rpr.main(["--config", str(cfg_path), "--output-dir", str(out)])
    return out


def test_window_stats_five_metrics_no_mixing(tmp_path):
    root = _make_pose_root(tmp_path / "artifacts")
    out = _run(tmp_path, _config(root))
    summary = json.loads((out / "summary.json").read_text())
    clip = summary["clips"][0]
    metrics = clip["windows"][0]["metrics"]
    assert set(metrics) == {"elbow_angle/projected_2d", "elbow_angle/estimated_3d",
                            "upper_arm_torso_angle/projected_2d",
                            "upper_arm_torso_angle/estimated_3d",
                            "torso_axis_angle/projected_2d"}
    elbow = metrics["elbow_angle/projected_2d"]
    assert elbow["observed_valid_min"] == pytest.approx(90.0)
    assert elbow["observed_valid_max"] == pytest.approx(90.0)
    assert elbow["excursion"] == pytest.approx(0.0)
    ua = metrics["upper_arm_torso_angle/projected_2d"]
    assert ua["observed_valid_min"] == pytest.approx(90.0)
    torso = metrics["torso_axis_angle/projected_2d"]
    assert torso["observed_valid_min"] == pytest.approx(0.0)
    assert torso["observed_valid_max"] == pytest.approx(0.0)
    # no pooled full-clip all-metric range anywhere
    assert "observed_valid_min" not in clip["summary_metadata"]
    assert "observed_valid_min" not in clip
    assert summary["valid_technique_score"] is None
    assert summary["endpoint"] is None
    assert summary["endpoint_reason"] == "not_implemented"
    assert clip["pose_artifact_hash"] and clip["joint_mapping_version"] == "jm1"


def test_sample_uses_actual_pts_even_invalid(tmp_path):
    root = _make_pose_root(tmp_path / "artifacts", bad_mid_wrist=True)
    out = _run(tmp_path, _config(root))
    summary = json.loads((out / "summary.json").read_text())
    s = summary["clips"][0]["sample_values"]["0.05"]
    assert s["reason"] is None
    assert s["actual_pts_s"] == pytest.approx(0.05)  # not a search for a valid frame
    assert set(s["observations"]) == {"elbow_angle/projected_2d", "elbow_angle/estimated_3d",
                                      "upper_arm_torso_angle/projected_2d",
                                      "upper_arm_torso_angle/estimated_3d",
                                      "torso_axis_angle/projected_2d"}
    row = s["observations"]["elbow_angle/projected_2d"]
    assert row["value"] is None and isinstance(row["reason"], str) and row["reason"]
    assert s["observations"]["torso_axis_angle/projected_2d"]["value"] == pytest.approx(0.0)


def test_sample_outside_gap_null_reason(tmp_path):
    root = _make_pose_root(tmp_path / "artifacts")
    out = _run(tmp_path, _config(root, clip={"sample_times_s": [5.0]}))
    s = json.loads((out / "summary.json").read_text())["clips"][0]["sample_values"]["5.0"]
    assert s["actual_pts_s"] is None and s["observations"] is None
    assert s["reason"] == "no_nearby_frame_within_max_gap"


def test_sample_outside_window_marked(tmp_path):
    root = _make_pose_root(tmp_path / "artifacts")
    cfg = _config(root, clip={"windows_s": [[0.06, 0.1]], "sample_times_s": [0.0]})
    out = _run(tmp_path, cfg)
    s = json.loads((out / "summary.json").read_text())["clips"][0]["sample_values"]["0.0"]
    assert s["actual_pts_s"] == pytest.approx(0.0)
    assert s["within_any_window"] is False


def test_strict_axis_bool_sign_rejected(tmp_path):
    root = _make_pose_root(tmp_path / "artifacts")
    bad = _config(root, clip={"axis": {**AXIS, "positive_cross_sign": True}})
    with pytest.raises(SystemExit):
        _run(tmp_path, bad)
    bad2 = _config(root, clip={"axis": {**AXIS, "positive_cross_sign": 1.0}})
    with pytest.raises(SystemExit):
        _run(tmp_path, bad2)


def test_duplicate_and_path_traversal_ids_rejected(tmp_path):
    root = _make_pose_root(tmp_path / "artifacts")
    dup = _config(root)
    dup["clips"].append(dict(dup["clips"][0]))
    with pytest.raises(SystemExit):
        _run(tmp_path, dup)
    trav = _config(root, clip={"id": "../evil"})
    with pytest.raises(SystemExit):
        _run(tmp_path, trav)


def test_output_dir_must_be_under_artifacts(tmp_path):
    root = _make_pose_root(tmp_path / "artifacts")
    cfg_path = tmp_path / "artifacts" / "config.json"
    cfg_path.write_text(json.dumps(_config(root)))
    with pytest.raises(SystemExit):
        rpr.main(["--config", str(cfg_path), "--output-dir", str(tmp_path / "out")])


def test_refuses_overwrite_of_config_input(tmp_path):
    root = _make_pose_root(tmp_path / "artifacts")
    out = tmp_path / "artifacts" / "out"
    out.mkdir(parents=True)
    cfg_path = out / "summary.json"  # config occupies the summary output path
    cfg_path.write_text(json.dumps(_config(root)))
    with pytest.raises(SystemExit):
        rpr.main(["--config", str(cfg_path), "--output-dir", str(out)])


def test_deterministic_repeat_output(tmp_path):
    root = _make_pose_root(tmp_path / "artifacts")
    cfg = _config(root)
    out1 = _run(tmp_path, cfg, "out1")
    out2 = _run(tmp_path, cfg, "out2")
    assert (out1 / "summary.json").read_bytes() == (out2 / "summary.json").read_bytes()
    assert (out1 / "clip_a-observations.json").read_bytes() == \
        (out2 / "clip_a-observations.json").read_bytes()
    # outputs are new files, never the inputs
    inputs = {cfg_path for cfg_path in (tmp_path / "artifacts").glob("*.json")}
    inputs |= set(root.glob("*.json*"))
    for produced in list(out1.glob("*.json")):
        assert produced.resolve() not in {p.resolve() for p in inputs}
