"""Unit tests for bootstrap_local.py helper functions.

These tests use importlib to load the helper module from the repo scripts
directory and exercise the pure functions with temporary directories and
mocked HTTP responses. No real network, Docker, or provider credentials are
used.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import tempfile
from pathlib import Path
import urllib.error

import pytest

# ---------------------------------------------------------------------------
# Load the helper module from the repo scripts directory.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER_PATH = REPO_ROOT / "scripts" / "bootstrap_local.py"

spec = importlib.util.spec_from_file_location("bootstrap_local", HELPER_PATH)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_repo():
    """Create a temporary directory that mimics a repo root."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def example_env(tmp_repo):
    """Write a minimal .env.example with a SESSION_SECRET line."""
    path = tmp_repo / ".env.example"
    path.write_text(
        "APP_ENV=development\n"
        "SESSION_SECRET=\n"
        "DATABASE_URL=sqlite:////state/motion_xray.db\n"
    )
    return path


@pytest.fixture
def valid_manifest(tmp_repo):
    """Write a valid manifest JSON file."""
    manifest_dir = tmp_repo / "data" / "pose_models"
    manifest_dir.mkdir(parents=True)
    path = manifest_dir / "mediapipe-full-v1.json"
    path.write_text(json.dumps({
        "download_url": helper.EXPECTED_MODEL_URL,
        "sha256": helper.EXPECTED_MODEL_SHA256,
        "bytes": helper.EXPECTED_MODEL_BYTES,
        "local_path": "models/pose_landmarker_full.task",
    }))
    return path


@pytest.fixture
def mock_download_bytes():
    """Return a small deterministic byte sequence for mock downloads."""
    return b"mock-model-data" * 100  # 1500 bytes


@pytest.fixture
def mock_download_sha(mock_download_bytes):
    """SHA-256 of the mock download bytes."""
    return hashlib.sha256(mock_download_bytes).hexdigest()


# ---------------------------------------------------------------------------
# prepare_env tests
# ---------------------------------------------------------------------------

def test_prepare_env_creates_from_example(tmp_repo, example_env):
    """When .env does not exist, it is created from .env.example with a secret."""
    env_path = tmp_repo / ".env"
    result = helper.prepare_env(tmp_repo, env_path, example_env)
    assert result["created"] is True
    assert result["secret_filled"] is True
    assert result["secret_already_set"] is False
    assert result["changed"] is True
    assert env_path.is_file()
    content = env_path.read_text()
    assert "SESSION_SECRET=" in content
    # The secret should be 64 hex chars, not empty.
    for line in content.splitlines():
        if line.startswith("SESSION_SECRET="):
            val = line.split("=", 1)[1]
            assert len(val) == 64
            assert val != ""


def test_prepare_env_preserves_existing_secret(tmp_repo, example_env):
    """When .env already has a non-empty SESSION_SECRET, it is preserved."""
    env_path = tmp_repo / ".env"
    env_path.write_text(
        "APP_ENV=development\n"
        "SESSION_SECRET=my-existing-secret\n"
        "DATABASE_URL=sqlite:////state/motion_xray.db\n"
    )
    result = helper.prepare_env(tmp_repo, env_path, example_env)
    assert result["created"] is False
    assert result["secret_filled"] is False
    assert result["secret_already_set"] is True
    assert result["changed"] is False
    assert "my-existing-secret" in env_path.read_text()


def test_prepare_env_fills_placeholder(tmp_repo, example_env):
    """When SESSION_SECRET is a known placeholder, it is replaced."""
    env_path = tmp_repo / ".env"
    env_path.write_text(
        "APP_ENV=development\n"
        "SESSION_SECRET=changeme\n"
        "DATABASE_URL=sqlite:////state/motion_xray.db\n"
    )
    result = helper.prepare_env(tmp_repo, env_path, example_env)
    assert result["secret_filled"] is True
    content = env_path.read_text()
    assert "changeme" not in content
    for line in content.splitlines():
        if line.startswith("SESSION_SECRET="):
            val = line.split("=", 1)[1]
            assert len(val) == 64


def test_prepare_env_duplicate_secret_raises(tmp_repo, example_env):
    """Duplicate SESSION_SECRET lines raise ValueError."""
    env_path = tmp_repo / ".env"
    env_path.write_text(
        "SESSION_SECRET=first\n"
        "SESSION_SECRET=second\n"
    )
    with pytest.raises(ValueError, match="malformed .env"):
        helper.prepare_env(tmp_repo, env_path, example_env)


def test_prepare_env_rejects_symlink_env(tmp_repo, example_env):
    """Reject an existing symlink without modifying its target."""
    env_path = tmp_repo / ".env"
    real_path = tmp_repo / "real.env"
    original = "SESSION_SECRET=original\n"
    real_path.write_text(original)
    env_path.symlink_to(real_path)
    with pytest.raises(ValueError, match="symlink env"):
        helper.prepare_env(tmp_repo, env_path, example_env)
    assert env_path.is_symlink()
    assert real_path.read_text() == original


# ---------------------------------------------------------------------------
# verify_model_manifest tests
# ---------------------------------------------------------------------------

def test_verify_valid_manifest(valid_manifest):
    """A valid manifest passes verification."""
    data = helper.verify_model_manifest(valid_manifest)
    assert data["download_url"] == helper.EXPECTED_MODEL_URL


def test_verify_manifest_wrong_url(tmp_repo):
    """A manifest with a different URL raises ValueError."""
    path = tmp_repo / "manifest.json"
    path.write_text(json.dumps({
        "download_url": "https://evil.example.com/model.task",
        "sha256": helper.EXPECTED_MODEL_SHA256,
        "bytes": helper.EXPECTED_MODEL_BYTES,
        "local_path": "models/pose_landmarker_full.task",
    }))
    with pytest.raises(ValueError, match="does not match the pinned URL"):
        helper.verify_model_manifest(path)


def test_verify_manifest_wrong_sha(tmp_repo):
    """A manifest with a different SHA raises ValueError."""
    path = tmp_repo / "manifest.json"
    path.write_text(json.dumps({
        "download_url": helper.EXPECTED_MODEL_URL,
        "sha256": "00" * 32,
        "bytes": helper.EXPECTED_MODEL_BYTES,
        "local_path": "models/pose_landmarker_full.task",
    }))
    with pytest.raises(ValueError, match="sha256 does not match"):
        helper.verify_model_manifest(path)


def test_verify_manifest_traversal_local_path(tmp_repo):
    """A manifest with '..' in local_path raises ValueError."""
    path = tmp_repo / "manifest.json"
    path.write_text(json.dumps({
        "download_url": helper.EXPECTED_MODEL_URL,
        "sha256": helper.EXPECTED_MODEL_SHA256,
        "bytes": helper.EXPECTED_MODEL_BYTES,
        "local_path": "../etc/passwd",
    }))
    with pytest.raises(ValueError, match="local_path"):
        helper.verify_model_manifest(path)


# ---------------------------------------------------------------------------
# download_model tests
# ---------------------------------------------------------------------------

def test_download_model_skips_valid_cache(tmp_repo, mock_download_bytes, mock_download_sha):
    """When a valid model already exists, download is skipped."""
    models_dir = tmp_repo / "models"
    models_dir.mkdir()
    target = models_dir / "pose_landmarker_full.task"
    target.write_bytes(mock_download_bytes)

    manifest = {
        "download_url": helper.EXPECTED_MODEL_URL,
        "sha256": mock_download_sha,
        "bytes": len(mock_download_bytes),
        "local_path": "models/pose_landmarker_full.task",
    }

    # url_opener should never be called.
    def fail_opener(*args, **kwargs):
        raise RuntimeError("should not download")

    result = helper.download_model(tmp_repo, manifest, url_opener=fail_opener)
    assert result == target


def test_download_model_corrupt_cache_raises(tmp_repo, mock_download_sha):
    """When an existing model has wrong content, ValueError is raised."""
    models_dir = tmp_repo / "models"
    models_dir.mkdir()
    target = models_dir / "pose_landmarker_full.task"
    target.write_bytes(b"corrupt data")

    manifest = {
        "download_url": helper.EXPECTED_MODEL_URL,
        "sha256": mock_download_sha,
        "bytes": 100,
        "local_path": "models/pose_landmarker_full.task",
    }

    with pytest.raises(ValueError, match="existing model file"):
        helper.download_model(tmp_repo, manifest)


def test_download_model_symlink_target_rejected(tmp_repo):
    """If the target path is a symlink, download is rejected."""
    models_dir = tmp_repo / "models"
    models_dir.mkdir()
    real = tmp_repo / "real.model"
    real.write_bytes(b"data")
    target = models_dir / "pose_landmarker_full.task"
    target.symlink_to(real)

    manifest = {
        "download_url": helper.EXPECTED_MODEL_URL,
        "sha256": helper.EXPECTED_MODEL_SHA256,
        "bytes": helper.EXPECTED_MODEL_BYTES,
        "local_path": "models/pose_landmarker_full.task",
    }

    with pytest.raises(ValueError, match="symlink"):
        helper.download_model(tmp_repo, manifest)


def test_download_model_url_spoof_rejected(tmp_repo, mock_download_bytes, mock_download_sha):
    """If the opener returns a response with a different final URL, download fails."""
    manifest = {
        "download_url": helper.EXPECTED_MODEL_URL,
        "sha256": mock_download_sha,
        "bytes": len(mock_download_bytes),
        "local_path": "models/pose_landmarker_full.task",
    }

    class SpoofedResponse(io.BytesIO):
        url = "https://evil.example.com/fake.task"

    def spoof_opener(url, timeout):
        return SpoofedResponse(mock_download_bytes)

    with pytest.raises(ValueError, match="redirected to unexpected URL"):
        helper.download_model(tmp_repo, manifest, url_opener=spoof_opener)


def test_download_model_oversize_rejected(tmp_repo, mock_download_bytes):
    """If the download exceeds the manifest size, it is rejected."""
    manifest = {
        "download_url": helper.EXPECTED_MODEL_URL,
        "sha256": helper.EXPECTED_MODEL_SHA256,
        "bytes": 10,  # much smaller than mock data
        "local_path": "models/pose_landmarker_full.task",
    }

    class OversizedResponse(io.BytesIO):
        url = helper.EXPECTED_MODEL_URL

    def oversized_opener(url, timeout):
        return OversizedResponse(mock_download_bytes)

    with pytest.raises(ValueError, match="exceeded manifest size"):
        helper.download_model(tmp_repo, manifest, url_opener=oversized_opener)


def test_download_model_checksum_mismatch_rejected(tmp_repo):
    """If the downloaded data has a different SHA, it is rejected."""
    manifest = {
        "download_url": helper.EXPECTED_MODEL_URL,
        "sha256": "00" * 32,
        "bytes": 10,
        "local_path": "models/pose_landmarker_full.task",
    }

    class MismatchResponse(io.BytesIO):
        url = helper.EXPECTED_MODEL_URL

    def mismatch_opener(url, timeout):
        return MismatchResponse(b"1234567890")

    with pytest.raises(ValueError, match="sha256"):
        helper.download_model(tmp_repo, manifest, url_opener=mismatch_opener)


def test_download_model_partial_cleanup(tmp_repo):
    """If download fails, the .part file is cleaned up."""
    manifest = {
        "download_url": helper.EXPECTED_MODEL_URL,
        "sha256": helper.EXPECTED_MODEL_SHA256,
        "bytes": helper.EXPECTED_MODEL_BYTES,
        "local_path": "models/pose_landmarker_full.task",
    }

    def failing_opener(url, timeout):
        raise urllib.error.URLError("connection refused")

    with pytest.raises(urllib.error.URLError):
        helper.download_model(tmp_repo, manifest, url_opener=failing_opener)

    # The .part file should not exist.
    part_path = tmp_repo / "models" / "pose_landmarker_full.task.part"
    assert not part_path.exists()


# ---------------------------------------------------------------------------
# Targeted regression tests
# ---------------------------------------------------------------------------

def test_prepare_env_rejects_symlink_env_file(tmp_repo, example_env):
    """If .env is a symlink (even dangling), prepare_env must reject it."""
    env_path = tmp_repo / ".env"
    # Dangling symlink: target does not exist.
    env_path.symlink_to(tmp_repo / "does-not-exist")
    with pytest.raises(ValueError, match="symlink env"):
        helper.prepare_env(tmp_repo, env_path, example_env)


def test_validate_local_target_rejects_symlink_parent(tmp_repo):
    """If a parent component of the model path is a symlink, reject it."""
    real_models = tmp_repo / "real_models"
    real_models.mkdir()
    models_link = tmp_repo / "models"
    models_link.symlink_to(real_models)
    with pytest.raises(ValueError, match="symlink"):
        helper._validate_local_target(tmp_repo, "models/pose_landmarker_full.task")


def test_prepare_env_missing_newline_safe_append(tmp_repo, example_env):
    """If .env has no trailing newline and no SESSION_SECRET, append safely."""
    env_path = tmp_repo / ".env"
    # No trailing newline, no SESSION_SECRET line at all.
    env_path.write_text("APP_ENV=development")
    result = helper.prepare_env(tmp_repo, env_path, example_env)
    assert result["secret_filled"] is True
    content = env_path.read_text()
    # The previous line must not be concatenated onto the secret.
    assert "APP_ENV=development\nSESSION_SECRET=" in content
    # The secret value must be 64 hex chars.
    for line in content.splitlines():
        if line.startswith("SESSION_SECRET="):
            assert len(line.split("=", 1)[1]) == 64
