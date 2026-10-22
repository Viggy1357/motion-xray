from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import stat
import time
from pathlib import Path
from typing import BinaryIO, Iterator

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from app.analyses import (
    _RESULT_KEY_RE,
    _auth,
    _canonical_uuid,
    _error_response,
    _no_store,
    _store,
    _translate_http_exception,
)
from app.store import NotFound, Store
from contracts.enums import JobState
from contracts.pose_job import PoseJobArtifacts
from contracts.proxy import ProxyTimestampMap

router = APIRouter(prefix="/v1")

_KINDS = {"proxy", "pose", "timestamps"}
_MAX_PROXY = 512 * 1024 * 1024
_MAX_POSE = 64 * 1024 * 1024
_MAX_MAP = 1024 * 1024
_MAX_MANIFEST = 1024 * 1024
_CHUNK = 1024 * 1024
_FRAME_KEY_RE = re.compile(r"^pose/([0-9a-f]{64})[.]jsonl$")
_RANGE_RE = re.compile(r"^bytes=(\d{0,18})-(\d{0,18})$")
_MAX_RANGE_HEADER = 100


def _open_secure(root: Path, key: str) -> tuple[int, int]:
    if not root.is_absolute() or ".." in root.parts:
        raise ValueError("unsafe root")
    for p in [root, *root.parents]:
        if p.is_symlink():
            raise ValueError("symlink in root ancestors")
    if not key or key.startswith("/") or "\\" in key:
        raise ValueError("unsafe key")
    parts = key.split("/")
    if any(not p or p in (".", "..") for p in parts):
        raise ValueError("unsafe key segment")
    dirfd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        for part in parts[:-1]:
            nfd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dirfd)
            os.close(dirfd)
            dirfd = nfd
        ffd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dirfd)
    finally:
        os.close(dirfd)
    try:
        st = os.fstat(ffd)
        if not stat.S_ISREG(st.st_mode):
            raise ValueError("not a regular file")
        return ffd, st.st_size
    except Exception:
        os.close(ffd)
        raise


def _read_file(f: BinaryIO, size: int) -> bytes:
    f.seek(0)
    buf = bytearray()
    while len(buf) < size:
        chunk = f.read(size - len(buf))
        if not chunk:
            raise OSError("file truncated")
        buf += chunk
    f.seek(0)
    return bytes(buf)


def _hash_file(f: BinaryIO, size: int) -> str:
    h = hashlib.sha256()
    f.seek(0)
    remaining = size
    while remaining > 0:
        chunk = f.read(min(_CHUNK, remaining))
        if not chunk:
            raise OSError("file truncated")
        h.update(chunk)
        remaining -= len(chunk)
    f.seek(0)
    return h.hexdigest()


def _unavailable() -> HTTPException:
    return HTTPException(status_code=503, detail={"code": "RESULT_UNAVAILABLE", "message": "Result artifact is unavailable"})


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Analysis not found"})


def _load_validated(store: Store, owner: str, job_id: str) -> tuple[PoseJobArtifacts, Path]:
    try:
        job = store.get_job(owner, job_id, now=time.time())
    except NotFound:
        raise _not_found()
    if job.state != JobState.SUCCEEDED:
        raise HTTPException(status_code=409, detail={"code": "RESULT_NOT_READY", "message": "Analysis result is not ready"})
    result_key = job.result_key
    if result_key is None or not _RESULT_KEY_RE.fullmatch(result_key):
        raise _unavailable()
    parts = result_key.split("/")
    if len(parts) < 4 or parts[0] != "attempts" or parts[1] != job.id:
        raise _unavailable()
    artifact_root = os.environ.get("ARTIFACT_ROOT", "/state/artifacts")
    if not os.path.isabs(artifact_root):
        raise HTTPException(status_code=503, detail={"code": "CONFIG_INVALID", "message": "Invalid server configuration"})
    root = Path(artifact_root)
    try:
        fd, size = _open_secure(root, result_key)
    except (ValueError, OSError):
        raise _unavailable()
    f = os.fdopen(fd, "rb")
    try:
        if size <= 0 or size > _MAX_MANIFEST:
            raise ValueError("manifest size out of bounds")
        artifacts = PoseJobArtifacts.model_validate_json(_read_file(f, size))
    except (ValueError, OSError):
        raise _unavailable()
    finally:
        f.close()
    manifest = artifacts.report
    if manifest.analysis_id != job.id:
        raise _unavailable()
    if artifacts.proxy.source_sha256 != job.input_hash:
        raise _unavailable()
    prov = manifest.provenance
    if prov.get("input_sha256") != job.input_hash:
        raise _unavailable()
    if prov.get("version_hash") != job.version_hash:
        raise _unavailable()
    if prov.get("pipeline") != "pose-job-v1":
        raise _unavailable()
    if prov.get("pose_model_revision") != artifacts.pose.model_revision:
        raise _unavailable()
    attempt_root = root.joinpath(*parts[:-1])
    return artifacts, attempt_root


def _recheck(store: Store, owner: str, job_id: str) -> None:
    """Abort if job revoked/expired/deleted or raw input TTL elapsed."""
    try:
        job = store.get_job(owner, job_id, now=time.time())
        store.get_input(owner, job_id, now=time.time())
    except NotFound:
        raise _not_found()
    if job.state != JobState.SUCCEEDED:
        raise HTTPException(status_code=409, detail={"code": "RESULT_NOT_READY", "message": "Analysis result is not ready"})


def _alive(store: Store, owner: str, job_id: str) -> bool:
    try:
        _recheck(store, owner, job_id)
    except Exception:
        return False
    return True


def _stream(f: BinaryIO, start: int, length: int, store: Store, owner: str, job_id: str) -> Iterator[bytes]:
    sent = 0
    try:
        f.seek(start)
        while sent < length:
            if not _alive(store, owner, job_id):
                return  # graceful abort mid-stream; bytes already sent cannot be recalled
            chunk = f.read(min(_CHUNK, length - sent))
            if not chunk:
                return
            sent += len(chunk)
            yield chunk
    finally:
        f.close()  # idempotent; response wrapper may also close


class _ArtifactResponse(StreamingResponse):
    """StreamingResponse that owns the artifact file object.

    The owned file is closed exactly once in a finally block after the ASGI
    call finishes, including client disconnects and errors raised before the
    generator starts. The generator's own close is idempotent.
    """

    def __init__(self, fileobj: BinaryIO, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fileobj = fileobj

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            self._fileobj.close()


def _parse_range(header: str, size: int) -> tuple[int, int] | None:
    if len(header) > _MAX_RANGE_HEADER:
        return None
    m = _RANGE_RE.fullmatch(header.strip())
    if not m:
        return None
    a, b = m.group(1), m.group(2)
    if not a and not b:
        return None
    if not a:  # suffix
        n = int(b)
        if n <= 0:
            return None
        if n >= size:
            return (0, size - 1)
        return (size - n, size - 1)
    start = int(a)
    end = int(b) if b else size - 1
    if start >= size or start > end:
        return None
    return (start, min(end, size - 1))


@router.get(
    "/analyses/{analysis_id}/artifacts/{kind}",
    operation_id="get_analysis_artifact_v1_analyses__analysis_id__artifacts__kind__get",
    response_class=Response,
    responses={
        200: {"description": "Private proxy, pose JSONL, or timestamp map; raw retention applies.",
              "content": {"video/mp4": {"schema": {"type": "string", "format": "binary"}},
                          "application/x-ndjson": {"schema": {"type": "string"}},
                          "application/json": {"schema": {"type": "object"}}}},
        206: {"description": "Single byte range of the private proxy video.",
              "content": {"video/mp4": {"schema": {"type": "string", "format": "binary"}}}},
        416: {"description": "Malformed or unsatisfiable proxy byte range."},
    },
)
def get_artifact(request: Request, response: Response, analysis_id: str, kind: str):
    """Serve proxy, pose or timestamps to the signed owner; never original media.

    Proxy supports one Range header (bytes=start-end, bytes=start-, or bytes=-suffix).
    Pose/timestamp requests ignore Range and return the complete bounded artifact.
    """
    try:
        owner = _auth(request, mutation=False)
        job_id = _canonical_uuid(analysis_id)
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)
    if kind not in _KINDS:
        _no_store(response)
        return _error_response(404, "NOT_FOUND", "Artifact not found")
    try:
        store = _store()
        artifacts, attempt_root = _load_validated(store, owner, job_id)
        try:
            store.get_input(owner, job_id, now=time.time())
        except NotFound:
            _no_store(response)
            return _error_response(404, "NOT_FOUND", "Analysis not found")
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)
    except (sqlite3.Error, OSError):
        _no_store(response)
        return _error_response(503, "STORAGE_UNAVAILABLE", "Storage temporarily unavailable", retryable=True)

    expected: str | None
    if kind == "proxy":
        key, limit, expected = "proxy/proxy.mp4", _MAX_PROXY, artifacts.proxy.proxy_sha256
        media, filename = "video/mp4", "proxy.mp4"
    elif kind == "pose":
        m = _FRAME_KEY_RE.fullmatch(artifacts.pose.frames_artifact_key)
        if not m:
            _no_store(response)
            return _error_response(503, "RESULT_UNAVAILABLE", "Artifact reference is invalid")
        key, limit, expected = artifacts.pose.frames_artifact_key, _MAX_POSE, m.group(1)
        media, filename = "application/x-ndjson", "pose.jsonl"
    else:
        key, limit, expected = "proxy/timestamp_map.json", _MAX_MAP, None
        media, filename = "application/json", "timestamp_map.json"

    try:
        fd, size = _open_secure(attempt_root, key)
    except (ValueError, OSError):
        _no_store(response)
        return _error_response(503, "RESULT_UNAVAILABLE", "Artifact is unavailable")
    fileobj = os.fdopen(fd, "rb")
    try:
        if size <= 0 or size > limit:
            raise ValueError("size out of bounds")
        if expected is not None and _hash_file(fileobj, size) != expected:
            raise ValueError("hash mismatch")
        if kind == "timestamps":
            if ProxyTimestampMap.model_validate_json(_read_file(fileobj, size)) != artifacts.proxy:
                raise ValueError("map mismatch")
        _recheck(store, owner, job_id)
    except HTTPException as exc:
        fileobj.close()
        _no_store(response)
        return _translate_http_exception(exc)
    except (ValueError, OSError):
        fileobj.close()
        _no_store(response)
        return _error_response(503, "RESULT_UNAVAILABLE", "Artifact is unavailable")
    except sqlite3.Error:
        fileobj.close()
        _no_store(response)
        return _error_response(503, "STORAGE_UNAVAILABLE", "Storage temporarily unavailable", retryable=True)

    headers = {
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "Content-Disposition": f'inline; filename="{filename}"',
    }
    if kind == "proxy":
        headers["Accept-Ranges"] = "bytes"
        range_header = request.headers.get("range")
        if range_header is not None:
            parsed = None if "," in range_header else _parse_range(range_header, size)
            if parsed is None:
                fileobj.close()
                return JSONResponse(
                    status_code=416,
                    content={"code": "RANGE_NOT_SATISFIABLE", "message": "Range not satisfiable", "retryable": False},
                    headers={**headers, "Content-Range": f"bytes */{size}"},
                )
            start, end = parsed
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"
            headers["Content-Length"] = str(end - start + 1)
            return _ArtifactResponse(
                fileobj,
                _stream(fileobj, start, end - start + 1, store, owner, job_id),
                status_code=206,
                media_type=media,
                headers=headers,
            )
    # JSON kinds (pose/timestamps) intentionally ignore Range: partial JSON is not useful.
    headers["Content-Length"] = str(size)
    return _ArtifactResponse(
        fileobj,
        _stream(fileobj, 0, size, store, owner, job_id),
        status_code=200,
        media_type=media,
        headers=headers,
    )
