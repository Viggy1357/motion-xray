from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.store import Store
from app.supervisor import supervise_once
from contracts.enums import JobState
from contracts.jobs import AnalysisJob
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


class CollisionStore(Store):
    def __init__(self, dbpath: Path, root: Path) -> None:
        super().__init__(dbpath)
        self.root = root
        self.attempt_dir: Path | None = None
        self.sentinel: Path | None = None

    def claim(self, *args, **kwargs) -> AnalysisJob | None:
        job = super().claim(*args, **kwargs)
        if job is not None and job.lease_owner is not None:
            self.attempt_dir = self.root / "attempts" / job.id / job.lease_owner
            self.attempt_dir.mkdir(parents=True, exist_ok=True)
            self.sentinel = self.attempt_dir / "sentinel"
            self.sentinel.write_text("keep")
        return job


def test_collision_attempt_unavailable(tmp_path: Path) -> None:
    store, original_job, artifact_root = queued_case(tmp_path)
    collision_store = CollisionStore(tmp_path / "jobs.sqlite3", artifact_root)

    def make_command(claimed: AnalysisJob, attempt: Path) -> list[str]:
        raise AssertionError("command callback should not be called")

    def validate_output(claimed: AnalysisJob, attempt: Path) -> str:
        raise AssertionError("validate_output should not be called")

    result = supervise_once(
        collision_store,
        artifact_root,
        make_command,
        validate_output,
        worker="pose",
        lease_s=2,
        poll_s=0.05,
        timeout_s=3,
        terminate_grace_s=0.05,
    )

    assert result is True
    final_job = store.get_job("owner", original_job.id)
    assert final_job.state == JobState.FAILED
    assert final_job.error == "ATTEMPT_UNAVAILABLE"
    assert collision_store.sentinel is not None
    assert collision_store.sentinel.read_text() == "keep"


@pytest.mark.parametrize("bad_kind", ["missing", "empty", "dir", "oversize", "symlink", "traversal"])
def test_bad_output_invalid(bad_kind: str, tmp_path: Path) -> None:
    store, original_job, artifact_root = queued_case(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_file = outside / "keep"
    outside_file.write_text("keep")

    def make_command(claimed: AnalysisJob, attempt: Path) -> list[str]:
        script = (
            "import json, os, sys, time\n"
            "kind = sys.argv[1]\n"
            "attempt = sys.argv[2]\n"
            "outside = sys.argv[3]\n"
            "if kind == 'missing':\n"
            "    pass\n"
            "elif kind == 'empty':\n"
            "    open(os.path.join(attempt, 'result.json'), 'wb').close()\n"
            "elif kind == 'dir':\n"
            "    os.mkdir(os.path.join(attempt, 'result.json'))\n"
            "elif kind == 'oversize':\n"
            "    open(os.path.join(attempt, 'result.json'), 'wb').write(b'x' * (1_048_576 + 1))\n"
            "elif kind == 'symlink':\n"
            "    os.symlink(outside, os.path.join(attempt, 'result.json'))\n"
            "elif kind == 'traversal':\n"
            "    pass\n"
        )
        return [sys.executable, "-c", script, bad_kind, str(attempt), str(outside_file)]

    def validate_output(claimed: AnalysisJob, attempt: Path) -> str:
        if bad_kind == "traversal":
            return "../outside"
        return "result.json"

    result = supervise_once(
        store,
        artifact_root,
        make_command,
        validate_output,
        worker="pose",
        lease_s=2,
        poll_s=0.05,
        timeout_s=3,
        terminate_grace_s=0.05,
    )

    assert result is True
    final_job = store.get_job("owner", original_job.id)
    assert final_job.state == JobState.FAILED
    assert final_job.error == "OUTPUT_INVALID"
    assert final_job.result_key is None
    assert outside_file.read_text() == "keep"
    attempts_dir = artifact_root / "attempts" / original_job.id
    assert not any(d.exists() for d in attempts_dir.iterdir())


class FaultStore(Store):
    def __init__(self, dbpath: Path, marker: Path, exception_type: type[BaseException]) -> None:
        super().__init__(dbpath)
        self.marker = marker
        self.raised = False
        self.exception_type = exception_type

    def heartbeat(self, *args, **kwargs) -> AnalysisJob:
        if self.marker.exists() and self.marker.read_text():
            if not self.raised:
                self.raised = True
                raise self.exception_type("fault")
        return super().heartbeat(*args, **kwargs)


@pytest.mark.parametrize("exception_type", [sqlite3.OperationalError, KeyboardInterrupt])
def test_heartbeat_fault_propagates_and_reaps(exception_type: type[BaseException], tmp_path: Path) -> None:
    store, original_job, artifact_root = queued_case(tmp_path)
    marker = tmp_path / "pid"
    fault_store = FaultStore(tmp_path / "jobs.sqlite3", marker, exception_type)

    def make_command(claimed: AnalysisJob, attempt: Path) -> list[str]:
        script = (
            "import os, sys, time\n"
            "open(sys.argv[1], 'w').write(str(os.getpid()))\n"
            "time.sleep(30)\n"
        )
        return [sys.executable, "-c", script, str(marker)]

    def validate_output(claimed: AnalysisJob, attempt: Path) -> str:
        raise AssertionError("validate_output should not be called")

    with pytest.raises(exception_type):
        supervise_once(
            fault_store,
            artifact_root,
            make_command,
            validate_output,
            worker="pose",
            lease_s=2,
            poll_s=0.05,
            timeout_s=3,
            terminate_grace_s=0.05,
        )

    pid_text = marker.read_text()
    assert pid_text
    pid = int(pid_text)

    with pytest.raises(ChildProcessError):
        os.waitpid(pid, os.WNOHANG)

    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)

    final_job = store.get_job("owner", original_job.id)
    assert final_job.state == JobState.RUNNING
    attempts_dir = artifact_root / "attempts" / original_job.id
    assert not any(d.exists() for d in attempts_dir.iterdir())


def test_grandchild_orphaned_after_leader_exit(tmp_path: Path) -> None:
    store, original_job, artifact_root = queued_case(tmp_path)
    marker = tmp_path / "grandchild.pid"

    gc_script = (
        "import os, signal, sys, time\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "open(sys.argv[1], 'w').write(str(os.getpid()))\n"
        "time.sleep(30)\n"
    )

    leader_script = (
        "import json, subprocess, sys, time\n"
        "from pathlib import Path\n"
        "marker = Path(sys.argv[1])\n"
        "subprocess.Popen([sys.executable, '-c', sys.argv[2], str(marker)])\n"
        "deadline = time.monotonic() + 2\n"
        "while time.monotonic() < deadline:\n"
        "    if marker.exists() and marker.read_text():\n"
        "        Path('result.json').write_text(json.dumps({'job': sys.argv[3]}))\n"
        "        sys.exit(0)\n"
        "    time.sleep(0.01)\n"
        "raise RuntimeError('grandchild marker not ready')\n"
    )

    def make_command(claimed: AnalysisJob, attempt: Path) -> list[str]:
        return [
            sys.executable, "-c", leader_script,
            str(marker), gc_script, claimed.id,
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
        lease_s=2,
        poll_s=0.05,
        timeout_s=3,
        terminate_grace_s=0.05,
    )

    assert result is True
    final_job = store.get_job("owner", original_job.id)
    assert final_job.state == JobState.SUCCEEDED
    assert marker.exists()

    pid_text = marker.read_text()
    assert pid_text
    pid = int(pid_text)

    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        stat_path = Path(f"/proc/{pid}/stat")
        if not stat_path.exists():
            break
        state = stat_path.read_text().split()[2]
        if state == "Z":
            break
        time.sleep(0.01)
    stat_path = Path(f"/proc/{pid}/stat")
    assert not stat_path.exists() or stat_path.read_text().split()[2] == "Z"
