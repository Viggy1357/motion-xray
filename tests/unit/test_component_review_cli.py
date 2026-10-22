from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from contracts.pose import PoseSequence

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import component_comparison_review as ccr  # noqa: E402

KEYS = [k for _, k in ccr.SCORED_METRICS] + [k for _, k in ccr.UNSCORED_METRICS]
HASH = "a" * 64


def _manifest(root: Path, provider: str = "testprovider", key: str = HASH + ".jsonl") -> None:
    root.mkdir(parents=True, exist_ok=True)
    seq = PoseSequence(
        video_id="synthetic-video", provider=provider, model_revision="synthetic-v1",
        native_skeleton="synthetic", joint_mapping_version="jm-v1", sample_rate_hz=30,
        units="model_estimated_meters_uncalibrated", coordinate_system="synthetic",
        capabilities={"supports_2d": True}, quality_method="fixture",
        frames_artifact_key=key,
    )
    (root / "manifest.json").write_text(seq.model_dump_json())


def _comp(v, unit="deg"):
    return {"value": v, "unit": unit, "reason": None if v is not None else "no_keypoints"}


def _clip(cid, role, prov, comps, reps=("r1",)):
    return {
        "id": cid, "role": role, "view_id": "view_a", "variant": "right",
        "joint_mapping_version": "jm-v1", "pose_artifact_hash": HASH,
        "source_pose_provenance": str(prov),
        "reps": [{"rep_id": r,
                  "label": {"start_s": 1.0, "bottom_s": 2.0, "end_s": 3.0},
                  "components": comps, "available_count": 0} for r in reps],
        "profile_observed_ranges": (
            {k: {"value_min": 10.0, "value_max": 20.0, "valid_count": 2,
                 "unit": "deg", "provisional": True} for k in KEYS}
            if role == "reference" else None
        ),
    }


def _policy(tmp: Path) -> Path:
    p = json.loads((ROOT / "data/review_configs/lat-component-policy-v1.json").read_text())
    p["reference_ids"] = ["ref_a", "ref_b"]
    p["primary_reference_id"] = "ref_a"
    p["per_reference"] = {
        r: {"compatibility": "unknown", "compatibility_reviewer": None,
            "compatibility_version": "view-review-pending"} for r in ("ref_a", "ref_b")
    }
    path = tmp / "policy.json"
    path.write_text(json.dumps(p))
    return path


def _fixture(tmp: Path):
    art = tmp / "artifacts"
    provs = {}
    for cid in ("user_roi_a", "user_roi_b", "ref_a", "ref_b"):
        provs[cid] = art / "pose" / cid
        _manifest(provs[cid])
    comps = {k: _comp(15.0) for k in KEYS}
    comps["elbow_angle/estimated_3d/end"] = _comp(None)
    clips = [
        _clip("user_roi_a", "user", provs["user_roi_a"], comps, ("r1",)),
        _clip("user_roi_b", "user", provs["user_roi_b"], comps, ("r1", "r2")),
        _clip("ref_a", "reference", provs["ref_a"], comps),
        _clip("ref_b", "reference", provs["ref_b"], comps),
    ]
    mpath = art / "measurements.json"
    mpath.parent.mkdir(parents=True, exist_ok=True)
    mpath.write_text(json.dumps({"version": "t", "authoritative": False, "clips": clips}))
    return mpath, _policy(tmp), art / "out"


def test_dedup_reason_preserved_no_scores(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    m, p, out = _fixture(tmp_path)
    paths = ccr.run(m, p, out)
    data = json.loads(paths["json"].read_text())
    assert data["user_crop_rep_count"] == 2  # r1 deduped across crops
    assert data["comparison_count"] == 2 * 2 * 5
    assert data["scored_count"] == 0
    assert all(c["score"] is None for c in data["comparisons"])
    m6 = [c for c in data["comparisons"] if c["metric_id"] == "M6"]
    assert all(c["value"] is None and c["reason"] == "no_keypoints" for c in m6)
    assert data["aggregate_score"] is None


def test_label_mismatch_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    m, p, out = _fixture(tmp_path)
    data = json.loads(m.read_text())
    data["clips"][1]["reps"][0]["label"]["start_s"] = 9.9
    m.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="label mismatch"):
        ccr.run(m, p, out)


def test_unit_mismatch_descriptive(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    m, p, out = _fixture(tmp_path)
    data = json.loads(m.read_text())
    data["clips"][0]["reps"][0]["components"]["elbow_angle/estimated_3d/excursion"]["unit"] = "rad"
    m.write_text(json.dumps(data))
    res = json.loads(ccr.run(m, p, out)["json"].read_text())
    bad = [c for c in res["comparisons"] if c["component_key"] == "elbow_angle/estimated_3d/excursion"
           and c["rep_id"] == "r1"]
    assert bad and all(c["score_reason"].startswith("unit_mismatch") for c in bad)


def test_hash_mismatch_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    m, p, out = _fixture(tmp_path)
    _manifest(tmp_path / "artifacts/pose/ref_a", key="b" * 64 + ".jsonl")
    with pytest.raises(ValueError, match="pose hash mismatch"):
        ccr.run(m, p, out)


def test_malformed_policy_fails_before_write(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    m, p, out = _fixture(tmp_path)
    bad = json.loads(p.read_text())
    bad["authoritative"] = True
    p.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="authoritative"):
        ccr.run(m, p, out)
    assert not (out / "comparison.json").exists()


def test_output_never_overwrites_input(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    m, p, out = _fixture(tmp_path)
    with pytest.raises(ValueError, match="artifacts"):
        ccr.run(m, p, tmp_path / "notartifacts")


def test_cli_subprocess(tmp_path):
    m, p, out = _fixture(tmp_path)
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/component_comparison_review.py"),
         "--measurements", str(m), "--policy", str(p), "--output-dir", str(out)],
        cwd=tmp_path, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    for name in ("comparison.json", "t047.html", "comparison.md"):
        assert (out / name).is_file()
    html = (out / "t047.html").read_text()
    assert "media/user_lat.mp4" in html and "cdn" not in html.lower()


def test_cli_subprocess_bad_policy_exit(tmp_path):
    m, p, out = _fixture(tmp_path)
    bad = json.loads(p.read_text())
    bad["metrics"]["torso_axis_angle/projected_2d/excursion"]["tolerance"] = True
    p.write_text(json.dumps(bad))
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/component_comparison_review.py"),
         "--measurements", str(m), "--policy", str(p), "--output-dir", str(out)],
        cwd=tmp_path, capture_output=True, text=True)
    assert proc.returncode == 1
    assert "tolerance" in proc.stderr
    assert not (out / "comparison.json").exists()


@pytest.mark.parametrize("missing", ["user_component", "reference_profile"])
def test_missing_comparison_preserves_row_identity(tmp_path, monkeypatch, missing):
    monkeypatch.chdir(tmp_path)
    m, p, out = _fixture(tmp_path)
    data = json.loads(m.read_text())
    key = "elbow_angle/estimated_3d/excursion"
    if missing == "user_component":
        for clip in data["clips"][:2]:
            for rep in clip["reps"]:
                rep["components"].pop(key, None)
    else:
        data["clips"][2]["profile_observed_ranges"].pop(key)
    m.write_text(json.dumps(data))
    result = json.loads(ccr.run(m, p, out)["json"].read_text())
    unavailable = [c for c in result["comparisons"] if c["metric_id"] == "M3" and c["score_reason"] in ("missing_user_component", "reference_band_unavailable")]
    assert unavailable
    assert all(c["rep_id"] and c["reference_clip"] and c["score"] is None for c in unavailable)
