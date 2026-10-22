from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from contracts.pose import PoseSequence
from movement.observations import AngleObservation, measure_frame
from movement.posture import ProjectionAxis, measure_torso_frame
from movement.rep_observations import RepWindow, measure_rep
from providers.pose.artifacts import read_pose_frames

ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
HEX64_RE = re.compile(r"^[0-9a-fA-F]{64}$")


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
    clips = data["clips"]
    if not isinstance(clips, list) or not clips:
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
        raise ValueError("positive_cross_sign must be exactly +1 or -1")
    if not isinstance(obj["version"], str) or not obj["version"]:
        raise ValueError("axis version must be a non-empty string")
    if not isinstance(obj["axis_id"], str) or not obj["axis_id"]:
        raise ValueError("axis_id must be a non-empty string")
    return ProjectionAxis(
        version=obj["version"],
        axis_id=obj["axis_id"],
        up_xy=(float(up[0]), float(up[1])),
        positive_cross_sign=sign,
    )


def _validate_rep(obj: Any, idx: int, side: str) -> RepWindow:
    if not isinstance(obj, dict):
        raise ValueError(f"rep {idx} must be an object")
    for k in ("rep_id", "start_s", "bottom_s", "end_s"):
        if k not in obj:
            raise ValueError(f"rep {idx} missing field: {k}")
    rid = obj["rep_id"]
    if not isinstance(rid, str) or not rid or not ID_RE.match(rid):
        raise ValueError(f"invalid rep_id: {rid!r}")
    vals = [obj["start_s"], obj["bottom_s"], obj["end_s"]]
    if not all(_num(v) for v in vals):
        raise ValueError(f"rep {idx} timing must be finite non-bool numbers")
    return RepWindow(
        rep_id=rid,
        side=side,  # type: ignore[arg-type]
        start_s=float(vals[0]),
        bottom_s=float(vals[1]),
        end_s=float(vals[2]),
    )


def _validate_clip(obj: Any, idx: int) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise ValueError(f"clip {idx} must be an object")
    required = (
        "id", "role", "pose_root", "source_sha256", "side", "width", "height",
        "axis", "view_id", "variant", "review_status", "annotation_origin",
        "uncertainty_s", "reps",
    )
    for k in required:
        if k not in obj:
            raise ValueError(f"clip {idx} missing field: {k}")
    cid = obj["id"]
    if not isinstance(cid, str) or not ID_RE.match(cid):
        raise ValueError(f"invalid clip id: {cid!r}")
    if obj["role"] not in ("reference", "user"):
        raise ValueError(f"invalid role: {obj['role']!r}")
    sha = obj["source_sha256"]
    if not isinstance(sha, str) or not HEX64_RE.match(sha):
        raise ValueError(f"invalid source_sha256: {sha!r}")
    if obj["side"] not in ("left", "right"):
        raise ValueError(f"invalid side: {obj['side']!r}")
    w, h = obj["width"], obj["height"]
    if any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in (w, h)):
        raise ValueError("width and height must be positive integers")
    unc = obj["uncertainty_s"]
    if not _num(unc) or unc < 0:
        raise ValueError("uncertainty_s must be finite non-negative")
    if obj["review_status"] != "visual_provisional":
        raise ValueError("review_status must be exactly 'visual_provisional'")
    for k in ("view_id", "variant", "annotation_origin"):
        if not isinstance(obj[k], str) or not obj[k]:
            raise ValueError(f"{k} must be a non-empty string")
    reps = obj["reps"]
    if not isinstance(reps, list) or not reps:
        raise ValueError("reps must be a non-empty list")
    parsed = [_validate_rep(r, i, obj["side"]) for i, r in enumerate(reps)]
    return {
        "id": cid,
        "role": obj["role"],
        "pose_root": Path(str(obj["pose_root"])),
        "source_sha256": sha.lower(),
        "side": obj["side"],
        "width": w,
        "height": h,
        "axis": _validate_axis(obj["axis"]),
        "view_id": obj["view_id"],
        "variant": obj["variant"],
        "review_status": obj["review_status"],
        "annotation_origin": obj["annotation_origin"],
        "uncertainty_s": float(unc),
        "reps": parsed,
    }


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
    """Read pose artifacts; verify pose bytes against the manifest key stem.

    The config ``source_sha256`` is declared source/video provenance only and
    is intentionally NOT compared to the JSONL pose artifact hash.
    """
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


def _measure_all(frames: list[Any], side: str, width: int, height: int,
                 axis: ProjectionAxis) -> list[AngleObservation]:
    obs: list[AngleObservation] = []
    for f in frames:
        obs.extend(measure_frame(f, side=side, width=width, height=height))  # type: ignore[arg-type]
        obs.append(measure_torso_frame(f, side=side, width=width, height=height, axis=axis))  # type: ignore[arg-type]
    obs.sort(key=lambda o: (o.timestamp_s, o.metric, o.space))
    return obs


def _profile(reps_components: list[dict[str, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    """Observed ranges over a REFERENCE clip's reps, per component key.

    Only finite non-bool numeric values count; units are kept separate
    (seconds durations are never pooled with degree components).
    """
    keys = sorted({k for comps in reps_components for k in comps})
    out: dict[str, dict[str, Any]] = {}
    for key in keys:
        vals = [c[key]["value"] for c in reps_components
                if key in c and _num(c[key]["value"])]
        unit = next((c[key]["unit"] for c in reps_components if key in c), None)
        out[key] = {
            "value_min": min(vals) if vals else None,
            "value_max": max(vals) if vals else None,
            "valid_count": len(vals),
            "unit": unit,
            "provisional": True,
        }
    return out


def _run(config_path: Path, output_dir: Path) -> Path:
    config_path = config_path.resolve()
    cfg = _load_config(config_path)  # validate config BEFORE any writing
    clips_cfg = [_validate_clip(c, i) for i, c in enumerate(cfg["clips"])]
    if len({c["id"] for c in clips_cfg}) != len(clips_cfg):
        raise ValueError("duplicate clip ids")
    outdir = _prepare_output_dir(output_dir)
    max_gap = float(cfg["max_gap_s"])

    inputs: set[Path] = {config_path}
    prepared = []
    for c in clips_cfg:
        root = c["pose_root"].resolve()
        seq, frames, pose_hash, clip_inputs = _read_clip(root)
        inputs |= clip_inputs
        obs = _measure_all(frames, c["side"], c["width"], c["height"], c["axis"])
        prepared.append((c, seq, obs, pose_hash))

    clip_reports = []
    for c, seq, obs, pose_hash in prepared:
        rep_reports = []
        for rep in c["reps"]:
            measured = measure_rep(obs, rep, max_gap_s=max_gap)
            components = {k: asdict(comp) for k, comp in measured.items()}
            rep_reports.append({
                "rep_id": rep.rep_id,
                "label": {"start_s": rep.start_s, "bottom_s": rep.bottom_s,
                          "end_s": rep.end_s},
                "components": components,
                "available_count": sum(1 for v in components.values()
                                       if v["value"] is not None),
            })
        comps_list = [r["components"] for r in rep_reports]
        clip_reports.append({
            "id": c["id"],
            "role": c["role"],
            "view_id": c["view_id"],
            "variant": c["variant"],
            "side": c["side"],
            "width": c["width"],
            "height": c["height"],
            "source_sha256": c["source_sha256"],
            "pose_artifact_hash": pose_hash,
            "source_pose_provenance": str(c["pose_root"]),
            "joint_mapping_version": seq.joint_mapping_version,
            "axis": asdict(c["axis"]),
            "review_status": c["review_status"],
            "annotation_origin": c["annotation_origin"],
            "uncertainty_s": c["uncertainty_s"],
            "reps": rep_reports,
            "profile_observed_ranges": (
                _profile(comps_list) if c["role"] == "reference" else None
            ),
        })

    summary = {
        "config_sha256": _sha256_file(config_path),
        "version": cfg["version"],
        "authoritative": False,
        "valid_technique_score": None,
        "endpoint": None,
        "endpoint_reason": "not_implemented",
        "clips": clip_reports,
    }
    summary_path = _safe_output_path(outdir, "measurements.json", inputs)
    summary_path.write_text(
        json.dumps(summary, sort_keys=True, separators=(",", ":"), allow_nan=False))
    print(f"Wrote measurements to {summary_path}")
    return summary_path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Offline rep measurement CLI using visual-provisional annotations.")
    parser.add_argument("--annotations", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    if not args.annotations.is_file():
        _die(f"annotations not found: {args.annotations}")
    try:
        _run(args.annotations, args.output_dir)
    except Exception as e:  # noqa: BLE001
        _die(str(e))


if __name__ == "__main__":
    main()
