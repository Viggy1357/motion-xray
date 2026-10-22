"""Conservative manual retention cleanup.

One-shot, bounded, no daemon. Only touches well-known committed artifacts:
- raw video files whose asset is expired/deleted AND no non-terminal job ever
  referenced the asset (cancelled/running/queued, even deleted, defers),
- payload files of unexpired completed jobs whose raw asset is expired/deleted
  (manifest/report preserved; reports keep their own TTL),
- committed attempt directories of report-TTL-expired completed jobs after
  manifest validation (job marked deleted; state/result_key preserved for
  retry; already-deleted completed jobs with a result_key are retried).

Partial-rmtree recovery uses a small private cleanup receipt stored next to
the attempt dir (``.retention-<token>.json`` inside the job folder, which
must live on a trusted private filesystem that is not user-writable). The
receipt is written with O_CREAT|O_EXCL|O_NOFOLLOW (mode 0600, fsync of file
and parent directory) AFTER manifest validation and BEFORE any destructive
removal; it binds job id, input_hash, version_hash and result_key and
carries no credentials. On retry, an expired completed job whose manifest is
gone but whose attempt dir still exists is only removed when a strictly
matching receipt proves an earlier validated manifest; invalid, tampered or
symlinked receipts defer. Receipts are removed once the attempt is gone and
the job is marked deleted. An attempt dir that is entirely absent marks the
expired job deleted idempotently (nothing left to delete).

Never claims full cleanup; unknown paths, invalid manifests, and ambiguous
jobs are deferred. Per-category bounds are each <= max_items (not a strict
total). Individual file OSErrors increment ``errors`` and processing
continues; database corruption is never masked.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import time
from pathlib import Path

from contracts.pose_job import PoseJobArtifacts

from .store import Store

_RESULT_KEY_RE = re.compile(
    r"^attempts/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/([0-9a-f]{32})/manifest\.json$"
)
_PAYLOADS = ("proxy/proxy.mp4", "proxy/timestamp_map.json")
_MANIFEST_MAX = 1 * 1024 * 1024
_RECEIPT_MAX = 4 * 1024
_RECEIPT_VERSION = "cleanup-receipt-v1"
_POSE_KEY_RE = re.compile(r"^pose/[0-9a-f]{64}\.jsonl$")
_TERMINAL = ("succeeded", "failed")
_OPEN_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _safe_rel(key) -> bool:
    """Reject absolute/traversal/NUL/backslash/empty-segment relative keys."""
    if not isinstance(key, str) or not key or "\x00" in key or "\\" in key:
        return False
    if key.startswith("/") or (len(key) > 1 and key[1] == ":"):
        return False
    return all(part not in ("", ".", "..") for part in key.split("/"))


def _open_root(path: Path) -> int:
    fd = os.open(path.anchor, _OPEN_FLAGS)
    try:
        for part in path.parts[1:]:
            nfd = os.open(part, _OPEN_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = nfd
        return fd
    except Exception:
        os.close(fd)
        raise


def _open_dir(root_fd: int, rel: str) -> int:
    fd = os.dup(root_fd)
    try:
        for part in rel.split("/"):
            nfd = os.open(part, _OPEN_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = nfd
        return fd
    except Exception:
        os.close(fd)
        raise


def _dir_exists(root_fd: int, rel: str) -> bool:
    try:
        fd = _open_dir(root_fd, rel)
    except FileNotFoundError:
        return False
    os.close(fd)
    return True


def _unlink_regular(parent_fd: int, name: str) -> bool:
    st = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
        return False
    os.unlink(name, dir_fd=parent_fd)
    return True


def _unlink_rel(root_fd: int, rel: str) -> bool:
    if not _safe_rel(rel):
        raise ValueError(f"unsafe relative key: {rel!r}")
    parent, _, name = rel.rpartition("/")
    fd = _open_dir(root_fd, parent) if parent else os.dup(root_fd)
    try:
        return _unlink_regular(fd, name)
    finally:
        os.close(fd)


def _rmtree_dir(root_fd: int, rel: str) -> bool:
    """Remove exactly the committed attempt dir; Python 3.12 dir_fd rmtree
    is symlink-attack safe. Never called on a job folder."""
    if not _safe_rel(rel):
        raise ValueError(f"unsafe relative key: {rel!r}")
    parent, _, name = rel.rpartition("/")
    fd = _open_dir(root_fd, parent) if parent else os.dup(root_fd)
    try:
        st = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if not stat.S_ISDIR(st.st_mode):
            return False
        shutil.rmtree(name, dir_fd=fd)
        return True
    finally:
        os.close(fd)


def _validate_manifest(art_fd: int, result_key: str, job) -> PoseJobArtifacts | None:
    """Return validated artifacts, or None for invalid/mismatched manifests.

    Raises FileNotFoundError when the manifest is absent and OSError for
    other I/O failures; callers decide defer vs skip.
    """
    m = _RESULT_KEY_RE.fullmatch(result_key)
    if m is None or m.group(1) != job["id"]:
        return None
    attempt_rel = result_key.rsplit("/", 1)[0]
    fd = _open_dir(art_fd, attempt_rel)
    try:
        mfd = os.open("manifest.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(mfd, "rb") as f:
            st = os.fstat(mfd)
            if not stat.S_ISREG(st.st_mode) or st.st_size > _MANIFEST_MAX:
                return None
            data = f.read(_MANIFEST_MAX + 1)
        try:
            art = PoseJobArtifacts.model_validate(json.loads(data))
        except ValueError:
            return None
        prov = art.report.provenance
        if (
            art.report.analysis_id != job["id"]
            or prov.get("input_sha256") != job["input_hash"]
            or prov.get("version_hash") != job["version_hash"]
            or art.proxy.source_sha256 != job["input_hash"]
            or _POSE_KEY_RE.fullmatch(art.pose.frames_artifact_key) is None
        ):
            return None
        return art
    finally:
        os.close(fd)


def _receipt_parts(result_key: str) -> tuple[str, str] | None:
    """(job-dir rel, receipt name) strictly derived from the result key."""
    m = _RESULT_KEY_RE.fullmatch(result_key)
    if m is None:
        return None
    return f"attempts/{m.group(1)}", f".retention-{m.group(2)}.json"


def _receipt_payload(job) -> dict:
    return {
        "format_version": _RECEIPT_VERSION,
        "job_id": job["id"],
        "input_hash": job["input_hash"],
        "version_hash": job["version_hash"],
        "result_key": job["result_key"],
    }


def _receipt_valid(art_fd: int, job) -> bool | None:
    """True = valid receipt, False = absent, None = invalid/tampered."""
    parts = _receipt_parts(job["result_key"])
    if parts is None:
        return None
    parent, name = parts
    try:
        fd = _open_dir(art_fd, parent)
    except OSError:
        return False
    try:
        try:
            mfd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        except FileNotFoundError:
            return False
        except OSError:
            return None
        with os.fdopen(mfd, "rb") as f:
            st = os.fstat(mfd)
            if not stat.S_ISREG(st.st_mode) or st.st_size > _RECEIPT_MAX:
                return None
            data = f.read(_RECEIPT_MAX + 1)
    finally:
        os.close(fd)
    try:
        got = json.loads(data)
    except ValueError:
        return None
    return True if got == _receipt_payload(job) else None


def _write_receipt(art_fd: int, job) -> None:
    """Exclusive, durable receipt write; raises OSError/FileExistsError."""
    parts = _receipt_parts(job["result_key"])
    if parts is None:
        raise ValueError("invalid committed attempt reference")
    parent, name = parts
    fd = _open_dir(art_fd, parent)
    try:
        mfd = os.open(
            name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=fd,
        )
        with os.fdopen(mfd, "wb") as f:
            f.write(json.dumps(_receipt_payload(job)).encode())
            f.flush()
            os.fsync(f.fileno())
        os.fsync(fd)
    finally:
        os.close(fd)


def _remove_receipt(art_fd: int, job) -> None:
    parts = _receipt_parts(job["result_key"])
    if parts is None:
        return
    parent, name = parts
    try:
        fd = _open_dir(art_fd, parent)
    except OSError:
        return
    try:
        try:
            st = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISREG(st.st_mode):
                os.unlink(name, dir_fd=fd)
                os.fsync(fd)
        except FileNotFoundError:
            pass
        except OSError:
            pass
    finally:
        os.close(fd)


def cleanup_once(
    store: Store,
    video_root: Path,
    artifact_root: Path,
    *,
    now: float,
    max_items: int = 100,
) -> dict[str, int]:
    if isinstance(now, bool) or not isinstance(now, (int, float)) or not (now == now) or now in (float("inf"), float("-inf")) or now < 0:
        raise ValueError("now must be finite non-negative float")
    if isinstance(max_items, bool) or not isinstance(max_items, int) or not (1 <= max_items <= 10000):
        raise ValueError("max_items must be int in [1, 10000]")
    for name, p in (("video_root", video_root), ("artifact_root", artifact_root)):
        if not p.is_absolute() or ".." in p.parts:
            raise ValueError(f"{name} must be absolute without '..'")
    vs, as_ = os.path.normpath(str(video_root)), os.path.normpath(str(artifact_root))
    if os.path.commonpath([vs, as_]) in (vs, as_):
        raise ValueError("roots must not overlap")

    counts = {"raw_removed": 0, "payloads_removed": 0, "attempts_removed": 0,
              "reports_deleted": 0, "deferred": 0, "errors": 0}
    vfd = _open_root(video_root)
    try:
        afd = _open_root(artifact_root)
    except Exception:
        os.close(vfd)
        raise
    try:
        with store._conn() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                # 1. Raw assets: expired or deleted, no non-terminal job EVER.
                rows = conn.execute(
                    "SELECT id, payload FROM assets WHERE deleted=1 OR (expires_at IS NOT NULL AND expires_at<=?) ORDER BY id LIMIT ?",
                    (now, max_items),
                ).fetchall()
                for row in rows:
                    busy = conn.execute(
                        "SELECT 1 FROM jobs WHERE asset_id=? AND state NOT IN (?,?) LIMIT 1",
                        (row["id"], *_TERMINAL),
                    ).fetchone()
                    if busy is not None:
                        counts["deferred"] += 1
                        continue
                    try:
                        key = json.loads(row["payload"])["storage_key"]
                        if not _safe_rel(key):
                            counts["deferred"] += 1
                            continue
                        if _unlink_rel(vfd, key):
                            counts["raw_removed"] += 1
                    except FileNotFoundError:
                        pass
                    except (OSError, ValueError, KeyError, TypeError):
                        counts["errors"] += 1

                # 2. Terminal jobs with committed attempt artifacts, including
                #    already-deleted completed jobs (retry of attempt removal).
                jobs = conn.execute(
                    "SELECT j.id, j.input_hash, j.version_hash, j.result_key, j.expires_at, j.deleted, "
                    "a.deleted AS a_deleted, a.expires_at AS a_expires FROM jobs j "
                    "JOIN assets a ON a.id=j.asset_id "
                    "WHERE j.state IN (?,?) AND j.result_key IS NOT NULL ORDER BY j.id LIMIT ?",
                    (*_TERMINAL, max_items),
                ).fetchall()
                for job in jobs:
                    expired = job["expires_at"] is not None and job["expires_at"] <= now
                    attempt_rel = job["result_key"].rsplit("/", 1)[0]
                    try:
                        art = _validate_manifest(afd, job["result_key"], job)
                        manifest_gone = False
                    except FileNotFoundError:
                        art = None
                        manifest_gone = True
                    except OSError:
                        counts["errors"] += 1
                        continue
                    if manifest_gone:
                        if not expired:
                            counts["deferred"] += 1
                            continue
                        try:
                            exists = _dir_exists(afd, attempt_rel)
                        except OSError:
                            counts["errors"] += 1
                            continue
                        if not exists:
                            # Attempt fully absent: nothing to delete; mark
                            # the expired job deleted idempotently.
                            if not job["deleted"]:
                                conn.execute("UPDATE jobs SET deleted=1 WHERE id=?", (job["id"],))
                                counts["reports_deleted"] += 1
                            _remove_receipt(afd, job)
                            continue
                        # Residual attempt without manifest: only a strictly
                        # valid private receipt proves earlier validation.
                        if _receipt_valid(afd, job) is not True:
                            counts["deferred"] += 1
                            continue
                    else:
                        if art is None:
                            counts["deferred"] += 1
                            continue
                        if expired:
                            # Persist proof of manifest validation BEFORE any
                            # destructive removal; no receipt -> no delete.
                            rv = _receipt_valid(afd, job)
                            if rv is None:
                                counts["deferred"] += 1
                                continue
                            if rv is False:
                                try:
                                    _write_receipt(afd, job)
                                except FileExistsError:
                                    if _receipt_valid(afd, job) is not True:
                                        counts["deferred"] += 1
                                        continue
                                except OSError:
                                    counts["errors"] += 1
                                    continue
                    if expired:
                        if _receipt_valid(afd, job) is not True:
                            counts["deferred"] += 1
                            continue
                        try:
                            if _rmtree_dir(afd, attempt_rel):
                                counts["attempts_removed"] += 1
                            if not job["deleted"]:
                                conn.execute("UPDATE jobs SET deleted=1 WHERE id=?", (job["id"],))
                            counts["reports_deleted"] += 1
                            _remove_receipt(afd, job)
                        except OSError:
                            counts["errors"] += 1
                    elif not job["deleted"]:
                        assert art is not None  # unexpired reports require a validated manifest
                        # Payload strip only once the raw asset is gone/stale.
                        raw_gone = job["a_deleted"] or (job["a_expires"] is not None and job["a_expires"] <= now)
                        if not raw_gone:
                            continue
                        for rel in list(_PAYLOADS) + [art.pose.frames_artifact_key]:
                            try:
                                if _unlink_rel(afd, f"{attempt_rel}/{rel}"):
                                    counts["payloads_removed"] += 1
                            except FileNotFoundError:
                                pass
                            except (OSError, ValueError):
                                counts["errors"] += 1

                # 3. Explicitly deleted jobs: result_key cleared, state cancelled.
                n = conn.execute(
                    "SELECT COUNT(*) FROM jobs WHERE deleted=1 AND state='cancelled' AND result_key IS NULL"
                ).fetchone()[0]
                counts["deferred"] += n
                conn.execute("COMMIT")
            except Exception:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise
    finally:
        os.close(vfd)
        os.close(afd)
    return counts


def main() -> None:
    p = argparse.ArgumentParser(description="One-shot conservative retention cleanup")
    p.add_argument("--database", required=True, type=Path)
    p.add_argument("--video-root", required=True, type=Path)
    p.add_argument("--artifact-root", required=True, type=Path)
    p.add_argument("--max-items", type=int, default=100)
    p.add_argument("--now", type=float, default=None)
    a = p.parse_args()
    counts = cleanup_once(
        Store(a.database), a.video_root, a.artifact_root,
        now=a.now if a.now is not None else time.time(), max_items=a.max_items,
    )
    print(json.dumps(counts, sort_keys=True))


if __name__ == "__main__":
    main()
