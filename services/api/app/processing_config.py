from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CHECKPOINT_SHA256 = "5134a3aad27a58b93da0088d431f366da362b44e3ccfbe3462b3827a839011b1"

_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def checkpoint_sha_from_env() -> str:
    sha = os.environ.get("POSE_CHECKPOINT_SHA256", "")
    if not sha:
        sha = DEFAULT_CHECKPOINT_SHA256
    if not _SHA_RE.fullmatch(sha):
        raise ValueError("POSE_CHECKPOINT_SHA256 must be 64 lowercase hex chars")
    return sha


ANALYSIS_RESIZE_EXERCISES = ("dumbbell_curl",)


def analysis_resize_enabled() -> bool:
    raw = os.environ.get("POSE_ANALYSIS_RESIZE", "0")
    if raw not in ("0", "1"):
        raise ValueError("POSE_ANALYSIS_RESIZE must be '0' or '1'")
    return raw == "1"


def analysis_resize_enabled_for(exercise_id: str) -> bool:
    return analysis_resize_enabled() and exercise_id in ANALYSIS_RESIZE_EXERCISES


def processing_version(checkpoint_sha256: str) -> str:
    if not _SHA_RE.fullmatch(checkpoint_sha256):
        raise ValueError("checkpoint_sha256 must be 64 lowercase hex chars")
    recipe = {
        "pipeline": "pose-job-v1",
        "checkpoint_sha256": checkpoint_sha256,
        "mapping": "mp33-camera-v1",
        "sample_rate_hz": 30,
        "visibility_threshold": 0.6,
        "media_limits_version": "full-set-60s-v3",
        "max_duration_s": 60,
        "decoder_wall_budget_s": 120,
        "timestamp_probe_budget_s": 90,
        "analysis_decode_recipe": "analysis-decode-720-v1",
        "analysis_resize_enabled": analysis_resize_enabled(),
        "analysis_resize_exercises": list(ANALYSIS_RESIZE_EXERCISES),
        "analysis_short_edge": 720,
        "analysis_long_edge": 1280,
    }
    return hashlib_canonical_json(recipe)


def hashlib_canonical_json(obj: dict) -> str:
    compact = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(compact.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class WorkerConfig:
    db_path: Path
    source_root: Path
    artifact_root: Path
    checkpoint_path: Path
    checkpoint_sha256: str
    lease_s: float
    poll_s: float
    timeout_s: float
    idle_s: float


def _has_traversal_or_symlink(path: Path) -> bool:
    if ".." in path.parts:
        return True
    for p in [path] + list(path.parents):
        if p.is_symlink():
            return True
    return False


def _env_path(name: str, default: str) -> Path:
    raw = os.environ.get(name, default)
    if "\x00" in raw:
        raise ValueError(f"{name} contains NUL")
    path = Path(raw)
    if not path.is_absolute():
        raise ValueError(f"{name} must be absolute")
    if _has_traversal_or_symlink(path):
        raise ValueError(f"{name} contains traversal or symlink")
    return path


def _finite_positive(name: str, val: float, *, max_val: float | None = None) -> float:
    if not isinstance(val, (int, float)) or isinstance(val, bool) or val <= 0 or val != val or val == float("inf"):
        raise ValueError(f"{name} must be finite positive")
    if max_val is not None and val > max_val:
        raise ValueError(f"{name} must be <= {max_val}")
    return float(val)


def _verify_checkpoint(path: Path, expected_sha256: str) -> None:
    h = hashlib.sha256()
    size = 0
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > 64 * 1024 * 1024:
                raise ValueError("checkpoint exceeds 64MiB")
            h.update(chunk)
    if size == 0:
        raise ValueError("checkpoint is empty")
    if h.hexdigest() != expected_sha256:
        raise ValueError("checkpoint SHA256 mismatch")


def load_worker_config() -> WorkerConfig:
    db_url = os.environ.get("DATABASE_URL", "sqlite:////state/motion_xray.db")
    if "\x00" in db_url:
        raise ValueError("DATABASE_URL contains NUL")
    if "?" in db_url or "#" in db_url:
        raise ValueError("DATABASE_URL must not contain query or fragment")
    if not db_url.startswith("sqlite:///"):
        raise ValueError("DATABASE_URL must be sqlite absolute path")
    db_path = Path(db_url[len("sqlite:///"):])
    if not db_path.is_absolute():
        raise ValueError("DATABASE_URL sqlite path must be absolute")
    if _has_traversal_or_symlink(db_path):
        raise ValueError("DATABASE_URL path contains traversal or symlink")

    source_root = _env_path("VIDEO_ROOT", "/state/media")
    artifact_root = _env_path("ARTIFACT_ROOT", "/state/artifacts")
    checkpoint_path = _env_path("POSE_CHECKPOINT_PATH", "/models/pose_landmarker_full.task")

    if source_root.exists() and not source_root.is_dir():
        raise ValueError("VIDEO_ROOT must be a directory")
    if not checkpoint_path.is_file():
        raise ValueError("POSE_CHECKPOINT_PATH must be an existing regular file")

    checkpoint_sha256 = checkpoint_sha_from_env()
    _verify_checkpoint(checkpoint_path, checkpoint_sha256)

    lease_s = _finite_positive("WORKER_LEASE_SECONDS", float(os.environ.get("WORKER_LEASE_SECONDS", 60)), max_val=3600)
    poll_s = _finite_positive("WORKER_POLL_SECONDS", float(os.environ.get("WORKER_POLL_SECONDS", 1)))
    timeout_s = _finite_positive("JOB_TIMEOUT_SECONDS", float(os.environ.get("JOB_TIMEOUT_SECONDS", 300)), max_val=3600)
    idle_s = _finite_positive("WORKER_IDLE_SECONDS", float(os.environ.get("WORKER_IDLE_SECONDS", 1)), max_val=60)

    if poll_s >= lease_s / 3:
        raise ValueError("WORKER_POLL_SECONDS must be < WORKER_LEASE_SECONDS/3")

    concurrency = os.environ.get("WORKER_CONCURRENCY", "1")
    if concurrency != "1":
        raise ValueError("WORKER_CONCURRENCY must be 1")

    return WorkerConfig(
        db_path=db_path,
        source_root=source_root,
        artifact_root=artifact_root,
        checkpoint_path=checkpoint_path,
        checkpoint_sha256=checkpoint_sha256,
        lease_s=lease_s,
        poll_s=poll_s,
        timeout_s=timeout_s,
        idle_s=idle_s,
    )
