"""Private audio-free proxy builder with actual source/proxy timestamp mapping."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from contracts.media import VideoAsset
from contracts.proxy import ProxyTimestampMap, TimestampPair
from providers.pose.mediapipe_provider import VideoProbe, probe_video


_PROXY_NAME: str = "proxy.mp4"
_MAP_NAME: str = "timestamp_map.json"
_MAX_SIZE: int = 100 * 1024 * 1024
_MAX_DURATION: float = 30.0
_MAX_FRAMES: int = 7200
_MIN_FRAMES: int = 2
_TOLERANCE_DURATION: float = 0.1
_TOLERANCE_PTS: float = 0.002
_TIMEOUT_S: int = 120


def _verify_source_path(source_root: Path, storage_key: str) -> Path:
    if not storage_key or storage_key in (".", ".."):
        raise ValueError("Invalid storage_key")
    if chr(92) in storage_key:
        raise ValueError("Invalid storage_key: backslash not allowed")
    parts = storage_key.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise ValueError("Invalid storage_key component")
    path = Path(storage_key)
    if path.is_absolute():
        raise ValueError("storage_key must be relative")
    resolved_root = source_root.resolve()
    candidate = resolved_root / path
    for p in candidate.parents:
        if p == resolved_root:
            break
        if p.is_symlink():
            raise ValueError("Source path contains symlinks")
    if candidate.is_symlink():
        raise ValueError("Source path contains symlinks")
    candidate = candidate.resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError:
        raise ValueError("Source file escapes source_root")
    if not candidate.is_file():
        raise ValueError("Source file not found")
    if candidate.stat().st_size > _MAX_SIZE:
        raise ValueError("Source file exceeds 100MB")
    return candidate


def _verify_source_hash(source: Path, expected: str) -> None:
    sha = hashlib.sha256()
    with source.open("rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            sha.update(chunk)
    if sha.hexdigest() != expected:
        raise ValueError("Source file SHA256 mismatch")


def _verify_source_metadata(source: Path, asset: VideoAsset) -> VideoProbe:
    if source.stat().st_size != asset.bytes:
        raise ValueError("Source file size mismatch")
    probe = probe_video(source)
    if abs(probe.duration_s - asset.duration_s) > _TOLERANCE_DURATION:
        raise ValueError("Duration mismatch between probe and asset")
    if probe.width != asset.width or probe.height != asset.height or probe.rotation != asset.rotation:
        raise ValueError("Video metadata mismatch")
    if probe.duration_s > _MAX_DURATION + 1e-6:
        raise ValueError("Source duration exceeds 30s")
    if len(probe.timestamps) < _MIN_FRAMES or len(probe.timestamps) > _MAX_FRAMES:
        raise ValueError(f"Source frame count out of range: {len(probe.timestamps)}")
    return probe


def _ensure_private_dir(output_dir: Path) -> Path:
    for component in (output_dir, *output_dir.parents):
        if component.is_symlink():
            raise ValueError("output_dir path contains symlinks")
    resolved = output_dir.resolve()
    if resolved.is_symlink():
        raise ValueError("output_dir must not be a symlink")
    for p in resolved.parents:
        if p.is_symlink():
            raise ValueError("output_dir path contains symlinks")
    resolved.mkdir(parents=True, mode=0o700, exist_ok=True)
    if resolved.stat().st_mode & 0o777 != 0o700:
        os.chmod(resolved, 0o700)
    return resolved


def _reject_existing_outputs(output_dir: Path) -> None:
    for name in (_PROXY_NAME, _MAP_NAME):
        p = output_dir / name
        if p.exists() or p.is_symlink():
            raise ValueError(f"Output already exists: {name}")


def _build_ffmpeg_cmd(source: Path, proxy: Path) -> list[str]:
    return [
        "ffmpeg",
        "-nostdin",
        "-v", "error",
        "-protocol_whitelist", "file,pipe",
        "-format_whitelist", "mov,matroska,webm",
        "-i", str(source),
        "-map", "0:v:0",
        "-an",
        "-sn",
        "-dn",
        "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2,setpts=PTS-STARTPTS",
        "-fps_mode", "passthrough",
        "-enc_time_base", "-1",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-map_metadata", "-1",
        "-movflags", "+faststart",
        "-video_track_timescale", "1000000",
        "-n",
        str(proxy),
    ]


def _run_ffmpeg(cmd: list[str]) -> None:
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg timed out") from None
    if result.returncode != 0:
        raise RuntimeError("FFmpeg failed")


def _probe_output_streams(proxy: Path) -> list[dict[str, Any]]:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "stream=codec_type",
        "-print_format", "json",
        str(proxy),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, check=True, timeout=30)
    except subprocess.CalledProcessError:
        raise RuntimeError("FFmpeg failed") from None
    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        raise ValueError("Malformed ffprobe JSON output")
    if not isinstance(data, dict):
        raise ValueError("Malformed ffprobe JSON output")
    streams = data.get("streams", [])
    if not isinstance(streams, list):
        raise ValueError("Malformed ffprobe JSON output")
    return streams


def _verify_no_extra_streams(proxy: Path) -> None:
    streams = _probe_output_streams(proxy)
    if len(streams) != 1:
        raise ValueError("Unexpected stream type in proxy")
    for stream in streams:
        if not isinstance(stream, dict):
            raise ValueError("Malformed ffprobe JSON output")
        ctype = stream.get("codec_type")
        if ctype != "video":
            raise ValueError(f"Unexpected stream type in proxy: {ctype}")


def _compute_proxy_sha(proxy: Path) -> str:
    sha = hashlib.sha256()
    with proxy.open("rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()


def _build_timestamp_map(source_probe: VideoProbe, proxy_probe: VideoProbe, source_sha: str, proxy_sha: str) -> ProxyTimestampMap:
    if len(source_probe.timestamps) != len(proxy_probe.timestamps):
        raise ValueError(f"Frame count mismatch: source={len(source_probe.timestamps)} proxy={len(proxy_probe.timestamps)}")
    source_first = source_probe.timestamps[0]
    frames: list[TimestampPair] = []
    for i, (sts, pts) in enumerate(zip(source_probe.timestamps, proxy_probe.timestamps)):
        if abs(pts - (sts - source_first)) > _TOLERANCE_PTS:
            raise ValueError(f"PTS drift at frame {i}: proxy={pts:.6f} expected={sts - source_first:.6f}")
        frames.append(TimestampPair(source_index=i, source_s=sts, proxy_s=pts))
    sw, sh = source_probe.width, source_probe.height
    if abs(source_probe.rotation) == 90:
        sw, sh = sh, sw
    pw, ph = proxy_probe.width, proxy_probe.height
    pr = pw - sw
    pb = ph - sh
    if proxy_probe.rotation != 0 or (pw, ph) != (sw + sw % 2, sh + sh % 2):
        raise ValueError("Unexpected padding or proxy rotation")
    if pr not in (0, 1) or pb not in (0, 1):
        raise ValueError(f"Unexpected padding: right={pr} bottom={pb}")
    return ProxyTimestampMap(
        source_sha256=source_sha,
        proxy_sha256=proxy_sha,
        source_width=sw,
        source_height=sh,
        source_rotation=source_probe.rotation,
        proxy_width=pw,
        proxy_height=ph,
        padding_right=pr,
        padding_bottom=pb,
        frames=frames,
    )


def _write_json_exclusive(path: Path, data: ProxyTimestampMap) -> None:
    encoded = json.dumps(data.model_dump(mode="json"), sort_keys=True, allow_nan=False).encode("utf-8")
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _cleanup_owned(output_dir: Path, owned: set[str]) -> None:
    for name in owned:
        p = output_dir / name
        try:
            if p.exists() or p.is_symlink():
                p.unlink()
        except OSError:
            pass


def build_proxy(video: VideoAsset, source_root: Path, output_dir: Path) -> ProxyTimestampMap:
    """Build a private audio-free proxy and its timestamp map.

    Writes exactly two files into ``output_dir``:
    * ``proxy.mp4`` — the transcoded video
    * ``timestamp_map.json`` — the source-to-proxy timestamp mapping

    Raises sanitized ValueError/RuntimeError on any validation or processing
    failure. Cleans up only files written by this call on failure.
    """
    if not 0 < video.duration_s <= _MAX_DURATION:
        raise ValueError("Source duration exceeds 30s")
    out = _ensure_private_dir(output_dir)
    _reject_existing_outputs(out)
    source = _verify_source_path(source_root, video.storage_key)
    _verify_source_hash(source, video.sha256)
    source_probe = _verify_source_metadata(source, video)
    proxy = out / _PROXY_NAME
    map_path = out / _MAP_NAME
    owned: set[str] = set()
    try:
        owned.add(_PROXY_NAME)
        _run_ffmpeg(_build_ffmpeg_cmd(source, proxy))
        os.chmod(proxy, 0o600)
        owned.add(_PROXY_NAME)
        proxy_probe = probe_video(proxy)
        _verify_no_extra_streams(proxy)
        proxy_sha = _compute_proxy_sha(proxy)
        ts_map = _build_timestamp_map(source_probe, proxy_probe, video.sha256, proxy_sha)
        _write_json_exclusive(map_path, ts_map)
        owned.add(_MAP_NAME)
        return ts_map
    except BaseException:
        _cleanup_owned(out, owned)
        raise
