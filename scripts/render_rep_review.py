from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

MEDIA = {
    "qmotion_roi": "media/qmotion.mp4",
    "catalyst_roi": "media/catalyst.mp4",
    "imsa_right": "media/imsa-right.mp4",
}
USER_MEDIA = "media/user_lat.mp4"
ALIASES = [
    ("torso_start", "torso_axis_angle/projected_2d/start"),
    ("torso_bottom", "torso_axis_angle/projected_2d/bottom"),
    ("pull_change", "torso_axis_angle/projected_2d/pull_change"),
    ("torso_excursion", "torso_axis_angle/projected_2d/excursion"),
    ("elbow_min", "elbow_angle/estimated_3d/minimum"),
    ("elbow_max", "elbow_angle/estimated_3d/maximum"),
]
EXPECTED_KEYS = {k for _, k in ALIASES}


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def media_for(clip_id: str) -> str:
    if clip_id.startswith("user_"):
        return USER_MEDIA
    if clip_id in MEDIA:
        return MEDIA[clip_id]
    raise ValueError(f"no media mapping for clip id: {clip_id!r}")


def comp(rep: dict[str, Any], key: str) -> dict[str, Any] | None:
    c = rep["components"].get(key)
    return c if isinstance(c, dict) else None


def cell(rep: dict[str, Any], key: str) -> str:
    c = comp(rep, key)
    if c is None:
        return "<td>n/a (missing)</td>"
    v = c.get("value")
    if v is None:
        return f"<td>n/a ({html.escape(str(c.get('reason') or 'unavailable'))})</td>"
    return f"<td>{float(v):.2f}</td>"


def md_cell(rep: dict[str, Any], key: str) -> str:
    c = comp(rep, key)
    if c is None:
        return "n/a (missing)"
    v = c.get("value")
    if v is None:
        return f"n/a ({c.get('reason') or 'unavailable'})"
    return f"{float(v):.2f}"


def buttons(which: str, clip_id: str, label: dict[str, Any]) -> str:
    out = []
    for name in ("start_s", "bottom_s", "end_s"):
        t = float(label[name])
        out.append(
            f'<button data-which="{which}" data-clip="{html.escape(clip_id)}" '
            f'data-t="{t:.3f}" onclick="seekVideo(this.dataset.which,this.dataset.clip,'
            f'parseFloat(this.dataset.t))">{name[:-2]}</button>'
        )
    return " ".join(out)


def load_measurements(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or not isinstance(data.get("clips"), list):
        raise ValueError("measurements must be an object with a clips list")
    if data.get("authoritative") is not False:
        raise ValueError("measurements must be non-authoritative")
    return data


def collect_user_pairs(clips: list[dict[str, Any]]) -> list[dict[str, Any]]:
    originals = {c["id"]: c for c in clips if c.get("role") == "user" and not c["id"].startswith("user_roi_")}
    crops = {c["id"]: c for c in clips if c.get("role") == "user" and c["id"].startswith("user_roi_")}
    if not originals and not crops:
        raise ValueError("no user clips found; this trial requires a user-owned set")
    pairs: dict[str, dict[str, Any]] = {}
    for kind, group in (("original", originals), ("crop", crops)):
        for clip in group.values():
            for rep in clip["reps"]:
                keys = set(rep["components"])
                if len(keys) != 32:
                    raise ValueError("expected exactly 32 generated components")
                if rep["available_count"] != sum(v["value"] is not None for v in rep["components"].values()):
                    raise ValueError("available_count does not match component values")
                missing = EXPECTED_KEYS - keys
                if missing:
                    raise ValueError(f"{clip['id']}/{rep['rep_id']} missing components: {sorted(missing)}")
                slot = pairs.setdefault(rep["rep_id"], {})
                if kind in slot:
                    raise ValueError(f"duplicate {kind} rep {rep['rep_id']}")
                slot[kind] = {"clip": clip, "rep": rep}
    out = []
    for rid in sorted(pairs, key=lambda r: int("".join(ch for ch in r if ch.isdigit()) or 0)):
        p = pairs[rid]
        if "original" not in p or "crop" not in p:
            raise ValueError(f"rep {rid} lacks original/crop pair")
        if p["original"]["rep"]["label"] != p["crop"]["rep"]["label"]:
            raise ValueError(f"rep {rid} label mismatch between original and crop")
        out.append({"rep_id": rid, **p})
    if not out:
        raise ValueError("no paired user reps found")
    return out


def reference_clips(clips: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs = [c for c in clips if c.get("role") == "reference"]
    for c in refs:
        if not isinstance(c.get("profile_observed_ranges"), dict):
            raise ValueError(f"reference clip {c['id']} lacks profile_observed_ranges")
    return refs


def build_html(pairs: list[dict[str, Any]], refs: list[dict[str, Any]], version: str) -> str:
    user_rows = []
    for p in pairs:
        rep, clip = p["crop"]["rep"], p["crop"]["clip"]
        label = rep["label"]
        cols = "".join(cell(rep, k) for _, k in ALIASES)
        user_rows.append(
            f"<tr><td>{html.escape(p['rep_id'])}</td>"
            f"<td>{label['start_s']:.2f}–{label['end_s']:.2f}s</td>{cols}"
            f"<td>{rep['available_count']}</td>"
            f"<td>{buttons('user', clip['id'], label)}</td></tr>"
        )
    ref_rows = []
    for clip in refs:
        for rep in clip["reps"]:
            label = rep["label"]
            cols = "".join(cell(rep, k) for _, k in ALIASES)
            ref_rows.append(
                f"<tr><td>{html.escape(clip['id'])}</td><td>{html.escape(rep['rep_id'])}</td>"
                f"<td>{label['start_s']:.2f}–{label['end_s']:.2f}s</td>{cols}"
                f"<td>{rep['available_count']}</td>"
                f"<td>{buttons('ref', clip['id'], label)}</td></tr>"
            )
    cov_rows = []
    for p in pairs:
        o, c = p["original"]["rep"], p["crop"]["rep"]
        exc = ALIASES[3][1]
        def excv(r: dict[str, Any]) -> str:
            v = comp(r, exc)
            return f"{v['value']:.2f}" if v and v.get("value") is not None else "n/a"
        cov_rows.append(
            f"<tr><td>{html.escape(p['rep_id'])}</td><td>{o['available_count']}</td>"
            f"<td>{c['available_count']}</td><td>{excv(o)}</td><td>{excv(c)}</td></tr>"
        )
    heads = "".join(f"<th>{html.escape(a)}</th>" for a, _ in ALIASES)
    notes = (
        "<ul>"
        "<li>Model-assisted labels checked at 3 event frames; not expert ground truth.</li>"
        "<li>±0.25s reference / ±0.5s user timing allowances are tolerances, not measured accuracy.</li>"
        "<li>Torso values are projected 2D degrees; elbow values are model-estimated 3D joint degrees. Bar endpoint localization is unimplemented.</li>"
        "<li>Reference ranges are source-specific observations from different cameras; "
        "unvalidated, not a physical error or technique score.</li>"
        "</ul>"
    )
    js = (
        "const MEDIA=" + json.dumps({**MEDIA, "user": USER_MEDIA}) + ";\n"
        "function mediaFor(id){return id.startsWith('user_')?MEDIA.user:MEDIA[id];}\n"
        "function seekVideo(which,clipId,t){\n"
        " const v=document.getElementById(which==='user'?'user-video':'ref-video');\n"
        " const src=mediaFor(clipId); if(!src)return;\n"
        " const doSeek=()=>{v.pause();const d=isFinite(v.duration)?v.duration:t;"
        "v.currentTime=Math.max(0,Math.min(t,d));};\n"
        " if(!v.currentSrc.endsWith(src)){v.src=src;"
        "v.addEventListener('loadedmetadata',doSeek,{once:true});}"
        " else if(v.readyState>=1){doSeek();}"
        " else{v.addEventListener('loadedmetadata',doSeek,{once:true});}\n"
        "}\n"
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Provisional rep measurements — no technique score</title>
<style>
body{{font:14px system-ui,sans-serif;margin:18px;color:#202b37;background:#f8fafc;max-width:1200px}}
h1{{font-size:23px;line-height:1.2}}h2{{font-size:17px;margin:18px 0 10px}}
p,li{{font-size:12px;line-height:1.4}}ul{{padding-left:20px;color:#475569}}
.videos{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}
.videos h2{{margin:6px 0}}video{{width:100%;height:220px;object-fit:contain;background:#111827;border-radius:8px}}
table{{display:block;max-width:100%;overflow-x:auto;border-collapse:collapse;font-size:12px;background:white;border:1px solid #dbe2ea}}
th,td{{padding:7px;border:1px solid #dbe2ea;text-align:right;white-space:nowrap}}th{{background:#eaf0f6}}
th:first-child,td:first-child{{text-align:left}}button{{padding:6px;margin:2px;border:1px solid #a8b5c7;border-radius:5px;background:#f1f5f9;cursor:pointer}}
</style></head>
<body>
<h1>Provisional rep measurements — no technique score</h1>
<p>Version {html.escape(version)}. Videos stay on this computer and load from the local review server.</p>
{notes}
<div class="videos">
<section><h2>Your set</h2><video id="user-video" controls muted src="{USER_MEDIA}"></video></section>
<section><h2>Reference</h2><video id="ref-video" controls muted src="{MEDIA['qmotion_roi']}"></video></section>
</div>
<h2>User reps (crop measurements; original video playback)</h2>
<table id="user-reps" border="1"><thead><tr><th>rep</th><th>interval</th>{heads}<th>available</th><th>seek</th></tr></thead>
<tbody>{''.join(user_rows)}</tbody></table>
<h2>Reference reps</h2>
<table id="reference-reps" border="1"><thead><tr><th>clip</th><th>rep</th><th>interval</th>{heads}<th>available</th><th>seek</th></tr></thead>
<tbody>{''.join(ref_rows)}</tbody></table>
<h2>Original vs crop coverage (paired physical reps)</h2>
<table id="coverage" border="1"><thead><tr><th>rep</th><th>original available</th><th>crop available</th><th>original torso_excursion</th><th>crop torso_excursion</th></tr></thead>
<tbody>{''.join(cov_rows)}</tbody></table>
<script>{js}</script>
</body></html>"""


def build_markdown(pairs: list[dict[str, Any]], refs: list[dict[str, Any]], version: str) -> str:
    lines = [
        "# Provisional rep measurements — no technique score",
        "",
        f"Version `{version}`. This report covers the measurement stage only; it is **not** a validated posture or technique score.",
        "",
        "## User reps (crop measurements; original video playback)",
        "",
        "| rep | interval (s) | " + " | ".join(a for a, _ in ALIASES) + " | available |",
        "| --- | --- | " + " | ".join("---" for _ in ALIASES) + " | --- |",
    ]
    for p in pairs:
        rep = p["crop"]["rep"]
        label = rep["label"]
        cols = " | ".join(md_cell(rep, k) for _, k in ALIASES)
        lines.append(f"| {p['rep_id']} | {label['start_s']:.2f}–{label['end_s']:.2f} | {cols} | {rep['available_count']} |")
    lines += ["", "## Measured component availability (original vs crop, paired physical reps)", "",
              "| rep | original available | crop available |", "| --- | --- | --- |"]
    for p in pairs:
        lines.append(f"| {p['rep_id']} | {p['original']['rep']['available_count']} | {p['crop']['rep']['available_count']} |")
    lines += ["", "## Reference observed ranges (per source clip, phase-specific, provisional)", ""]
    for clip in refs:
        lines.append(f"### {clip['id']} (view `{clip['view_id']}`)")
        lines.append("")
        lines.append("| component | min | max | valid_count | unit |")
        lines.append("| --- | --- | --- | --- | --- |")
        for key, prof in sorted(clip["profile_observed_ranges"].items()):
            mn, mx = prof.get("value_min"), prof.get("value_max")
            def f(v: Any) -> str:
                return f"{v:.2f}" if isinstance(v, (int, float)) else "n/a"
            lines.append(f"| {key} | {f(mn)} | {f(mx)} | {prof.get('valid_count')} | {prof.get('unit') or ''} |")
        lines.append("")
    lines += [
        "## Honest notes",
        "",
        "- Model-assisted labels checked at 3 event frames; not expert ground truth.",
        "- ±0.25s reference / ±0.5s user timing allowances are tolerances, not measured accuracy.",
        "- Torso values are projected 2D degrees; elbow values are model-estimated 3D joint degrees. Bar endpoint localization is unimplemented.",
        "- Reference ranges are source-specific observations from different cameras; unvalidated, not a physical error or technique score.",
        "",
        "## Remaining work",
        "",
        "- Bar endpoint / bar localization.",
        "- Phase-label review with uncertainty.",
        "- View-compatible tolerances with versioned fixtures before any aggregate score.",
        "",
        "No universal safe-form claim and no ranking algorithm is made or implied.",
        "",
    ]
    return "\n".join(lines)


def build_results(pairs: list[dict[str, Any]], refs: list[dict[str, Any]], data: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": data.get("version"),
        "authoritative": False,
        "valid_technique_score": None,
        "user_physical_rep_count": len(pairs),
        "user_original_complete": sum(1 for p in pairs if p["original"]["rep"]["available_count"] == len(p["original"]["rep"]["components"])),
        "user_crop_complete": sum(1 for p in pairs if p["crop"]["rep"]["available_count"] == len(p["crop"]["rep"]["components"])),
        "reference_clip_count": len(refs),
        "reference_rep_count": sum(len(c["reps"]) for c in refs),
        "pairs": [
            {
                "rep_id": p["rep_id"],
                "label": p["crop"]["rep"]["label"],
                "original_available": p["original"]["rep"]["available_count"],
                "crop_available": p["crop"]["rep"]["available_count"],
            }
            for p in pairs
        ],
    }


def build_evidence(pairs: list[dict[str, Any]], refs: list[dict[str, Any]], data: dict[str, Any]) -> dict[str, Any]:
    def slim(rep: dict[str, Any]) -> dict[str, Any]:
        return {
            "rep_id": rep["rep_id"],
            "label": rep["label"],
            "available_count": rep["available_count"],
            "components": {
                k: {"value": v.get("value"), "unit": v.get("unit"),
                    "reason": v.get("reason"), "actual_pts_s": v.get("actual_pts_s")}
                for k, v in rep["components"].items()
            },
        }
    def prov(clip: dict[str, Any]) -> dict[str, Any]:
        return {
            "clip_id": clip["id"],
            "view_id": clip.get("view_id"),
            "variant": clip.get("variant"),
            "axis": clip.get("axis"),
            "source_sha256": clip.get("source_sha256"),
            "pose_artifact_hash": clip.get("pose_artifact_hash"),
            "source_pose_provenance": clip.get("source_pose_provenance"),
        }
    return {
        "version": data.get("version"),
        "authoritative": False,
        "valid_technique_score": None,
        "user_pairs": [
            {
                "rep_id": p["rep_id"],
                "original": {"provenance": prov(p["original"]["clip"]), "rep": slim(p["original"]["rep"])},
                "crop": {"provenance": prov(p["crop"]["clip"]), "rep": slim(p["crop"]["rep"])},
            }
            for p in pairs
        ],
        "references": [
            {"provenance": prov(c), "profile_observed_ranges": c["profile_observed_ranges"],
             "rep_count": len(c["reps"])}
            for c in refs
        ],
        "counts": {
            "user_physical_reps": len(pairs),
            "reference_clips": len(refs),
            "reference_reps": sum(len(c["reps"]) for c in refs),
        },
    }


def safe_out(path: Path, inputs: set[Path]) -> Path:
    p = path.resolve()
    if p in inputs:
        raise ValueError(f"refusing to overwrite input file: {p}")
    if p.name == "index.html":
        raise ValueError("refusing to overwrite index.html")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def run(measurements: Path, output_dir: Path, report: Path, evidence: Path) -> None:
    measurements = measurements.resolve()
    data = load_measurements(measurements)
    clips = data["clips"]
    pairs = collect_user_pairs(clips)
    refs = reference_clips(clips)
    version = str(data.get("version") or "unknown")
    inputs = {measurements}
    outdir = output_dir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    html_path = safe_out(outdir / "t052c.html", inputs)
    json_path = safe_out(outdir / "t052c-results.json", inputs)
    report_path = safe_out(report, inputs)
    evidence_path = safe_out(evidence, inputs)
    html_path.write_text(build_html(pairs, refs, version))
    json_path.write_text(json.dumps(build_results(pairs, refs, data), indent=2, sort_keys=True, allow_nan=False))
    report_path.write_text(build_markdown(pairs, refs, version))
    evidence_path.write_text(json.dumps(build_evidence(pairs, refs, data), indent=2, sort_keys=True, allow_nan=False))
    print(f"Wrote {html_path}")
    print(f"Wrote {json_path}")
    print(f"Wrote {report_path}")
    print(f"Wrote {evidence_path}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Render private provisional rep-measurement review artifacts.")
    ap.add_argument("--measurements", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--report", required=True, type=Path)
    ap.add_argument("--evidence", required=True, type=Path)
    args = ap.parse_args(argv)
    if not args.measurements.is_file():
        die(f"measurements not found: {args.measurements}")
    try:
        run(args.measurements, args.output_dir, args.report, args.evidence)
    except Exception as e:  # noqa: BLE001
        die(str(e))


if __name__ == "__main__":
    main()
