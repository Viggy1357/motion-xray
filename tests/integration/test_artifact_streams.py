from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.main import app
from app.session import SessionSecurity
from app.store import Store
from contracts.analysis import AnalysisResult, CoachingResult
from contracts.enums import CoachingStatus
from contracts.media import VideoAsset
from contracts.pose import JointObservation, PoseFrame, PoseSequence
from contracts.pose_job import PoseJobArtifacts
from contracts.proxy import ProxyTimestampMap, TimestampPair

PROXY_BYTES = b"proxy-bytes-0123456789abcdef" * 64  # 1664 bytes


@pytest.fixture
def env_setup(monkeypatch, tmp_path: Path):
    db_path = tmp_path / "jobs.db"
    media_path = tmp_path / "media"
    media_path.mkdir(parents=True, exist_ok=True)
    artifacts_path = tmp_path / "artifacts"
    artifacts_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("VIDEO_ROOT", str(media_path))
    monkeypatch.setenv("ARTIFACT_ROOT", str(artifacts_path))
    monkeypatch.setenv("SESSION_SECRET", "x" * 64)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_ORIGIN", "http://testserver")
    monkeypatch.setenv("MAX_UPLOAD_MB", "100")
    monkeypatch.setenv("MAX_VIDEO_SECONDS", "30")
    monkeypatch.setenv("RAW_MEDIA_TTL_HOURS", "24")
    monkeypatch.setenv("POSE_CHECKPOINT_SHA256", "b" * 64)
    monkeypatch.setenv("REPORT_TTL_DAYS", "7")
    yield tmp_path, str(db_path), str(media_path), str(artifacts_path)


@pytest.fixture
def client(env_setup):
    with TestClient(app, base_url="http://testserver") as c:
        yield c


def _session(client: TestClient) -> str:
    r = client.get("/v1/session")
    assert r.status_code == 200
    return r.json()["csrf_token"]


def _owner_from_cookie(client: TestClient) -> str:
    cookie = client.cookies["mxr_session"]
    req = Request({"type": "http", "headers": [(b"cookie", f"mxr_session={cookie}".encode())]})
    return SessionSecurity.from_environment().validate(req)


def _headers(csrf: str) -> dict[str, str]:
    return {"Origin": "http://testserver", "X-CSRF-Token": csrf}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _frames_payload(frames: list[PoseFrame]) -> bytes:
    lines = [
        json.dumps(f.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        for f in frames
    ]
    return b"\n".join(lines) + b"\n"


def _succeeded(client: TestClient, env_setup) -> SimpleNamespace:
    """Real session owner, genuine Store, job marked succeeded with artifacts on disk."""
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
    job = store.enqueue(owner, "a" * 32, "squat", "v1", "req1", "vhash")
    token = store.claim("worker")
    assert token is not None and token.lease_owner is not None
    lease = token.lease_owner

    attempt = Path(artifacts_root) / "attempts" / job.id / lease
    (attempt / "proxy").mkdir(parents=True)
    (attempt / "pose").mkdir()

    proxy_sha = _sha256(PROXY_BYTES)
    (attempt / "proxy" / "proxy.mp4").write_bytes(PROXY_BYTES)

    frames = [
        PoseFrame(frame_index=0, timestamp_s=0.0, joints={
            "left_shoulder": JointObservation(xy=(0.5, 0.5), valid=True, interpolated=False),
        }),
        PoseFrame(frame_index=1, timestamp_s=0.1, joints={
            "left_shoulder": JointObservation(xy=(0.5, 0.5), valid=True, interpolated=False),
        }),
    ]
    frames_bytes = _frames_payload(frames)
    frames_key = f"pose/{_sha256(frames_bytes)}.jsonl"
    (attempt / frames_key).write_bytes(frames_bytes)

    proxy = ProxyTimestampMap(
        source_sha256="a" * 64,
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
    (attempt / "proxy" / "timestamp_map.json").write_bytes(proxy.model_dump_json().encode())

    pose = PoseSequence(
        video_id="a" * 32,
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
        exercise="squat",
        variant="v1",
        coaching=CoachingResult(status=CoachingStatus.UNAVAILABLE),
        warnings=["POSE_ONLY"],
        provenance={
            "pipeline": "pose-job-v1",
            "input_sha256": "a" * 64,
            "version_hash": job.version_hash,
            "pose_model_revision": pose.model_revision,
        },
    )
    manifest = PoseJobArtifacts(request_sha256="c" * 64, pose=pose, proxy=proxy, report=report)
    (attempt / "manifest.json").write_bytes(manifest.model_dump_json().encode())

    result_key = f"attempts/{job.id}/{lease}/manifest.json"
    store.finish(job.id, lease, result_key=result_key)
    return SimpleNamespace(
        store=store, job=job, owner=owner, csrf=csrf, attempt=attempt,
        proxy=proxy, proxy_sha=proxy_sha, frames_bytes=frames_bytes,
        frames_key=frames_key, result_key=result_key,
    )


def test_proxy_full_200(client: TestClient, env_setup):
    f = _succeeded(client, env_setup)
    r = client.get(f"/v1/analyses/{f.job.id}/artifacts/proxy", headers=_headers(f.csrf))
    assert r.status_code == 200
    assert r.content == PROXY_BYTES
    assert r.headers["content-type"].startswith("video/mp4")
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["accept-ranges"] == "bytes"
    assert r.headers["content-length"] == str(len(PROXY_BYTES))
    assert r.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize(
    "range_header,expected",
    [
        ("bytes=0-9", PROXY_BYTES[0:10]),
        ("bytes=100-", PROXY_BYTES[100:]),
        ("bytes=-16", PROXY_BYTES[-16:]),
        (f"bytes=0-{len(PROXY_BYTES) + 1000}", PROXY_BYTES),
    ],
    ids=["explicit", "open_end", "suffix", "overshoot"],
)
def test_proxy_range_206(client: TestClient, env_setup, range_header, expected):
    f = _succeeded(client, env_setup)
    r = client.get(
        f"/v1/analyses/{f.job.id}/artifacts/proxy",
        headers={**_headers(f.csrf), "Range": range_header},
    )
    assert r.status_code == 206
    assert r.content == expected
    assert r.headers["content-range"].endswith(f"/{len(PROXY_BYTES)}")
    assert r.headers["content-length"] == str(len(expected))


@pytest.mark.parametrize(
    "range_header",
    [
        "bytes=999999-1000000",
        "bytes=10-2",
        "bytes=-0",
        "bytes=0-1,4-8",
        "bytes=-",
        "bytes=" + "1" * 19 + "-",
        "bytes=0-" + "9" * 19,
        "garbage",
    ],
    ids=["beyond", "reversed", "zero_suffix", "multi", "empty", "long_start", "long_end", "junk"],
)
def test_proxy_range_416(client: TestClient, env_setup, range_header):
    f = _succeeded(client, env_setup)
    r = client.get(
        f"/v1/analyses/{f.job.id}/artifacts/proxy",
        headers={**_headers(f.csrf), "Range": range_header},
    )
    assert r.status_code == 416
    assert r.headers["content-range"] == f"bytes */{len(PROXY_BYTES)}"
    body = r.json()
    assert set(body.keys()) == {"code", "message", "retryable"}
    assert body["code"] == "RANGE_NOT_SATISFIABLE"
    assert body["retryable"] is False


def test_pose_200_ignores_range(client: TestClient, env_setup):
    f = _succeeded(client, env_setup)
    r = client.get(
        f"/v1/analyses/{f.job.id}/artifacts/pose",
        headers={**_headers(f.csrf), "Range": "bytes=0-3"},
    )
    assert r.status_code == 200
    assert r.content == f.frames_bytes
    assert r.headers["content-type"].startswith("application/x-ndjson")
    assert "content-range" not in r.headers


def test_timestamps_200_matches_manifest(client: TestClient, env_setup):
    f = _succeeded(client, env_setup)
    r = client.get(f"/v1/analyses/{f.job.id}/artifacts/timestamps", headers=_headers(f.csrf))
    assert r.status_code == 200
    assert ProxyTimestampMap.model_validate_json(r.content) == f.proxy


def test_unknown_kind_404(client: TestClient, env_setup):
    f = _succeeded(client, env_setup)
    r = client.get(f"/v1/analyses/{f.job.id}/artifacts/video", headers=_headers(f.csrf))
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"


def test_pending_job_409(client: TestClient, env_setup):
    _, db_path, _, _ = env_setup
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
    job = store.enqueue(owner, "a" * 32, "squat", "v1", "req1", "vhash")
    r = client.get(f"/v1/analyses/{job.id}/artifacts/proxy", headers=_headers(csrf))
    assert r.status_code == 409
    assert r.json()["code"] == "RESULT_NOT_READY"


def test_cross_owner_404(client: TestClient, env_setup):
    f = _succeeded(client, env_setup)
    client.cookies.clear()
    csrf2 = _session(client)
    r = client.get(f"/v1/analyses/{f.job.id}/artifacts/proxy", headers=_headers(csrf2))
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"


def test_corrupt_manifest_503_no_leak(client: TestClient, env_setup):
    f = _succeeded(client, env_setup)
    (f.attempt / "manifest.json").write_bytes(b"PRIVATE_CORRUPT")
    r = client.get(f"/v1/analyses/{f.job.id}/artifacts/proxy", headers=_headers(f.csrf))
    assert r.status_code == 503
    assert r.json()["code"] == "RESULT_UNAVAILABLE"
    assert "PRIVATE_CORRUPT" not in r.text
    assert r.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "kind,mutate",
    [
        ("proxy", lambda f: (f.attempt / "proxy" / "proxy.mp4").write_bytes(b"tampered")),
        ("pose", lambda f: (f.attempt / f.frames_key).write_bytes(b"tampered\n")),
        ("timestamps", lambda f: (f.attempt / "proxy" / "timestamp_map.json").write_bytes(b"{}")),
    ],
    ids=["proxy_hash", "pose_hash", "map_mismatch"],
)
def test_tampered_artifact_503(client: TestClient, env_setup, kind, mutate):
    f = _succeeded(client, env_setup)
    mutate(f)
    r = client.get(f"/v1/analyses/{f.job.id}/artifacts/{kind}", headers=_headers(f.csrf))
    assert r.status_code == 503
    assert r.json()["code"] == "RESULT_UNAVAILABLE"


@pytest.mark.skipif(not os.path.isdir("/proc/self/fd"), reason="requires procfs")
def test_no_fd_leak_across_responses(client: TestClient, env_setup):
    f = _succeeded(client, env_setup)
    h = _headers(f.csrf)
    client.get(f"/v1/analyses/{f.job.id}/artifacts/proxy", headers=h)
    before = len(os.listdir("/proc/self/fd"))
    for _ in range(5):
        assert client.get(f"/v1/analyses/{f.job.id}/artifacts/proxy", headers=h).status_code == 200
        assert client.get(
            f"/v1/analyses/{f.job.id}/artifacts/proxy", headers={**h, "Range": "bytes=0-9"}
        ).status_code == 206
        assert client.get(f"/v1/analyses/{f.job.id}/artifacts/pose", headers=h).status_code == 200
        assert client.get(
            f"/v1/analyses/{f.job.id}/artifacts/proxy", headers={**h, "Range": "bytes=999999-"}
        ).status_code == 416
    after = len(os.listdir("/proc/self/fd"))
    assert after <= before


def test_stream_generator_stops_on_revocation_and_closes(tmp_path: Path, monkeypatch):
    from app import artifact_streams as m

    payload = b"x" * (m._CHUNK + 10)
    p = tmp_path / "blob.bin"
    p.write_bytes(payload)
    fileobj = open(p, "rb")

    calls = {"n": 0}

    def fake_alive(*args) -> bool:
        calls["n"] += 1
        return calls["n"] <= 1  # revoked after the first chunk

    monkeypatch.setattr(m, "_alive", fake_alive)
    gen = m._stream(fileobj, 0, len(payload), None, "owner", "job")  # type: ignore[arg-type]
    first = next(gen)
    assert first == payload[: m._CHUNK]
    assert list(gen) == []  # graceful stop, no error after bytes sent
    assert fileobj.closed


def test_stream_generator_closes_on_early_abandon(tmp_path: Path):
    import asyncio

    from app import artifact_streams as m

    p = tmp_path / "blob.bin"
    p.write_bytes(b"y" * 4096)
    fileobj = open(p, "rb")
    gen = m._stream(fileobj, 0, 4096, None, "owner", "job")  # type: ignore[arg-type]
    response = m._ArtifactResponse(fileobj, gen)

    async def receive():
        return {"type": "http.disconnect"}

    async def send(message):
        raise RuntimeError("client connection failed before body iteration")

    with pytest.raises(ExceptionGroup) as caught:
        asyncio.run(response({"type": "http", "asgi": {"spec_version": "2.4"}}, receive, send))
    assert any(isinstance(exc, RuntimeError) and "client connection failed" in str(exc)
               for exc in caught.value.exceptions)
    assert fileobj.closed
