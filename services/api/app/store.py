"""Internal durable asset/job metadata; HTTP authentication and file cleanup are separate."""

from __future__ import annotations

import json
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional, Tuple

from contracts.enums import JobStage, JobState
from contracts.jobs import AnalysisJob
from contracts.media import VideoAsset


class NotFound(Exception):
    """Requested entity does not exist or is inaccessible."""


class Conflict(Exception):
    """Entity already exists or request conflicts with stored state."""


class LeaseLost(Exception):
    """Lease token mismatch, expired, or job no longer claimable."""


_MAX_STR = 256
_ERROR_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")


def _utc_from_ts(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _checked_deadline(ts: float, delta: float) -> float:
    try:
        # Validate that ts + delta is representable and fromtimestamp won't overflow
        result = ts + delta
        if result != result or result == float("inf") or result == float("-inf"):
            raise ValueError("deadline overflow")
        # Verify datetime conversion is possible (catches OSError on overflow)
        datetime.fromtimestamp(result, tz=timezone.utc)
        return result
    except (OSError, OverflowError) as exc:
        raise ValueError("deadline overflow") from exc


def _validate_str(name: str, value: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be non-empty string")
    if len(value) > _MAX_STR:
        raise ValueError(f"{name} exceeds {_MAX_STR} chars")


def _validate_safe_path(name: str, value: str) -> None:
    _validate_str(name, value)
    if "\x00" in value:
        raise ValueError(f"{name} contains invalid characters")
    if "\\" in value:
        raise ValueError(f"{name} contains invalid characters")
    if value.startswith("/"):
        raise ValueError(f"{name} contains unsafe path segment")
    if value.endswith("/"):
        raise ValueError(f"{name} contains unsafe path segment")
    for part in value.split("/"):
        if part in ("", ".", ".."):
            raise ValueError(f"{name} contains unsafe path segment")


class Store:
    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self._path), timeout=10.0, isolation_level=None)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.row_factory = sqlite3.Row
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                version = conn.execute("PRAGMA user_version").fetchone()[0]
                if version > 1:
                    raise RuntimeError(f"Database user_version {version} is newer than supported 1")
                if version == 0:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS assets (
                            id TEXT PRIMARY KEY,
                            owner TEXT NOT NULL,
                            payload TEXT NOT NULL,
                            expires_at REAL,
                            deleted INTEGER NOT NULL DEFAULT 0
                        )
                    """)
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS jobs (
                            id TEXT PRIMARY KEY,
                            owner TEXT NOT NULL,
                            asset_id TEXT NOT NULL,
                            exercise_id TEXT NOT NULL,
                            variant TEXT NOT NULL,
                            request_key TEXT NOT NULL,
                            input_hash TEXT NOT NULL,
                            version_hash TEXT NOT NULL,
                            state TEXT NOT NULL,
                            stage TEXT NOT NULL,
                            attempt INTEGER NOT NULL DEFAULT 0,
                            lease_token TEXT,
                            lease_until REAL,
                            cancel_requested INTEGER NOT NULL DEFAULT 0,
                            error TEXT,
                            result_key TEXT,
                            created_at REAL NOT NULL,
                            updated_at REAL NOT NULL,
                            expires_at REAL,
                            deleted INTEGER NOT NULL DEFAULT 0,
                            FOREIGN KEY (asset_id) REFERENCES assets(id),
                            UNIQUE(owner, request_key)
                        )
                    """)
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_claim ON jobs(state, lease_until, deleted, cancel_requested, expires_at)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_owner ON jobs(owner, id)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_assets_owner ON assets(owner, id)")
                    conn.execute("PRAGMA user_version=1")
                conn.execute("COMMIT")
            except Exception:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise

    def _now(self, now: float | None) -> float:
        if now is None:
            now = time.time()
        if not isinstance(now, (int, float)) or isinstance(now, bool):
            raise TypeError("now must be a finite float")
        if now < 0 or now != now or now == float("inf") or now == float("-inf"):
            raise ValueError("now must be finite non-negative float")
        return _checked_deadline(float(now), 0)

    def _validate_owner(self, owner: str) -> None:
        _validate_str("owner", owner)

    def _validate_id(self, id: str) -> None:
        _validate_str("id", id)

    def _validate_worker(self, worker: str) -> None:
        _validate_str("worker", worker)

    def _validate_lease_s(self, lease_s: float) -> None:
        if not isinstance(lease_s, (int, float)) or isinstance(lease_s, bool):
            raise TypeError("lease_s must be finite float")
        if lease_s <= 0 or lease_s > 3600 or lease_s != lease_s or lease_s == float("inf"):
            raise ValueError("lease_s must be in (0, 3600]")

    def _validate_ttl(self, ttl_s: float) -> None:
        if not isinstance(ttl_s, (int, float)) or isinstance(ttl_s, bool):
            raise TypeError("ttl_s must be finite float")
        if ttl_s <= 0 or ttl_s != ttl_s or ttl_s == float("inf"):
            raise ValueError("ttl_s must be finite positive float")

    def _row_to_asset(self, row: sqlite3.Row) -> VideoAsset:
        payload = json.loads(row["payload"])
        return VideoAsset.model_validate(payload)

    def _row_to_job(self, row: sqlite3.Row) -> AnalysisJob:
        return AnalysisJob(
            id=row["id"],
            owner=row["owner"],
            state=JobState(row["state"]),
            stage=JobStage(row["stage"]),
            attempt=row["attempt"],
            lease_owner=row["lease_token"],
            lease_until=_utc_from_ts(row["lease_until"]) if row["lease_until"] else None,
            cancel_requested=bool(row["cancel_requested"]),
            input_hash=row["input_hash"],
            version_hash=row["version_hash"],
            created_at=_utc_from_ts(row["created_at"]),
            updated_at=_utc_from_ts(row["updated_at"]),
            error=row["error"],
            result_key=row["result_key"],
        )

    def register_asset(self, video: VideoAsset, *, now: float | None = None) -> VideoAsset:
        ts = self._now(now)
        self._validate_owner(video.owner_session_id)
        self._validate_id(video.id)
        if video.expires_at is None:
            raise ValueError("expires_at required")
        expires_ts = video.expires_at.timestamp()
        if expires_ts <= ts:
            raise ValueError("expires_at must be in the future")
        if video.bytes <= 0:
            raise ValueError("bytes must be positive")
        if not (0 < video.duration_s <= 30):
            raise ValueError("duration_s must be in (0, 30]")
        if video.width <= 0 or video.height <= 0:
            raise ValueError("dimensions must be positive")
        if not re.fullmatch(r"[0-9a-f]{64}", video.sha256):
            raise ValueError("sha256 must be 64 lowercase hex chars")
        _validate_safe_path("storage_key", video.storage_key)

        payload = video.model_dump_json()
        with self._conn() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT INTO assets (id, owner, payload, expires_at, deleted) VALUES (?, ?, ?, ?, 0)",
                    (video.id, video.owner_session_id, payload, expires_ts),
                )
                conn.execute("COMMIT")
            except sqlite3.IntegrityError:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise Conflict("asset already exists")
            except Exception:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise
        return video

    def get_asset(self, owner: str, asset_id: str, *, now: float | None = None) -> VideoAsset:
        ts = self._now(now)
        self._validate_owner(owner)
        self._validate_id(asset_id)
        with self._conn() as conn:
            row = conn.execute(
                "SELECT payload FROM assets WHERE id=? AND owner=? AND deleted=0 AND (expires_at IS NULL OR expires_at > ?)",
                (asset_id, owner, ts),
            ).fetchone()
            if row is None:
                raise NotFound("asset not found")
            return self._row_to_asset(row)

    def enqueue(
        self,
        owner: str,
        asset_id: str,
        exercise_id: str,
        variant: str,
        request_key: str,
        version_hash: str,
        *,
        now: float | None = None,
        ttl_s: float = 604800,
    ) -> AnalysisJob:
        ts = self._now(now)
        self._validate_owner(owner)
        self._validate_id(asset_id)
        _validate_str("exercise_id", exercise_id)
        _validate_str("variant", variant)
        _validate_str("request_key", request_key)
        _validate_str("version_hash", version_hash)
        self._validate_ttl(ttl_s)
        expires_at = _checked_deadline(ts, ttl_s)

        with self._conn() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                asset_row = conn.execute(
                    "SELECT payload FROM assets WHERE id=? AND owner=? AND deleted=0 AND (expires_at IS NULL OR expires_at > ?)",
                    (asset_id, owner, ts),
                ).fetchone()
                if asset_row is None:
                    raise NotFound("asset not found")
                payload = json.loads(asset_row["payload"])
                video = VideoAsset.model_validate(payload)
                input_hash = video.sha256

                existing = conn.execute(
                    "SELECT * FROM jobs WHERE owner=? AND request_key=?",
                    (owner, request_key),
                ).fetchone()
                if existing is not None:
                    if existing["deleted"] or (existing["expires_at"] is not None and existing["expires_at"] <= ts):
                        raise Conflict("request key tombstoned")
                    if (existing["asset_id"] != asset_id or existing["exercise_id"] != exercise_id or
                        existing["variant"] != variant or existing["version_hash"] != version_hash):
                        raise Conflict("conflicting payload for request key")
                    job = self._row_to_job(existing)
                    conn.execute("COMMIT")
                    return job

                job_id = str(uuid.uuid4())
                conn.execute(
                    """INSERT INTO jobs (id, owner, asset_id, exercise_id, variant, request_key,
                        input_hash, version_hash, state, stage, attempt, cancel_requested,
                        created_at, updated_at, expires_at, deleted)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?, 0)""",
                    (job_id, owner, asset_id, exercise_id, variant, request_key, input_hash, version_hash,
                     JobState.QUEUED.value, JobStage.VALIDATE.value, ts, ts, expires_at),
                )
                row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
                job = self._row_to_job(row)
                conn.execute("COMMIT")
                return job
            except Exception:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise

    def get_job(self, owner: str, id: str, *, now: float | None = None) -> AnalysisJob:
        ts = self._now(now)
        self._validate_owner(owner)
        self._validate_id(id)
        with self._conn() as conn:
            # Preserve UNEXPIRED job status even when raw asset expired:
            # job expiry is independent; only filter job by its own expiry
            row = conn.execute(
                "SELECT * FROM jobs WHERE id=? AND owner=? AND deleted=0 AND (expires_at IS NULL OR expires_at > ?)",
                (id, owner, ts),
            ).fetchone()
            if row is None:
                raise NotFound("job not found")
            return self._row_to_job(row)

    def get_input(self, owner: str, job_id: str, *, now: float | None = None) -> Tuple[VideoAsset, str, str]:
        ts = self._now(now)
        self._validate_owner(owner)
        self._validate_id(job_id)
        with self._conn() as conn:
            job_row = conn.execute(
                "SELECT * FROM jobs WHERE id=? AND owner=? AND deleted=0 AND (expires_at IS NULL OR expires_at > ?)",
                (job_id, owner, ts),
            ).fetchone()
            if job_row is None:
                raise NotFound("job not found")
            asset_row = conn.execute(
                "SELECT payload FROM assets WHERE id=? AND owner=? AND deleted=0 AND (expires_at IS NULL OR expires_at > ?)",
                (job_row["asset_id"], owner, ts),
            ).fetchone()
            if asset_row is None:
                raise NotFound("asset not found")
            video = self._row_to_asset(asset_row)
            return (video, job_row["exercise_id"], job_row["variant"])

    def claim(self, worker: str, *, now: float | None = None, lease_s: float = 60) -> Optional[AnalysisJob]:
        ts = self._now(now)
        self._validate_worker(worker)
        self._validate_lease_s(lease_s)
        lease_token = uuid.uuid4().hex
        lease_until = _checked_deadline(ts, lease_s)

        with self._conn() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute("""
                    SELECT j.* FROM jobs j
                    JOIN assets a ON j.asset_id = a.id
                    WHERE j.deleted=0 AND j.cancel_requested=0
                    AND (j.expires_at IS NULL OR j.expires_at > ?)
                    AND a.deleted=0 AND (a.expires_at IS NULL OR a.expires_at > ?)
                    AND j.state IN (?, ?)
                    AND (j.lease_until IS NULL OR j.lease_until <= ?)
                    ORDER BY j.created_at ASC
                    LIMIT 1
                """, (ts, ts, JobState.QUEUED.value, JobState.RUNNING.value, ts)).fetchone()

                if row is None:
                    conn.execute("COMMIT")
                    return None

                new_attempt = row["attempt"] + 1
                new_state = JobState.RUNNING.value
                stage = row["stage"] if row["stage"] else JobStage.VALIDATE.value

                conn.execute(
                    """UPDATE jobs SET state=?, stage=?, attempt=?, lease_token=?,
                        lease_until=?, updated_at=? WHERE id=?""",
                    (new_state, stage, new_attempt, lease_token, lease_until, ts, row["id"]),
                )
                updated = conn.execute("SELECT * FROM jobs WHERE id=?", (row["id"],)).fetchone()
                job = self._row_to_job(updated)
                conn.execute("COMMIT")
                return job
            except Exception:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise

    def heartbeat(self, job_id: str, lease_token: str, *, now: float | None = None, lease_s: float = 60) -> AnalysisJob:
        ts = self._now(now)
        self._validate_id(job_id)
        _validate_str("lease_token", lease_token)
        self._validate_lease_s(lease_s)
        lease_until = _checked_deadline(ts, lease_s)
        return self._fenced_update(job_id, lease_token, ts, lease_until=lease_until)

    def checkpoint(self, job_id: str, lease_token: str, stage: JobStage, *, now: float | None = None) -> AnalysisJob:
        ts = self._now(now)
        self._validate_id(job_id)
        _validate_str("lease_token", lease_token)
        return self._fenced_update(job_id, lease_token, ts, stage=stage.value)

    def finish(self, job_id: str, lease_token: str, *, result_key: str, now: float | None = None) -> AnalysisJob:
        ts = self._now(now)
        self._validate_id(job_id)
        _validate_str("lease_token", lease_token)
        _validate_safe_path("result_key", result_key)
        return self._fenced_update(
            job_id, lease_token, ts,
            state=JobState.SUCCEEDED.value,
            result_key=result_key,
            terminal=True,
        )

    def fail(self, job_id: str, lease_token: str, *, error: str, now: float | None = None) -> AnalysisJob:
        ts = self._now(now)
        self._validate_id(job_id)
        _validate_str("lease_token", lease_token)
        if not _ERROR_CODE_RE.fullmatch(error):
            raise ValueError("error must match [A-Z][A-Z0-9_]{0,63}")
        return self._fenced_update(
            job_id, lease_token, ts,
            state=JobState.FAILED.value,
            error=error,
            terminal=True,
        )

    def _fenced_update(
        self,
        job_id: str,
        expected_token: str,
        ts: float,
        *,
        state: Optional[str] = None,
        stage: Optional[str] = None,
        lease_until: Optional[float] = None,
        result_key: Optional[str] = None,
        error: Optional[str] = None,
        terminal: bool = False,
    ) -> AnalysisJob:
        with self._conn() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT * FROM jobs WHERE id=? AND state=? AND lease_token=? AND lease_until > ? AND deleted=0 AND cancel_requested=0",
                    (job_id, JobState.RUNNING.value, expected_token, ts),
                ).fetchone()
                if row is None:
                    raise LeaseLost("lease invalid or expired")

                asset_row = conn.execute(
                    "SELECT 1 FROM assets WHERE id=? AND deleted=0 AND (expires_at IS NULL OR expires_at > ?)",
                    (row["asset_id"], ts),
                ).fetchone()
                if asset_row is None:
                    raise LeaseLost("asset expired or deleted")

                if (row["expires_at"] is not None and row["expires_at"] <= ts):
                    raise LeaseLost("job expired")

                updates = []
                params: list = []
                if state is not None:
                    updates.append("state=?")
                    params.append(state)
                if stage is not None:
                    updates.append("stage=?")
                    params.append(stage)
                if lease_until is not None:
                    updates.append("lease_until=?")
                    params.append(lease_until)
                if terminal:
                    updates.append("lease_token=NULL")
                    updates.append("lease_until=NULL")
                if result_key is not None:
                    updates.append("result_key=?")
                    params.append(result_key)
                if error is not None:
                    updates.append("error=?")
                    params.append(error)
                updates.append("updated_at=?")
                params.append(ts)
                params.append(job_id)

                conn.execute(f"UPDATE jobs SET {', '.join(updates)} WHERE id=?", params)
                updated = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
                job = self._row_to_job(updated)
                conn.execute("COMMIT")
                return job
            except Exception:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise

    def cancel(self, owner: str, id: str, *, now: float | None = None) -> AnalysisJob:
        ts = self._now(now)
        self._validate_owner(owner)
        self._validate_id(id)
        with self._conn() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT * FROM jobs WHERE id=? AND owner=? AND deleted=0 AND (expires_at IS NULL OR expires_at > ?)",
                    (id, owner, ts),
                ).fetchone()
                if row is None:
                    raise NotFound("job not found")

                state = JobState(row["state"])
                if state in (JobState.SUCCEEDED, JobState.FAILED):
                    job = self._row_to_job(row)
                    conn.execute("COMMIT")
                    return job

                conn.execute(
                    "UPDATE jobs SET state=?, cancel_requested=1, lease_token=NULL, lease_until=NULL, updated_at=? WHERE id=?",
                    (JobState.CANCELLED.value, ts, id),
                )
                updated = conn.execute("SELECT * FROM jobs WHERE id=?", (id,)).fetchone()
                job = self._row_to_job(updated)
                conn.execute("COMMIT")
                return job
            except Exception:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise

    def delete_job(self, owner: str, id: str, *, now: float | None = None) -> None:
        ts = self._now(now)
        self._validate_owner(owner)
        self._validate_id(id)
        with self._conn() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute("SELECT owner FROM jobs WHERE id=?", (id,)).fetchone()
                if row is None:
                    raise NotFound("job not found")
                if row["owner"] != owner:
                    raise NotFound("job not found")
                conn.execute(
                    "UPDATE jobs SET deleted=1, cancel_requested=1, state=?, result_key=NULL, lease_token=NULL, lease_until=NULL, updated_at=? WHERE id=?",
                    (JobState.CANCELLED.value, ts, id),
                )
                conn.execute("COMMIT")
            except Exception:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise

    def delete_asset(self, owner: str, id: str, *, now: float | None = None) -> None:
        ts = self._now(now)
        self._validate_owner(owner)
        self._validate_id(id)
        with self._conn() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute("SELECT owner FROM assets WHERE id=?", (id,)).fetchone()
                if row is None:
                    raise NotFound("asset not found")
                if row["owner"] != owner:
                    raise NotFound("asset not found")
                conn.execute(
                    "UPDATE assets SET deleted=1 WHERE id=?",
                    (id,),
                )
                conn.execute(
                    """UPDATE jobs SET deleted=1, cancel_requested=1, state=?,
                        result_key=NULL, lease_token=NULL, lease_until=NULL, updated_at=?
                        WHERE asset_id=?""",
                    (JobState.CANCELLED.value, ts, id),
                )
                conn.execute("COMMIT")
            except Exception:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise
