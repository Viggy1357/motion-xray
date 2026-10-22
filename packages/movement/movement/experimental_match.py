"""Experimental reference-match estimate for lat pulldown (schema 0.3).

NOT a technique score, NOT an accuracy measure, NOT owner-reviewed. Pure,
deterministic, local arithmetic over an existing PrototypeAnalysisResult plus
the versioned package config ``lat-experimental-match-v1.json``. No I/O beyond
that config, no LLM, no mutation of the input report. The 30-degree
normalization is an explicit unreviewed engineering hypothesis, never a
validated tolerance. Reference bands are observed historical min/max from the
fixed primary source (QMotion); no pooling or best-of selection.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, cast

from contracts.product import PrototypeAnalysisResult

CONFIG_VERSION = "lat-experimental-match-v1"
_REVIEW_STATUS = "unreviewed_algorithm_proposal"
_PRIMARY_ID = "qmotion_roi"
_VARIANT = "cable_seated_bilateral"
_NORM_BASIS = "engineering_proposal_not_calibrated_tolerance"
_BAND_BASIS = "observed_min_max_not_tolerance"
_FORMULA = "distance=max(L-x,0,x-U);resemblance=100*max(0,1-distance/normalization)"
_AGGREGATION = "arm_rom_metric_mean_then_equal_family_mean_per_cycle_then_cycle_mean"
_CALIBRATION = "uncalibrated_engineering_hypothesis_not_validated"
_BASE_REASONS = ["unreviewed_view", "unreviewed_normalization", "partial_metric_scope"]
_EXPECTED_FAMILIES: dict[str, list[str]] = {
    "torso_dynamic": ["torso_axis_angle/projected_2d/excursion"],
    "arm_rom": ["elbow_angle/estimated_3d/excursion", "elbow_angle/estimated_3d/end"],
    "shoulder_drive": ["upper_arm_torso_angle/estimated_3d/bottom"],
}
_ALL_KEYS = [k for members in _EXPECTED_FAMILIES.values() for k in members]
_OMITTED = ["torso_start", "bar_endpoint"]


def _is_num(v: object) -> bool:
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def _validate_config(data: Any) -> dict:
    if not isinstance(data, dict):
        raise ValueError("experimental config must be a JSON object")
    if data.get("version") != CONFIG_VERSION:
        raise ValueError(f"unknown experimental config version: {data.get('version')!r}")
    if data.get("authoritative") is not False:
        raise ValueError("experimental config must be non-authoritative")
    if data.get("review_status") != _REVIEW_STATUS:
        raise ValueError("experimental config review_status must be unreviewed_algorithm_proposal")
    if data.get("normalization_basis") != _NORM_BASIS:
        raise ValueError("normalization_basis must be engineering_proposal_not_calibrated_tolerance")
    norm = data.get("normalization_degrees")
    if not _is_num(norm) or cast(float, norm) <= 0:
        raise ValueError("normalization_degrees must be a positive finite non-bool number")
    cov = data.get("coverage_threshold")
    if not _is_num(cov) or not (0.0 < cast(float, cov) <= 1.0):
        raise ValueError("coverage_threshold must be finite non-bool in (0, 1]")
    if data.get("primary_reference_id") != _PRIMARY_ID:
        raise ValueError("primary_reference_id must be the fixed qmotion_roi source")
    if data.get("family_groups") != _EXPECTED_FAMILIES:
        raise ValueError("family_groups must be exactly the 3 expected families / 4 metric keys")
    if data.get("omitted_components") != _OMITTED:
        raise ValueError("omitted_components must be exactly torso_start and bar_endpoint")
    refs = data.get("references")
    if not isinstance(refs, list) or not refs or not all(isinstance(r, dict) for r in refs):
        raise ValueError("references must be a nonempty list of objects")
    ids = [r.get("id") for r in refs]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("reference ids must be unique nonempty strings")
    if _PRIMARY_ID not in ids:
        raise ValueError("primary reference qmotion_roi must be configured")
    for r in refs:
        rc = r.get("rep_count")
        if isinstance(rc, bool) or not isinstance(rc, int) or rc <= 0:
            raise ValueError(f"reference {r.get('id')!r} rep_count must be a positive integer")
        if not isinstance(r.get("view_id"), str) or not r["view_id"]:
            raise ValueError(f"reference {r.get('id')!r} view_id must be nonempty")
        bands = r.get("bands")
        if not isinstance(bands, dict) or set(bands) != set(_ALL_KEYS):
            raise ValueError(f"reference {r.get('id')!r} bands must cover exactly the family metrics")
        for k in _ALL_KEYS:
            b = bands[k]
            if not isinstance(b, dict) or b.get("unit") != "degrees":
                raise ValueError(f"band {k!r} must use unit degrees")
            if b.get("provisional") is not True:
                raise ValueError(f"band {k!r} must be provisional")
            vc = b.get("valid_count")
            if isinstance(vc, bool) or not isinstance(vc, int) or vc <= 0 or vc > rc:
                raise ValueError(f"band {k!r} valid_count must be a positive integer <= rep_count")
            lo, hi = b.get("value_min"), b.get("value_max")
            if not _is_num(lo) or not _is_num(hi) or cast(float, lo) > cast(float, hi):
                raise ValueError(f"band {k!r} bounds must be finite with min <= max")
    return data


def _load_config() -> dict:
    from pathlib import Path

    path = Path(__file__).parent / "configs" / f"{CONFIG_VERSION}.json"
    return _validate_config(json.loads(path.read_text(encoding="utf-8")))


def _sha256(data: dict) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _resemblance(x: float, lo: float, hi: float, norm: float) -> tuple[float, float]:
    distance = max(lo - x, 0.0, x - hi)
    deviation = (x - lo) if x < lo else ((x - hi) if x > hi else 0.0)
    score = 100.0 * max(0.0, 1.0 - distance / norm)
    if not (math.isfinite(score) and math.isfinite(deviation)):
        raise ValueError("non-finite experimental match output")
    return score, deviation


def apply_experimental_match(report: PrototypeAnalysisResult) -> PrototypeAnalysisResult:
    """Return a new validated report with the experimental estimate applied.

    Non-lat reports pass through unchanged. The input report is never mutated.
    """
    if report.exercise != "lat_pulldown":
        return report
    cfg = _load_config()
    norm = float(cast(float, cfg["normalization_degrees"]))
    cov_min = float(cast(float, cfg["coverage_threshold"]))
    families: dict[str, list[str]] = cfg["family_groups"]
    ref = next(r for r in cfg["references"] if r["id"] == _PRIMARY_ID)
    bands = ref["bands"]

    updates: dict[tuple[str, str, str], tuple[tuple[float, float], float]] = {}
    cycle_scores: list[float] = []
    excluded = 0
    comparable = report.variant == _VARIANT
    if comparable:
        for rep in report.reps:
            if rep.completion_status.value != "completed":
                continue
            if rep.side is None:
                excluded += 1
                continue
            side = rep.side
            candidates = [m for m in report.metrics if m.rep_id == rep.id]
            picked: dict[str, float] = {}
            ok = True
            for key in _ALL_KEYS:
                matches = [m for m in candidates if m.id == key and m.side == side]
                if len(matches) != 1:
                    ok = False
                    break
                m = matches[0]
                cov = m.coverage
                if (
                    m.unit != "degrees"
                    or m.status != "observed"
                    or m.value is None
                    or m.dimensionality != key.split("/")[1]
                    or cov is None
                    or cov < cov_min
                ):
                    ok = False
                    break
                picked[key] = m.value
            if not ok:
                excluded += 1
                continue
            fam_scores = []
            for members in families.values():
                vals = []
                for key in members:
                    b = bands[key]
                    lo, hi = float(b["value_min"]), float(b["value_max"])
                    score, dev = _resemblance(picked[key], lo, hi, norm)
                    vals.append(score)
                    updates[(rep.id, key, side)] = ((lo, hi), dev)
                fam_scores.append(sum(vals) / len(vals))
            cycle_scores.append(sum(fam_scores) / len(fam_scores))

    data = report.model_dump(mode="python")
    for row in data["metrics"]:
        hit = updates.get((row["rep_id"], row["id"], row["side"]))
        if hit is not None:
            row["reference_interval"], row["deviation"] = hit

    reasons = list(_BASE_REASONS)
    if excluded:
        reasons.append("excluded_cycles")
    assessment: dict[str, Any] = {
        "policy_version": cfg["version"],
        "included_components": list(families) if cycle_scores else [],
        "omitted_components": list(cfg["omitted_components"]),
    }
    if cycle_scores:
        assessment["status"] = "partial"  # partial even at 100: omitted scope, unreviewed view
        assessment["estimated_match"] = sum(cycle_scores) / len(cycle_scores)
        assessment["missing_reasons"] = reasons
    else:
        assessment["status"] = "unavailable"
        assessment["estimated_match"] = None
        extra = [] if comparable else ["variant_not_comparable"]
        assessment["missing_reasons"] = reasons + extra + ["no_eligible_cycles"]
    data["prototype_assessment"] = assessment
    base_recipe = report.recipe_version.removesuffix("+matchv1")
    data["recipe_version"] = f"{base_recipe}+matchv1"
    data["provenance"] = {
        **data["provenance"],
        "experimental_policy_version": cfg["version"],
        "experimental_policy_sha256": _sha256(cfg),
        "reference_id": ref["id"],
        "reference_view_id": ref["view_id"],
        "reference_review_status": cfg["review_status"],
        "reference_rep_count": str(ref["rep_count"]),
        "reference_band_basis": _BAND_BASIS,
        "match_formula": _FORMULA,
        "match_normalization_degrees": repr(norm),
        "match_coverage_threshold": repr(cov_min),
        "match_aggregation": _AGGREGATION,
        "matched_cycles": str(len(cycle_scores)),
        "omitted_cycle_count": str(excluded),
        "calibration_status": _CALIBRATION,
    }
    return PrototypeAnalysisResult.model_validate(data)
