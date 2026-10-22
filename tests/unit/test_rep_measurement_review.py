from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / "packages" / "contracts", ROOT / "packages" / "movement",
          ROOT / "packages" / "providers"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from contracts.pose import JointObservation, PoseFrame, PoseSequence  # noqa: E402
from providers.pose.artifacts import write_pose_frames  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "rep_measurement_review", ROOT / "scripts" / "rep_measurement_review.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)

WIDTH, HEIGHT = 100, 100


def _joint(x, y, z=0.5, xy=True):
    return JointObservation(
        xy=(x, y) if xy else None, xyz=(x, y, z), valid=True, interpolated=False)


def _frame(idx, t, wrist_xy=True):
    return PoseFrame(
        frame_index=idx,
        timestamp_s=t,
        joints={
            "left_shoulder": _joint(0.5, 0.4),
            "left_elbow": _joint(0.5, 0.6),
            "left_wrist": _joint(0.7, 0.8, xy=wrist_xy),
            "left_hip": _joint(0.5, 0.9),
        },
    )


def _write_pose(root: Path) -> str:
    root.mkdir(parents=True, exist_ok=True)
    frames = [_frame(0, 0.0), _frame(1, 0.5, wrist_xy=False), _frame(2, 1.0)]
    digest = write_pose_frames(root, "tmp.jsonl", frames)
    key = f"{digest}.jsonl"
    (root / "tmp.jsonl").rename(root / key)
    seq = PoseSequence(
        video_id="vid-1",
        provider="synthetic",
        model_revision="rev-1",
        native_skeleton="coco-17",
        joint_mapping_version="jm-1",
        sample_rate_hz=2.0,
        units="normalized_xy_estimated_xyz",
        coordinate_system="image_top_left",
        capabilities={"xyz": True},
        quality_method="none",
        frames_artifact_key=key,
    )
    (root / "manifest.json").write_text(seq.model_dump_json())
    return Path(key).stem


def _config(pose_root: Path, source_sha: str, role: str = "reference") -> dict:
    return {
        "version": "cfg-1",
        "authoritative": False,
        "max_gap_s": 0.25,
        "clips": [{
            "id": "clipA",
            "role": role,
            "pose_root": str(pose_root),
            "source_sha256": source_sha,
            "side": "left",
            "width": WIDTH,
            "height": HEIGHT,
            "axis": {"version": "v1", "axis_id": "gravity",
                     "up_xy": [0.0, -1.0], "positive_cross_sign": 1},
            "view_id": "front",
            "variant": "bodyweight",
            "review_status": "visual_provisional",
            "annotation_origin": "human-review-tool",
            "uncertainty_s": 0.04,
            "reps": [{"rep_id": "r1", "start_s": 0.0,
                      "bottom_s": 0.5, "end_s": 1.0}],
        }],
    }


@pytest.fixture()
def setup(tmp_path):
    pose_root = tmp_path / "pose"
    pose_hash = _write_pose(pose_root)
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(_config(pose_root, "a" * 64)))
    outdir = tmp_path / "artifacts" / "out"
    return cfg_path, outdir, pose_hash


def _run(cfg_path, outdir):
    cli.main(["--annotations", str(cfg_path), "--output-dir", str(outdir)])
    return json.loads((outdir / "measurements.json").read_text())


def test_happy_path_exact_math_and_identity(setup):
    cfg_path, outdir, pose_hash = setup
    report = _run(cfg_path, outdir)
    assert report["authoritative"] is False
    assert report["valid_technique_score"] is None
    assert report["endpoint"] is None
    assert report["endpoint_reason"] == "not_implemented"
    clip = report["clips"][0]
    assert clip["pose_artifact_hash"] == pose_hash
    assert clip["source_sha256"] == "a" * 64  # declared provenance, not pose hash
    rep = clip["reps"][0]
    comps = rep["components"]
    assert len(comps) == 32
    assert comps["pull_duration_s"] == {"value": 0.5, "reason": None,
                                        "unit": "seconds", "actual_pts_s": None}
    assert comps["return_duration_s"]["value"] == 0.5
    start = comps["elbow_angle/projected_2d/start"]
    # shoulder(50,40) elbow(50,60) wrist(70,80): angle at elbow = 135 deg
    assert start["value"] == pytest.approx(135.0)
    assert start["actual_pts_s"] == 0.0
    assert rep["available_count"] < 32  # wrist gap removes some components


def test_explicit_gap_reason_at_bottom(setup):
    cfg_path, outdir, _ = setup
    comps = _run(cfg_path, outdir)["clips"][0]["reps"][0]["components"]
    bottom = comps["elbow_angle/projected_2d/bottom"]
    assert bottom["value"] is None
    assert bottom["reason"] == "missing_coordinates"
    assert bottom["actual_pts_s"] == 0.5
    # 3d wrist coordinates still present -> 3d bottom is measured
    assert comps["elbow_angle/estimated_3d/bottom"]["value"] is not None


def test_reference_profile_observed_ranges(setup):
    cfg_path, outdir, _ = setup
    clip = _run(cfg_path, outdir)["clips"][0]
    prof = clip["profile_observed_ranges"]
    assert prof is not None
    e2d = prof["elbow_angle/projected_2d/start"]
    assert e2d["valid_count"] == 1
    assert e2d["value_min"] == pytest.approx(135.0)
    assert e2d["value_max"] == pytest.approx(135.0)
    assert e2d["unit"] == "degrees" and e2d["provisional"] is True
    assert prof["pull_duration_s"]["unit"] == "seconds"
    assert prof["pull_duration_s"]["valid_count"] == 1
    gap = prof["elbow_angle/projected_2d/bottom"]
    assert gap["valid_count"] == 0 and gap["value_min"] is None


def test_user_clip_has_no_profile(setup, tmp_path):
    cfg_path, outdir, _ = setup
    cfg = json.loads(cfg_path.read_text())
    cfg["clips"][0]["role"] = "user"
    cfg_path.write_text(json.dumps(cfg))
    clip = _run(cfg_path, outdir)["clips"][0]
    assert clip["role"] == "user"
    assert clip["profile_observed_ranges"] is None


def test_deterministic_two_runs(setup):
    cfg_path, outdir, _ = setup
    first = (outdir / "measurements.json")
    _run(cfg_path, outdir)
    a = first.read_text()
    _run(cfg_path, outdir)
    assert first.read_text() == a


def _expect_fail(cfg_path, outdir, fragment):
    with pytest.raises(SystemExit):
        cli.main(["--annotations", str(cfg_path), "--output-dir", str(outdir)])
    assert not (outdir / "measurements.json").exists()


def test_strict_bool_and_type_rejected_before_writes(setup, tmp_path):
    cfg_path, outdir, _ = setup
    cfg = json.loads(cfg_path.read_text())
    cfg["clips"][0]["side"] = True  # no bool coercion
    cfg_path.write_text(json.dumps(cfg))
    _expect_fail(cfg_path, outdir, "side")
    cfg = json.loads(cfg_path.read_text())
    cfg["clips"][0]["side"] = "left"
    cfg["clips"][0]["axis"]["positive_cross_sign"] = True
    cfg_path.write_text(json.dumps(cfg))
    _expect_fail(cfg_path, outdir, "cross_sign")


def test_review_status_and_uncertainty_enforced(setup):
    cfg_path, outdir, _ = setup
    cfg = json.loads(cfg_path.read_text())
    cfg["clips"][0]["review_status"] = "approved"
    cfg_path.write_text(json.dumps(cfg))
    _expect_fail(cfg_path, outdir, "review_status")
    cfg = json.loads(cfg_path.read_text())
    cfg["clips"][0]["review_status"] = "visual_provisional"
    cfg["clips"][0]["uncertainty_s"] = -0.1
    cfg_path.write_text(json.dumps(cfg))
    _expect_fail(cfg_path, outdir, "uncertainty")


def test_output_guards(setup, tmp_path):
    cfg_path, outdir, _ = setup
    # symlink escape rejected
    target = tmp_path / "artifacts" / "real"
    target.mkdir(parents=True)
    link = tmp_path / "artifacts" / "link"
    link.symlink_to(target, target_is_directory=True)
    _expect_fail(cfg_path, link, "symlink")
    # non-artifacts output dir rejected
    bad = tmp_path / "notartifacts"
    _expect_fail(cfg_path, bad, "artifacts")


def test_pose_hash_mismatch_detected(setup):
    cfg_path, outdir, _ = setup
    pose_root = Path(json.loads(cfg_path.read_text())["clips"][0]["pose_root"])
    key = next(p for p in pose_root.iterdir() if p.name != "manifest.json")
    key.write_text(key.read_text() + "tamper")
    _expect_fail(cfg_path, outdir, "hash")
