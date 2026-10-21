from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.store import NotFound, Store
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


@pytest.mark.parametrize("action", ["cancel", "delete_job", "delete_asset", "reclaim"])
def test_supervisor_reaps_child_on_external_action(tmp_path: Path, action: str) -> None:
    store, original_job, artifact_root = queued_case(tmp_path)
    marker = tmp_path / "pid"
    recorded: list[tuple[str, Path]] = []

    def make_command(claimed: AnalysisJob, attempt: Path) -> list[str]:
        assert claimed.lease_owner is not None
        recorded.append((claimed.lease_owner, attempt))
        return [
            sys.executable, "-c",
            "import os, signal, sys, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            "open(sys.argv[1], 'w').write(str(os.getpid())); time.sleep(30)",
            str(marker),
        ]

    def validate_output(claimed: AnalysisJob, attempt: Path) -> str:
        raise AssertionError("validate_output should not be called")

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            supervise_once,
            store,
            artifact_root,
            make_command,
            validate_output,
            worker="pose",
            lease_s=2,
            poll_s=0.05,
            timeout_s=5,
            terminate_grace_s=0.05,
        )

        try:
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline and (not marker.exists() or not marker.read_text()):
                time.sleep(0.01)
            assert marker.exists() and marker.read_text(), "child did not start and write pid"
            pid = int(marker.read_text())
            old_owner, old_path = recorded[0]

            if action == "cancel":
                store.cancel("owner", original_job.id)
            elif action == "delete_job":
                store.delete_job("owner", original_job.id)
            elif action == "delete_asset":
                store.delete_asset("owner", "asset1")
            else:
                new_claim = store.claim("other", now=time.time() + 3, lease_s=60)
                assert new_claim is not None
                assert new_claim.id == original_job.id
                assert new_claim.lease_owner is not None
                new_path = artifact_root / "attempts" / original_job.id / new_claim.lease_owner
                new_path.mkdir(parents=True, exist_ok=True)
                (new_path / "sentinel").write_text("keep")

            assert future.result(timeout=3) is True
        finally:
            if not future.done():
                try:
                    store.cancel("owner", original_job.id)
                except NotFound:
                    pass
                future.result(timeout=3)

    with pytest.raises(ChildProcessError):
        os.waitpid(pid, os.WNOHANG)

    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)

    assert not old_path.exists()

    if action == "cancel":
        job = store.get_job("owner", original_job.id)
        assert job.state == JobState.CANCELLED
        assert job.result_key is None
    elif action in ("delete_job", "delete_asset"):
        with pytest.raises(NotFound):
            store.get_job("owner", original_job.id)
    else:
        job = store.get_job("owner", original_job.id)
        assert job.state == JobState.RUNNING
        assert job.lease_owner != old_owner
        assert job.result_key is None
        new_path = artifact_root / "attempts" / original_job.id / job.lease_owner
        assert (new_path / "sentinel").read_text() == "keep"


@pytest.mark.parametrize("action", ["cancel", "delete_job", "reclaim"])
def test_supervisor_finish_rejects_stale_lease_before_publication(tmp_path: Path, action: str) -> None:
    store, original_job, artifact_root = queued_case(tmp_path)
    recorded: list[tuple[str, Path]] = []

    def make_command(claimed: AnalysisJob, attempt: Path) -> list[str]:
        assert claimed.lease_owner is not None
        recorded.append((claimed.lease_owner, attempt))
        return [
            sys.executable, "-c",
            "import json, sys; open('result.json', 'w').write(json.dumps({'job': sys.argv[1]})); sys.exit(0)",
            claimed.id,
        ]

    def validate_output(claimed: AnalysisJob, attempt: Path) -> str:
        data = json.loads((attempt / "result.json").read_text())
        assert data["job"] == claimed.id
        if action == "cancel":
            store.cancel("owner", original_job.id)
        elif action == "delete_job":
            store.delete_job("owner", original_job.id)
        else:
            store.claim("other", now=time.time() + 3, lease_s=60)
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
    old_owner, old_path = recorded[0]
    assert not old_path.exists()

    if action == "cancel":
        job = store.get_job("owner", original_job.id)
        assert job.state == JobState.CANCELLED
        assert job.result_key is None
    elif action == "delete_job":
        with pytest.raises(NotFound):
            store.get_job("owner", original_job.id)
    else:
        job = store.get_job("owner", original_job.id)
        assert job.state == JobState.RUNNING
        assert job.lease_owner != old_owner
        assert job.result_key is None
