from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.store import Store
from app.supervisor import supervise_once
from contracts.jobs import AnalysisJob
from contracts.enums import JobState
from contracts.media import VideoAsset


def queued_case(tmp_path: Path) -> tuple[Store, AnalysisJob, Path]:
    store = Store(tmp_path / "jobs.sqlite3")
    now = datetime.now(timezone.utc)
    store.register_asset(VideoAsset(
        id="asset1", owner_session_id="owner", storage_key="uploads/asset1.mp4",
        sha256="a" * 64, mime="video/mp4", bytes=1024, duration_s=5,
        width=640, height=480, rotation=0, created_at=now,
        expires_at=now + timedelta(hours=1),
    ))
    job = store.enqueue("owner", "asset1", "lat_pulldown", "v1", "request1", "vhash")
    assert store.get_job("owner", job.id).id == job.id
    return store, job, tmp_path / "artifacts"


@pytest.mark.parametrize("delay_s", [0, 0.7])
def test_supervise_once_success(tmp_path: Path, delay_s: float) -> None:
    store, original_job, artifact_root = queued_case(tmp_path)

    def make_command(claimed: AnalysisJob, attempt: Path) -> list[str]:
        return [
            sys.executable, "-c",
            "import json, sys, time; time.sleep(float(sys.argv[2])); "
            "open('result.json', 'w').write(json.dumps({'job': sys.argv[1]}))",
            claimed.id, str(delay_s),
        ]

    def validate_output(claimed: AnalysisJob, attempt: Path) -> str:
        data = json.loads((attempt / "result.json").read_text())
        assert data["job"] == claimed.id
        return "result.json"

    result = supervise_once(
        store,
        artifact_root,
        make_command,
        validate_output,
        worker="pose",
        lease_s=0.4,
        poll_s=0.05,
        timeout_s=3,
        terminate_grace_s=0.05,
    )

    assert result is True
    final_job = store.get_job("owner", original_job.id)
    assert final_job.state == JobState.SUCCEEDED
    assert final_job.result_key is not None
    assert final_job.result_key.startswith("attempts/" + original_job.id + "/")
    assert final_job.result_key.endswith("/result.json")

    claimed = store.get_job("owner", original_job.id)
    assert claimed.lease_owner is None

    attempts_dir = artifact_root / "attempts"
    job_dir = attempts_dir / original_job.id
    assert (attempts_dir.stat().st_mode & 0o777) == 0o700
    assert (job_dir.stat().st_mode & 0o777) == 0o700

    attempt_dir = next(job_dir.iterdir())
    assert (attempt_dir.stat().st_mode & 0o777) == 0o700
    result_file = attempt_dir / "result.json"
    assert (result_file.stat().st_mode & 0o777) == 0o600
    assert json.loads(result_file.read_text()) == {"job": original_job.id}


def test_supervise_once_timeout(tmp_path: Path) -> None:
    store, original_job, artifact_root = queued_case(tmp_path)
    marker = tmp_path / "pid"
    recorded: list[Path] = []

    def make_command(claimed: AnalysisJob, attempt: Path) -> list[str]:
        recorded.append(attempt)
        return [
            sys.executable, "-c",
            "import os, signal, sys, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            "open(sys.argv[1], 'w').write(str(os.getpid())); time.sleep(30)",
            str(marker),
        ]

    def validate_output(claimed: AnalysisJob, attempt: Path) -> str:
        raise AssertionError("validate_output should not be called on timeout")

    result = supervise_once(
        store,
        artifact_root,
        make_command,
        validate_output,
        worker="pose",
        lease_s=2,
        poll_s=0.05,
        timeout_s=0.5,
        terminate_grace_s=0.05,
    )

    assert result is True
    final_job = store.get_job("owner", original_job.id)
    assert final_job.state == JobState.FAILED
    assert final_job.error == "CHILD_TIMEOUT"
    assert final_job.result_key is None

    assert marker.exists()
    pid_text = marker.read_text()
    assert pid_text
    pid = int(pid_text)

    with pytest.raises(ChildProcessError):
        os.waitpid(pid, os.WNOHANG)

    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)

    assert len(recorded) == 1
    assert not recorded[0].exists()
