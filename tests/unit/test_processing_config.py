import hashlib
import json
from pathlib import Path

import pytest

from app.processing_config import (
    DEFAULT_CHECKPOINT_SHA256,
    checkpoint_sha_from_env,
    load_worker_config,
    processing_version,
)


def test_processing_version_deterministic():
    v1 = processing_version(DEFAULT_CHECKPOINT_SHA256)
    v2 = processing_version(DEFAULT_CHECKPOINT_SHA256)
    assert v1 == v2
    recipe = {
        "pipeline": "pose-job-v1",
        "checkpoint_sha256": DEFAULT_CHECKPOINT_SHA256,
        "mapping": "mp33-camera-v1",
        "sample_rate_hz": 30,
        "visibility_threshold": 0.6,
    }
    expected = hashlib.sha256(json.dumps(recipe, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert v1 == expected


def test_processing_version_different_sha():
    other = "0" * 64
    assert processing_version(other) != processing_version(DEFAULT_CHECKPOINT_SHA256)


def test_processing_version_invalid_sha():
    with pytest.raises(ValueError):
        processing_version("bad")


def test_checkpoint_sha_from_env_default(monkeypatch):
    monkeypatch.delenv("POSE_CHECKPOINT_SHA256", raising=False)
    assert checkpoint_sha_from_env() == DEFAULT_CHECKPOINT_SHA256


def test_checkpoint_sha_from_env_override(monkeypatch):
    sha = "a" * 64
    monkeypatch.setenv("POSE_CHECKPOINT_SHA256", sha)
    assert checkpoint_sha_from_env() == sha


def test_checkpoint_sha_from_env_invalid(monkeypatch):
    monkeypatch.setenv("POSE_CHECKPOINT_SHA256", "GGGG")
    with pytest.raises(ValueError):
        checkpoint_sha_from_env()


def _make_checkpoint(tmp_path: Path, monkeypatch) -> Path:
    data = b"dummy checkpoint bytes"
    p = tmp_path / "pose_landmarker_full.task"
    p.write_bytes(data)
    monkeypatch.setenv("POSE_CHECKPOINT_SHA256", hashlib.sha256(data).hexdigest())
    return p


def test_load_worker_config_defaults(tmp_path, monkeypatch):
    cp = _make_checkpoint(tmp_path, monkeypatch)
    src = tmp_path / "media"
    src.mkdir()
    art = tmp_path / "artifacts"
    db = tmp_path / "db.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    monkeypatch.setenv("VIDEO_ROOT", str(src))
    monkeypatch.setenv("ARTIFACT_ROOT", str(art))
    monkeypatch.setenv("POSE_CHECKPOINT_PATH", str(cp))
    cfg = load_worker_config()
    assert cfg.db_path == db
    assert cfg.source_root == src
    assert cfg.artifact_root == art
    assert cfg.checkpoint_path == cp
    assert cfg.checkpoint_sha256 == hashlib.sha256(cp.read_bytes()).hexdigest()
    assert cfg.lease_s == 60.0
    assert cfg.poll_s == 1.0
    assert cfg.timeout_s == 300.0
    assert cfg.idle_s == 1.0


def test_load_worker_config_actual_sha(tmp_path, monkeypatch):
    data = b"dummy checkpoint bytes"
    cp = tmp_path / "pose_landmarker_full.task"
    cp.write_bytes(data)
    sha = hashlib.sha256(data).hexdigest()
    src = tmp_path / "media"
    src.mkdir()
    db = tmp_path / "db.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    monkeypatch.setenv("VIDEO_ROOT", str(src))
    monkeypatch.setenv("ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("POSE_CHECKPOINT_PATH", str(cp))
    monkeypatch.setenv("POSE_CHECKPOINT_SHA256", sha)
    cfg = load_worker_config()
    assert cfg.checkpoint_sha256 == sha


def test_load_worker_config_bounds(tmp_path, monkeypatch):
    cp = _make_checkpoint(tmp_path, monkeypatch)
    src = tmp_path / "media"
    src.mkdir()
    db = tmp_path / "db.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    monkeypatch.setenv("VIDEO_ROOT", str(src))
    monkeypatch.setenv("ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("POSE_CHECKPOINT_PATH", str(cp))
    monkeypatch.setenv("WORKER_LEASE_SECONDS", "3601")
    with pytest.raises(ValueError):
        load_worker_config()


def test_load_worker_config_poll_too_large(tmp_path, monkeypatch):
    cp = _make_checkpoint(tmp_path, monkeypatch)
    src = tmp_path / "media"
    src.mkdir()
    db = tmp_path / "db.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    monkeypatch.setenv("VIDEO_ROOT", str(src))
    monkeypatch.setenv("ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("POSE_CHECKPOINT_PATH", str(cp))
    monkeypatch.setenv("WORKER_LEASE_SECONDS", "6")
    monkeypatch.setenv("WORKER_POLL_SECONDS", "2.1")
    with pytest.raises(ValueError):
        load_worker_config()


def test_load_worker_config_rejects_symlink(tmp_path, monkeypatch):
    cp = _make_checkpoint(tmp_path, monkeypatch)
    src = tmp_path / "media"
    src.mkdir()
    real = tmp_path / "real_media"
    real.mkdir()
    link = tmp_path / "media_link"
    link.symlink_to(real)
    db = tmp_path / "db.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    monkeypatch.setenv("VIDEO_ROOT", str(link))
    monkeypatch.setenv("ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("POSE_CHECKPOINT_PATH", str(cp))
    with pytest.raises(ValueError):
        load_worker_config()


def test_load_worker_config_rejects_traversal(tmp_path, monkeypatch):
    cp = _make_checkpoint(tmp_path, monkeypatch)
    src = tmp_path / "media"
    src.mkdir()
    db = tmp_path / "db.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    monkeypatch.setenv("VIDEO_ROOT", str(src / ".." / "media"))
    monkeypatch.setenv("ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("POSE_CHECKPOINT_PATH", str(cp))
    with pytest.raises(ValueError):
        load_worker_config()
