"""Private pose-only child; no database, scoring, LLM calls or fake provider flag."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

from contracts.analysis import AnalysisResult, CoachingResult
from contracts.enums import CoachingStatus
from contracts.pose import PoseFrame
from contracts.pose_job import PoseJobArtifacts, PoseJobInput
from providers.pose.artifacts import read_pose_frames
from app.processing_config import analysis_resize_enabled_for
from providers.pose.mediapipe_provider import MediaPipePoseProvider
from providers.pose.proxy import build_proxy

MAX_REQUEST_BYTES = 1 << 20
POSE_KEY_RE = re.compile(r"^pose/([0-9a-f]{64})\.jsonl$")


def _has_dotdot(path: Path) -> bool:
    return ".." in path.parts


def _any_symlink_in_ancestors(path: Path) -> bool:
    for parent in [path, *path.parents]:
        if parent.is_symlink():
            return True
    return False


def _validate_request_path(request_path: Path, attempt_root: Path, source_root: Path) -> bytes:
    if not attempt_root.is_absolute():
        raise ValueError("attempt_root must be absolute")
    if not source_root.is_absolute():
        raise ValueError("source_root must be absolute")
    if _has_dotdot(request_path) or _has_dotdot(attempt_root) or _has_dotdot(source_root):
        raise ValueError("paths must not contain '..'")
    if any(_any_symlink_in_ancestors(p) for p in (request_path, attempt_root, source_root)):
        raise ValueError("request_path has symlink in ancestors")
    if request_path != attempt_root / "request.json":
        raise ValueError("request_path must equal attempt_root/request.json")
    if not attempt_root.is_dir():
        raise ValueError("attempt_root must be an existing directory")
    if not source_root.is_dir():
        raise ValueError("source_root must be an existing directory")
    if not request_path.is_file():
        raise ValueError("request must be an existing regular file")
    size = request_path.stat().st_size
    if size <= 0 or size > MAX_REQUEST_BYTES:
        raise ValueError("request must be a non-empty regular file <= 1MiB")
    return request_path.read_bytes()


def _any_valid_joints(frames: list[PoseFrame]) -> bool:
    for frame in frames:
        for joint in frame.joints.values():
            if joint.valid:
                return True
    return False


def run_child(
    request_path: Path,
    source_root: Path,
    attempt_root: Path,
    checkpoint: Path,
    checkpoint_sha256: str,
) -> None:
    request_bytes = _validate_request_path(request_path, attempt_root, source_root)
    request_hash = hashlib.sha256(request_bytes).hexdigest()
    request = PoseJobInput.model_validate_json(request_bytes)

    video = request.video
    proxy_root = attempt_root / "proxy"
    proxy_map = build_proxy(video, source_root, proxy_root)

    provider = MediaPipePoseProvider(
        checkpoint_path=str(checkpoint),
        checkpoint_sha256=checkpoint_sha256,
        source_root=source_root,
        artifact_root=attempt_root,
        start_s=0,
        duration_s=video.duration_s,
        sample_rate_hz=30,
        visibility_threshold=0.6,
        resize_for_analysis=analysis_resize_enabled_for(request.exercise_id),
    )
    pose = provider.infer(video)

    m = POSE_KEY_RE.fullmatch(pose.frames_artifact_key)
    if not m:
        raise ValueError("invalid pose frames artifact key")
    content_hash = m.group(1)
    frames = read_pose_frames(attempt_root, pose.frames_artifact_key, expected_sha256=content_hash)
    if not _any_valid_joints(frames):
        raise ValueError("no valid joints across all frames")

    pose_dir = attempt_root / "pose"
    pose_dir.chmod(0o700)

    report = AnalysisResult(
        analysis_id=request.job.id,
        exercise=request.exercise_id,
        variant=request.variant,
        reps=[],
        metrics=[],
        score=None,
        source_ids=[],
        coaching=CoachingResult(status=CoachingStatus.UNAVAILABLE, limitations=["POSE_ONLY"]),
        warnings=[
            "POSE_ONLY",
            "MEASUREMENTS_UNAVAILABLE",
            "REFERENCE_UNAVAILABLE",
            "COACHING_UNAVAILABLE",
            "ESTIMATED_3D",
            "IDENTITY_UNVERIFIED",
        ],
        provenance={
            "pipeline": "pose-job-v1",
            "input_sha256": video.sha256,
            "version_hash": request.job.version_hash,
            "pose_model_revision": pose.model_revision,
        },
    )

    artifacts = PoseJobArtifacts(
        request_sha256=request_hash,
        pose=pose,
        proxy=proxy_map,
        report=report,
    )

    manifest_path = attempt_root / "manifest.json"
    body = artifacts.model_dump_json().encode("utf-8")
    if len(body) > MAX_REQUEST_BYTES:
        raise ValueError("manifest body exceeds 1MiB")

    fd = os.open(str(manifest_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--attempt-root", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--checkpoint-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        run_child(args.request, args.source_root, args.attempt_root, args.checkpoint, args.checkpoint_sha256)
        return 0
    except KeyboardInterrupt:
        raise
    except Exception:
        print("POSE_CHILD_FAILED", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
