from __future__ import annotations

import os
import re
import sqlite3
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from app.errors import ErrorEnvelope
from app.processing_config import checkpoint_sha_from_env, processing_version
from app.session import SessionSecurity
from app.store import Conflict, NotFound
from app.uploads import get_store
from contracts.analysis import AnalysisResult
from contracts.lifecycle import AnalysisCreateRequest, AnalysisStatus
from contracts.pose_job import PoseJobArtifacts
from contracts.enums import JobState

router = APIRouter(prefix="/v1")

_VARIANT_DEFAULTS = {
    "lat_pulldown": "cable_seated_bilateral",
    "squat": "bodyweight",
    "dumbbell_curl": "standing_both_arms",
    "lateral_raise": "standing_both_arms",
    "incline_chest_press": "incline_dumbbell_bilateral",
}

_RESULT_KEY_RE = re.compile(r"^attempts/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{32}/manifest\.json$")


def _get_security() -> SessionSecurity:
    return SessionSecurity.from_environment()


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"


def _error_response(status_code: int, code: str, message: str, retryable: bool = False) -> JSONResponse:
    body = ErrorEnvelope(code=code, message=message, retryable=retryable)
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(),
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


def _translate_http_exception(exc: HTTPException) -> JSONResponse:
    detail: dict = exc.detail if isinstance(exc.detail, dict) else {}
    code = detail.get("code", "SESSION_INVALID")
    message = str(detail.get("message", "Invalid request"))
    return _error_response(exc.status_code, code, message)


def _parse_ttl() -> float:
    raw = os.environ.get("REPORT_TTL_DAYS", "7")
    try:
        days = float(raw)
        if not (0 < days <= 7) or days != days or days == float("inf"):
            raise ValueError
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=503,
            detail={"code": "CONFIG_INVALID", "message": "Invalid processing configuration"},
        )
    return days * 86400.0


def _canonical_uuid(analysis_id: str) -> str:
    if len(analysis_id) != 36:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Analysis not found"})
    try:
        canonical = str(uuid.UUID(analysis_id))
    except ValueError:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Analysis not found"})
    if canonical != analysis_id:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Analysis not found"})
    return canonical


def _resolve_variant(exercise_id: str, variant: str | None) -> str:
    canonical = _VARIANT_DEFAULTS.get(exercise_id)
    if canonical is None:
        raise HTTPException(
            status_code=422,
            detail={"code": "UNSUPPORTED_EXERCISE", "message": "Unsupported exercise_id"},
        )
    if variant is None:
        return canonical
    if variant != canonical:
        raise HTTPException(
            status_code=422,
            detail={"code": "UNSUPPORTED_VARIANT", "message": "Unsupported variant"},
        )
    return variant


def _store():
    try:
        return get_store()
    except HTTPException:
        raise
    except (sqlite3.Error, OSError):
        raise HTTPException(
            status_code=503,
            detail={"code": "STORAGE_UNAVAILABLE", "message": "Storage temporarily unavailable"},
        )


def _auth(request: Request, mutation: bool) -> str:
    return _get_security().validate(request, mutation=mutation)


@router.post("/analyses", status_code=202, response_model=AnalysisStatus)
def create_analysis(
    body: AnalysisCreateRequest,
    request: Request,
    response: Response,
) -> AnalysisStatus | JSONResponse:
    try:
        owner = _auth(request, mutation=True)
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)

    try:
        ttl_s = _parse_ttl()
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)

    try:
        variant = _resolve_variant(body.exercise_id, body.variant)
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)

    try:
        version = processing_version(checkpoint_sha_from_env())
    except ValueError:
        _no_store(response)
        return _error_response(503, "CONFIG_INVALID", "Invalid processing configuration")

    try:
        store = _store()
        job = store.enqueue(
            owner,
            body.video_id,
            body.exercise_id,
            variant,
            body.request_key,
            version,
            ttl_s=ttl_s,
        )
    except NotFound:
        _no_store(response)
        return _error_response(404, "NOT_FOUND", "Video asset not found")
    except Conflict:
        _no_store(response)
        return _error_response(409, "IDEMPOTENCY_CONFLICT", "Conflicting analysis request")
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)
    except (sqlite3.Error, OSError):
        _no_store(response)
        return _error_response(503, "STORAGE_UNAVAILABLE", "Storage temporarily unavailable", retryable=True)

    _no_store(response)
    return AnalysisStatus.from_job(job)


@router.get("/analyses/{analysis_id}", response_model=AnalysisStatus)
def get_analysis_status(
    request: Request,
    response: Response,
    analysis_id: str,
) -> AnalysisStatus | JSONResponse:
    try:
        owner = _auth(request, mutation=False)
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)

    try:
        job_id = _canonical_uuid(analysis_id)
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)

    try:
        store = _store()
        job = store.get_job(owner, job_id, now=time.time())
    except NotFound:
        _no_store(response)
        return _error_response(404, "NOT_FOUND", "Analysis not found")
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)
    except (sqlite3.Error, OSError):
        _no_store(response)
        return _error_response(503, "STORAGE_UNAVAILABLE", "Storage temporarily unavailable", retryable=True)

    _no_store(response)
    return AnalysisStatus.from_job(job)


@router.post("/analyses/{analysis_id}/cancel", response_model=AnalysisStatus)
def cancel_analysis(
    request: Request,
    response: Response,
    analysis_id: str,
) -> AnalysisStatus | JSONResponse:
    try:
        owner = _auth(request, mutation=True)
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)

    try:
        job_id = _canonical_uuid(analysis_id)
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)

    try:
        store = _store()
        job = store.cancel(owner, job_id, now=time.time())
    except NotFound:
        _no_store(response)
        return _error_response(404, "NOT_FOUND", "Analysis not found")
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)
    except (sqlite3.Error, OSError):
        _no_store(response)
        return _error_response(503, "STORAGE_UNAVAILABLE", "Storage temporarily unavailable", retryable=True)

    _no_store(response)
    return AnalysisStatus.from_job(job)


@router.delete("/analyses/{analysis_id}", status_code=204, response_model=None)
def delete_analysis(
    request: Request,
    response: Response,
    analysis_id: str,
) -> Response | JSONResponse:
    try:
        owner = _auth(request, mutation=True)
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)

    try:
        job_id = _canonical_uuid(analysis_id)
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)

    try:
        store = _store()
        store.delete_job(owner, job_id, now=time.time())
    except NotFound:
        _no_store(response)
        return _error_response(404, "NOT_FOUND", "Analysis not found")
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)
    except (sqlite3.Error, OSError):
        _no_store(response)
        return _error_response(503, "STORAGE_UNAVAILABLE", "Storage temporarily unavailable", retryable=True)

    _no_store(response)
    response.status_code = 204
    return response


@router.get("/analyses/{analysis_id}/result", response_model=AnalysisResult)
def get_analysis_result(
    request: Request,
    response: Response,
    analysis_id: str,
) -> AnalysisResult | JSONResponse:
    try:
        owner = _auth(request, mutation=False)
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)

    try:
        job_id = _canonical_uuid(analysis_id)
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)

    try:
        store = _store()
        job = store.get_job(owner, job_id, now=time.time())
    except NotFound:
        _no_store(response)
        return _error_response(404, "NOT_FOUND", "Analysis not found")
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)
    except (sqlite3.Error, OSError):
        _no_store(response)
        return _error_response(503, "STORAGE_UNAVAILABLE", "Storage temporarily unavailable", retryable=True)

    if job.state != JobState.SUCCEEDED:
        _no_store(response)
        return _error_response(409, "RESULT_NOT_READY", "Analysis result is not ready")

    result_key = job.result_key
    if result_key is None or not _RESULT_KEY_RE.fullmatch(result_key):
        _no_store(response)
        return _error_response(503, "RESULT_UNAVAILABLE", "Result reference is invalid", retryable=False)

    parts = result_key.split("/")
    if len(parts) < 2 or parts[1] != job.id:
        _no_store(response)
        return _error_response(503, "RESULT_UNAVAILABLE", "Result reference is invalid", retryable=False)

    artifact_root = os.environ.get("ARTIFACT_ROOT", "/state/artifacts")
    if not os.path.isabs(artifact_root):
        _no_store(response)
        return _error_response(503, "CONFIG_INVALID", "Invalid server configuration")

    try:
        from app.pose_jobs import safe_file
        data = safe_file(Path(artifact_root), result_key, 1048576)
        artifacts = PoseJobArtifacts.model_validate_json(data)
    except (ValueError, OSError):
        _no_store(response)
        return _error_response(503, "RESULT_UNAVAILABLE", "Result artifact is unavailable", retryable=False)

    manifest = artifacts.report
    if manifest.analysis_id != job.id:
        _no_store(response)
        return _error_response(503, "RESULT_UNAVAILABLE", "Result analysis_id mismatch", retryable=False)
    if artifacts.proxy.source_sha256 != job.input_hash:
        _no_store(response)
        return _error_response(503, "RESULT_UNAVAILABLE", "Result input hash mismatch", retryable=False)
    if manifest.provenance.get("input_sha256") != job.input_hash:
        _no_store(response)
        return _error_response(503, "RESULT_UNAVAILABLE", "Result provenance input hash mismatch", retryable=False)
    if manifest.provenance.get("version_hash") != job.version_hash:
        _no_store(response)
        return _error_response(503, "RESULT_UNAVAILABLE", "Result version hash mismatch", retryable=False)
    if manifest.provenance.get("pipeline") != "pose-job-v1":
        _no_store(response)
        return _error_response(503, "RESULT_UNAVAILABLE", "Result pipeline mismatch", retryable=False)
    if manifest.provenance.get("pose_model_revision") != artifacts.pose.model_revision:
        _no_store(response)
        return _error_response(503, "RESULT_UNAVAILABLE", "Result pose model revision mismatch", retryable=False)

    try:
        store.get_job(owner, job_id, now=time.time())
    except NotFound:
        _no_store(response)
        return _error_response(404, "NOT_FOUND", "Analysis not found")
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)
    except (sqlite3.Error, OSError):
        _no_store(response)
        return _error_response(503, "STORAGE_UNAVAILABLE", "Storage temporarily unavailable", retryable=True)

    _no_store(response)
    return manifest
