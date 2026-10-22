#!/usr/bin/env python3
"""Render endpoint-review.html from a private endpoint-review JSON file.

Stdlib-only, offline, deterministic. Never writes outside --output-dir and
never modifies the input. Fails loudly on invalid input.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_IMG_RE = re.compile(r"^endpoint-points/[A-Za-z0-9_-]+\.png$")
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def _fail(msg: str) -> None:
    raise SystemExit(f"error: {msg}")


def _esc(x: object) -> str:
    return html.escape(str(x), quote=True)


def _num(x: object, name: str) -> float:
    if not isinstance(x, (int, float)) or isinstance(x, bool):
        _fail(f"{name} must be a number")
    return float(x)


def _measurement_html(m: object, name: str) -> str:
    if not isinstance(m, dict):
        _fail(f"{name} must be an object")
    value, reason, unit = m.get("value"), m.get("reason"), m.get("unit")
    if value is None:
        if not isinstance(reason, str) or not reason:
            _fail(f"{name}: missing value requires non-empty reason")
        return f'<span class="na">n/a ({_esc(reason)})</span>'
    return f"{_num(value, name):.2f} <small>{_esc(unit)}</small>"


def _validate_top(data: object) -> dict:
    if not isinstance(data, dict):
        _fail("top-level JSON must be an object")
    if data.get("authoritative") is not True and data.get("authoritative") is not False:
        _fail("authoritative must be boolean")
    if data.get("authoritative") is not False:
        _fail("authoritative must be false")
    if data.get("automatic_endpoint_localization") is not False:
        _fail("automatic_endpoint_localization must be false")
    if data.get("bar_contact") is not None:
        _fail("bar_contact must always be null")
    if not isinstance(data.get("records"), list):
        _fail("records must be a list")
    return data


def _card(rec: object) -> str:
    if not isinstance(rec, dict):
        _fail("each record must be an object")
    for key in ("rep_id", "clip_id"):
        v = rec.get(key)
        if not isinstance(v, str) or _ID_RE.fullmatch(v) is None:
            _fail(f"{key} must match {_ID_RE.pattern}")
    img = rec.get("image")
    if not isinstance(img, str) or _IMG_RE.fullmatch(img) is None:
        _fail("image must match endpoint-points/[A-Za-z0-9_-]+.png")
    sha = rec.get("source_sha256")
    if not isinstance(sha, str) or _HASH_RE.fullmatch(sha) is None:
        _fail("source_sha256 must be 64-char lowercase hex")
    if rec.get("score") is not None:
        _fail("score must always be null")
    if not isinstance(rec.get("score_reason"), str) or not rec["score_reason"]:
        _fail("score_reason must be a non-empty string")
    meas = rec.get("measurements")
    if not isinstance(meas, dict):
        _fail("measurements must be an object")
    contact = meas.get("bar_chest_contact")
    if not isinstance(contact, dict) or contact.get("value") is not None:
        _fail("bar_chest_contact.value must always be null")
    actual = _num(rec.get("actual_pts_s"), "actual_pts_s")
    requested = _num(rec.get("requested_pts_s"), "requested_pts_s")
    radius = rec.get("declared_radius_px")
    radius_html = "n/a" if radius is None else f"{_num(radius, 'declared_radius_px'):.2f} px"
    interval = rec.get("vertical_ratio_allowance_interval")
    if interval is None:
        interval_html = "n/a"
    else:
        if not isinstance(interval, list) or len(interval) != 2:
            _fail("vertical_ratio_allowance_interval must be [low, high] or null")
        lo, hi = (_num(interval[0], "interval low"), _num(interval[1], "interval high"))
        interval_html = f"[{lo:.2f}, {hi:.2f}]"
    vert = _measurement_html(meas.get("bar_chest_vertical_norm"), "bar_chest_vertical_norm")
    eucl = _measurement_html(meas.get("bar_chest_euclidean_norm"), "bar_chest_euclidean_norm")
    return f"""<section class="card">
<h2>Rep {_esc(rec['rep_id'])} <span class="badge">points rough &mdash; pending owner review</span></h2>
<p class="meta">clip <code>{_esc(rec['clip_id'])}</code> &middot; actual PTS <strong>{actual:.3f}s</strong> (requested {requested:.3f}s) &middot; source <code>{_esc(sha[:12])}&hellip;</code></p>
<img src="{_esc(img)}" alt="endpoint points for rep {_esc(rec['rep_id'])}" loading="lazy">
<ul class="legend"><li><span class="dot bar"></span>bar (red)</li><li><span class="dot chest"></span>chest (yellow)</li><li><span class="dot shoulder"></span>shoulder (cyan)</li><li><span class="dot hip"></span>hip (lime)</li></ul>
<dl>
<dt>vertical ratio (bar&ndash;chest, normalized)</dt><dd>{vert}</dd>
<dt>euclidean ratio (bar&ndash;chest, normalized)</dt><dd>{eucl}</dd>
<dt>declared radius</dt><dd>{radius_html}</dd>
<dt>declared vertical-ratio allowance interval</dt><dd>{interval_html}</dd>
<dt>bar&ndash;chest contact</dt><dd><span class="na">unavailable ({_esc(contact.get('reason', 'depth_unobserved'))})</span></dd>
<dt>score</dt><dd><span class="na">none ({_esc(rec['score_reason'])})</span></dd>
</dl>
</section>"""


CSS = """body{font-family:system-ui,sans-serif;margin:1.5rem;max-width:1100px;color:#1a1a1a}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:1rem}
.card{border:1px solid #ccc;border-radius:8px;padding:1rem}
.card img{max-width:100%;max-height:360px;height:auto;width:auto;display:block;margin:.5rem 0}
.badge{background:#e8830c;color:#fff;border-radius:4px;padding:.1rem .4rem;font-size:.75rem;vertical-align:middle}
.legend{list-style:none;padding:0;display:flex;gap:1rem;flex-wrap:wrap;font-size:.85rem}
.dot{display:inline-block;width:.7em;height:.7em;border-radius:50%;margin-right:.25em}
.bar{background:#d62728}.chest{background:#e6c200}.shoulder{background:#17becf}.hip{background:#7ed321}
dt{font-weight:600;margin-top:.4rem}dd{margin:0}.na{color:#666}.meta{font-size:.85rem;color:#444}
.notes{background:#f6f6f6;border-left:4px solid #999;padding:.6rem 1rem;font-size:.9rem}
"""

NOTES = """<div class="notes">
<p><strong>How to read this.</strong> The chest target is an approximate upper-chest
point chosen by the annotator; it is <em>not</em> an observed anatomical sternum or
contact point. The bar point marks the central bar attachment region, <em>not</em> a
wrist. The sampled frame may catch a hold rather than the deepest position, and depth
is unobserved in a single 2D image. Physical bar&ndash;chest contact is therefore
<strong>always unavailable</strong>, even when the 2D points overlap. Ratios are
normalized by the manually observed shoulder&ndash;hip segment and are comparable only
between view-compatible setups.</p>
<p><strong>How to correct a point.</strong> Report the rep ID and which point
(bar / chest / shoulder / hip) needs to move. There is no form, no saved data, and no
approval checkbox here &mdash; nothing is automatic; review is owner-personal prototype
work and no PT is required.</p>
<p>Related: <a href="t047.html">t047.html</a> &middot; <a href="t052c.html">t052c.html</a></p>
</div>"""


def render(data: dict) -> str:
    records = sorted(data["records"], key=lambda r: (not str(r.get("rep_id", "")).startswith("U"), str(r.get("rep_id", ""))))
    cards = "\n".join(_card(r) for r in records)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Endpoint review (v{_esc(data.get('version', '?'))})</title>
<style>{CSS}</style></head><body>
<h1>Endpoint point review</h1>
<p class="meta">status: {_esc(data.get('status', 'unknown'))} &middot; non-authoritative &middot; manual annotations only &middot; {_esc(data.get('measurement_source_note', ''))}</p>
<p>{_esc(data.get('point_definition', ''))}</p>
<p class="na">{_esc(data.get('uncertainty_note', ''))}</p>
{NOTES}
<div class="grid">
{cards}
</div>
</body></html>
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, help="path to private endpoint-review JSON")
    ap.add_argument("--output-dir", required=True, help="existing artifact directory")
    args = ap.parse_args(argv)
    src = Path(args.input)
    outdir = Path(args.output_dir)
    if not src.is_file():
        _fail(f"input not found: {src}")
    if not outdir.is_dir() or outdir.is_symlink():
        _fail("output-dir must be an existing real directory (no symlink)")
    if "artifacts" not in outdir.resolve().parts:
        _fail("output-dir must be under artifacts")
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _fail(f"cannot read/parse input: {e}")
    _validate_top(data)
    out = (outdir / "endpoint-review.html").resolve()
    if out.parent != outdir.resolve():
        _fail("resolved output escapes output-dir")
    if out == src.resolve():
        _fail("refusing to overwrite input")
    out.write_text(render(data), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
