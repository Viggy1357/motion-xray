#!/usr/bin/env python3
"""Standalone local acceptance benchmark: guest session -> video upload ->
analysis -> movement report. Operator-owned local demo clips against the
local API only. Prints one aggregate JSON object to stdout; never prints
tokens, cookies, video bytes, poses, or request headers."""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

import httpx

ALLOWED_HOSTS = {"web", "localhost", "127.0.0.1"}
MIME_BY_EXT = {".mp4": "video/mp4", ".m4v": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm"}
TERMINAL_BAD = {"failed", "cancelled"}
REQUEST_TIMEOUT = 120.0
TOTAL_DEADLINE_S = 420.0
POLL_INTERVAL_S = 1.0
POLL_MAX_S = 360.0


class BenchError(Exception):
    pass


def _check_base_url(raw: str) -> str:
    parsed = urlparse(raw if "://" in raw else f"http://{raw}")
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise BenchError("invalid --base-url")
    if parsed.hostname.lower() not in ALLOWED_HOSTS:
        raise BenchError("base-url host must be web, localhost or 127.0.0.1")
    if parsed.username or parsed.password:
        raise BenchError("base-url must not embed credentials")
    if parsed.query or parsed.fragment:
        raise BenchError("base-url must not contain query or fragment")
    if parsed.path not in ("", "/"):
        raise BenchError("base-url must not contain a path")
    return f"{parsed.scheme}://{parsed.netloc}"


def _require_ok(resp: httpx.Response, step: str) -> dict:
    if not (200 <= resp.status_code < 300):
        code = None
        try:
            body = resp.json()
            code = body.get("code") if isinstance(body, dict) else None
        except ValueError:
            code = None
        raise BenchError(f"{step} failed: HTTP {resp.status_code}" + (f" code={code}" if code else ""))
    try:
        data = resp.json()
    except ValueError as exc:
        raise BenchError(f"{step} returned non-JSON body") from exc
    if not isinstance(data, dict):
        raise BenchError(f"{step} returned unexpected JSON shape")
    return data


def run(args: argparse.Namespace) -> dict:
    base = _check_base_url(args.base_url)
    video_path = Path(args.video)
    if not video_path.is_file():
        raise BenchError(f"video not found: {video_path.name}")
    mime = MIME_BY_EXT.get(video_path.suffix.lower())
    if mime is None:
        raise BenchError("unsupported video extension (mp4/m4v/mov/webm)")
    size = video_path.stat().st_size
    if size <= 0:
        raise BenchError("video file is empty")

    started = time.monotonic()
    transitions: list[dict] = []

    with httpx.Client(base_url=base, timeout=REQUEST_TIMEOUT, follow_redirects=False) as client:
        session = _require_ok(client.get("/api/session"), "session")
        csrf = session.get("csrf_token")
        if not isinstance(csrf, str) or not csrf:
            raise BenchError("session response missing csrf_token")
        mutation_headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:3000"}

        t0 = time.monotonic()
        with video_path.open("rb") as fh:
            upload_resp = client.post(
                "/api/videos",
                content=fh,
                headers={
                    **mutation_headers,
                    "Content-Type": mime,
                    "Content-Length": str(size),
                    "X-Upload-Consent": "true",
                },
            )
        upload_s = time.monotonic() - t0
        asset = _require_ok(upload_resp, "upload")
        video_id = asset.get("id")
        if not isinstance(video_id, str) or not video_id:
            raise BenchError("upload response missing asset id")

        t0 = time.monotonic()
        payload: dict = {"video_id": video_id, "exercise_id": args.exercise, "request_key": f"bench-{uuid.uuid4()}"}
        if args.variant:
            payload["variant"] = args.variant
        create_resp = client.post("/api/analyses", json=payload, headers=mutation_headers)
        create_s = time.monotonic() - t0
        status = _require_ok(create_resp, "create analysis")
        job_id = status.get("id")
        if not isinstance(job_id, str) or not job_id:
            raise BenchError("create analysis response missing job id")

        poll_start = time.monotonic()
        last_sig = None
        final = status
        while True:
            state, stage = final.get("state"), final.get("stage")
            sig = (state, stage)
            if sig != last_sig:
                transitions.append({"state": state, "stage": stage, "at_s": round(time.monotonic() - poll_start, 3)})
                last_sig = sig
            if state == "succeeded":
                break
            if state in TERMINAL_BAD:
                raise BenchError(f"analysis terminated with state={state}")
            if time.monotonic() - poll_start >= POLL_MAX_S:
                raise BenchError("analysis polling deadline exceeded")
            if time.monotonic() - started >= TOTAL_DEADLINE_S:
                raise BenchError("total deadline exceeded")
            time.sleep(POLL_INTERVAL_S)
            final = _require_ok(client.get(f"/api/analyses/{job_id}"), "poll status")
        queue_worker_s = time.monotonic() - poll_start

        t0 = time.monotonic()
        result = _require_ok(client.get(f"/api/analyses/{job_id}/result"), "fetch result")
        report = _require_ok(client.get(f"/api/analyses/{job_id}/movement-report"), "fetch movement report")
        report_s = time.monotonic() - t0

    legacy_metrics = result.get("metrics")
    if not isinstance(legacy_metrics, list) or legacy_metrics:
        raise BenchError("legacy /result must be pose-only with empty metrics")
    metrics = report.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        raise BenchError("movement report has no metrics (fake/empty report)")
    if not any(isinstance(m, dict) and m.get("value") is not None for m in metrics):
        raise BenchError("movement report has no measured metric value")
    if report.get("score") is not None:
        raise BenchError("expected report score to be null for this prototype")
    if result.get("score") is not None:
        raise BenchError("expected legacy result score to be null for this prototype")

    provenance = report.get("provenance") if isinstance(report.get("provenance"), dict) else {}
    safe_prov = {k: v for k, v in provenance.items() if isinstance(v, (int, float, str)) and len(str(v)) <= 128}
    legacy_prov = result.get("provenance") if isinstance(result.get("provenance"), dict) else {}
    legacy_version = legacy_prov.get("version_hash")
    if isinstance(legacy_version, str) and len(legacy_version) <= 128:
        safe_prov["legacy_version_hash"] = legacy_version
    assessment = report.get("prototype_assessment")
    if isinstance(assessment, dict):
        assessment = {k: v for k, v in assessment.items() if isinstance(v, (int, float, str, bool, type(None)))}

    out = {
        "label": args.label,
        "job_id": job_id,
        "exercise": args.exercise,
        "variant": args.variant,
        "status": final.get("state"),
        "transitions": transitions,
        "timing_s": {
            "upload": round(upload_s, 3),
            "create": round(create_s, 3),
            "queue_and_worker": round(queue_worker_s, 3),
            "report": round(report_s, 3),
            "total": round(time.monotonic() - started, 3),
        },
        "report": {
            "recipe_version": report.get("recipe_version"),
            "detected_rep_count": report.get("detected_rep_count"),
            "quality": report.get("quality"),
            "prototype_assessment": assessment,
        },
        "result": {
            "score": result.get("score"),
            "metric_count": len(metrics),
            "warnings": result.get("warnings"),
        },
        "provenance": safe_prov,
    }
    if args.output:
        Path(args.output).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Local upload->analysis->report acceptance benchmark")
    parser.add_argument("--base-url", default="http://web:3000")
    parser.add_argument("--video", required=True)
    parser.add_argument("--exercise", required=True,
                        choices=["lat_pulldown", "squat", "dumbbell_curl", "lateral_raise", "incline_chest_press"])
    parser.add_argument("--variant", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--label", default=None)
    args = parser.parse_args()
    try:
        summary = run(args)
    except (BenchError, httpx.HTTPError, OSError) as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}))
        return 1
    print(json.dumps({"ok": True, **summary}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
