#!/usr/bin/env python3
"""Build exercise-reference-bands-v1 config from actual local reference videos.

Reads a manifest of locally reviewed reference pose artifacts, runs the
generic exercise runtime, and derives per-metric min/max bands ONLY from
measured completed reference cycles (coverage >= 0.8 on all four comparison
keys, at least 2 usable reference cycles, strict). No band numbers are
fabricated: references without enough valid cycles are recorded under
rejected_references with a reason.

A manifest entry may optionally carry ``rep_windows``: a list of
{start_s, bottom_s, end_s, side, origin, review_status} dicts with
origin="visually_proposed_reference_window" and review_status="unreviewed".
When present, arithmetic components are derived over the actual reference
pose frames inside those explicit windows via the generic PROFILE-groups
summarizer (used when automatic segmentation is fragmented). These windows
are visually proposed reference labels, never claimed as ground truth.

Local operator tool only; no API uploads.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from movement.runtime_exercises import (
    COMPARISON_KEYS,
    _MIN_COVERAGE,
    _MIN_REFERENCE_CYCLES,
    build_exercise_report,
    measure_reference_windows,
)
from providers.pose.artifacts import read_pose_frames

_REQUIRED = (
    "id", "exercise_id", "variant", "pose_root", "frames_artifact_key",
    "pose_sha256", "width", "height", "processing_version", "source_url",
    "view_id", "primary",
)
_WINDOW_ORIGIN = "visually_proposed_reference_window"
_WINDOW_REVIEW = "unreviewed"


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _load_manifest(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    refs = data.get("references") if isinstance(data, dict) else data
    if not isinstance(refs, list) or not refs:
        raise ValueError("manifest must contain a nonempty references list")
    for entry in refs:
        missing = [k for k in _REQUIRED if k not in entry]
        if missing:
            raise ValueError(f"manifest entry missing keys: {missing}")
        _validate_rep_windows(entry)
    return refs


def _validate_rep_windows(entry: dict) -> list[dict] | None:
    wins = entry.get("rep_windows")
    if wins is None:
        return None
    if not isinstance(wins, list) or not wins:
        raise ValueError("rep_windows must be a nonempty list when present")
    bounds = entry.get("window_s")
    out = []
    for w in wins:
        if not isinstance(w, dict):
            raise ValueError("each rep window must be an object")
        missing = [k for k in ("start_s", "bottom_s", "end_s", "side", "origin", "review_status") if k not in w]
        if missing:
            raise ValueError(f"rep window missing keys: {missing}")
        start, bottom, end = w["start_s"], w["bottom_s"], w["end_s"]
        if not (_is_num(start) and _is_num(bottom) and _is_num(end)):
            raise ValueError("rep window times must be finite non-bool numbers")
        if not (0.0 <= start < bottom < end):
            raise ValueError("rep window times must satisfy 0 <= start_s < bottom_s < end_s")
        if w["side"] not in ("left", "right"):
            raise ValueError("rep window side must be 'left' or 'right'")
        if w["origin"] != _WINDOW_ORIGIN:
            raise ValueError(f"rep window origin must be {_WINDOW_ORIGIN!r}")
        if w["review_status"] != _WINDOW_REVIEW:
            raise ValueError(f"rep window review_status must be {_WINDOW_REVIEW!r}")
        if bounds is not None:
            lo, hi = float(bounds[0]), float(bounds[1])
            if not (lo <= start and end <= hi):
                raise ValueError("rep window must lie inside window_s")
        out.append({
            "start_s": float(start), "bottom_s": float(bottom), "end_s": float(end),
            "side": w["side"], "origin": w["origin"], "review_status": w["review_status"],
        })
    return out


def _measure_reference(entry: dict) -> dict:
    frames = read_pose_frames(
        Path(entry["pose_root"]), entry["frames_artifact_key"],
        expected_sha256=entry["pose_sha256"],
    )
    window = entry.get("window_s")
    if window is not None:
        start, end = float(window[0]), float(window[1])
        # Inclusive PTS filter on original timestamps; indices unchanged.
        frames = [f for f in frames if start <= f.timestamp_s <= end]
    report = build_exercise_report(
        frames,
        analysis_id=f"calib-{entry['id']}",
        exercise_id=entry["exercise_id"],
        variant=entry["variant"],
        width=entry["width"],
        height=entry["height"],
        pose_sha256=entry["pose_sha256"],
        processing_version=entry["processing_version"],
    )
    keys = COMPARISON_KEYS[entry["exercise_id"]]
    windows = _validate_rep_windows(entry)
    if windows is not None:
        # Explicit visually proposed reference windows (unreviewed, not
        # ground truth); used when automatic segmentation is fragmented.
        comps_list = measure_reference_windows(
            frames, exercise_id=entry["exercise_id"], windows=windows,
            width=entry["width"], height=entry["height"],
        )
        values: dict[str, list[float]] = {k: [] for k in keys}
        usable = 0
        for comps in comps_list:
            if all(
                comps[k][0] is not None and comps[k][3] >= _MIN_COVERAGE for k in keys
            ):
                usable += 1
                for k in keys:
                    values[k].append(comps[k][0])
        return {
            "report": report, "values": values, "usable_cycles": usable,
            "window_origin": _WINDOW_ORIGIN, "review_status": _WINDOW_REVIEW,
        }
    completed = {r.id for r in report.reps if r.completion_status.value == "completed"}
    values = {k: [] for k in keys}
    cycles: dict[str, dict[str, float]] = {rid: {} for rid in completed}
    for m in report.metrics:
        if m.rep_id in completed and m.id in keys and m.value is not None and (m.coverage or 0.0) >= _MIN_COVERAGE:
            cycles[m.rep_id][m.id] = m.value
    usable = 0
    for vals in cycles.values():
        if all(k in vals for k in keys):
            usable += 1
            for k in keys:
                values[k].append(vals[k])
    return {
        "report": report, "values": values, "usable_cycles": usable,
        "window_origin": "automatic_segmentation_signal_only",
        "review_status": _WINDOW_REVIEW,
    }


def build_config(manifest_path: Path) -> dict:
    refs = _load_manifest(manifest_path)
    config = {
        "version": "exercise-reference-bands-v1",
        "author": False,
        "review": "unreviewed",
        "normalization_degrees": 30,
        "normalization_status": "proposal_experimental",
        "aggregation": "equal_metric_mean_per_cycle_then_cycle_mean",
        "min_coverage": _MIN_COVERAGE,
        "min_reference_cycles": _MIN_REFERENCE_CYCLES,
        "references": {},
        "rejected_references": [],
    }
    primaries: dict[str, dict] = {}
    for entry in refs:
        if entry.get("primary"):
            if entry["exercise_id"] in primaries:
                raise ValueError(f"duplicate primary for {entry['exercise_id']}")
            primaries[entry["exercise_id"]] = entry
    for entry in refs:
        ex = entry["exercise_id"]
        try:
            measured = _measure_reference(entry)
        except Exception as exc:  # record, never fabricate
            config["rejected_references"].append({"id": entry["id"], "exercise_id": ex, "reason": f"measurement_failed:{exc}"})
            continue
        if measured["usable_cycles"] < _MIN_REFERENCE_CYCLES:
            config["rejected_references"].append({
                "id": entry["id"], "exercise_id": ex,
                "reason": f"insufficient_valid_reference_cycles:{measured['usable_cycles']}",
            })
            continue
        bands = {
            k: {
                "lower": min(v), "upper": max(v), "valid_count": len(v),
                "unit": "degrees", "source": "measured_reference_cycles",
            }
            for k, v in measured["values"].items()
        }
        record = {
            "reference_id": entry["id"],
            "reference_name": entry.get("name", entry["id"]),
            "source_url": entry["source_url"],
            "view_id": entry["view_id"],
            "primary": bool(entry.get("primary")),
            "rep_count": measured["usable_cycles"],
            "automatic_cycle_count": measured["report"].detected_rep_count,
            "source_sha256": entry.get("source_sha256"),
            "valid_reference_cycles": measured["usable_cycles"],
            "pose_sha256": entry["pose_sha256"],
            "processing_version": entry["processing_version"],
            "window_origin": measured["window_origin"],
            "review_status": measured["review_status"],
            "bands": bands,
        }
        if entry.get("primary"):
            config["references"][ex] = record
        else:
            config["references"].setdefault(f"{ex}#secondary:{entry['id']}", record)
    for ex, entry in primaries.items():
        if ex not in config["references"] and not any(x["id"] == entry["id"] for x in config["rejected_references"]):
            config["rejected_references"].append({
                "id": entry["id"], "exercise_id": ex,
                "reason": "primary_reference_rejected_no_band",
            })
    if not config["references"]:
        raise ValueError("no usable reference bands derived; refusing to write empty config")
    return config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Derive reference bands from actual videos")
    parser.add_argument("--manifest", required=True, help="manifest JSON path (local relative paths allowed)")
    parser.add_argument("--output", required=True, help="output config JSON path")
    args = parser.parse_args(argv)
    config = build_config(Path(args.manifest))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(config, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"wrote {out} with {len(config['references'])} reference(s), "
          f"{len(config['rejected_references'])} rejected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
