"""The child rejects malformed private requests before importing the ML runtime."""
import runpy
import subprocess
import sys
from pathlib import Path

import pytest


CHILD = Path(__file__).resolve().parents[2] / "services/pose/child.py"


@pytest.mark.parametrize("body", [b"not json: PRIVATE_INPUT", b'{"private":"PRIVATE_INPUT"}'])
def test_bad_request_cli_is_sanitized(tmp_path: Path, body: bytes):
    source = tmp_path / "source"
    attempt = tmp_path / "attempt"
    source.mkdir()
    attempt.mkdir()
    request = attempt / "request.json"
    request.write_bytes(body)
    result = subprocess.run([
        sys.executable, str(CHILD), "--request", str(request), "--source-root", str(source),
        "--attempt-root", str(attempt), "--checkpoint", str(tmp_path / "unused.task"),
        "--checkpoint-sha256", "b" * 64,
    ], capture_output=True, text=True, timeout=5)
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "POSE_CHILD_FAILED\n"
    assert not (attempt / "manifest.json").exists()


def test_child_rejects_request_symlink_before_reading(tmp_path: Path):
    source = tmp_path / "source"
    attempt = tmp_path / "attempt"
    source.mkdir()
    attempt.mkdir()
    outside = tmp_path / "private.json"
    outside.write_text("PRIVATE_INPUT")
    request = attempt / "request.json"
    request.symlink_to(outside)
    validate = runpy.run_path(str(CHILD))["_validate_request_path"]
    with pytest.raises(ValueError, match="symlink"):
        validate(request, attempt, source)
    assert outside.read_text() == "PRIVATE_INPUT"
