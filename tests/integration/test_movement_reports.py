from __future__ import annotations

import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.store import Store
from contracts.analysis import AnalysisResult, CoachingResult
from contracts.enums import CoachingStatus
from contracts.media import VideoAsset
from contracts.pose import JointObservation, PoseFrame, PoseSequence
from contracts.pose_job import PoseJobArtifacts
from contracts.proxy import ProxyTimestampMap, TimestampPair

from tests.integration import test_artifact_streams as artifact_fixtures
from tests.integration.test_artifact_streams import _headers, _owner_from_cookie, _session, _sha256

client = artifact_fixtures.client
env_setup = artifact_fixtures.env_setup

JOINTS = [
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
]

_STEP_S = 0.05
_HIGH_DEG = 140.0
_LOW_DEG = 95.0


def _angle_timeline() -> list[float]:
    """Two full pull cycles: 140deg high plateau, ramp to 95deg low plateau, back.

    Plateaus last 0.1s (two 0.05s steps); ramps span 0.2s so the signal is
    mathematically smooth and monotonic within each phase.
    """
    hold = [0.0, _STEP_S, 2 * _STEP_S, 3 * _STEP_S]  # >0.1s observed plateau
    ramp_steps = 4  # 0.2s ramp
    angles: list[float] = []
    for _ in range(2):
        angles.extend(_HIGH_DEG for _ in hold)
        angles.extend(
            _HIGH_DEG + (_LOW_DEG - _HIGH_DEG) * (k + 1) / (ramp_steps + 1)
            for k in range(ramp_steps)
        )
        angles.extend(_LOW_DEG for _ in hold)
        angles.extend(
            _LOW_DEG + (_HIGH_DEG - _LOW_DEG) * (k + 1) / (ramp_steps + 1)
            for k in range(ramp_steps)
        )
    angles.extend([_HIGH_DEG] * 4)
    return angles


def _lat_frames() -> list[PoseFrame]:
    """Analytic 2-cycle lat pulldown capture.

    Model-space geometry (meters, hip-relative): shoulder (0, 1, 0),
    elbow (0, 0, 0), wrist (sin(theta), cos(theta), 0), hip (0, -1, 0),
    so the elbow angle equals theta exactly. Normalized xy is a sensible
    orthographic projection into the [0, 1] image plane. All joints valid.
    """
    frames: list[PoseFrame] = []
    for i, deg in enumerate(_angle_timeline()):
        theta = math.radians(deg)
        wx, wy = math.sin(theta), math.cos(theta)

        def obs(x: float, y: float, z: float = 0.0) -> JointObservation:
            return JointObservation(
                xy=(0.5 + 0.2 * x, 0.5 - 0.2 * y),
                xyz=(x, y, z),
                valid=True,
                interpolated=False,
            )

        joints = {
            "left_shoulder": obs(0.0, 1.0),
            "right_shoulder": obs(0.0, 1.0),
            "left_elbow": obs(0.0, 0.0),
            "right_elbow": obs(0.0, 0.0),
            "left_wrist": obs(wx, wy),
            "right_wrist": obs(wx, wy),
            "left_hip": obs(0.0, -1.0),
            "right_hip": obs(0.0, -1.0),
        }
        frames.append(PoseFrame(frame_index=i, timestamp_s=i * _STEP_S, joints=joints))
    return frames


def _rehash_frames(f, frames: list[PoseFrame]) -> None:
    """Rewrite the pose artifact with new frames and re-point the manifest."""
    data = b"".join(
        json.dumps(fr.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"
        for fr in frames
    )
    key = f"pose/{_sha256(data)}.jsonl"
    (f.attempt / key).write_bytes(data)
    manifest = json.loads((f.attempt / "manifest.json").read_text())
    manifest["pose"]["frames_artifact_key"] = key
    (f.attempt / "manifest.json").write_text(json.dumps(manifest))


@pytest.fixture
def lat_succeeded(client: TestClient, env_setup) -> SimpleNamespace:
    _, db_path, _, artifacts_root = env_setup
    store = Store(Path(db_path))
    csrf = _session(client)
    owner = _owner_from_cookie(client)
    now = datetime.now(timezone.utc)
    store.register_asset(VideoAsset(
        id="a" * 32, owner_session_id=owner, storage_key="uploads/video.mp4",
        sha256="a" * 64, mime="video/mp4", bytes=1024, duration_s=5.0,
        width=640, height=480, rotation=0, created_at=now,
        expires_at=now + timedelta(hours=1),
    ))
    job = store.enqueue(owner, "a" * 32, "lat_pulldown", "cable_seated_bilateral", "req1", "vhash")
    token = store.claim("worker")
    assert token is not None and token.lease_owner is not None
    lease = token.lease_owner
    attempt = Path(artifacts_root) / "attempts" / job.id / lease
    (attempt / "proxy").mkdir(parents=True)
    (attempt / "pose").mkdir()

    frames = _lat_frames()
    frames_bytes = b"".join(
        json.dumps(fr.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"
        for fr in frames
    )
    frames_key = f"pose/{_sha256(frames_bytes)}.jsonl"
    (attempt / frames_key).write_bytes(frames_bytes)

    proxy = ProxyTimestampMap(
        source_sha256="a" * 64, proxy_sha256=_sha256(b"proxy"), source_width=640, source_height=480,
        source_rotation=0, proxy_width=640, proxy_height=480, padding_right=0, padding_bottom=0,
        frames=[TimestampPair(source_index=i, source_s=i * _STEP_S, proxy_s=i * _STEP_S) for i in range(len(frames))],
    )
    pose = PoseSequence(
        video_id="a" * 32, provider="mediapipe", model_revision="sha256:" + "b" * 64,
        native_skeleton="mediapipe-33", joint_mapping_version="mp33-camera-v1",
        sample_rate_hz=20, units="model_estimated_meters_uncalibrated",
        coordinate_system="hip_relative_camera_x_right_y_up_z_toward_viewer",
        capabilities={"supports_2d": True, "supports_estimated_3d": True}, quality_method="test",
        frames_artifact_key=frames_key,
    )
    report = AnalysisResult(
        analysis_id=job.id, exercise="lat_pulldown", variant="cable_seated_bilateral",
        coaching=CoachingResult(status=CoachingStatus.UNAVAILABLE), warnings=["POSE_ONLY"],
        provenance={
            "pipeline": "pose-job-v1", "input_sha256": "a" * 64,
            "version_hash": job.version_hash, "pose_model_revision": pose.model_revision,
        },
    )
    manifest = PoseJobArtifacts(request_sha256="c" * 64, pose=pose, proxy=proxy, report=report)
    (attempt / "manifest.json").write_bytes(manifest.model_dump_json().encode())
    store.finish(job.id, lease, result_key=f"attempts/{job.id}/{lease}/manifest.json")
    return SimpleNamespace(
        store=store, job=job, owner=owner, csrf=csrf, attempt=attempt,
        frames_key=frames_key, frames_bytes=frames_bytes, pose=pose, proxy=proxy,
    )


def _get(client: TestClient, f) -> object:
    return client.get(f"/v1/analyses/{f.job.id}/movement-report", headers=_headers(f.csrf))


def test_valid_lat_report(client: TestClient, lat_succeeded):
    r = _get(client, lat_succeeded)
    assert r.status_code == 200
    body = r.json()
    assert body["schema_version"] == "0.3.0"
    assert body["analysis_id"] == lat_succeeded.job.id
    assert body["exercise"] == "lat_pulldown"
    assert body["score"] is None
    assert body["prototype_assessment"]["status"] == "partial"
    assert body["prototype_assessment"]["estimated_match"] is not None
    assert body["provenance"]["reference_id"] == "qmotion_roi"
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert body["detected_rep_count"] == 2
    measured = [m for m in body["metrics"] if m["status"] == "observed"]
    assert measured and all(m["value"] is not None for m in measured)
    torso = [m for m in measured if m["id"] == "torso_axis_angle/projected_2d/excursion"]
    assert torso and all(m["value"] == 0.0 for m in torso)


def test_unsupported_exercise_profile_200(client: TestClient, env_setup):
    from tests.integration.test_artifact_streams import _succeeded
    f = _succeeded(client, env_setup)  # squat artifacts, valid but no profile
    r = client.get(f"/v1/analyses/{f.job.id}/movement-report", headers=_headers(f.csrf))
    assert r.status_code == 200
    body = r.json()
    assert body["detected_rep_count"] is None
    assert body["detected_rep_count_unavailable_reason"] == "exercise_profile_unavailable"
    legacy = client.get(f"/v1/analyses/{f.job.id}/result", headers=_headers(f.csrf))
    assert legacy.status_code == 200
    assert legacy.json()["schema_version"] == "0.2.0"


def test_missing_estimated_3d_capability_422(client: TestClient, lat_succeeded):
    manifest = json.loads((lat_succeeded.attempt / "manifest.json").read_text())
    manifest["pose"]["capabilities"] = {"supports_2d": True}
    (lat_succeeded.attempt / "manifest.json").write_text(json.dumps(manifest))
    r = _get(client, lat_succeeded)
    assert r.status_code == 422
    assert r.json()["code"] == "UNSUPPORTED_POSE_CAPABILITY"


def test_foreign_owner_404(client: TestClient, lat_succeeded):
    client.cookies.clear()
    csrf2 = _session(client)
    r = client.get(
        f"/v1/analyses/{lat_succeeded.job.id}/movement-report", headers=_headers(csrf2)
    )
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"


def test_invalid_session_403(client: TestClient, lat_succeeded):
    client.cookies.clear()
    r = client.get(f"/v1/analyses/{lat_succeeded.job.id}/movement-report")
    assert r.status_code == 403


def test_raw_asset_deleted_404(client: TestClient, lat_succeeded):
    lat_succeeded.store.delete_asset(lat_succeeded.owner, "a" * 32)
    r = _get(client, lat_succeeded)
    assert r.status_code == 404


def test_raw_asset_expired_404(client: TestClient, lat_succeeded):
    past = (datetime.now(timezone.utc) - timedelta(seconds=1)).timestamp()
    with lat_succeeded.store._conn() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("UPDATE assets SET expires_at=? WHERE id=?", (past, "a" * 32))
        conn.execute("COMMIT")
    r = _get(client, lat_succeeded)
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"


def test_revoked_after_builder_404(client: TestClient, lat_succeeded, monkeypatch):
    import app.movement_reports as m

    real = m.build_movement_report

    def build_then_delete(*args, **kwargs):
        result = real(*args, **kwargs)
        lat_succeeded.store.delete_job(lat_succeeded.owner, lat_succeeded.job.id)
        return result

    monkeypatch.setattr(m, "build_movement_report", build_then_delete)
    r = _get(client, lat_succeeded)
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"


def test_hash_corruption_503(client: TestClient, lat_succeeded):
    (lat_succeeded.attempt / lat_succeeded.frames_key).write_bytes(b"tampered\n")
    r = _get(client, lat_succeeded)
    assert r.status_code == 503
    assert r.json()["code"] == "RESULT_UNAVAILABLE"
    assert "tampered" not in r.text


def test_symlink_pose_503(client: TestClient, lat_succeeded, tmp_path: Path):
    target = tmp_path / "secret.bin"
    target.write_bytes(b"secret")
    os.remove(lat_succeeded.attempt / lat_succeeded.frames_key)
    os.symlink(target, lat_succeeded.attempt / lat_succeeded.frames_key)
    r = _get(client, lat_succeeded)
    assert r.status_code == 503
    assert "secret" not in r.text


def test_key_traversal_503(client: TestClient, lat_succeeded):
    manifest = json.loads((lat_succeeded.attempt / "manifest.json").read_text())
    manifest["pose"]["frames_artifact_key"] = "pose/../manifest.json"
    (lat_succeeded.attempt / "manifest.json").write_text(json.dumps(manifest))
    r = _get(client, lat_succeeded)
    assert r.status_code == 503


def test_bad_mapping_503(client: TestClient, lat_succeeded):
    manifest = json.loads((lat_succeeded.attempt / "manifest.json").read_text())
    manifest["pose"]["joint_mapping_version"] = "other-v9"
    (lat_succeeded.attempt / "manifest.json").write_text(json.dumps(manifest))
    r = _get(client, lat_succeeded)
    assert r.status_code == 503


def test_out_of_order_frames_503(client: TestClient, lat_succeeded):
    frames = _lat_frames()
    frames[5] = frames[5].model_copy(update={"frame_index": 1})
    _rehash_frames(lat_succeeded, frames)
    r = _get(client, lat_succeeded)
    assert r.status_code == 503


def test_duplicate_timestamp_503(client: TestClient, lat_succeeded):
    frames = _lat_frames()
    frames[5] = frames[5].model_copy(update={"timestamp_s": frames[4].timestamp_s})
    _rehash_frames(lat_succeeded, frames)
    r = _get(client, lat_succeeded)
    assert r.status_code == 503
    assert r.json()["code"] == "RESULT_UNAVAILABLE"


def test_empty_published_artifact_503(client: TestClient, lat_succeeded):
    # A successful published artifact cannot contain zero frames; this is
    # integrity failure, distinct from the pure engine's empty-input fallback.
    _rehash_frames(lat_succeeded, [])
    assert _get(client, lat_succeeded).status_code == 503


def test_no_llm_import_or_spend(client: TestClient, lat_succeeded):
    import sys

    r = _get(client, lat_succeeded)
    assert r.status_code == 200
    assert not any(name.startswith(("openai", "anthropic", "tavily")) for name in sys.modules)
