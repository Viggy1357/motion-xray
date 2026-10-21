from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.store import Store
from contracts.jobs import AnalysisJob
from contracts.media import VideoAsset
from providers.pose.artifacts import write_pose_frames
from contracts.pose import JointObservation, PoseFrame, PoseSequence
from contracts.pose_job import PoseJobArtifacts, PoseJobInput
from contracts.proxy import ProxyTimestampMap, TimestampPair
from contracts.analysis import AnalysisResult, CoachingResult
from contracts.enums import CoachingStatus


def queued_case(tmp_path: Path) -> tuple[Store, AnalysisJob, Path]:
    store = Store(tmp_path / "jobs.sqlite3")
    now = datetime.now(timezone.utc)
    store.register_asset(VideoAsset(
        id="asset1", owner_session_id="owner", storage_key="uploads/asset1.mp4",
        sha256="a" * 64, mime="video/mp4", bytes=1024, duration_s=5,
        width=640, height=480, rotation=0, created_at=now,
        expires_at=now + timedelta(hours=1),
    ))
    job = store.enqueue("owner", "asset1", "lat_pulldown", "v1", "request1", "vhash")
    return store, job, tmp_path / "artifacts"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_pose_frames_artifact(frames: list[PoseFrame]) -> tuple[bytes, str]:
    lines = []
    for frame in frames:
        lines.append(json.dumps(frame.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), allow_nan=False).encode())
    payload = b"\n".join(lines) + b"\n"
    return payload, _sha256(payload)


def _build_fixture(tmp_path: Path):
    store, job, artifacts_root = queued_case(tmp_path)
    claimed = store.claim("pose")
    video = store.get_input("owner", claimed.id)[0]
    request = PoseJobInput(job=claimed, video=video, exercise_id="lat_pulldown", variant="v1")

    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir()

    request_bytes = request.model_dump_json().encode()
    request_sha = _sha256(request_bytes)
    (attempt_dir / "request.json").write_bytes(request_bytes)

    proxy_bytes = b"proxy fixture"
    proxy_sha = _sha256(proxy_bytes)
    proxy_dir = attempt_dir / "proxy"
    proxy_dir.mkdir()
    (proxy_dir / "proxy.mp4").write_bytes(proxy_bytes)

    proxy = ProxyTimestampMap(
        source_sha256=video.sha256,
        proxy_sha256=proxy_sha,
        source_width=640,
        source_height=480,
        source_rotation=0,
        proxy_width=640,
        proxy_height=480,
        padding_right=0,
        padding_bottom=0,
        frames=[
            TimestampPair(source_index=0, source_s=0.0, proxy_s=0.0),
            TimestampPair(source_index=1, source_s=0.1, proxy_s=0.1),
        ],
    )

    frames = [
        PoseFrame(frame_index=0, timestamp_s=0.0, joints={
            "left_shoulder": JointObservation(xy=(0.5, 0.5), valid=True, interpolated=False),
        }),
        PoseFrame(frame_index=1, timestamp_s=0.1, joints={
            "left_shoulder": JointObservation(xy=(0.5, 0.5), valid=True, interpolated=False),
        }),
    ]
    frames_bytes, frames_sha = _make_pose_frames_artifact(frames)
    frames_key = "pose/" + frames_sha + ".jsonl"

    pose = PoseSequence(
        video_id=video.id,
        provider="mediapipe",
        model_revision="sha256:" + "b" * 64,
        native_skeleton="mediapipe-33",
        joint_mapping_version="mp33-camera-v1",
        sample_rate_hz=10,
        units="model_estimated_meters_uncalibrated",
        coordinate_system="hip_relative_camera_x_right_y_up_z_toward_viewer",
        capabilities={"supports_2d": True},
        quality_method="test",
        frames_artifact_key=frames_key,
    )

    report = AnalysisResult(
        analysis_id=job.id,
        exercise=request.exercise_id,
        variant=request.variant,
        coaching=CoachingResult(status=CoachingStatus.UNAVAILABLE),
        warnings=["POSE_ONLY"],
        provenance={
            "pipeline": "pose-job-v1",
            "input_sha256": video.sha256,
            "version_hash": job.version_hash,
            "pose_model_revision": pose.model_revision,
        },
    )

    manifest = PoseJobArtifacts(
        request_sha256=request_sha,
        pose=pose,
        proxy=proxy,
        report=report,
    )

    (proxy_dir / "timestamp_map.json").write_bytes(proxy.model_dump_json().encode())
    (attempt_dir / "manifest.json").write_bytes(manifest.model_dump_json().encode())

    return {
        "store": store,
        "job": job,
        "video": video,
        "request": request,
        "request_bytes": request_bytes,
        "request_sha": request_sha,
        "proxy_bytes": proxy_bytes,
        "proxy_sha": proxy_sha,
        "proxy": proxy,
        "frames": frames,
        "frames_bytes": frames_bytes,
        "frames_sha": frames_sha,
        "frames_key": frames_key,
        "pose": pose,
        "report": report,
        "manifest": manifest,
        "attempt_dir": attempt_dir,
        "proxy_dir": proxy_dir,
    }


def test_validate_pose_artifacts_valid(tmp_path: Path):
    from app.pose_jobs import validate_pose_artifacts

    f = _build_fixture(tmp_path)
    write_pose_frames(f["attempt_dir"], f["frames_key"], f["frames"])

    result = validate_pose_artifacts(f["request"], f["request_sha"], f["attempt_dir"], "b" * 64)
    assert Path(result).name == "manifest.json"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda f: (f["attempt_dir"] / "request.json").write_bytes(b"tampered"),
        lambda f: (f["proxy_dir"] / "proxy.mp4").write_bytes(b"tampered"),
        lambda f: (f["attempt_dir"] / f["frames_key"]).write_bytes(b"tampered"),
        lambda f: _alter_manifest(f, "report", "analysis_id", "wrong-id"),
        lambda f: _alter_manifest(f, "pose", "frames_artifact_key", "pose/wronghash.jsonl"),
        lambda f: _alter_manifest(f, "report", "score", 0),
        lambda f: _alter_embedded_proxy_hash(f),
    ],
    ids=[
        "request_bytes",
        "proxy_bytes",
        "frames_bytes",
        "report_id",
        "frames_key",
        "score_zero",
        "embedded_map",
    ],
)
def test_validate_pose_artifacts_tampered(tmp_path: Path, mutate):
    from app.pose_jobs import validate_pose_artifacts

    f = _build_fixture(tmp_path)
    write_pose_frames(f["attempt_dir"], f["frames_key"], f["frames"])
    mutate(f)

    with pytest.raises((ValueError, OSError)):
        validate_pose_artifacts(f["request"], f["request_sha"], f["attempt_dir"], "b" * 64)


def _alter_manifest(f: dict, section: str, key: str, value):
    path = f["attempt_dir"] / "manifest.json"
    data = json.loads(path.read_text())
    data[section][key] = value
    path.write_bytes(json.dumps(data, sort_keys=True, separators=(",", ":")).encode())


def _alter_embedded_proxy_hash(f: dict):
    path = f["attempt_dir"] / "manifest.json"
    data = json.loads(path.read_text())
    data["proxy"]["proxy_sha256"] = "c" * 64
    path.write_bytes(json.dumps(data, sort_keys=True, separators=(",", ":")).encode())


def test_validate_pose_artifacts_gap_frame(tmp_path: Path):
    from app.pose_jobs import validate_pose_artifacts

    f = _build_fixture(tmp_path)
    gap_frames = list(f["frames"])
    gap_frames[1] = PoseFrame(frame_index=1, timestamp_s=0.1, joints={
        "left_shoulder": JointObservation(valid=False, interpolated=False),
    })
    payload, digest = _make_pose_frames_artifact(gap_frames)
    key = "pose/" + digest + ".jsonl"

    pose = f["pose"].model_copy(update={"frames_artifact_key": key})
    manifest = PoseJobArtifacts(
        request_sha256=f["request_sha"],
        pose=pose,
        proxy=f["proxy"],
        report=f["report"],
    )
    (f["attempt_dir"] / "manifest.json").write_bytes(manifest.model_dump_json().encode())
    write_pose_frames(f["attempt_dir"], key, gap_frames)

    result = validate_pose_artifacts(f["request"], f["request_sha"], f["attempt_dir"], "b" * 64)
    assert Path(result).name == "manifest.json"


@pytest.mark.parametrize("drop_expected", [False, True])
def test_source_downsampling_requires_all_selected_samples(tmp_path: Path, drop_expected: bool):
    from app.pose_jobs import validate_pose_artifacts

    f = _build_fixture(tmp_path)
    proxy = f["proxy"].model_copy(update={"frames": [
        TimestampPair(source_index=i, source_s=t, proxy_s=t)
        for i, t in enumerate([0.0, 0.016667, 0.033333])
    ]})
    frames = [f["frames"][0]]
    if not drop_expected:
        frames.append(f["frames"][1].model_copy(update={"frame_index": 2, "timestamp_s": 0.033333}))
    _, digest = _make_pose_frames_artifact(frames)
    key = f"pose/{digest}.jsonl"
    write_pose_frames(f["attempt_dir"], key, frames)
    pose = f["pose"].model_copy(update={"frames_artifact_key": key})
    manifest = f["manifest"].model_copy(update={"pose": pose, "proxy": proxy})
    (f["proxy_dir"] / "timestamp_map.json").write_text(proxy.model_dump_json())
    (f["attempt_dir"] / "manifest.json").write_text(manifest.model_dump_json())
    if drop_expected:
        with pytest.raises(ValueError, match="samples do not cover"):
            validate_pose_artifacts(f["request"], f["request_sha"], f["attempt_dir"], "b" * 64)
    else:
        assert validate_pose_artifacts(f["request"], f["request_sha"], f["attempt_dir"], "b" * 64) == "manifest.json"
