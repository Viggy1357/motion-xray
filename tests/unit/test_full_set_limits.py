"""Full-set 60s/100MiB limit tests (offline; no real media or inference).

Gaps: no end-to-end 60s real clip is exercised here; ingest/proxy paths are
verified with mocked probes and static fixtures only. MAX_FRAMES=7200 in
proxy.py and probe_video's 7200-frame cap remain sufficient for 60s at up
to 120fps (60*120=7200); 60s at 240fps would exceed it, but intake fps cap
is 240 and proxy cap is unchanged by design (not relaxed per scope).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.ingest import MediaInfo, UploadRejected, ingest_video, probe_media
from app.store import Store
from app.uploads import _parse_config
from contracts.pose_job import PoseJobInput
from providers.pose.mediapipe_provider import MediaPipePoseProvider
from providers.pose.proxy import build_proxy

from tests.unit.test_ingest import FakeRequest, _make_probe_result, _run  # noqa: E501


def _cfg_env(monkeypatch, **over):
    for k in ("MAX_UPLOAD_MB", "MAX_VIDEO_SECONDS", "RAW_MEDIA_TTL_HOURS",
              "DATABASE_URL", "VIDEO_ROOT"):
        monkeypatch.delenv(k, raising=False)
    for k, v in over.items():
        monkeypatch.setenv(k, v)


def test_api_config_default_max_duration_60(monkeypatch):
    _cfg_env(monkeypatch)
    max_mb, max_dur, ttl_h, db_path, video_root = _parse_config()
    assert max_mb == 100
    assert max_dur == 60.0


def test_api_config_accepts_60_rejects_61(monkeypatch):
    _cfg_env(monkeypatch, MAX_VIDEO_SECONDS="60")
    assert _parse_config()[1] == 60.0
    _cfg_env(monkeypatch, MAX_VIDEO_SECONDS="61")
    with pytest.raises(Exception) as exc:
        _parse_config()
    assert "MAX_VIDEO_SECONDS" in str(exc.value)


@pytest.mark.parametrize("raw", ["nan", "inf", "-inf", "true", "0", "-1"])
def test_api_config_rejects_bool_nan_inf(monkeypatch, raw):
    _cfg_env(monkeypatch, MAX_VIDEO_SECONDS=raw)
    with pytest.raises(Exception):
        _parse_config()


def test_probe_media_accepts_60_rejects_61():
    ok = _make_probe_result(duration="60.0")
    with patch("subprocess.run", return_value=MagicMock(stdout=ok, returncode=0)):
        info = probe_media(Path("/tmp/f.mp4"), "video/mp4")
    assert info.duration_s == 60.0
    over = _make_probe_result(duration="61.0")
    with patch("subprocess.run", return_value=MagicMock(stdout=over, returncode=0)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/f.mp4"), "video/mp4")
    assert exc.value.status_code == 422


def test_ingest_accepts_60s_with_mock_probe(tmp_path: Path):
    store = Store(tmp_path / "s.db")
    data = b"\x00\x00\x00\x18ftypmp42" + b"x" * 100
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4",
                 "content-length": str(len(data))},
        chunks=[data],
    )
    mi = MediaInfo(duration_s=60.0, width=640, height=480, rotation=0,
                   mime="video/mp4")
    with patch("app.ingest.probe_media", return_value=mi):
        asset = _run(ingest_video(req, store, tmp_path / "up", "a" * 32,
                                  now=1000.0))
    assert asset.duration_s == 60.0


def test_ingest_rejects_config_duration_61():
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4"},
        chunks=[b"x"],
    )
    with pytest.raises(UploadRejected) as exc:
        _run(ingest_video(req, MagicMock(), Path("/tmp/r"), "a" * 32,
                          max_duration_s=61))
    assert exc.value.status_code == 503
    assert exc.value.code == "CONFIG_INVALID"


def _pose_job_input(tmp_path: Path, duration_s: float) -> PoseJobInput:
    store = Store(tmp_path / "jobs.sqlite3")
    now = datetime.now(timezone.utc)
    from contracts.media import VideoAsset
    store.register_asset(VideoAsset(
        id="asset1", owner_session_id="owner",
        storage_key="uploads/asset1.mp4", sha256="a" * 64,
        mime="video/mp4", bytes=1024, duration_s=duration_s,
        width=640, height=480, rotation=0, created_at=now,
        expires_at=now + timedelta(hours=1),
    ))
    store.enqueue("owner", "asset1", "lat_pulldown", "v1", "request1", "vh")
    claimed = store.claim("pose")
    video = store.get_input("owner", claimed.id)[0]
    return PoseJobInput(job=claimed, video=video,
                        exercise_id="lat_pulldown", variant="v1")


def test_pose_job_input_accepts_60(tmp_path: Path):
    assert _pose_job_input(tmp_path, 60.0).video.duration_s == 60.0


def test_pose_job_input_rejects_61(tmp_path: Path):
    with pytest.raises(ValueError, match=r"\(0, 60\]"):
        _pose_job_input(tmp_path, 61.0)


def test_provider_duration_60_accepted_61_rejected():
    p = MediaPipePoseProvider(checkpoint_path="/x.task",
                              checkpoint_sha256="a" * 64, duration_s=60)
    assert p._duration_s == 60.0
    with pytest.raises(ValueError, match=r"\(0, 60\]"):
        MediaPipePoseProvider(checkpoint_path="/x.task",
                              checkpoint_sha256="a" * 64, duration_s=61)


def test_proxy_header_accepts_60_rejects_61(tmp_path: Path):
    from contracts.media import VideoAsset
    now = datetime.now(timezone.utc)
    base = dict(id="v1", owner_session_id="s1",
                storage_key="demo/source.bin", sha256="a" * 64,
                mime="video/mp4", bytes=10, width=640, height=480,
                rotation=0, created_at=now,
                expires_at=now + timedelta(hours=1))
    ok = VideoAsset(**base, duration_s=60.0)
    # 60s passes the duration gate; fails later on missing static source file.
    with pytest.raises(ValueError, match="not found"):
        build_proxy(ok, tmp_path / "src", tmp_path / "out")
    over = VideoAsset(**base, duration_s=61.0)
    with pytest.raises(ValueError, match="exceeds 60s"):
        build_proxy(over, tmp_path / "src", tmp_path / "out2")


def test_processing_recipe_includes_media_limits():
    from app.processing_config import DEFAULT_CHECKPOINT_SHA256, processing_version
    v = processing_version(DEFAULT_CHECKPOINT_SHA256)
    recipe = {
        "pipeline": "pose-job-v1",
        "checkpoint_sha256": DEFAULT_CHECKPOINT_SHA256,
        "mapping": "mp33-camera-v1",
        "sample_rate_hz": 30,
        "visibility_threshold": 0.6,
        "media_limits_version": "full-set-60s-v3",
        "max_duration_s": 60,
        "decoder_wall_budget_s": 120,
        "timestamp_probe_budget_s": 90,
    }
    import hashlib
    expected = hashlib.sha256(
        json.dumps(recipe, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert v == expected
