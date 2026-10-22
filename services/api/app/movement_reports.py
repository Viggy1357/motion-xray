from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import ValidationError

from app.analyses import (
    _auth,
    _canonical_uuid,
    _error_response,
    _no_store,
    _store,
    _translate_http_exception,
)
from app.artifact_streams import _load_validated, _open_secure, _read_file, _recheck
from app.store import NotFound
from contracts.pose import PoseFrame
from contracts.product import PrototypeAnalysisResult
from movement.runtime_lat import build_movement_report
from movement.experimental_match import apply_experimental_match
from movement.runtime_exercises import apply_reference_assessment, build_exercise_report

router = APIRouter(prefix="/v1")

_MAX_POSE = 64 * 1024 * 1024
_MAX_FRAMES = 10000
_MAX_LINE = 128 * 1024
_FRAME_KEY_RE = re.compile(r"^pose/([0-9a-f]{64})[.]jsonl$")
_SUPPORTED = {"lat_pulldown", "dumbbell_curl", "squat", "incline_chest_press"}
_REQUIRES_ESTIMATED_3D = _SUPPORTED
_VARIANTS = {
    "lat_pulldown": "cable_seated_bilateral",
    "dumbbell_curl": "standing_both_arms",
    "squat": "bodyweight",
    "incline_chest_press": "incline_dumbbell_bilateral",
}


def _parse_frames(data: bytes) -> list[PoseFrame]:
    """Published successful pose artifacts must contain at least one frame."""
    frames: list[PoseFrame] = []
    prev_index = -1
    prev_ts = -1.0
    for raw in data.splitlines():
        if len(frames) >= _MAX_FRAMES:
            raise ValueError("too many frames")
        if len(raw) > _MAX_LINE:
            raise ValueError("line too long")
        if not raw.strip():
            continue
        frame = PoseFrame.model_validate(json.loads(raw))
        if frame.frame_index <= prev_index or frame.timestamp_s <= prev_ts:
            raise ValueError("non-monotonic frames")
        prev_index, prev_ts = frame.frame_index, frame.timestamp_s
        frames.append(frame)
    if not frames:
        raise ValueError("no frames")
    return frames


@router.get("/analyses/{analysis_id}/movement-report", response_model=PrototypeAnalysisResult)
def get_movement_report(request: Request, response: Response, analysis_id: str):
    try:
        owner = _auth(request, mutation=False)
        job_id = _canonical_uuid(analysis_id)
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)

    try:
        store = _store()
        artifacts, attempt_root = _load_validated(store, owner, job_id)
        try:
            video, exercise_id, variant = store.get_input(owner, job_id, now=time.time())
        except NotFound:
            _no_store(response)
            return _error_response(404, "NOT_FOUND", "Analysis not found")
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)
    except (sqlite3.Error, OSError):
        _no_store(response)
        return _error_response(503, "STORAGE_UNAVAILABLE", "Storage temporarily unavailable", retryable=True)

    manifest = artifacts.report
    pose = artifacts.pose
    if manifest.exercise != exercise_id or manifest.variant != variant:
        _no_store(response)
        return _error_response(503, "RESULT_UNAVAILABLE", "Result manifest mismatch")
    if pose.provider != "mediapipe" or pose.joint_mapping_version != "mp33-camera-v1":
        _no_store(response)
        return _error_response(503, "RESULT_UNAVAILABLE", "Result pose mapping is unsupported")
    if pose.video_id != video.id:
        _no_store(response)
        return _error_response(503, "RESULT_UNAVAILABLE", "Result pose video mismatch")
    if exercise_id not in _SUPPORTED:
        _no_store(response)
        return _error_response(422, "UNSUPPORTED_EXERCISE", "No movement profile is available for this exercise")
    if variant != _VARIANTS[exercise_id]:
        _no_store(response)
        return _error_response(422, "UNSUPPORTED_VARIANT", "No movement profile is available for this variant")
    if exercise_id in _REQUIRES_ESTIMATED_3D and not pose.capabilities.get("supports_estimated_3d", False):
        _no_store(response)
        return _error_response(422, "UNSUPPORTED_POSE_CAPABILITY", "Pose capture lacks the estimated 3D capability required for this exercise")

    m = _FRAME_KEY_RE.fullmatch(pose.frames_artifact_key)
    if not m:
        _no_store(response)
        return _error_response(503, "RESULT_UNAVAILABLE", "Artifact reference is invalid")
    expected_sha = m.group(1)

    try:
        fd, size = _open_secure(attempt_root, pose.frames_artifact_key)
    except (ValueError, OSError):
        _no_store(response)
        return _error_response(503, "RESULT_UNAVAILABLE", "Artifact is unavailable")
    f = os.fdopen(fd, "rb")
    try:
        if size <= 0 or size > _MAX_POSE:
            raise ValueError("size out of bounds")
        data = _read_file(f, size)
        if hashlib.sha256(data).hexdigest() != expected_sha:
            raise ValueError("hash mismatch")
        frames = _parse_frames(data)
    except (ValueError, ValidationError, OSError):
        f.close()
        _no_store(response)
        return _error_response(503, "RESULT_UNAVAILABLE", "Artifact is unavailable")
    f.close()

    try:
        builder = build_movement_report if exercise_id == "lat_pulldown" else build_exercise_report
        report = builder(
            frames,
            analysis_id=job_id,
            exercise_id=exercise_id,
            variant=variant,
            width=artifacts.proxy.source_width,
            height=artifacts.proxy.source_height,
            pose_sha256=expected_sha,
            processing_version=manifest.provenance.get("version_hash", ""),
        )
        report = apply_experimental_match(report) if exercise_id == "lat_pulldown" else apply_reference_assessment(report)
    except ValueError:
        _no_store(response)
        return _error_response(503, "REPORT_UNAVAILABLE", "Derived report configuration is invalid", retryable=True)

    try:
        _recheck(store, owner, job_id)
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)
    except (sqlite3.Error, OSError):
        _no_store(response)
        return _error_response(503, "STORAGE_UNAVAILABLE", "Storage temporarily unavailable", retryable=True)

    _no_store(response)
    return report
