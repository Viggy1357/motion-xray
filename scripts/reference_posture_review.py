from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

from contracts.pose import PoseSequence
from movement.observations import measure_frame
from movement.posture import ProjectionAxis, measure_torso_frame, summarize_window
from providers.pose.artifacts import read_pose_frames

ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
HEX64_RE = re.compile(r"^[0-9a-fA-F]{64}$")

# All five metric/space observation rows produced per frame.
COMBOS = (
    ("elbow_angle", "projected_2d"),
    ("elbow_angle", "estimated_3d"),
    ("upper_arm_torso_angle", "projected_2d"),
    ("upper_arm_torso_angle", "estimated_3d"),
    ("torso_axis_angle", "projected_2d"),
)


def _die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def _num(obj: Any) -> bool:
    return not isinstance(obj, bool) and isinstance(obj, (int, float)) and math.isfinite(obj)


def _load_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("config must be a JSON object")
    for k in ("version", "authoritative", "max_gap_s", "clips"):
        if k not in data:
            raise ValueError(f"missing top-level config field: {k}")
    if not isinstance(data["version"], str) or not data["version"]:
        raise ValueError("version must be a non-empty string")
    if data["authoritative"] is not False:
        raise ValueError("authoritative must be false")
    mg = data["max_gap_s"]
    if not _num(mg) or mg <= 0:
        raise ValueError("max_gap_s must be a finite positive number")
    if not isinstance(data["clips"], list) or not data["clips"]:
        raise ValueError("clips must be a non-empty list")
    return data


def _validate_axis(obj: Any) -> ProjectionAxis:
    if not isinstance(obj, dict):
        raise ValueError("axis must be an object")
    for k in ("version", "axis_id", "up_xy", "positive_cross_sign"):
        if k not in obj:
            raise ValueError(f"missing axis field: {k}")
    up = obj["up_xy"]
    if not isinstance(up, (list, tuple)) or len(up) != 2 or not all(_num(c) for c in up):
        raise ValueError("up_xy must be two finite non-bool numbers")
    sign = obj["positive_cross_sign"]
    if isinstance(sign, bool) or not isinstance(sign, int) or sign not in (-1, 1):
        raise ValueError("positive_cross_sign must be exactly +1 or -1 (no bool/float casts)")
    if not isinstance(obj["version"], str) or not obj["version"]:
        raise ValueError("axis version must be a non-empty string")
    if not isinstance(obj["axis_id"], str) or not obj["axis_id"]:
        raise ValueError("axis_id must be a non-empty string")
    return ProjectionAxis(version=obj["version"], axis_id=obj["axis_id"],
                          up_xy=(float(up[0]), float(up[1])), positive_cross_sign=sign)


def _validate_clip(obj: Any, idx: int) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise ValueError(f"clip {idx} must be an object")
    for k in ("id", "pose_root", "side", "width", "height", "axis", "windows_s"):
        if k not in obj:
            raise ValueError(f"clip {idx} missing field: {k}")
    cid = obj["id"]
    if not isinstance(cid, str) or not ID_RE.match(cid):
        raise ValueError(f"invalid clip id (path-unsafe): {cid!r}")
    if obj["side"] not in ("left", "right"):
        raise ValueError(f"invalid side: {obj['side']!r}")
    w, h = obj["width"], obj["height"]
    if any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in (w, h)):
        raise ValueError("width and height must be positive integers")
    windows = obj["windows_s"]
    if not isinstance(windows, list):
        raise ValueError("windows_s must be a list")
    wins: list[tuple[float, float]] = []
    for i, win in enumerate(windows):
        if not isinstance(win, (list, tuple)) or len(win) != 2:
            raise ValueError(f"window {i} must be [start,end]")
        s, e = win
        if not _num(s) or s < 0 or not _num(e) or e <= s:
            raise ValueError(f"window {i} invalid")
        wins.append((float(s), float(e)))
    sts = obj.get("sample_times_s", [])
    if not isinstance(sts, list) or not all(_num(t) and t >= 0 for t in sts):
        raise ValueError("sample_times_s must be a list of finite non-negative numbers")
    return {"id": cid, "pose_root": Path(str(obj["pose_root"])), "side": obj["side"],
            "width": w, "height": h, "axis": _validate_axis(obj["axis"]),
            "windows_s": wins, "sample_times_s": [float(t) for t in sts],
            "view_note": str(obj.get("view_note", ""))}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _prepare_output_dir(outdir: Path) -> Path:
    if outdir.is_symlink():
        raise ValueError("output dir must not be a symlink")
    resolved = outdir.resolve()
    if "artifacts" not in resolved.parts:
        raise ValueError("output dir must live under an actual 'artifacts' path component")
    resolved.mkdir(parents=True, exist_ok=True)
    if resolved.is_symlink():
        raise ValueError("output dir resolves through a symlink escape")
    return resolved


def _safe_output_path(outdir: Path, name: str, inputs: set[Path]) -> Path:
    p = (outdir / name).resolve()
    if not p.is_relative_to(outdir):
        raise ValueError(f"output path escapes output dir: {name}")
    if p in inputs:
        raise ValueError(f"refusing to overwrite input file: {p}")
    return p


def _read_clip(root: Path) -> tuple[PoseSequence, list[Any], str, set[Path]]:
    manifest = root / "manifest.json"
    if not manifest.is_file():
        raise ValueError(f"missing manifest.json under {root}")
    seq = PoseSequence.model_validate_json(manifest.read_bytes())
    stem = Path(seq.frames_artifact_key).stem
    if not HEX64_RE.match(stem):
        raise ValueError(f"malformed expected hash from artifact key stem: {stem}")
    frames = read_pose_frames(root, seq.frames_artifact_key, expected_sha256=stem)
    inputs = {manifest.resolve(), (root / seq.frames_artifact_key).resolve()}
    return seq, frames, stem.lower(), inputs


def _measure_all(frames: list[Any], side: Literal["left", "right"], width: int,
                 height: int, axis: ProjectionAxis) -> list[Any]:
    obs: list[Any] = []
    for f in frames:
        obs.extend(measure_frame(f, side=side, width=width, height=height))
        obs.append(measure_torso_frame(f, side=side, width=width, height=height, axis=axis))
    obs.sort(key=lambda o: (o.timestamp_s, o.metric, o.space))
    return obs


def _sample_payload(obs: list[Any], target: float, max_gap: float,
                    windows: list[tuple[float, float]]) -> dict[str, Any]:
    """Nearest FRAME by PTS regardless of validity; then all 5 rows at that PTS."""
    pts_list = sorted({o.timestamp_s for o in obs})
    if not pts_list:
        return {"requested_s": target, "actual_pts_s": None, "observations": None,
                "within_any_window": False, "reason": "no_frames"}
    best = min(pts_list, key=lambda p: (abs(p - target), p))
    if abs(best - target) > max_gap:
        return {"requested_s": target, "actual_pts_s": None, "observations": None,
                "within_any_window": False, "reason": "no_nearby_frame_within_max_gap"}
    rows: dict[str, Any] = {}
    for metric, space in COMBOS:
        o = next((x for x in obs if x.timestamp_s == best and x.metric == metric
                  and x.space == space), None)
        rows[f"{metric}/{space}"] = ({"value": o.value, "reason": o.reason} if o
                                    else {"value": None, "reason": "missing_observation"})
    return {"requested_s": target, "actual_pts_s": best,
            "within_any_window": any(s <= best <= e for s, e in windows),
            "observations": rows, "reason": None}


def _summarize(obs: list[Any], windows: list[tuple[float, float]], max_gap: float) -> list[dict[str, Any]]:
    records = []
    for start, end in windows:
        metrics: dict[str, Any] = {}
        for metric, space in COMBOS:
            sub = [o for o in obs if o.metric == metric and o.space == space]
            if not sub:
                metrics[f"{metric}/{space}"] = {"reason": "missing_observation"}
                continue
            summ = summarize_window(sub, start_s=start, end_s=end, max_gap_s=max_gap,
                                    circular=(metric == "torso_axis_angle"))
            d = asdict(summ)
            raw_values = [o.value for o in sub
                          if start <= o.timestamp_s <= end and o.value is not None]
            d["observed_valid_min"] = min(raw_values, default=None)
            d["observed_valid_max"] = max(raw_values, default=None)
            d["range_note"] = ("raw valid samples in this window only; descriptive, "
                               "not a full-span/rep/score range (gapped or circular data)")
            metrics[f"{metric}/{space}"] = d
        records.append({"start_s": start, "end_s": end, "metrics": metrics})
    return records


def _run(config_path: Path, output_dir: Path) -> None:
    config_path = config_path.resolve()
    cfg = _load_config(config_path)
    clips_cfg = [_validate_clip(c, i) for i, c in enumerate(cfg["clips"])]
    ids = [c["id"] for c in clips_cfg]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate clip ids")
    outdir = _prepare_output_dir(output_dir)
    config_sha = _sha256_file(config_path)
    max_gap = float(cfg["max_gap_s"])

    # Read and measure everything before writing anything.
    inputs: set[Path] = {config_path}
    prepared = []
    for c in clips_cfg:
        root = c["pose_root"].resolve()
        seq, frames, pose_hash, clip_inputs = _read_clip(root)
        inputs |= clip_inputs
        prepared.append((c, seq, _measure_all(frames, c["side"], c["width"], c["height"], c["axis"]), pose_hash))

    clip_summaries = []
    for c, seq, obs, pose_hash in prepared:
        raw_path = _safe_output_path(outdir, f"{c['id']}-observations.json", inputs)
        raw_path.write_text(json.dumps([asdict(o) for o in obs], sort_keys=True,
                                       separators=(",", ":"), allow_nan=False))
        samples = {str(t): _sample_payload(obs, t, max_gap, c["windows_s"])
                   for t in c["sample_times_s"]}
        clip_summaries.append({
            "id": c["id"],
            "pose_artifact_hash": pose_hash,
            "source_pose_provenance": str(c["pose_root"]),
            "joint_mapping_version": seq.joint_mapping_version,
            "width": c["width"], "height": c["height"],
            "axis": asdict(c["axis"]), "view_note": c["view_note"],
            "windows": _summarize(obs, c["windows_s"], max_gap),
            "sample_values": samples,
            "summary_metadata": {
                "diagnostic_description": "raw valid observed samples only; not a full "
                "window/rep/benchmark/tolerance range; no pooled cross-metric range",
            },
        })

    summary = {
        "config_sha256": config_sha,
        "version": cfg["version"],
        "experimental": True,
        "authoritative": False,
        "valid_technique_score": None,
        "endpoint": None,
        "endpoint_reason": "not_implemented",
        "clips": clip_summaries,
    }
    summary_path = _safe_output_path(outdir, "summary.json", inputs)
    summary_path.write_text(json.dumps(summary, sort_keys=True, separators=(",", ":"),
                                       allow_nan=False))
    print(f"Wrote {len(clip_summaries)} clip observation files and {summary_path}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Offline posture diagnostic CLI")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    if not args.config.is_file():
        _die(f"config not found: {args.config}")
    try:
        _run(args.config, args.output_dir)
    except Exception as e:  # noqa: BLE001 - CLI boundary
        _die(str(e))


if __name__ == "__main__":
    main()
