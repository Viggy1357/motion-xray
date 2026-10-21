from __future__ import annotations

import json
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


def test_finish_after_commit_interrupt_retains_output(tmp_path: Path) -> None:
    store, original_job, artifact_root = queued_case(tmp_path)
    orig_finish = store.finish

    def fault_finish(*args, **kwargs):
        orig_finish(*args, **kwargs)
        raise KeyboardInterrupt("after commit")

    store.finish = fault_finish  # type: ignore[method-assign]

    def make_command(claimed: AnalysisJob, attempt: Path) -> list[str]:
        return [
            sys.executable, "-c",
            "import json; open('result.json', 'w').write(json.dumps('published'))",
        ]

    def validate_output(claimed: AnalysisJob, attempt: Path) -> str:
        data = json.loads((attempt / "result.json").read_text())
        assert data == "published"
        return "result.json"

    with pytest.raises(KeyboardInterrupt):
        supervise_once(
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

    final_job = store.get_job("owner", original_job.id)
    assert final_job.state == JobState.SUCCEEDED
    assert final_job.result_key is not None
    result_key = final_job.result_key

    result_path = artifact_root / result_key
    assert result_path.exists()
    assert json.loads(result_path.read_text()) == "published"
