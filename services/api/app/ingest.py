from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any

from fastapi import Request
from starlette.concurrency import run_in_threadpool
from starlette.requests import ClientDisconnect

from app.store import Store
from contracts.media import VideoAsset


class UploadRejected(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class MediaInfo:
    duration_s: float
    width: int
    height: int
    rotation: int
    mime: str


_ALLOWED_CODECS = {"h264", "hevc", "vp8", "vp9", "av1"}
_MIME_TO_FORMATS = {
    "video/mp4": {"mov", "mp4", "m4a", "3gp", "3g2", "mj2"},
    "video/quicktime": {"mov", "mp4", "m4a", "3gp", "3g2", "mj2"},
    "video/webm": {"matroska", "webm"},
}


def _parse_rotation(val: Any) -> int:
    if isinstance(val, bool):
        raise UploadRejected(422, "INVALID_MEDIA", "invalid rotation")
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        if val != val or val == float("inf") or val == float("-inf"):
            raise UploadRejected(422, "INVALID_MEDIA", "invalid rotation")
        if val != int(val):
            raise UploadRejected(422, "INVALID_MEDIA", "invalid rotation")
        return int(val)
    if isinstance(val, str):
        if not re.fullmatch(r"-?\d+", val):
            raise UploadRejected(422, "INVALID_MEDIA", "invalid rotation")
        return int(val)
    raise UploadRejected(422, "INVALID_MEDIA", "invalid rotation")


def probe_media(path: Path, declared_mime: str, *, max_duration_s: float = 30) -> MediaInfo:
    if declared_mime not in _MIME_TO_FORMATS:
        raise UploadRejected(415, "INVALID_MEDIA", "unsupported mime type")

    if not (isinstance(max_duration_s, (int, float)) and not isinstance(max_duration_s, bool)
            and max_duration_s > 0 and max_duration_s <= 30
            and max_duration_s == max_duration_s and max_duration_s != float("inf")):
        raise UploadRejected(503, "CONFIG_INVALID", "invalid max_duration_s")

    args = [
        "ffprobe",
        "-v", "error",
        "-protocol_whitelist", "file,pipe",
        "-format_whitelist", "mov,matroska,webm",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height,avg_frame_rate:stream_side_data=rotation:stream_tags=rotate:format=duration,format_name",
        "-of", "json",
        str(path),
    ]

    try:
        result = subprocess.run(args, capture_output=True, check=True, timeout=30)
    except subprocess.TimeoutExpired:
        raise UploadRejected(422, "INVALID_MEDIA", "probe timeout")
    except FileNotFoundError:
        raise UploadRejected(503, "MEDIA_VALIDATOR_UNAVAILABLE", "ffprobe not found")
    except subprocess.CalledProcessError:
        raise UploadRejected(422, "INVALID_MEDIA", "probe failed")

    if len(result.stdout) > 65536:
        raise UploadRejected(422, "INVALID_MEDIA", "probe output too large")

    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise UploadRejected(422, "INVALID_MEDIA", "invalid probe output")

    if not isinstance(data, dict):
        raise UploadRejected(422, "INVALID_MEDIA", "invalid probe output")

    streams = data.get("streams")
    if not isinstance(streams, list) or len(streams) != 1:
        raise UploadRejected(422, "INVALID_MEDIA", "invalid stream count")

    stream = streams[0]
    if not isinstance(stream, dict):
        raise UploadRejected(422, "INVALID_MEDIA", "invalid stream")

    fmt = data.get("format", {})
    if not isinstance(fmt, dict):
        raise UploadRejected(422, "INVALID_MEDIA", "invalid format")

    codec = stream.get("codec_name")
    if not isinstance(codec, str) or codec.lower() not in _ALLOWED_CODECS:
        raise UploadRejected(422, "INVALID_MEDIA", "unsupported video codec")

    format_name = fmt.get("format_name", "")
    if not isinstance(format_name, str):
        raise UploadRejected(422, "INVALID_MEDIA", "invalid format")
    actual_formats = set(format_name.split(","))
    allowed = _MIME_TO_FORMATS[declared_mime]
    if not actual_formats.intersection(allowed):
        raise UploadRejected(422, "INVALID_MEDIA", "container format mismatch")

    duration_raw = fmt.get("duration")
    if duration_raw is None:
        raise UploadRejected(422, "INVALID_MEDIA", "missing duration")
    try:
        duration = float(duration_raw)
    except (ValueError, TypeError):
        raise UploadRejected(422, "INVALID_MEDIA", "invalid duration")
    if isinstance(duration_raw, bool) or not (0 < duration <= max_duration_s) or duration != duration or duration == float("inf"):
        raise UploadRejected(422, "INVALID_MEDIA", "duration out of range")

    width = stream.get("width")
    height = stream.get("height")
    if not isinstance(width, int) or not isinstance(height, int) or isinstance(width, bool) or isinstance(height, bool):
        raise UploadRejected(422, "INVALID_MEDIA", "invalid dimensions")
    if not (1 <= width <= 1920 and 1 <= height <= 1920):
        raise UploadRejected(422, "INVALID_MEDIA", "dimensions out of range")

    fps_raw = stream.get("avg_frame_rate", "")
    if not isinstance(fps_raw, str) or not fps_raw:
        raise UploadRejected(422, "INVALID_MEDIA", "invalid frame rate")
    try:
        fps_frac = Fraction(fps_raw)
    except (ValueError, ZeroDivisionError, OverflowError):
        raise UploadRejected(422, "INVALID_MEDIA", "invalid frame rate")
    fps_val = float(fps_frac)
    if fps_val <= 0 or fps_val > 240 or fps_val != fps_val or fps_val == float("inf"):
        raise UploadRejected(422, "INVALID_MEDIA", "frame rate out of range")

    rotation: int | None = None
    side_data = stream.get("side_data_list")
    if side_data is not None:
        if not isinstance(side_data, list):
            raise UploadRejected(422, "INVALID_MEDIA", "invalid side_data")
        if any(not isinstance(entry, dict) for entry in side_data):
            raise UploadRejected(422, "INVALID_MEDIA", "invalid side_data")
        for entry in side_data:
            if isinstance(entry, dict) and "rotation" in entry:
                rotation = _parse_rotation(entry["rotation"])
                break

    if rotation is None:
        tags = stream.get("tags")
        if tags is not None:
            if not isinstance(tags, dict):
                raise UploadRejected(422, "INVALID_MEDIA", "invalid tags")
            if "rotate" in tags:
                rotation = _parse_rotation(tags["rotate"])

    if rotation is None:
        rotation = 0

    if rotation not in (0, 90, -90, 180, -180):
        raise UploadRejected(422, "INVALID_MEDIA", "invalid rotation")

    return MediaInfo(duration_s=duration, width=width, height=height, rotation=rotation, mime=declared_mime)


def _check_duplicate_headers(request: Request) -> None:
    for name in ("content-length", "content-type", "x-upload-consent"):
        raw = request.headers.getlist(name) if hasattr(request.headers, "getlist") else None
        if raw is not None and len(raw) > 1:
            raise UploadRejected(400, "INVALID_MEDIA", f"duplicate {name}")


def _check_symlink(path: Path) -> bool:
    return path.is_symlink()


def _rmdir_if_owned(path: Path) -> None:
    try:
        if path.exists():
            path.rmdir()
    except OSError:
        pass


def _rmrf_if_owned(path: Path) -> None:
    import shutil
    try:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass


async def ingest_video(
    request: Request,
    store: Store,
    root: Path,
    owner: str,
    *,
    now: float | None = None,
    max_bytes: int = 104857600,
    max_duration_s: float = 30,
    ttl_s: float = 86400,
) -> VideoAsset:
    _check_duplicate_headers(request)

    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes <= 0 or max_bytes > 104857600:
        raise UploadRejected(503, "CONFIG_INVALID", "invalid max_bytes")
    if not isinstance(max_duration_s, (int, float)) or isinstance(max_duration_s, bool) or max_duration_s <= 0 or max_duration_s > 30 or max_duration_s != max_duration_s or max_duration_s == float("inf"):
        raise UploadRejected(503, "CONFIG_INVALID", "invalid max_duration_s")
    if not isinstance(ttl_s, (int, float)) or isinstance(ttl_s, bool) or ttl_s <= 0 or ttl_s > 86400 or ttl_s != ttl_s or ttl_s == float("inf"):
        raise UploadRejected(503, "CONFIG_INVALID", "invalid ttl_s")

    if now is None:
        now = time.time()
    if not isinstance(now, (int, float)) or isinstance(now, bool) or now < 0 or now != now or now == float("inf") or now == float("-inf"):
        raise UploadRejected(503, "CONFIG_INVALID", "invalid clock")
    try:
        datetime.fromtimestamp(float(now) + float(ttl_s), tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        raise UploadRejected(503, "CONFIG_INVALID", "invalid clock")

    if not isinstance(owner, str) or not re.fullmatch(r"[0-9a-f]{32}", owner):
        raise ValueError("owner must be 32 lowercase hex chars")

    consent = request.headers.get("x-upload-consent")
    if consent != "true":
        raise UploadRejected(400, "CONSENT_REQUIRED", "upload consent required")

    content_type = request.headers.get("content-type", "")
    if content_type:
        mime = content_type.split(";")[0].strip().lower()
    else:
        mime = ""
    if mime not in _MIME_TO_FORMATS:
        raise UploadRejected(415, "INVALID_MEDIA", "unsupported content type")

    content_length = request.headers.get("content-length")
    declared_len: int | None = None
    if content_length is not None:
        if not re.fullmatch(r"\d+", content_length) or len(content_length) > 12:
            raise UploadRejected(400, "INVALID_MEDIA", "invalid content length")
        try:
            declared_len = int(content_length)
        except ValueError:
            raise UploadRejected(400, "INVALID_MEDIA", "invalid content length")
        if declared_len < 0:
            raise UploadRejected(400, "INVALID_MEDIA", "invalid content length")
        if declared_len > max_bytes:
            raise UploadRejected(413, "INVALID_MEDIA", "content too large")

    root_resolved = root.resolve()
    if _check_symlink(root_resolved):
        raise UploadRejected(503, "CONFIG_INVALID", "root is symlink")

    asset_id = os.urandom(16).hex()
    final_rel = Path("uploads") / owner / asset_id
    final_dir = root_resolved / final_rel

    staging_dir: Path | None = None
    staging_file: Path | None = None
    owned_final = False
    success = False

    try:
        root_resolved.mkdir(mode=0o700, parents=True, exist_ok=True)
        if _check_symlink(root_resolved):
            raise UploadRejected(503, "CONFIG_INVALID", "root is symlink")

        staging_dir = Path(tempfile.mkdtemp(prefix=".upload-", dir=root_resolved))
        staging_file = staging_dir / "source.bin"

        fd = os.open(str(staging_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            f = os.fdopen(fd, "wb")
        except OSError:
            os.close(fd)
            raise

        h = hashlib.sha256()
        total = 0
        try:
            async with asyncio.timeout(30):
                async for chunk in request.stream():
                    if not isinstance(chunk, (bytes, bytearray, memoryview)):
                        chunk = bytes(chunk)
                    next_total = total + len(chunk)
                    if next_total > max_bytes:
                        raise UploadRejected(413, "INVALID_MEDIA", "upload exceeds size limit")
                    await run_in_threadpool(f.write, chunk)
                    h.update(chunk)
                    total = next_total
        except ClientDisconnect:
            raise UploadRejected(400, "INVALID_MEDIA", "client disconnected")
        except asyncio.TimeoutError:
            raise UploadRejected(408, "UPLOAD_TIMEOUT", "upload timeout")
        finally:
            f.close()

        if total == 0:
            raise UploadRejected(422, "INVALID_MEDIA", "empty upload")
        if declared_len is not None and total != declared_len:
            raise UploadRejected(400, "INVALID_MEDIA", "size mismatch")

        probe = await run_in_threadpool(probe_media, staging_file, mime, max_duration_s=max_duration_s)

        final_parent = final_dir.parent
        final_parent_rel = final_parent.relative_to(root_resolved)
        if ".." in str(final_parent_rel).split("/"):
            raise UploadRejected(503, "CONFIG_INVALID", "path traversal detected")

        if _check_symlink(final_parent) or _check_symlink(final_parent.parent):
            raise UploadRejected(503, "CONFIG_INVALID", "symlink in path")

        final_parent.mkdir(mode=0o700, parents=True, exist_ok=True)

        if final_dir.exists():
            raise UploadRejected(409, "INVALID_MEDIA", "asset already exists")

        os.rename(staging_dir, final_dir)
        staging_dir = None
        owned_final = True

        sha = h.hexdigest()
        created = datetime.fromtimestamp(now, tz=timezone.utc)
        expires = datetime.fromtimestamp(now + ttl_s, tz=timezone.utc)

        if created.tzinfo is None or expires.tzinfo is None:
            raise UploadRejected(503, "CONFIG_INVALID", "invalid datetime")

        video = VideoAsset(
            id=asset_id,
            owner_session_id=owner,
            storage_key=str(final_rel / "source.bin"),
            sha256=sha,
            mime=probe.mime,
            bytes=total,
            duration_s=probe.duration_s,
            width=probe.width,
            height=probe.height,
            rotation=probe.rotation,
            timestamp_map_key=None,
            created_at=created,
            expires_at=expires,
        )

        store.register_asset(video, now=now)
        success = True
        return video

    except UploadRejected:
        raise
    except asyncio.CancelledError:
        raise
    except Exception:
        raise
    finally:
        if staging_dir is not None and staging_dir.exists():
            _rmrf_if_owned(staging_dir)
        if not success and owned_final and final_dir is not None and final_dir.exists():
            _rmrf_if_owned(final_dir)
