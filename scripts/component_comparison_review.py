"""Offline diagnostic component comparison review CLI (T047).

Reads a measurements.json produced by scripts/rep_measurement_review.py and a
versioned review policy, compares USER CROP reps (user_roi_* only, deduped by
rep_id with exact-label uniqueness) against each reference clip's own
profile_observed_ranges (never pooled across sources), and writes
comparison.json, t047.html and comparison.md under an artifacts output dir.

All policy bands here are review-pending: no numeric scores, no approvals,
no aggregate. Descriptive deltas only.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from contracts.pose import PoseSequence
from scoring.components import (
    AGGREGATE_UNAVAILABLE_REASON,
    ComparisonContext,
    ReferenceBand,
    compare_component,
)

SCORED_METRICS: tuple[tuple[str, str], ...] = (
    ("M2", "torso_axis_angle/projected_2d/excursion"),
    ("M2_alt", "torso_axis_angle/projected_2d/pull_change"),  # alternative, never aggregated
    ("M3", "elbow_angle/estimated_3d/excursion"),
    ("M6", "elbow_angle/estimated_3d/end"),
    ("M4", "upper_arm_torso_angle/estimated_3d/bottom"),
)
UNSCORED_METRICS: tuple[tuple[str, str], ...] = (
    ("M1", "torso_axis_angle/projected_2d/start"),  # raw image-plane, not gravity calibrated
)
MEDIA = {
    "user": "media/user_lat.mp4",
    "qmotion_roi": "media/qmotion.mp4",
    "catalyst_roi": "media/catalyst.mp4",
    "imsa_right": "media/imsa-right.mp4",
}
POLICY_TOP_KEYS = {
    "version", "authoritative", "review_status", "reference_ids",
    "primary_reference_id", "per_reference", "metrics",
}
POLICY_REF_KEYS = {"compatibility", "compatibility_reviewer", "compatibility_version"}
POLICY_METRIC_KEYS = {"tolerance", "reviewer", "review_status"}


def _die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def _num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _nonempty(x: Any) -> bool:
    return isinstance(x, str) and bool(x.strip())


def load_policy(path: Path) -> dict[str, Any]:
    """Strictly validate the versioned pending policy BEFORE any writing."""
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("policy must be a JSON object")
    unknown = set(data) - POLICY_TOP_KEYS
    if unknown:
        raise ValueError(f"unknown policy keys: {sorted(unknown)}")
    missing = POLICY_TOP_KEYS - set(data)
    if missing:
        raise ValueError(f"missing policy keys: {sorted(missing)}")
    if not _nonempty(data["version"]):
        raise ValueError("policy version must be a non-empty string")
    if data["authoritative"] is not False:
        raise ValueError("policy authoritative must be false")
    if data["review_status"] != "pending":
        raise ValueError("policy review_status must be 'pending'")
    refs = data["reference_ids"]
    if not isinstance(refs, list) or not refs or not all(_nonempty(r) for r in refs):
        raise ValueError("reference_ids must be a non-empty list of strings")
    if len(set(refs)) != len(refs):
        raise ValueError("duplicate reference_ids")
    if data["primary_reference_id"] not in refs:
        raise ValueError("primary_reference_id must be one of reference_ids")
    per_ref = data["per_reference"]
    if not isinstance(per_ref, dict) or set(per_ref) != set(refs):
        raise ValueError("per_reference must cover exactly reference_ids")
    for rid, entry in per_ref.items():
        if not isinstance(entry, dict) or set(entry) != POLICY_REF_KEYS:
            raise ValueError(f"per_reference[{rid}] keys must be {sorted(POLICY_REF_KEYS)}")
        if entry["compatibility"] not in ("confirmed", "unknown", "incompatible"):
            raise ValueError(f"per_reference[{rid}].compatibility invalid")
        cr = entry["compatibility_reviewer"]
        if cr is not None and not _nonempty(cr):
            raise ValueError(f"per_reference[{rid}].compatibility_reviewer invalid")
        if entry["compatibility"] == "confirmed" and not _nonempty(cr):
            raise ValueError("confirmed compatibility requires an explicit reviewer")
        if not _nonempty(entry["compatibility_version"]):
            raise ValueError(f"per_reference[{rid}].compatibility_version invalid")
    metrics = data["metrics"]
    expected = {k for _, k in SCORED_METRICS}
    if not isinstance(metrics, dict) or set(metrics) != expected:
        raise ValueError(f"metrics must cover exactly {sorted(expected)}")
    for key, m in metrics.items():
        if not isinstance(m, dict) or set(m) != POLICY_METRIC_KEYS:
            raise ValueError(f"metrics[{key}] keys must be {sorted(POLICY_METRIC_KEYS)}")
        tol = m["tolerance"]
        if tol is not None and (not _num(tol) or tol <= 0):
            raise ValueError(f"metrics[{key}].tolerance must be null or a positive finite number")
        rev = m["reviewer"]
        if rev is not None and not _nonempty(rev):
            raise ValueError(f"metrics[{key}].reviewer invalid")
        if m["review_status"] not in ("pending", "owner_prototype", "qualified"):
            raise ValueError(f"metrics[{key}].review_status invalid")
        if m["review_status"] in ("owner_prototype", "qualified"):
            if not _nonempty(rev) or tol is None:
                raise ValueError(f"metrics[{key}] approved status requires reviewer and tolerance")
    return data


def load_measurements(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or not isinstance(data.get("clips"), list):
        raise ValueError("measurements must be an object with a clips list")
    if data.get("authoritative") is not False:
        raise ValueError("measurements must be non-authoritative")
    return data


def _guard_provenance(raw: Any) -> Path:
    if not _nonempty(raw):
        raise ValueError("clip missing source_pose_provenance")
    p = Path(raw).resolve()
    cwd = Path.cwd().resolve()
    if not (p.is_relative_to(cwd) or "artifacts" in p.parts):
        raise ValueError(f"source_pose_provenance escapes workspace/artifacts: {raw!r}")
    return p


def _provider_and_hash_check(clip: dict[str, Any]) -> str:
    """Read the clip's pose manifest to obtain the provider and verify the
    frames artifact key stem matches the header's pose_artifact_hash."""
    root = _guard_provenance(clip.get("source_pose_provenance"))
    manifest = root / "manifest.json"
    if not manifest.is_file():
        raise ValueError(f"missing manifest.json under {root}")
    seq = PoseSequence.model_validate_json(manifest.read_bytes())
    stem = Path(seq.frames_artifact_key).stem.lower()
    header = str(clip.get("pose_artifact_hash") or "").lower()
    if stem != header:
        raise ValueError(
            f"pose hash mismatch for clip {clip.get('id')!r}: manifest {stem} != header {header}")
    provider = getattr(seq, "provider", None)
    return provider if _nonempty(provider) else "unknown"


def select_user_crop_reps(clips: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select ONLY user crop rows (user_roi_*), dedup by rep_id, and require
    exact label uniqueness for any repeated rep_id."""
    seen: dict[str, dict[str, Any]] = {}
    for clip in clips:
        if clip.get("role") != "user" or not str(clip.get("id", "")).startswith("user_roi_"):
            continue
        for rep in clip.get("reps", []):
            rid = rep.get("rep_id")
            if not _nonempty(rid):
                raise ValueError("user crop rep missing rep_id")
            label = rep.get("label")
            if rid in seen:
                if seen[rid]["rep"].get("label") != label:
                    raise ValueError(f"rep {rid} label mismatch across user crop clips")
                continue
            seen[rid] = {"clip": clip, "rep": rep}
    if not seen:
        raise ValueError("no user crop reps (user_roi_*) found")
    return [seen[k] for k in sorted(seen)]


def select_references(clips: list[dict[str, Any]], policy: dict[str, Any]) -> list[dict[str, Any]]:
    refs = [c for c in clips if c.get("role") == "reference"]
    by_id = {c.get("id"): c for c in refs}
    out = []
    for rid in policy["reference_ids"]:
        clip = by_id.get(rid)
        if clip is None:
            raise ValueError(f"policy reference {rid!r} not present in measurements")
        if not isinstance(clip.get("profile_observed_ranges"), dict):
            raise ValueError(f"reference {rid!r} lacks profile_observed_ranges")
        out.append(clip)
    return out


def _unavailable(metric_id: str, key: str, comp: dict[str, Any] | None,
                 ref_id: str, reason: str) -> dict[str, Any]:
    value = comp.get("value") if comp else None
    creason = comp.get("reason") if comp else None
    return {
        "metric_id": metric_id, "component_key": key, "value": value,
        "reason": creason, "unit": (comp or {}).get("unit"),
        "observed_interval": None, "delta_low": None, "delta_high": None,
        "signed_deviation": None, "absolute_distance": None, "score": None,
        "score_kind": None, "score_reason": reason, "comparability": "unknown",
        "valid_technique_score": None,
        "policy_id": "component_comparison_policy:v1", "reference_id": ref_id,
    }


def compare_all(user_reps: list[dict[str, Any]], refs: list[dict[str, Any]],
                policy: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    comparisons: list[dict[str, Any]] = []
    unscored: list[dict[str, Any]] = []
    pversion = policy["version"]
    for ref in refs:
        rid = ref["id"]
        ref_policy = policy["per_reference"][rid]
        provider = _provider_and_hash_check(ref)
        profile = ref["profile_observed_ranges"]
        for entry in user_reps:
            rep, uclip = entry["rep"], entry["clip"]
            uprovider = _provider_and_hash_check(uclip)
            ctx = ComparisonContext(
                user_variant=str(uclip.get("variant") or "unknown"),
                reference_variant=str(ref.get("variant") or "unknown"),
                user_provider=uprovider,
                reference_provider=provider,
                user_mapping_version=str(uclip.get("joint_mapping_version") or "unknown"),
                reference_mapping_version=str(ref.get("joint_mapping_version") or "unknown"),
                user_view_id=str(uclip.get("view_id") or "unknown"),
                reference_view_id=str(ref.get("view_id") or "unknown"),
                compatibility=ref_policy["compatibility"],
                compatibility_reviewer=ref_policy["compatibility_reviewer"],
                compatibility_version=ref_policy["compatibility_version"],
            )
            for metric_id, key in SCORED_METRICS:
                comp = rep["components"].get(key)
                prof = profile.get(key)
                ref_id = f"{rid}:{pversion}:{metric_id}"
                if comp is None:
                    comparisons.append({**_unavailable(metric_id, key, None, ref_id,
                                                    "missing_user_component"),
                                        "rep_id": rep["rep_id"], "reference_clip": rid})
                    continue
                if not isinstance(prof, dict) or not _num(prof.get("value_min")) \
                        or not _num(prof.get("value_max")) or not _nonempty(prof.get("unit")):
                    # Preserve as unavailable; never fabricate null-bound bands.
                    comparisons.append({**_unavailable(metric_id, key, comp, ref_id,
                                                    "reference_band_unavailable"),
                                        "rep_id": rep["rep_id"], "reference_clip": rid})
                    continue
                mp = policy["metrics"][key]
                band = ReferenceBand(
                    metric_id=metric_id, unit=str(prof["unit"]),
                    lower=float(prof["value_min"]), upper=float(prof["value_max"]),
                    tolerance=mp["tolerance"], reviewer=mp["reviewer"],
                    review_status=mp["review_status"], source_id=rid,
                    version=pversion, authoritative=False,
                    view_id=ctx.reference_view_id, variant=ctx.reference_variant,
                    provider=provider,
                    mapping_version=ctx.reference_mapping_version,
                )
                value = comp.get("value")
                reason = comp.get("reason")
                if value is not None and not _num(value):
                    raise ValueError(f"non-finite user value for {key}")
                result = compare_component(value, reason, str(comp.get("unit") or ""),
                                           band, ctx)
                d = asdict(result)
                d["component_key"] = key
                d["rep_id"] = rep["rep_id"]
                d["reference_clip"] = rid
                comparisons.append(d)
            for metric_id, key in UNSCORED_METRICS:
                comp = rep["components"].get(key)
                unscored.append({
                    "metric_id": metric_id, "component_key": key,
                    "rep_id": rep["rep_id"], "reference_clip": rid,
                    "value": (comp or {}).get("value"),
                    "reason": (comp or {}).get("reason"),
                    "unit": (comp or {}).get("unit"),
                    "score": None,
                    "score_reason": "raw_image_plane_not_calibrated_unscored",
                })
    return comparisons, unscored


def _fmt(v: Any) -> str:
    return f"{float(v):.2f}" if _num(v) else "n/a"


def build_html(comparisons: list[dict[str, Any]], unscored: list[dict[str, Any]],
               policy: dict[str, Any], user_reps: list[dict[str, Any]],
               refs: list[dict[str, Any]]) -> str:
    primary = policy["primary_reference_id"]

    def score_cell(c: dict[str, Any]) -> str:
        if c["score"] is None:
            return f"n/a ({html.escape(str(c['score_reason'] or 'unavailable'))})"
        return f"{c['score']:.2f}"

    def row(c: dict[str, Any]) -> str:
        lo, hi = (c["observed_interval"] or (None, None))
        return (
            f"<tr><td>{html.escape(str(c.get('rep_id') or ''))}</td>"
            f"<td>{html.escape(c['metric_id'])}</td>"
            f"<td>{_fmt(c['value'])}</td>"
            f"<td>{_fmt(lo)} – {_fmt(hi)}</td>"
            f"<td>{_fmt(c['signed_deviation'])}</td>"
            f"<td>{score_cell(c)}</td></tr>"
        )

    prim_rows = "".join(row(c) for c in comparisons if c["reference_clip"] == primary)
    breakdown = []
    for ref in refs:
        rid = ref["id"]
        rows = "".join(row(c) for c in comparisons if c["reference_clip"] == rid)
        media = MEDIA.get(rid, "")
        breakdown.append(
            f"<h3>Source: {html.escape(rid)}</h3>"
            f"<p><a href=\"{html.escape(media)}\">video</a> · "
            f"<a href=\"t052c.html#user-reps\">seek UI (t052c)</a></p>"
            f"<table border=\"1\"><thead><tr><th>rep</th><th>metric</th><th>user value</th>"
            f"<th>source observed range</th><th>signed outside delta</th><th>score</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )
    un_rows = "".join(
        f"<tr><td>{html.escape(str(u['rep_id']))}</td><td>{html.escape(u['metric_id'])}</td>"
        f"<td>{_fmt(u['value'])}</td><td>{html.escape(str(u['score_reason']))}</td></tr>"
        for u in unscored
    )
    checklist = (
        "<h2>Owner review checklist</h2><ul>"
        "<li>Visible points and phase labels verified at event frames.</li>"
        "<li>Camera pairing / view compatibility confirmed per source.</li>"
        "<li>Proposed per-metric tolerances reviewed separately (none invented here).</li>"
        "<li>Missing: bar endpoint localization; baseline calibration; automated checks.</li>"
        "</ul>"
    )
    notes = (
        "<ul>"
        "<li>All bands are review-pending: scores are always n/a; deltas are descriptive only.</li>"
        "<li>Source observed ranges are newly computed per source, not validated norms.</li>"
        "<li>Large torso motion ranges may show positive deltas; that is not a physical error.</li>"
        "<li>M1 torso_start is raw image-plane, not gravity calibrated, and is unscored.</li>"
        "<li>Timing labels are retained for context and never compared as posture.</li>"
        "</ul>"
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Component comparison review — pending policy, no scores</title>
<style>
body{{font:14px system-ui,sans-serif;margin:18px;color:#202b37;background:#f8fafc;max-width:1100px}}
h1{{font-size:22px}}h2{{font-size:17px;margin:18px 0 8px}}h3{{font-size:14px;margin:14px 0 6px}}
p,li{{font-size:12px;line-height:1.4}}ul{{padding-left:20px;color:#475569}}
table{{display:block;max-width:100%;overflow-x:auto;border-collapse:collapse;font-size:12px;background:white;border:1px solid #dbe2ea}}
th,td{{padding:6px;border:1px solid #dbe2ea;text-align:right;white-space:nowrap}}th{{background:#eaf0f6}}
th:first-child,td:first-child{{text-align:left}}
</style></head>
<body>
<h1>Component comparison review — policy {html.escape(policy['version'])} (pending, no scores)</h1>
<p>User crop: <a href="{MEDIA['user']}">video</a>. Primary reference: {html.escape(primary)}.
No technique score is computed or implied.</p>
{notes}
<h2>Primary reference ({html.escape(primary)}) — per-rep metrics</h2>
<table border="1"><thead><tr><th>rep</th><th>metric</th><th>user value</th><th>source observed range</th><th>signed outside delta</th><th>score</th></tr></thead>
<tbody>{prim_rows}</tbody></table>
<h2>Breakdown by source</h2>
{''.join(breakdown)}
<h2>Unscored raw components (M1 torso_start, image-plane)</h2>
<table border="1"><thead><tr><th>rep</th><th>metric</th><th>value</th><th>status</th></tr></thead>
<tbody>{un_rows}</tbody></table>
{checklist}
</body></html>"""


def build_markdown(comparisons: list[dict[str, Any]], policy: dict[str, Any],
                   refs: list[dict[str, Any]]) -> str:
    lines = [
        "# Component comparison review — pending policy, no scores",
        "",
        f"Policy `{policy['version']}` (review pending, non-authoritative). "
        "All scores are n/a; deltas are descriptive only.",
        "",
        "## Comparisons",
        "",
        "| reference | rep | metric | user value | observed range | signed delta | score |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for c in comparisons:
        lo, hi = (c["observed_interval"] or (None, None))
        score = f"n/a ({c['score_reason']})" if c["score"] is None else f"{c['score']:.2f}"
        lines.append(
            f"| {c['reference_clip']} | {c.get('rep_id') or ''} | {c['metric_id']} | "
            f"{_fmt(c['value'])} | {_fmt(lo)} – {_fmt(hi)} | "
            f"{_fmt(c['signed_deviation'])} | {score} |"
        )
    lines += [
        "",
        "## Honest notes",
        "",
        "- Source observed ranges are newly computed per source, not validated norms.",
        "- Large torso motion ranges may show positive deltas; not a physical error.",
        "- M1 torso_start is raw image-plane, unscored; timing retained, never compared.",
        "- Missing: bar endpoint localization, baseline calibration, automated checks.",
        "- Owner checklist: visible points/phases, camera pairing, then proposed tolerances (none invented).",
        "",
    ]
    return "\n".join(lines)


def _prepare_outdir(outdir: Path) -> Path:
    if outdir.is_symlink():
        raise ValueError("output dir must not be a symlink")
    resolved = outdir.resolve()
    if "artifacts" not in resolved.parts:
        raise ValueError("output dir must live under an actual 'artifacts' path component")
    resolved.mkdir(parents=True, exist_ok=True)
    if resolved.is_symlink():
        raise ValueError("output dir resolves through a symlink escape")
    return resolved


def _safe_out(outdir: Path, name: str, inputs: set[Path]) -> Path:
    p = (outdir / name).resolve()
    if not p.is_relative_to(outdir):
        raise ValueError(f"output path escapes output dir: {name}")
    if p in inputs:
        raise ValueError(f"refusing to overwrite input file: {p}")
    if p.name in ("index.html", "t052c.html"):
        raise ValueError(f"refusing to overwrite protected file: {p.name}")
    return p


def run(measurements: Path, policy_path: Path, output_dir: Path) -> dict[str, Path]:
    measurements = measurements.resolve()
    policy_path = policy_path.resolve()
    policy = load_policy(policy_path)  # invalid config fails BEFORE any writing
    data = load_measurements(measurements)
    clips = data["clips"]
    user_reps = select_user_crop_reps(clips)
    refs = select_references(clips, policy)
    comparisons, unscored = compare_all(user_reps, refs, policy)
    outdir = _prepare_outdir(output_dir)
    inputs = {measurements, policy_path}
    for clip in clips:
        prov = clip.get("source_pose_provenance")
        if _nonempty(prov):
            inputs.add((_guard_provenance(prov) / "manifest.json"))
    summary = {
        "version": data.get("version"),
        "policy_version": policy["version"],
        "policy_review_status": policy["review_status"],
        "authoritative": False,
        "valid_technique_score": None,
        "aggregate_score": None,
        "aggregate_reason": AGGREGATE_UNAVAILABLE_REASON,
        "user_crop_rep_count": len(user_reps),
        "reference_count": len(refs),
        "comparison_count": len(comparisons),
        "scored_count": sum(1 for c in comparisons if c["score"] is not None),
        "unscored_raw": unscored,
        "comparisons": comparisons,
    }
    json_path = _safe_out(outdir, "comparison.json", inputs)
    html_path = _safe_out(outdir, "t047.html", inputs)
    md_path = _safe_out(outdir, "comparison.md", inputs)
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))
    html_path.write_text(build_html(comparisons, unscored, policy, user_reps, refs))
    md_path.write_text(build_markdown(comparisons, policy, refs))
    print(f"Wrote {json_path}")
    print(f"Wrote {html_path}")
    print(f"Wrote {md_path}")
    return {"json": json_path, "html": html_path, "md": md_path}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        description="Offline diagnostic component comparison review (pending policy).")
    ap.add_argument("--measurements", required=True, type=Path)
    ap.add_argument("--policy", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    args = ap.parse_args(argv)
    for p in (args.measurements, args.policy):
        if not p.is_file():
            _die(f"input not found: {p}")
    try:
        run(args.measurements, args.policy, args.output_dir)
    except Exception as e:  # noqa: BLE001
        _die(str(e))


if __name__ == "__main__":
    main()
