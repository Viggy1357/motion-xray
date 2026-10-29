from __future__ import annotations

import hashlib
import importlib.resources
import json
import math
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, TypeGuard

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from app.analyses import (
    _auth,
    _canonical_uuid,
    _error_response,
    _no_store,
    _store,
    _translate_http_exception,
)
from app.artifact_streams import _recheck
from app.movement_reports import get_movement_report
from app.store import NotFound
from contracts.analysis import CoachingResult
from contracts.enums import CoachingStatus

router = APIRouter(prefix="/v1")

# Versioned quota constants (per UTC day); defaults are fixed and cannot be
# raised via environment.
QUOTA_VERSION = "coaching-quota-v1"
GLOBAL_DAILY_LIMIT = 20
OWNER_DAILY_LIMIT = 4  # one request for each supported exercise
GLOBAL_LIFETIME_LIMIT = 100
RUNTIME_MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
CACHE_TTL_S = 24 * 3600.0
MAX_OBSERVATIONS = 8
MAX_OBS_TEXT = 350
PROMPT_VERSION = "v1"
MIN_COVERAGE = 0.8

_CLAIMS_REL = "packages/providers/providers/llm/coaching-claims-v1.json"
_CLAIMS_VERSION_DEFAULT = "coaching-claims-v1"


def _claims_path() -> Optional[Path]:
    for base in Path(__file__).resolve().parents:
        candidate = base / _CLAIMS_REL
        if candidate.is_file():
            return candidate
    return None


def _load_claims_resource() -> Optional[tuple[str, list[dict[str, Any]]]]:
    """Load the bundled claims JSON from the installed ``providers.llm`` package.

    Returns ``None`` when the resource is missing or unreadable so the caller
    can fall back to a safe empty result without inventing cues.
    """
    try:
        traversable = importlib.resources.files("providers.llm")
    except (ModuleNotFoundError, ImportError):
        return None
    try:
        resource = traversable.joinpath("coaching-claims-v1.json")
    except (AttributeError, TypeError):
        return None
    try:
        if not resource.is_file():
            return None
    except (OSError, ValueError):
        return None
    try:
        raw = resource.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    claims = data.get("claims") or []
    if not isinstance(claims, list):
        claims = []
    version = str(data.get("version") or _CLAIMS_VERSION_DEFAULT)
    return version, claims


def _load_claims(exercise: str) -> tuple[str, list[dict[str, Any]]]:
    """Return ``(version, claims_for_exercise)``.

    Resolution order:
      1. Source-tree path (developer checkout / editable install).
      2. Installed package resource (``providers.llm`` wheel data).

    Both sources fail closed: missing or malformed JSON yields the default
    version and an empty claim list, never an invented cue.
    """
    path = _claims_path()
    if path is not None:
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            return _CLAIMS_VERSION_DEFAULT, []
        if not isinstance(data, dict):
            return _CLAIMS_VERSION_DEFAULT, []
        if isinstance(data, dict):
            rows = data.get("claims") or []
            if not isinstance(rows, list):
                return _CLAIMS_VERSION_DEFAULT, []
            claims = [c for c in rows if isinstance(c, dict) and c.get("exercise") == exercise]
            return str(data.get("version") or _CLAIMS_VERSION_DEFAULT), claims

    bundled = _load_claims_resource()
    if bundled is None:
        return _CLAIMS_VERSION_DEFAULT, []
    version, claims = bundled
    filtered = [c for c in claims if isinstance(c, dict) and c.get("exercise") == exercise]
    return version, filtered


def _default_provider_factory():
    if os.getenv("NEBIUS_MODEL_ID") != RUNTIME_MODEL:
        return None
    try:
        from providers.llm.nebius_provider import NebiusLLMProvider
    except Exception:
        return None
    return NebiusLLMProvider(max_calls=1)


_provider_factory = _default_provider_factory


def _ensure_table(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS grounded_coaching ("
        "owner TEXT NOT NULL, job_id TEXT NOT NULL, key TEXT NOT NULL, "
        "result_json TEXT, state TEXT NOT NULL, reserved_at REAL NOT NULL, "
        "expires_at REAL NOT NULL, usage_json TEXT, "
        "UNIQUE(owner, job_id, key))"
    )


def _human(metric_id: str) -> str:
    labels = {
        "torso_axis_angle/projected_2d/excursion": "torso movement range (camera plane)",
        "elbow_angle/estimated_3d/excursion": "elbow range of motion (estimated 3D)",
        "elbow_angle/estimated_3d/end": "return elbow angle (estimated 3D)",
        "upper_arm_torso_angle/estimated_3d/bottom": "upper-arm to torso angle at the turn (estimated 3D)",
        "knee_angle/estimated_3d/bottom": "knee angle at the turn (estimated 3D)",
        "knee_angle/estimated_3d/excursion": "knee range of motion (estimated 3D)",
        "hip_angle/estimated_3d/bottom": "hip angle at the turn (estimated 3D)",
    }
    return labels.get(metric_id, metric_id.replace("_", " ").replace("/", " · "))


def _finite(v: Any) -> TypeGuard[float]:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _build_evidence(report: Any):
    """Bounded CoachingEvidence from completed reps / observed degree metrics.

    Joins ``metric.rep_id`` to the actual completed ``rep.id``; never
    synthesizes rep IDs or timestamps from metric indices.
    """
    from providers.llm.nebius_provider import CoachingCandidate, CoachingEvidence

    dump = report.model_dump(mode="json") if hasattr(report, "model_dump") else dict(report)
    exercise = str(dump.get("exercise") or "")
    if not exercise:
        return None
    reps = [r for r in (dump.get("reps") or []) if isinstance(r, dict)]
    metrics = [m for m in (dump.get("metrics") or []) if isinstance(m, dict)]
    completed = {
        str(r.get("id")): r
        for r in reps
        if r.get("id") and r.get("completion_status") == "completed"
    }
    rows: list[dict[str, Any]] = []
    for i, m in enumerate(metrics):
        if m.get("status") != "observed":
            continue
        if str(m.get("unit") or "").lower() not in ("degrees", "degree", "deg"):
            continue  # angles only; temporal/other metrics are not degrees
        value = m.get("value")
        if not _finite(value):
            continue  # exclude None / NaN / inf / partial fragments
        coverage = m.get("coverage")
        if not _finite(coverage) or float(coverage) < MIN_COVERAGE:
            continue
        rep = completed.get(str(m.get("rep_id") or ""))
        if rep is None:
            continue  # only exact completed reps; no partial segments
        if (m.get("side") or None) != (rep.get("side") or None):
            continue  # selected side must match the rep side
        ordinal = rep.get("ordinal")
        start, end = rep.get("start_s"), rep.get("end_s")
        if not (_finite(ordinal) and _finite(start) and _finite(end)):
            continue
        ref = m.get("reference_interval")
        low = high = None
        if isinstance(ref, (list, tuple)) and len(ref) == 2 and _finite(ref[0]) and _finite(ref[1]):
            low, high = float(ref[0]), float(ref[1])
        dev = m.get("deviation")
        if _finite(dev):
            dev = abs(float(dev))
        else:
            dev = 0.0
            if low is not None and high is not None:
                if value > high:
                    dev = float(value) - high
                elif value < low:
                    dev = low - float(value)
        rows.append({
            "ordinal": int(ordinal), "midx": i,
            "rep_id": str(rep["id"]), "metric_id": str(m.get("id") or f"metric-{i + 1}"),
            "value": float(value), "start": float(start), "end": float(end),
            "coverage": float(coverage), "low": low, "high": high, "dev": dev,
        })
    if not rows:
        return None
    # Priority: largest absolute deviation, then coverage, then rep ordinal,
    # then stable metric key.
    rows.sort(key=lambda r: (-abs(r["dev"]), -r["coverage"], r["ordinal"], r["metric_id"]))
    selected = rows[:MAX_OBSERVATIONS]
    candidates = []
    rep_ids: list[str] = []
    metric_ids: list[str] = []
    for r in selected:
        if r["rep_id"] not in rep_ids:
            rep_ids.append(r["rep_id"])
        if r["metric_id"] not in metric_ids:
            metric_ids.append(r["metric_id"])
        text = (
            f"Segment {r['ordinal']} ({r['start']:.2f}\u2013{r['end']:.2f}s): "
            f"{_human(r['metric_id'])} measured {r['value']:.1f} degrees."
        )
        if r["dev"] > 0 and r["low"] is not None and r["high"] is not None:
            sign = "above" if r["value"] > r["high"] else "below"
            text += (
                f" Observed reference band {r['low']:.1f}\u2013{r['high']:.1f} degrees; "
                f"measured {sign} the band by {r['dev']:.1f} degrees. "
                "This band is unreviewed and is not a correctness claim."
            )
        candidates.append(CoachingCandidate(
            id=f"obs-{r['ordinal']}-{r['midx']}", text=text[:MAX_OBS_TEXT],
            rep_ids=[r["rep_id"]], metric_ids=[r["metric_id"]], kind="observation",
        ))
    claims_version, claims = _load_claims(exercise)
    approved: list[str] = []
    limitations = [
        "3D positions are model-estimated from a single camera view and are uncalibrated.",
        "Image axis and camera view are unreviewed; angles may be projection-affected.",
        "This is not a technique grade and not medical or injury advice.",
    ]
    for claim in claims[:1]:
        cid = str(claim.get("id") or "")
        text = str(claim.get("text") or "").strip()
        url = str(claim.get("url") or "")
        if not cid or not text:
            continue
        approved.append(cid)
        candidates.append(CoachingCandidate(
            id=f"cue-{cid}", text=text[:MAX_OBS_TEXT], claim_ids=[cid], kind="cue",
        ))
        if url:
            limitations.append(f"Cue source: {url}")
    return CoachingEvidence(
        exercise=exercise, rep_ids=rep_ids, metric_ids=metric_ids,
        approved_claim_ids=approved, candidates=candidates,
        limitations=limitations, profile_version=claims_version,
        prompt_version=PROMPT_VERSION,
    )


def _cache_key(report: Any, evidence: Any) -> str:
    """Cross-model-safe cache key: report recipe, canonical evidence, claim
    version, prompt version, quota version, and the runtime model ID."""
    dump = report.model_dump(mode="json") if hasattr(report, "model_dump") else report
    canon = json.dumps(dump, sort_keys=True, separators=(",", ":"), default=str)
    ev = json.dumps(evidence.model_dump(), sort_keys=True, separators=(",", ":"))
    recipe = str(dump.get("recipe_version") or "") if isinstance(dump, dict) else ""
    model = os.getenv("NEBIUS_MODEL_ID") or ""
    material = (
        f"{canon}|{ev}|{recipe}|{evidence.profile_version}|"
        f"{PROMPT_VERSION}|{QUOTA_VERSION}|{model}"
    )
    return hashlib.sha256(material.encode()).hexdigest()


def _day_start(now: float) -> float:
    dt = datetime.fromtimestamp(now, timezone.utc)
    return datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc).timestamp()


def _reserve(conn, owner: str, job_id: str, key: str, now: float):
    """Atomically reserve one coaching generation.

    Expired rows fail closed: an expired reservation/cache entry is treated
    as unavailable and is never replaced, so quota history is never erased
    and a restart cannot grant a fresh call.
    """
    _ensure_table(conn)
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute(
            "SELECT state, result_json, expires_at FROM grounded_coaching "
            "WHERE owner=? AND job_id=? AND key=?",
            (owner, job_id, key),
        ).fetchone()
        if row is not None:
            state = row["state"] if isinstance(row, sqlite3.Row) else row[0]
            result_json = row["result_json"] if isinstance(row, sqlite3.Row) else row[1]
            expires_at = row["expires_at"] if isinstance(row, sqlite3.Row) else row[2]
            conn.execute("COMMIT")
            if expires_at <= now:
                return ("expired", None)  # fail closed; never erase quota history
            if state == "done" and result_json:
                return ("hit", result_json)
            if state == "reserved":
                return ("busy", None)
            if state == "failed" and result_json:
                return ("failed", result_json)
            return ("expired", None)  # unknown state: fail closed
        day = _day_start(now)
        global_count = conn.execute(
            "SELECT COUNT(*) FROM grounded_coaching WHERE reserved_at>=?", (day,)
        ).fetchone()[0]
        owner_count = conn.execute(
            "SELECT COUNT(*) FROM grounded_coaching WHERE reserved_at>=? AND owner=?",
            (day, owner),
        ).fetchone()[0]
        lifetime_count = conn.execute("SELECT COUNT(*) FROM grounded_coaching").fetchone()[0]
        if global_count >= GLOBAL_DAILY_LIMIT or owner_count >= OWNER_DAILY_LIMIT or lifetime_count >= GLOBAL_LIFETIME_LIMIT:
            conn.execute("COMMIT")
            return ("quota", None)
        conn.execute(
            "INSERT INTO grounded_coaching "
            "(owner, job_id, key, result_json, state, reserved_at, expires_at, usage_json) "
            "VALUES (?,?,?,NULL,'reserved',?,?,NULL)",
            (owner, job_id, key, now, now + CACHE_TTL_S),
        )
        conn.execute("COMMIT")
        return ("reserved", None)
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise


def _finalize(conn, owner: str, job_id: str, key: str, state: str,
              result_json: str, usage: Optional[dict], now: float) -> None:
    _ensure_table(conn)
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            "UPDATE grounded_coaching SET state=?, result_json=?, usage_json=?, expires_at=? "
            "WHERE owner=? AND job_id=? AND key=?",
            (state, result_json, json.dumps(usage) if usage else None,
             now + CACHE_TTL_S, owner, job_id, key),
        )
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise


def _unavailable(limitations: Optional[list[str]] = None) -> CoachingResult:
    return CoachingResult(status=CoachingStatus.UNAVAILABLE, limitations=list(limitations or []))


def _recheck_job(store, owner: str, job_id: str):
    """Re-validate raw job access before any cache read or response write."""
    store.get_input(owner, job_id, now=time.time())
    _recheck(store, owner, job_id)


@router.post("/analyses/{analysis_id}/coaching", response_model=CoachingResult)
async def post_coaching(request: Request, response: Response, analysis_id: str):
    try:
        owner = _auth(request, mutation=True)
        job_id = _canonical_uuid(analysis_id)
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)

    report = await run_in_threadpool(get_movement_report, request, Response(), job_id)
    if isinstance(report, JSONResponse):
        _no_store(response)
        return report

    try:
        evidence = _build_evidence(report)
    except Exception:
        evidence = None
    if evidence is None or not evidence.candidates:
        _no_store(response)
        return _unavailable(["No complete observed metrics are available for grounded coaching."])

    key = _cache_key(report, evidence)
    now = time.time()
    try:
        store = _store()
        _recheck_job(store, owner, job_id)
        with store._conn() as conn:
            decision, payload = _reserve(conn, owner, job_id, key, now)
    except NotFound:
        _no_store(response)
        return _error_response(404, "NOT_FOUND", "Analysis not found")
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)
    except (sqlite3.Error, OSError):
        _no_store(response)
        return _error_response(503, "STORAGE_UNAVAILABLE", "Storage temporarily unavailable", retryable=True)

    if decision == "busy":
        _no_store(response)
        return _error_response(409, "COACHING_IN_PROGRESS", "Coaching generation is already in progress", retryable=False)
    if decision == "quota":
        _no_store(response)
        return _error_response(429, "COACHING_QUOTA_EXCEEDED", "Coaching quota exhausted", retryable=True)
    if decision == "expired":
        _no_store(response)
        return _error_response(503, "COACHING_UNAVAILABLE", "Coaching is unavailable for this analysis", retryable=False)
    if decision in ("hit", "failed"):
        try:
            cached = CoachingResult.model_validate_json(payload)
        except Exception:
            cached = _unavailable(evidence.limitations)
        try:
            _recheck_job(store, owner, job_id)
        except NotFound:
            _no_store(response)
            return _error_response(404, "NOT_FOUND", "Analysis not found")
        except HTTPException as exc:
            _no_store(response)
            return _translate_http_exception(exc)
        except (sqlite3.Error, OSError):
            _no_store(response)
            return _error_response(503, "STORAGE_UNAVAILABLE", "Storage temporarily unavailable", retryable=True)
        _no_store(response)
        return cached

    # Reserved: generate before any further cache read; recheck after the
    # provider returns and before finalize/response.
    try:
        provider = _provider_factory()
    except Exception:
        provider = None
    if provider is None:
        result = _unavailable(evidence.limitations)
    else:
        try:
            result = await provider.coach(evidence)
        except Exception:
            result = _unavailable(evidence.limitations)  # SDK/client errors: unavailable, cached
    usage = getattr(provider, "last_usage", None) if provider is not None else None
    if not isinstance(result, CoachingResult):
        result = _unavailable(evidence.limitations)
    state = "done" if result.status == CoachingStatus.OK else "failed"
    finished = time.time()

    # Post-compute recheck: on revocation, mark the reservation failed
    # without any private payload and return 404.
    try:
        _recheck_job(store, owner, job_id)
    except NotFound:
        try:
            with store._conn() as conn:
                _finalize(conn, owner, job_id, key, "failed",
                          _unavailable().model_dump_json(), None, finished)
        except (sqlite3.Error, OSError):
            pass
        _no_store(response)
        return _error_response(404, "NOT_FOUND", "Analysis not found")
    except HTTPException as exc:
        _no_store(response)
        return _translate_http_exception(exc)
    except (sqlite3.Error, OSError):
        _no_store(response)
        return _error_response(503, "STORAGE_UNAVAILABLE", "Storage temporarily unavailable", retryable=True)

    try:
        with store._conn() as conn:
            _finalize(conn, owner, job_id, key, state, result.model_dump_json(), usage, finished)
    except (sqlite3.Error, OSError):
        _no_store(response)
        return _error_response(503, "STORAGE_UNAVAILABLE", "Storage temporarily unavailable", retryable=True)

    _no_store(response)
    return result
