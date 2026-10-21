"""Worker-side bridge: validate real child artifacts before fenced publication."""

from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path
from typing import Sequence

from contracts.jobs import AnalysisJob
from contracts.pose import PoseFrame
from contracts.pose_job import PoseJobArtifacts, PoseJobInput
from contracts.proxy import ProxyTimestampMap
from providers.pose.artifacts import read_pose_frames
from providers.pose.mediapipe_provider import select_samples

from app.store import LeaseLost, NotFound, Store
from app.supervisor import supervise_once

MAX_MANIFEST_BYTES = 1_048_576
MAX_REQUEST_BYTES = 1_048_576
MAX_PROXY_BYTES = 256 * 1_048_576
MAX_FRAME_BYTES = 64 * 1_048_576
MAX_CHUNK = 1_048_576

_FRAME_KEY_RE = re.compile(r"^pose/([0-9a-f]{64})[.]jsonl$")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_stream(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(MAX_CHUNK)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _fsync_path(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_exclusive(path: Path, data: bytes, mode: int = 0o600) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(fd, "wb", closefd=False) as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
    finally:
        os.close(fd)


def _chmod_parents(path: Path, root: Path) -> None:
    p = path.parent
    while p != root and p.is_relative_to(root):
        if p.exists():
            os.chmod(p, 0o700)
        p = p.parent


def _safe_root(root: Path) -> Path:
    if not isinstance(root, Path):
        raise TypeError("root must be Path")
    if not root.is_absolute():
        raise ValueError("root must be absolute")
    if ".." in root.parts:
        raise ValueError("root contains traversal")
    for p in [root] + list(root.parents):
        if p.is_symlink():
            raise ValueError("root contains symlink in ancestors")
    return root.resolve()


def _safe_path(root: Path, key: str) -> Path:
    if not key or key.startswith("/") or "\\" in key:
        raise ValueError(f"unsafe key: {key!r}")
    parts = key.split("/")
    for p in parts:
        if not p or p == "." or p == "..":
            raise ValueError(f"unsafe key segment: {key!r}")
    resolved_root = _safe_root(root)
    target = resolved_root
    for part in parts:
        target = target / part
        if target.is_symlink():
            raise ValueError(f"symlink in path: {key!r}")
    return target


def safe_file(root: Path, key: str, max_bytes: int) -> bytes:
    target = _safe_path(root, key)
    if not target.exists():
        raise FileNotFoundError(f"missing file: {key!r}")
    if not target.is_file():
        raise ValueError(f"not a regular file: {key!r}")
    st = target.stat()
    if st.st_size == 0 or st.st_size > max_bytes:
        raise ValueError(f"file size out of bounds: {key!r}")
    data = target.read_bytes()
    if len(data) != st.st_size:
        raise OSError("file size changed during read")
    return data


def _read_pose_frames(attempt: Path, key: str, *, expected_sha256: str) -> list[PoseFrame]:
    path = _safe_path(attempt, key)
    if not path.exists():
        raise FileNotFoundError(f"missing frames file: {key!r}")
    if not path.is_file():
        raise ValueError(f"not a regular file: {key!r}")
    st = path.stat()
    if st.st_size == 0 or st.st_size > MAX_FRAME_BYTES:
        raise ValueError(f"frame file size out of bounds: {key!r}")
    frames = read_pose_frames(attempt, key, expected_sha256=expected_sha256)
    if not any(j.valid for f in frames for j in f.joints.values()):
        raise ValueError("no valid joint observations in sequence")
    return frames


def validate_pose_artifacts(
    request: PoseJobInput,
    request_sha256: str,
    attempt: Path,
    checkpoint_sha256: str,
) -> str:
    expected_request = request.model_dump_json().encode("utf-8")
    if _sha256_bytes(expected_request) != request_sha256:
        raise ValueError("request_sha256 argument does not match serialized request")
    if _sha256_bytes(safe_file(attempt, "request.json", MAX_REQUEST_BYTES)) != request_sha256:
        raise ValueError("request.json bytes changed")

    manifest_data = safe_file(attempt, "manifest.json", MAX_MANIFEST_BYTES)
    artifacts = PoseJobArtifacts.model_validate_json(manifest_data)

    if artifacts.request_sha256 != request_sha256:
        raise ValueError("manifest request_sha256 mismatch")

    video = request.video
    job = request.job

    report = artifacts.report
    if report.analysis_id != job.id:
        raise ValueError("report.analysis_id mismatch")
    if report.exercise != request.exercise_id:
        raise ValueError("report.exercise mismatch")
    if report.variant != request.variant:
        raise ValueError("report.variant mismatch")

    pose = artifacts.pose
    if pose.video_id != video.id:
        raise ValueError("pose.video_id mismatch")
    if pose.provider != "mediapipe":
        raise ValueError("pose.provider must be mediapipe")
    if pose.model_revision != f"sha256:{checkpoint_sha256}":
        raise ValueError("pose.model_revision mismatch")

    expected_provenance = {
        "pipeline": "pose-job-v1",
        "input_sha256": video.sha256,
        "version_hash": job.version_hash,
        "pose_model_revision": pose.model_revision,
    }
    if report.provenance != expected_provenance:
        raise ValueError(f"report.provenance mismatch: {report.provenance}")

    proxy_data = safe_file(attempt, "proxy/timestamp_map.json", MAX_REQUEST_BYTES)
    proxy = ProxyTimestampMap.model_validate_json(proxy_data)

    if proxy.source_sha256 != video.sha256:
        raise ValueError("proxy.source_sha256 mismatch")

    proxy_video = _safe_path(attempt, "proxy/proxy.mp4")
    if not proxy_video.is_file():
        raise ValueError("proxy/proxy.mp4 not a regular file")
    if not 0 < proxy_video.stat().st_size <= MAX_PROXY_BYTES:
        raise ValueError("proxy size out of bounds")
    if _sha256_stream(proxy_video) != proxy.proxy_sha256:
        raise ValueError("proxy/proxy.mp4 hash mismatch")

    if proxy.source_rotation != video.rotation:
        raise ValueError("proxy.source_rotation mismatch")

    if video.rotation in (90, -90):
        expected_width, expected_height = video.height, video.width
    else:
        expected_width, expected_height = video.width, video.height
    if proxy.source_width != expected_width or proxy.source_height != expected_height:
        raise ValueError("proxy source dimensions do not match expected orientation swap")

    frames = proxy.frames
    if len(frames) < 2:
        raise ValueError("proxy must have at least 2 frames")
    first_source = frames[0].source_s
    last_source = frames[-1].source_s
    if last_source > video.duration_s + 1e-6:
        raise ValueError("proxy last source timestamp exceeds video duration")
    for i, pair in enumerate(frames):
        if pair.source_index != i:
            raise ValueError("proxy source indices must enumerate contiguously from 0")
        expected_proxy_s = pair.source_s - first_source
        if abs(pair.proxy_s - expected_proxy_s) > 0.002:
            raise ValueError(f"proxy_s mismatch at frame {i}")

    if artifacts.proxy != proxy:
        raise ValueError("proxy embedded map mismatch")

    match = _FRAME_KEY_RE.fullmatch(pose.frames_artifact_key)
    if not match:
        raise ValueError(f"invalid frames_artifact_key: {pose.frames_artifact_key}")
    frame_digest = match.group(1)
    pose_frames = _read_pose_frames(attempt, pose.frames_artifact_key, expected_sha256=frame_digest)

    index_map = {pair.source_index: pair.source_s for pair in frames}
    for frame in pose_frames:
        expected_ts = index_map.get(frame.frame_index)
        if expected_ts is None or abs(expected_ts - frame.timestamp_s) > 1e-6:
            raise ValueError(f"pose frame {frame.frame_index} at {frame.timestamp_s}s not matched by proxy")

    expected_samples = select_samples([p.source_s for p in frames], 0, video.duration_s, 30)
    if [f.frame_index for f in pose_frames] != [i for i, _ in expected_samples]:
        raise ValueError("pose samples do not cover the requested source interval")

    for rel_path in ["manifest.json", "request.json", "proxy/timestamp_map.json", "proxy/proxy.mp4", pose.frames_artifact_key]:
        abs_path = _safe_path(attempt, rel_path)
        if abs_path.is_symlink() or not abs_path.is_file():
            raise ValueError(f"not a regular file: {rel_path}")
        os.chmod(abs_path, 0o600)

    _chmod_parents(_safe_path(attempt, pose.frames_artifact_key), _safe_root(attempt))

    return "manifest.json"


def run_pose_once(
    store: Store,
    source_root: Path,
    artifact_root: Path,
    checkpoint_path: Path,
    checkpoint_sha256: str,
    *,
    worker: str = "pose",
    lease_s: float = 60,
    poll_s: float = 1,
    timeout_s: float = 120,
) -> bool:
    source_root = _safe_root(source_root)
    if not artifact_root.is_absolute() or ".." in artifact_root.parts:
        raise ValueError("artifact_root must be absolute and not contain traversal")
    for p in [artifact_root] + list(artifact_root.parents):
        if p.is_symlink():
            raise ValueError("artifact_root contains symlink in ancestors")
    artifact_root = artifact_root.resolve()
    checkpoint_path = _safe_root(checkpoint_path)

    child_script = (Path(__file__).resolve().parents[2] / "pose" / "child.py").resolve()
    if not child_script.is_absolute() or ".." in child_script.parts:
        raise ValueError("child script path is unsafe")
    if child_script.is_symlink() or not child_script.is_file():
        raise ValueError("child script does not exist")

    captured_request: PoseJobInput | None = None
    captured_hash: str | None = None

    def make_command(claimed: AnalysisJob, attempt: Path) -> Sequence[str]:
        nonlocal captured_request, captured_hash
        try:
            video, exercise, variant = store.get_input(claimed.owner, claimed.id)
        except NotFound as exc:
            raise LeaseLost("input revoked") from exc
        job_input = PoseJobInput(job=claimed, video=video, exercise_id=exercise, variant=variant)
        payload = job_input.model_dump_json().encode("utf-8")
        request_sha = _sha256_bytes(payload)
        captured_request = job_input
        captured_hash = request_sha

        attempt_path = _safe_root(attempt)
        if not attempt_path.is_relative_to(artifact_root):
            raise ValueError("attempt directory is outside artifact_root")

        request_path = attempt_path / "request.json"
        _write_exclusive(request_path, payload, mode=0o600)
        _fsync_path(request_path)

        return [
            sys.executable,
            str(child_script),
            "--request", str(request_path),
            "--source-root", str(source_root),
            "--attempt-root", str(attempt_path),
            "--checkpoint", str(checkpoint_path),
            "--checkpoint-sha256", checkpoint_sha256,
        ]

    def validate(claimed: AnalysisJob, attempt: Path) -> str:
        assert captured_request is not None
        assert captured_hash is not None
        if captured_request.job.id != claimed.id or captured_request.job.lease_owner != claimed.lease_owner:
            raise ValueError("claimed job identity does not match captured request")
        return validate_pose_artifacts(
            captured_request,
            captured_hash,
            attempt,
            checkpoint_sha256,
        )

    return supervise_once(
        store,
        artifact_root,
        make_command,
        validate,
        worker=worker,
        lease_s=lease_s,
        poll_s=poll_s,
        timeout_s=timeout_s,
    )
