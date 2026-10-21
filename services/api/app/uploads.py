from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from app.errors import ErrorEnvelope
from app.ingest import ingest_video, UploadRejected
from app.session import SessionSecurity
from app.store import NotFound, Conflict
from app.store import Store
from contracts.media import VideoAsset
from contracts.session import SessionInfo

router = APIRouter(prefix="/v1")

_SUPPORTED_MIME = {"video/mp4", "video/quicktime", "video/webm"}


def _env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)


def _parse_config() -> tuple[int, float, float, str, str]:
    errors: list[str] = []

    raw_max_mb = _env("MAX_UPLOAD_MB", "100")
    try:
        max_mb = int(raw_max_mb or "")
        if not (1 <= max_mb <= 100):
            raise ValueError("MAX_UPLOAD_MB must be 1..100")
    except (ValueError, TypeError) as exc:
        errors.append(f"MAX_UPLOAD_MB invalid: {exc}")
        max_mb = 0

    raw_max_dur = _env("MAX_VIDEO_SECONDS", "30")
    try:
        max_dur = float(raw_max_dur or "")
        if not (0 < max_dur <= 30):
            raise ValueError("MAX_VIDEO_SECONDS must be in (0,30]")
    except (ValueError, TypeError) as exc:
        errors.append(f"MAX_VIDEO_SECONDS invalid: {exc}")
        max_dur = 0.0

    raw_ttl = _env("RAW_MEDIA_TTL_HOURS", "24")
    try:
        ttl_h = float(raw_ttl or "")
        if not (0 < ttl_h <= 24):
            raise ValueError("RAW_MEDIA_TTL_HOURS must be in (0,24]")
    except (ValueError, TypeError) as exc:
        errors.append(f"RAW_MEDIA_TTL_HOURS invalid: {exc}")
        ttl_h = 0.0

    db_url = _env("DATABASE_URL", "sqlite:////state/motion_xray.db")
    if not isinstance(db_url, str) or not db_url.startswith("sqlite:///"):
        errors.append("DATABASE_URL must start with sqlite:///")
        db_path = ""
    else:
        if "?" in db_url:
            errors.append("DATABASE_URL must not contain query parameters")
            db_path = ""
        else:
            db_path = db_url[len("sqlite:///"):]
            if not Path(db_path).is_absolute():
                errors.append("DATABASE_URL must be absolute filesystem path")
                db_path = ""

    video_root = _env("VIDEO_ROOT", "/state/media")
    if not isinstance(video_root, str) or not os.path.isabs(video_root):
        errors.append("VIDEO_ROOT must be absolute path")
        video_root = ""

    if errors:
        raise HTTPException(
            status_code=503,
            detail={"code": "CONFIG_INVALID", "message": "; ".join(errors)},
        )

    return max_mb, max_dur, ttl_h, db_path, video_root


def get_store() -> Store:
    _, _, _, db_path, _ = _parse_config()
    return Store(Path(db_path))


def _get_security() -> SessionSecurity:
    return SessionSecurity.from_environment()


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


def _error_response(status_code: int, code: str, message: str, retryable: bool = False) -> JSONResponse:
    body = ErrorEnvelope(code=code, message=message, retryable=retryable)
    return JSONResponse(status_code=status_code, content=body.model_dump(), headers={"Cache-Control": "no-store"})


def _translate_http_exception(exc: HTTPException) -> JSONResponse:
    detail: dict = exc.detail if isinstance(exc.detail, dict) else {}
    code = detail.get("code", "SESSION_INVALID")
    message = "Invalid session" if exc.status_code == 403 else "Invalid server configuration"
    return _error_response(exc.status_code, code, message)


@router.get("/session", response_model=SessionInfo)
async def get_session(request: Request, response: Response) -> SessionInfo | JSONResponse:
    try:
        security = _get_security()
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)
    try:
        _parse_config()
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)
    try:
        info = security.establish(request, response)
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)
    _no_store(response)
    return info


@router.post(
    "/videos",
    status_code=201,
    response_model=VideoAsset,
    openapi_extra={
        "requestBody": {
            "content": {
                "video/mp4": {"schema": {"type": "string", "format": "binary"}},
                "video/quicktime": {"schema": {"type": "string", "format": "binary"}},
                "video/webm": {"schema": {"type": "string", "format": "binary"}},
            },
            "required": True,
        }
    },
)
async def post_video(
    request: Request,
    response: Response,
    x_csrf_token: Annotated[str | None, Header()] = None,
    x_upload_consent: Annotated[str | None, Header(description="true")] = None,
    origin: Annotated[str | None, Header()] = None,
) -> VideoAsset | JSONResponse:
    try:
        security = _get_security()
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)
    try:
        owner = security.validate(request, mutation=True)
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)
    try:
        max_mb, max_dur, ttl_h, _, video_root = _parse_config()
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)
    try:
        store = get_store()
    except (HTTPException, sqlite3.Error, OSError) as exc:
        _no_store(response)
        if isinstance(exc, HTTPException):
            return _translate_http_exception(exc)
        return _error_response(503, "STORAGE_UNAVAILABLE", "Storage temporarily unavailable", retryable=True)

    if x_upload_consent != "true":
        _no_store(response)
        return _error_response(400, "CONSENT_REQUIRED", "X-Upload-Consent header must be 'true'")

    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type not in _SUPPORTED_MIME:
        _no_store(response)
        return _error_response(415, "INVALID_MEDIA", "Unsupported content type")

    try:
        asset = await ingest_video(
            request,
            store,
            Path(video_root),
            owner,
            now=time.time(),
            max_bytes=max_mb * 1024 * 1024,
            max_duration_s=max_dur,
            ttl_s=ttl_h * 3600,
        )
    except UploadRejected as exc:
        _no_store(response)
        return _error_response(exc.status_code, exc.code, exc.message)
    except Conflict:
        return _error_response(409, "CONFLICT", "Asset conflict")
    except sqlite3.Error:
        _no_store(response)
        return _error_response(503, "STORAGE_UNAVAILABLE", "Storage temporarily unavailable", retryable=True)
    except OSError:
        _no_store(response)
        return _error_response(503, "STORAGE_UNAVAILABLE", "Storage temporarily unavailable", retryable=True)

    _no_store(response)
    return asset


@router.get("/videos/{video_id}", response_model=VideoAsset)
async def get_video(
    request: Request,
    response: Response,
    video_id: str,
) -> VideoAsset | JSONResponse:
    try:
        security = _get_security()
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)
    try:
        owner = security.validate(request, mutation=False)
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)
    if not 0 < len(video_id) <= 256:
        return _error_response(404, "NOT_FOUND", "Asset not found")
    try:
        store = get_store()
    except (HTTPException, sqlite3.Error, OSError) as exc:
        _no_store(response)
        if isinstance(exc, HTTPException):
            return _translate_http_exception(exc)
        return _error_response(503, "STORAGE_UNAVAILABLE", "Storage temporarily unavailable", retryable=True)

    try:
        asset = store.get_asset(owner, video_id, now=time.time())
    except NotFound:
        _no_store(response)
        return _error_response(404, "NOT_FOUND", "Asset not found")
    except Conflict:
        _no_store(response)
        return _error_response(409, "CONFLICT", "Asset conflict")
    except sqlite3.Error:
        _no_store(response)
        return _error_response(503, "STORAGE_UNAVAILABLE", "Storage temporarily unavailable", retryable=True)
    except OSError:
        _no_store(response)
        return _error_response(503, "STORAGE_UNAVAILABLE", "Storage temporarily unavailable", retryable=True)

    _no_store(response)
    return asset
