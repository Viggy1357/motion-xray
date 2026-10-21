"""Trusted synchronous parent-only supervisor.

Callbacks are trusted; artifact_root is a private directory (not an OS sandbox).
validate_output verifies content and returns a basename.  The 1 MiB cap applies only
to the small manifest; frame files may be separate.  Returns ``True`` when a job
was claimed and processed (including failures and cancellation).
"""

from __future__ import annotations

import errno
import os
import shutil
import signal
import stat
import subprocess
import time
import uuid
from pathlib import Path
from typing import Callable, Optional, Sequence

from contracts.enums import JobStage, JobState
from contracts.jobs import AnalysisJob

from app.store import LeaseLost, NotFound, Store


def supervise_once(
    store: Store,
    artifact_root: Path,
    make_command: Callable[[AnalysisJob, Path], Sequence[str]],
    validate_output: Callable[[AnalysisJob, Path], str],
    *,
    worker: str = "pose",
    lease_s: float = 60,
    poll_s: float = 1,
    timeout_s: float = 120,
    terminate_grace_s: float = 1,
) -> bool:
    # Timing validation
    for name, val in [
        ("lease_s", lease_s),
        ("poll_s", poll_s),
        ("timeout_s", timeout_s),
        ("terminate_grace_s", terminate_grace_s),
    ]:
        if not isinstance(val, (int, float)) or isinstance(val, bool) or val <= 0 or val != val or val == float("inf"):
            raise ValueError(f"{name} must be finite positive number")
    if lease_s > 3600:
        raise ValueError("lease_s must be <= 3600")
    if poll_s >= lease_s / 3:
        raise ValueError("poll_s must be < lease_s/3")

    # artifact_root validation
    if not isinstance(artifact_root, Path):
        raise TypeError("artifact_root must be Path")
    if not artifact_root.is_absolute():
        raise ValueError("artifact_root must be absolute")
    if ".." in artifact_root.parts:
        raise ValueError("artifact_root contains traversal")
    for p in [artifact_root] + list(artifact_root.parents):
        if p.is_symlink():
            raise ValueError("artifact_root contains symlink in ancestors")

    job = store.claim(worker, lease_s=lease_s)
    if job is None:
        return False

    lease_token = job.lease_owner
    assert lease_token is not None
    job_id = job.id

    if not job_id or not isinstance(job_id, str):
        raise ValueError("invalid job id")
    if str(uuid.UUID(job_id)) != job_id:
        raise ValueError("job id must be canonical UUID")
    if not lease_token or not isinstance(lease_token, str) or len(lease_token) != 32 or not all(c in "0123456789abcdef" for c in lease_token):
        raise ValueError("lease token must be 32 lowercase hex chars")

    attempts_dir = artifact_root / "attempts"
    job_dir = attempts_dir / job_id
    attempt_dir = job_dir / lease_token

    owned = False
    stopped = False
    publication_started = False
    result_key: Optional[str] = None
    proc: Optional[subprocess.Popen[bytes]] = None
    start_time = time.monotonic()

    def _cleanup() -> None:
        if owned and attempt_dir.is_symlink():
            attempt_dir.unlink()
        elif owned and attempt_dir.exists():
            shutil.rmtree(attempt_dir)

    def _terminate() -> None:
        nonlocal stopped
        if stopped or proc is None:
            return
        stopped = True
        pgid = proc.pid  # start_new_session => pgid == pid
        try:
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except OSError as exc:
            if exc.errno != errno.ESRCH:
                raise
        try:
            proc.wait(timeout=terminate_grace_s)
        except subprocess.TimeoutExpired:
            pass
        # Always SIGKILL the process group; kills descendants even if leader exited
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError as exc:
            if exc.errno != errno.ESRCH:
                raise
        proc.wait()

    def _fail(code: str) -> None:
        try:
            store.fail(job_id, lease_token, error=code)
        except LeaseLost:
            pass

    try:
        # Create artifact_root if needed (after lexical check)
        if not artifact_root.exists():
            artifact_root.mkdir(parents=True, mode=0o700)
        if artifact_root.is_symlink() or not artifact_root.is_dir():
            raise ValueError("artifact_root is not a safe directory")
        artifact_root.chmod(0o700)
        # Create ancestors safely
        for d in [attempts_dir, job_dir]:
            if d.is_symlink():
                raise ValueError("ancestor path is not a safe directory")
            if d.exists():
                if d.is_symlink() or not d.is_dir():
                    raise ValueError("ancestor path is not a safe directory")
                os.chmod(d, 0o700)
            else:
                d.mkdir(mode=0o700)
        # Exclusive attempt dir
        try:
            attempt_dir.mkdir(mode=0o700)
        except FileExistsError:
            _fail("ATTEMPT_UNAVAILABLE")
            return True
        owned = True

        store.checkpoint(job_id, lease_token, JobStage.POSE)
        store.heartbeat(job_id, lease_token, lease_s=lease_s)

        try:
            cmd = make_command(job, attempt_dir)
        except (OSError, ValueError):
            _fail("CHILD_START_FAILED")
            return True
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=attempt_dir,
                start_new_session=True,
            )
        except (OSError, ValueError):
            _fail("CHILD_START_FAILED")
            return True

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed >= timeout_s:
                _terminate()
                _fail("CHILD_TIMEOUT")
                return True

            ret = proc.poll()
            if ret is not None:
                break

            try:
                store.heartbeat(job_id, lease_token, lease_s=lease_s)
            except LeaseLost:
                _terminate()
                return True

            sleep_remaining = min(poll_s, timeout_s - elapsed)
            if sleep_remaining > 0:
                time.sleep(sleep_remaining)

        # Post-exit heartbeat
        try:
            store.heartbeat(job_id, lease_token, lease_s=lease_s)
        except LeaseLost:
            _terminate()
            return True

        _terminate()

        if ret != 0:
            _fail("CHILD_FAILED")
            return True

        try:
            basename = validate_output(job, attempt_dir)
        except (ValueError, OSError):
            _fail("OUTPUT_INVALID")
            return True

        if not isinstance(basename, str) or not basename or "/" in basename or "\\" in basename or basename == "." or basename == ".." or basename.startswith("/") or "\x00" in basename:
            _fail("OUTPUT_INVALID")
            return True

        result_path = attempt_dir / basename
        try:
            st = os.lstat(result_path)
        except OSError:
            _fail("OUTPUT_INVALID")
            return True

        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
            _fail("OUTPUT_INVALID")
            return True
        if st.st_size == 0 or st.st_size > 1_048_576:
            _fail("OUTPUT_INVALID")
            return True

        os.chmod(result_path, 0o600)
        try:
            result_key = result_path.relative_to(artifact_root).as_posix()
        except ValueError:
            _fail("OUTPUT_INVALID")
            return True

        publication_started = True
        try:
            store.finish(job_id, lease_token, result_key=result_key)
        except LeaseLost:
            return True

        owned = False
        return True
    except LeaseLost:
        return True
    finally:
        try:
            _terminate()
        finally:
            if owned and publication_started:
                try:
                    latest = store.get_job(job.owner, job.id)
                except NotFound:
                    pass
                else:
                    if latest.state == JobState.SUCCEEDED and latest.result_key == result_key:
                        owned = False
            _cleanup()
