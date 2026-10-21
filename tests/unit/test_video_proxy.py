"""Offline unit tests for providers.pose.proxy build_proxy."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from contracts.media import VideoAsset
from contracts.proxy import ProxyTimestampMap
from providers.pose.mediapipe_provider import VideoProbe
from providers.pose.proxy import build_proxy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_asset(source_path: Path, **overrides: Any) -> VideoAsset:
    data = source_path.read_bytes()
    defaults = dict(
        id="vid-1",
        owner_session_id="sess-1",
        storage_key="demo/source.bin",
        sha256=_sha256(data),
        mime="video/mp4",
        bytes=len(data),
        duration_s=1.0,
        width=640,
        height=480,
        rotation=0,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        expires_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return VideoAsset(**defaults)


def _fake_ffprobe(cmd: list[str]) -> subprocess.CompletedProcess:
    """Return a CompletedProcess with a video stream for ffprobe."""
    return subprocess.CompletedProcess(
        args=cmd,
        returncode=0,
        stdout=json.dumps({"streams": [{"codec_type": "video"}]}).encode(),
    )


def _make_source_probe(timestamps: list[float], **kw: Any) -> VideoProbe:
    defaults = dict(duration_s=1.0, width=640, height=480, rotation=0)
    defaults.update(kw)
    return VideoProbe(timestamps=timestamps, **defaults)


def _make_proxy_probe(timestamps: list[float], **kw: Any) -> VideoProbe:
    defaults = dict(duration_s=1.0, width=640, height=480, rotation=0)
    defaults.update(kw)
    return VideoProbe(timestamps=timestamps, **defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def source_file(tmp_path: Path) -> Path:
    root = tmp_path / "source_root" / "demo"
    root.mkdir(parents=True)
    src = root / "source.bin"
    src.write_bytes(b"actual-source-bytes-" + os.urandom(32))
    return src


@pytest.fixture
def asset(source_file: Path) -> VideoAsset:
    return _make_asset(source_file)


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    return tmp_path / "output"


# ---------------------------------------------------------------------------
# Parameterised source-probe / proxy-probe pairs
# ---------------------------------------------------------------------------

SOURCE_TS = [0.0, 0.03, 0.07]
PROXY_TS = [0.0, 0.03, 0.07]

# ---------------------------------------------------------------------------
# Core success case
# ---------------------------------------------------------------------------

def test_build_proxy_success(source_file: Path, asset: VideoAsset, output_dir: Path) -> None:
    """Happy path: timestamps persisted, source unchanged, proxy 0600."""
    source_probe = _make_source_probe(SOURCE_TS)
    proxy_probe = _make_proxy_probe(PROXY_TS)

    def fake_probe(path: Path) -> VideoProbe:
        return source_probe if "source" in str(path) else proxy_probe

    def fake_run(cmd: list[str], **kw: Any) -> subprocess.CompletedProcess:
        if cmd[0] == "ffmpeg":
            Path(cmd[-1]).write_bytes(b"proxy-content")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"", stderr=b"")
        return _fake_ffprobe(cmd)

    with patch("providers.pose.proxy.probe_video", side_effect=fake_probe):
        with patch("subprocess.run", side_effect=fake_run):
            result = build_proxy(asset, source_file.parent.parent, output_dir)

    assert isinstance(result, ProxyTimestampMap)
    assert result.source_sha256 == asset.sha256
    proxy_path = output_dir / "proxy.mp4"
    map_path = output_dir / "timestamp_map.json"
    assert proxy_path.exists()
    assert map_path.exists()
    assert proxy_path.stat().st_mode & 0o777 == 0o600
    assert hashlib.sha256(source_file.read_bytes()).hexdigest() == asset.sha256
    assert len(result.frames) == 3
    for i, pair in enumerate(result.frames):
        assert pair.source_index == i
        assert pair.source_s == SOURCE_TS[i]
        assert pair.proxy_s == PROXY_TS[i]


# ---------------------------------------------------------------------------
# Non-zero original PTS mapping
# ---------------------------------------------------------------------------

def test_nonzero_start_pts(source_file: Path, asset: VideoAsset, output_dir: Path) -> None:
    """Source timestamps [1, 1.03, 1.07] map to proxy [0, .03, .07]."""
    source_probe = _make_source_probe([1.0, 1.03, 1.07])
    proxy_probe = _make_proxy_probe([0.0, 0.03, 0.07])

    def fake_probe(path: Path) -> VideoProbe:
        return source_probe if "source" in str(path) else proxy_probe

    def fake_run(cmd: list[str], **kw: Any) -> subprocess.CompletedProcess:
        if cmd[0] == "ffmpeg":
            Path(cmd[-1]).write_bytes(b"proxy-content")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"", stderr=b"")
        return _fake_ffprobe(cmd)

    with patch("providers.pose.proxy.probe_video", side_effect=fake_probe):
        with patch("subprocess.run", side_effect=fake_run):
            result = build_proxy(asset, source_file.parent.parent, output_dir)

    assert result.frames[0].proxy_s == 0.0
    assert result.frames[1].proxy_s == pytest.approx(0.03, abs=0.001)
    assert result.frames[2].proxy_s == pytest.approx(0.07, abs=0.001)


# ---------------------------------------------------------------------------
# Rotation with padding
# ---------------------------------------------------------------------------

def test_rotation_90_with_padding(source_file: Path, asset: VideoAsset, output_dir: Path) -> None:
    """Source rotation 90 encoded 640x479 -> display 479x640 padded 480x640."""
    asset = asset.model_copy(update={"rotation": 90, "width": 640, "height": 480})
    source_probe = _make_source_probe(SOURCE_TS, rotation=90, width=640, height=480)
    proxy_probe = _make_proxy_probe(PROXY_TS, width=480, height=640)

    def fake_probe(path: Path) -> VideoProbe:
        return source_probe if "source" in str(path) else proxy_probe

    def fake_run(cmd: list[str], **kw: Any) -> subprocess.CompletedProcess:
        if cmd[0] == "ffmpeg":
            Path(cmd[-1]).write_bytes(b"proxy-content")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"", stderr=b"")
        return _fake_ffprobe(cmd)

    with patch("providers.pose.proxy.probe_video", side_effect=fake_probe):
        with patch("subprocess.run", side_effect=fake_run):
            result = build_proxy(asset, source_file.parent.parent, output_dir)

    assert result.source_rotation == 90
    assert result.source_width == 480
    assert result.source_height == 640
    assert result.proxy_width == 480
    assert result.proxy_height == 640
    assert result.padding_right == 0
    assert result.padding_bottom == 0


# ---------------------------------------------------------------------------
# Rejected inputs
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_key,expected_msg", [
    ("", "Invalid storage_key"),
    (".", "Invalid storage_key"),
    ("..", "Invalid storage_key"),
    ("foo/bar/..", "Invalid storage_key component"),
    ("foo//bar", "Invalid storage_key component"),
    ("foo\\bar", "Invalid storage_key: backslash not allowed"),
    ("/absolute", "Invalid storage_key component"),
])
def test_invalid_storage_key(source_file: Path, asset: VideoAsset, output_dir: Path, bad_key: str, expected_msg: str) -> None:
    asset = asset.model_copy(update={"storage_key": bad_key})
    with pytest.raises(ValueError, match=expected_msg):
        build_proxy(asset, source_file.parent.parent, output_dir)


def test_hash_mismatch(source_file: Path, asset: VideoAsset, output_dir: Path) -> None:
    asset = asset.model_copy(update={"sha256": "0" * 64})
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        build_proxy(asset, source_file.parent.parent, output_dir)


def test_directory_traversal(source_file: Path, asset: VideoAsset, output_dir: Path) -> None:
    asset = asset.model_copy(update={"storage_key": "../outside.bin"})
    with pytest.raises(ValueError, match="Invalid storage_key component"):
        build_proxy(asset, source_file.parent.parent, output_dir)


def test_symlink_inside_root(source_file: Path, asset: VideoAsset, output_dir: Path) -> None:
    root = source_file.parent.parent
    link_dir = root / "link_demo"
    link_dir.symlink_to(source_file.parent, target_is_directory=True)
    asset = asset.model_copy(update={"storage_key": "link_demo/source.bin"})
    with pytest.raises(ValueError, match="symlinks"):
        build_proxy(asset, root, output_dir)


def test_symlink_outside_root(source_file: Path, asset: VideoAsset, output_dir: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"outside")
    root = source_file.parent.parent
    link = root / "demo" / "link.bin"
    link.symlink_to(outside)
    asset = asset.model_copy(update={"storage_key": "demo/link.bin"})
    with pytest.raises(ValueError, match="symlinks"):
        build_proxy(asset, root, output_dir)


def test_source_too_long(source_file: Path, asset: VideoAsset, output_dir: Path) -> None:
    asset = asset.model_copy(update={"duration_s": 31.0})
    with pytest.raises(ValueError, match="exceeds 30s"):
        build_proxy(asset, source_file.parent.parent, output_dir)


# ---------------------------------------------------------------------------
# Proxy validation failures (no partial outputs)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("proxy_probe_kw,expected_msg", [
    ({"timestamps": [0.0, 0.03]}, "Frame count mismatch"),
    ({"timestamps": [0.0, 0.05, 0.09]}, "PTS drift"),
    ({"timestamps": [0.0, 0.03, 0.07], "width": 320, "height": 240}, "Unexpected padding"),
])
def test_proxy_validation_rejected(source_file: Path, asset: VideoAsset, output_dir: Path, proxy_probe_kw: dict[str, Any], expected_msg: str) -> None:
    source_probe = _make_source_probe(SOURCE_TS)
    proxy_probe = _make_proxy_probe(**proxy_probe_kw)

    def fake_probe(path: Path) -> VideoProbe:
        return source_probe if "source" in str(path) else proxy_probe

    def fake_run(cmd: list[str], **kw: Any) -> subprocess.CompletedProcess:
        if cmd[0] == "ffmpeg":
            Path(cmd[-1]).write_bytes(b"proxy-content")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"", stderr=b"")
        return _fake_ffprobe(cmd)

    with patch("providers.pose.proxy.probe_video", side_effect=fake_probe):
        with patch("subprocess.run", side_effect=fake_run):
            with pytest.raises(ValueError, match=expected_msg):
                build_proxy(asset, source_file.parent.parent, output_dir)

    assert not (output_dir / "proxy.mp4").exists()
    assert not (output_dir / "timestamp_map.json").exists()


def test_extra_audio_stream_rejected(source_file: Path, asset: VideoAsset, output_dir: Path) -> None:
    source_probe = _make_source_probe(SOURCE_TS)
    proxy_probe = _make_proxy_probe(PROXY_TS)

    def fake_probe(path: Path) -> VideoProbe:
        return source_probe if "source" in str(path) else proxy_probe

    def fake_run(cmd: list[str], **kw: Any) -> subprocess.CompletedProcess:
        if cmd[0] == "ffmpeg":
            Path(cmd[-1]).write_bytes(b"proxy-content")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"", stderr=b"")
        # ffprobe returns an audio stream
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps({"streams": [{"codec_type": "audio"}]}).encode(),
        )

    with patch("providers.pose.proxy.probe_video", side_effect=fake_probe):
        with patch("subprocess.run", side_effect=fake_run):
            with pytest.raises(ValueError, match="audio"):
                build_proxy(asset, source_file.parent.parent, output_dir)

    assert not (output_dir / "proxy.mp4").exists()


# ---------------------------------------------------------------------------
# Existing outputs preserved
# ---------------------------------------------------------------------------

def test_existing_proxy_preserved(source_file: Path, asset: VideoAsset, output_dir: Path) -> None:
    output_dir.mkdir(parents=True)
    existing = output_dir / "proxy.mp4"
    existing.write_bytes(b"old")
    with pytest.raises(ValueError, match="already exists"):
        build_proxy(asset, source_file.parent.parent, output_dir)
    assert existing.read_bytes() == b"old"


def test_existing_map_preserved(source_file: Path, asset: VideoAsset, output_dir: Path) -> None:
    output_dir.mkdir(parents=True)
    existing = output_dir / "timestamp_map.json"
    existing.write_bytes(b"old")
    with pytest.raises(ValueError, match="already exists"):
        build_proxy(asset, source_file.parent.parent, output_dir)
    assert existing.read_bytes() == b"old"


# ---------------------------------------------------------------------------
# FFmpeg failure cleanup
# ---------------------------------------------------------------------------

def test_ffmpeg_nonzero_exit_cleans_up(source_file: Path, asset: VideoAsset, output_dir: Path) -> None:
    source_probe = _make_source_probe(SOURCE_TS)

    def fake_probe(path: Path) -> VideoProbe:
        return source_probe

    def fake_run(cmd: list[str], **kw: Any) -> subprocess.CompletedProcess:
        if cmd[0] == "ffmpeg":
            # write partial file then fail
            Path(cmd[-1]).write_bytes(b"partial")
            return subprocess.CompletedProcess(args=cmd, returncode=1)
        return _fake_ffprobe(cmd)

    with patch("providers.pose.proxy.probe_video", side_effect=fake_probe):
        with patch("subprocess.run", side_effect=fake_run):
            with pytest.raises(RuntimeError, match="FFmpeg failed"):
                build_proxy(asset, source_file.parent.parent, output_dir)

    assert not (output_dir / "proxy.mp4").exists()
    assert not (output_dir / "timestamp_map.json").exists()


def test_ffmpeg_timeout_cleans_up(source_file: Path, asset: VideoAsset, output_dir: Path) -> None:
    source_probe = _make_source_probe(SOURCE_TS)

    def fake_probe(path: Path) -> VideoProbe:
        return source_probe

    def fake_run(cmd: list[str], **kw: Any) -> subprocess.CompletedProcess:
        if cmd[0] == "ffmpeg":
            Path(cmd[-1]).write_bytes(b"partial")
            raise subprocess.TimeoutExpired(cmd, timeout=120)
        return _fake_ffprobe(cmd)

    with patch("providers.pose.proxy.probe_video", side_effect=fake_probe):
        with patch("subprocess.run", side_effect=fake_run):
            with pytest.raises(RuntimeError, match="timed out"):
                build_proxy(asset, source_file.parent.parent, output_dir)

    assert not (output_dir / "proxy.mp4").exists()


# ---------------------------------------------------------------------------
# Timestamp map model validation (malformed hash / frame order)
# ---------------------------------------------------------------------------

def test_timestamp_map_malformed_hash_rejected(source_file: Path, asset: VideoAsset, output_dir: Path) -> None:
    """ProxyTimestampMap post-init rejects bad SHA256."""
    source_probe = _make_source_probe(SOURCE_TS)
    proxy_probe = _make_proxy_probe(PROXY_TS)

    def fake_probe(path: Path) -> VideoProbe:
        return source_probe if "source" in str(path) else proxy_probe

    def fake_run(cmd: list[str], **kw: Any) -> subprocess.CompletedProcess:
        if cmd[0] == "ffmpeg":
            Path(cmd[-1]).write_bytes(b"proxy-content")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"", stderr=b"")
        return _fake_ffprobe(cmd)

    # Patch _compute_proxy_sha to return invalid hash so map build fails validation
    with patch("providers.pose.proxy._compute_proxy_sha", return_value="badhash"):
        with patch("providers.pose.proxy.probe_video", side_effect=fake_probe):
            with patch("subprocess.run", side_effect=fake_run):
                with pytest.raises(ValueError, match="proxy_sha256 must be 64"):
                    build_proxy(asset, source_file.parent.parent, output_dir)

    assert not (output_dir / "timestamp_map.json").exists()


def test_timestamp_map_frame_order_rejected(source_file: Path, asset: VideoAsset, output_dir: Path) -> None:
    """ProxyTimestampMap post-init rejects non-increasing proxy_s."""
    source_probe = _make_source_probe(SOURCE_TS)
    proxy_probe = _make_proxy_probe([0.0, 0.03, 0.029])  # out of order

    def fake_probe(path: Path) -> VideoProbe:
        return source_probe if "source" in str(path) else proxy_probe

    def fake_run(cmd: list[str], **kw: Any) -> subprocess.CompletedProcess:
        if cmd[0] == "ffmpeg":
            Path(cmd[-1]).write_bytes(b"proxy-content")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"", stderr=b"")
        return _fake_ffprobe(cmd)

    with patch("providers.pose.proxy.probe_video", side_effect=fake_probe):
        with patch("subprocess.run", side_effect=fake_run):
            with pytest.raises(ValueError, match="PTS drift"):
                build_proxy(asset, source_file.parent.parent, output_dir)

    assert not (output_dir / "timestamp_map.json").exists()


def test_output_directory_symlink_does_not_write_to_target(tmp_path: Path, source_file: Path, asset: VideoAsset) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / "keep"
    marker.write_bytes(b"untouched")
    alias = tmp_path / "output-link"
    alias.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        build_proxy(asset, source_file.parent.parent, alias)
    assert marker.read_bytes() == b"untouched"
    assert sorted(path.name for path in outside.iterdir()) == ["keep"]


@pytest.mark.parametrize("proxy_width,rotation", [(641, 0), (642, 90)])
def test_proxy_geometry_cannot_silently_change_display_transform(proxy_width: int, rotation: int) -> None:
    from providers.pose.proxy import _build_timestamp_map
    source = _make_source_probe(SOURCE_TS, width=641)
    proxy = _make_proxy_probe(PROXY_TS, width=proxy_width, rotation=rotation)
    with pytest.raises(ValueError, match="Unexpected padding or proxy rotation"):
        _build_timestamp_map(source, proxy, "a" * 64, "b" * 64)
