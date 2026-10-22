"""Generic exercise runtime (schema 0.3) and reference-band assessment.

Pure arithmetic over pose artifacts for the three measured profiles
(dumbbell_curl, squat, incline_chest_press). No I/O except package-owned
versioned configs; no LLM; no fabricated numbers. Per-window components are
summarized by this module's own PROFILE-groups summarizer (nearest observed
sample within max_gap for start/bottom/end; min/max/excursion over the actual
window; explicit null+reason; coverage = valid samples / window frames). The
squat profile summarizes knee/hip groups directly; a knee is never relabeled
as an elbow. Reference bands come only from actual measured reference cycles
(see scripts/calibrate_exercises.py); when the baseline config is missing or
invalid the assessment is unavailable while measurements are still returned.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal, Sequence, cast

from contracts.analysis import CoachingResult, Metric, Rep
from contracts.enums import CoachingStatus, CompletionStatus
from contracts.pose import PoseFrame
from contracts.product import (
    ExerciseId,
    PrototypeAnalysisResult,
    PrototypeAssessment,
    ReportQuality,
)
from movement import profile_curl, profile_press, profile_squat
from movement.observations import AngleObservation
from movement.review_cycles import ReviewConfig, find_cycles
from movement.runtime_lat import _config_sha256, _is_num, _validate_inputs

Side = Literal["left", "right"]
_SIDES: tuple[Side, Side] = ("left", "right")
_PROFILES = {
    "dumbbell_curl": profile_curl,
    "squat": profile_squat,
    "incline_chest_press": profile_press,
}
_ARM_KEYS = [
    "torso_axis_angle/projected_2d/excursion",
    "elbow_angle/estimated_3d/excursion",
    "elbow_angle/estimated_3d/end",
    "upper_arm_torso_angle/estimated_3d/bottom",
]
COMPARISON_KEYS: dict[str, list[str]] = {
    "dumbbell_curl": list(_ARM_KEYS),
    "incline_chest_press": list(_ARM_KEYS),
    "squat": [
        "knee_angle/estimated_3d/bottom",
        "knee_angle/estimated_3d/excursion",
        "hip_angle/estimated_3d/bottom",
        "torso_axis_angle/projected_2d/excursion",
    ],
}
_NORMALIZATION_DEG = 30.0
_MIN_COVERAGE = 0.8
_MIN_REFERENCE_CYCLES = 2
_MIN_USER_CYCLES = 1
_AGGREGATION = "equal_metric_mean_per_cycle_then_cycle_mean"
_BAND_BASIS = "observed_min_max_not_tolerance"
_BASELINE_PATH = Path(__file__).parent / "configs" / "exercise-reference-bands-v1.json"


def _groups(profile: dict) -> list[tuple[str, str, str]]:
    """Normalize nested (metric->space->{unit}) and flat (metric/space->{unit})."""
    out: list[tuple[str, str, str]] = []
    for key, val in profile["metrics"].items():
        if "/" in key:
            metric, space = key.split("/", 1)
            out.append((metric, space, val["unit"]))
        else:
            for space, spec in val.items():
                out.append((key, space, spec["unit"]))
    return out


def _load_profile_config(profile: dict) -> dict:
    path = Path(__file__).parent / "configs" / f"{profile['version']}.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data == profile, f"profile config {path.name} diverges from module PROFILE"
    return profile


def _observe_profile(mod, frame: PoseFrame, side: Side, width: int, height: int) -> list[AngleObservation]:
    return mod.observe(frame, side=side, width=width, height=height)


def _group_coverage(obs: Sequence[AngleObservation], groups, total: int) -> dict:
    if total == 0:
        return {}
    return {
        f"{m}/{s}": sum(1 for o in obs if o.metric == m and o.space == s and o.value is not None) / total
        for m, s, _ in groups
    }


def _nearest_sample(
    series: Sequence[AngleObservation], t: float, max_gap_s: float
) -> tuple[float | None, str | None]:
    """Nearest observed sample to ``t`` within max_gap_s; tie picks earlier PTS.

    An invalid nearest sample propagates its own reason; no search for a
    farther valid sample is ever performed.
    """
    best: AngleObservation | None = None
    best_d: float | None = None
    for s in series:
        d = abs(s.timestamp_s - t)
        if d > max_gap_s:
            continue
        if best is None or best_d is None or d < best_d or (d == best_d and s.timestamp_s < best.timestamp_s):
            best, best_d = s, d
    if best is None:
        return None, "no_sample_in_tolerance"
    if best.value is None:
        return None, (best.reason or "invalid_sample")
    return best.value, None


def summarize_profile_window(
    obs: Sequence[AngleObservation],
    groups: Sequence[tuple[str, str, str]],
    *,
    side: Side,
    start_s: float,
    bottom_s: float,
    end_s: float,
    max_gap_s: float,
    window_frames: int,
) -> dict[str, tuple[float | None, str | None, str, float]]:
    """Summarize every PROFILE group over one actual rep window.

    For each (metric, space, unit) group emits start/bottom/end (nearest
    observed sample within max_gap_s), min/max/excursion=max-min over valid
    samples inside the actual window. Missing values are None with an
    explicit reason; coverage is valid samples / window frames. Returns
    ``key -> (value, reason, unit, coverage)``.
    """
    comps: dict[str, tuple[float | None, str | None, str, float]] = {}
    for metric, space, unit in groups:
        series = sorted(
            (
                o for o in obs
                if o.metric == metric and o.space == space and o.side == side
                and start_s <= o.timestamp_s <= end_s
            ),
            key=lambda o: o.timestamp_s,
        )
        valid = [o for o in series if o.value is not None]
        cov = (len(valid) / window_frames) if window_frames else 0.0
        prefix = f"{metric}/{space}"
        for label, t in (("start", start_s), ("bottom", bottom_s), ("end", end_s)):
            value, reason = _nearest_sample(series, t, max_gap_s)
            comps[f"{prefix}/{label}"] = (value, reason, unit, cov)
        if valid:
            vals = [o.value for o in valid if o.value is not None]
            lo, hi = min(vals), max(vals)
            comps[f"{prefix}/min"] = (lo, None, unit, cov)
            comps[f"{prefix}/max"] = (hi, None, unit, cov)
            comps[f"{prefix}/excursion"] = (hi - lo, None, unit, cov)
        else:
            for suffix in ("min", "max", "excursion"):
                comps[f"{prefix}/{suffix}"] = (None, "no_valid_samples_in_window", unit, cov)
    return comps


def measure_reference_windows(
    frames: Sequence[PoseFrame],
    *,
    exercise_id: str,
    windows: Sequence[dict],
    width: int,
    height: int,
) -> list[dict[str, tuple[float | None, str | None, str, float]]]:
    """Summarize explicit visually proposed reference windows (unreviewed).

    Used by the calibration CLI when automatic segmentation is fragmented.
    Windows are operator-proposed labels, never ground truth.
    """
    if exercise_id not in _PROFILES:
        raise ValueError(f"unsupported exercise_id: {exercise_id!r}")
    mod = _PROFILES[exercise_id]
    profile = _load_profile_config(mod.PROFILE)
    groups = _groups(profile)
    out = []
    for w in windows:
        if not all(_is_num(w.get(k)) for k in ("start_s", "bottom_s", "end_s")):
            raise ValueError("reference window times must be finite numbers")
        if not (0 <= w["start_s"] < w["bottom_s"] < w["end_s"]) or w.get("side") not in _SIDES:
            raise ValueError("reference window order or side is invalid")
        side = cast(Side, w["side"])
        obs: list[AngleObservation] = []
        for f in frames:
            obs.extend(_observe_profile(mod, f, side, width, height))
        window_frames = sum(1 for f in frames if w["start_s"] <= f.timestamp_s <= w["end_s"])
        out.append(summarize_profile_window(
            obs, groups, side=side, start_s=w["start_s"], bottom_s=w["bottom_s"],
            end_s=w["end_s"], max_gap_s=profile["max_gap_s"], window_frames=window_frames,
        ))
    return out


def _coaching() -> CoachingResult:
    return CoachingResult(
        status=CoachingStatus.UNAVAILABLE,
        limitations=[
            "measurement only: uncalibrated image-up axis, provisional cycle "
            "candidates; no technique verdict"
        ],
    )


def _pending_assessment(reason: str) -> PrototypeAssessment:
    return PrototypeAssessment(status="unavailable", missing_reasons=[reason])


def build_exercise_report(
    frames: Sequence[PoseFrame],
    *,
    analysis_id: str,
    exercise_id: str,
    variant: str,
    width: int,
    height: int,
    pose_sha256: str,
    processing_version: str,
) -> PrototypeAnalysisResult:
    if exercise_id not in _PROFILES:
        raise ValueError(f"unsupported exercise_id: {exercise_id!r}")
    exercise = cast(ExerciseId, exercise_id)
    _validate_inputs(frames, width, height, pose_sha256, processing_version)
    mod = _PROFILES[exercise_id]
    profile = _load_profile_config(mod.PROFILE)
    if variant != profile["variant"]:
        raise ValueError(f"unsupported variant for {exercise_id}: {variant!r}")
    groups = _groups(profile)
    seg = ReviewConfig(
        version=profile["version"],
        low_degrees=profile["low_degrees"],
        high_degrees=profile["high_degrees"],
        dwell_s=profile["dwell_s"],
        max_gap_s=profile["max_gap_s"],
    )
    sig_metric, sig_space = profile["signal_metric"], profile["signal_space"]

    counts = {"left": 0, "right": 0}
    for f in frames:
        for s in _SIDES:
            for o in _observe_profile(mod, f, s, width, height):
                if o.metric == sig_metric and o.space == sig_space and o.value is not None:
                    counts[s] += 1
    side: Side = "left" if counts["left"] >= counts["right"] else "right"

    obs: list[AngleObservation] = []
    for f in frames:
        obs.extend(_observe_profile(mod, f, side, width, height))
    obs.sort(key=lambda o: (o.timestamp_s, o.metric, o.space))

    signal = [(o.timestamp_s, o.value) for o in obs if o.metric == sig_metric and o.space == sig_space]
    valid_signal = sum(1 for _, v in signal if v is not None)
    expected = len(frames)
    base_warnings = [
        "PROVISIONAL_CYCLE_CANDIDATES: automatic windows are provisional, not ground truth",
        "IMAGE_AXIS_NOT_GRAVITY: torso axis is uncalibrated image-up, not gravity",
    ]
    provenance = {
        "pose_sha256": pose_sha256,
        "processing_version": processing_version,
        "config_sha256": _config_sha256(profile),
        "side": side,
        "segment_config_version": profile["version"],
        "pipeline_version": profile["version"],
        "automatic_window_origin": f"find_cycles:{sig_space}_{sig_metric}_signal",
        "count_source": "automatic_segmentation_signal_only",
    }
    if expected == 0 or valid_signal < 2:
        return PrototypeAnalysisResult(
            analysis_id=analysis_id, exercise=exercise, variant=variant,
            recipe_version=profile["version"], detected_rep_count=None,
            detected_rep_count_unavailable_reason="insufficient_valid_signal_samples",
            quality=ReportQuality(
                expected_supporting_samples=expected, valid_observed_samples=valid_signal,
                per_metric_coverage=_group_coverage(obs, groups, expected),
                usable_reps=0, total_reps=0,
                missing_reasons=["insufficient_valid_signal_samples"],
            ),
            prototype_assessment=_pending_assessment("insufficient_valid_signal_samples"),
            coaching=_coaching(), warnings=base_warnings, provenance=provenance,
        )

    result = find_cycles(signal, seg)
    completed = [(c.start_s, c.end_s) for c in result.cycles]
    partials = [
        (a, b) for a, b in result.partial_spans
        if b > a and not any(a < ce and b > cs for cs, ce in completed)
    ]
    entries: list[tuple[float, float, bool, float | None]] = [
        (c.start_s, c.end_s, True, c.bottom_s) for c in result.cycles
    ]
    entries.extend((a, b, False, None) for a, b in partials)
    entries.sort(key=lambda e: (e[0], e[1]))

    reps: list[Rep] = []
    metrics: list[Metric] = []
    usable = 0
    comp_keys = COMPARISON_KEYS[exercise_id]
    for ordinal, (start, end, is_complete, bottom) in enumerate(entries, 1):
        rep_id = f"rep-{ordinal:03d}"
        if not is_complete:
            reps.append(Rep(
                id=rep_id, ordinal=ordinal, side=side, start_s=start, end_s=end,
                completion_status=CompletionStatus.PARTIAL, scorable=False,
                excluded_reasons=["incomplete_motion_span_not_counted"],
            ))
            continue
        assert bottom is not None
        reps.append(Rep(
            id=rep_id, ordinal=ordinal, side=side, start_s=start,
            turnaround_start_s=bottom, turnaround_end_s=bottom, end_s=end,
            completion_status=CompletionStatus.COMPLETED, scorable=False,
            excluded_reasons=["benchmark_pending"],
        ))
        window_frames = sum(1 for f in frames if start <= f.timestamp_s <= end)
        comps = summarize_profile_window(
            obs, groups, side=side, start_s=start, bottom_s=bottom, end_s=end,
            max_gap_s=seg.max_gap_s, window_frames=window_frames,
        )
        rep_metrics: dict[str, Metric] = {}
        for key, (value, reason, unit, cov) in comps.items():
            space = key.split("/")[1]
            rep_metrics[key] = Metric(
                id=key, rep_id=rep_id, side=side, value=value, unit=unit,
                dimensionality=space, reference_interval=None, deviation=None,
                coverage=cov, status="observed" if value is not None else "missing",
                reason=reason,
            )
        for phase_id, phase_val in (
            ("lower_phase_duration_s", bottom - start),
            ("return_phase_duration_s", end - bottom),
        ):
            rep_metrics[phase_id] = Metric(
                id=phase_id, rep_id=rep_id, side=side, value=phase_val, unit="seconds",
                dimensionality="temporal", reference_interval=None, deviation=None,
                coverage=1.0, status="observed",
            )
        metrics.extend(rep_metrics.values())
        if all(
            rep_metrics.get(k) is not None and rep_metrics[k].value is not None
            and (rep_metrics[k].coverage or 0.0) >= _MIN_COVERAGE
            for k in comp_keys
        ):
            usable += 1

    warnings = list(base_warnings)
    if partials:
        warnings.append(f"PARTIAL_MOTION: {len(partials)} incomplete motion span(s) excluded from count")
    return PrototypeAnalysisResult(
        analysis_id=analysis_id, exercise=exercise, variant=variant,
        recipe_version=profile["version"], reps=reps, metrics=metrics,
        detected_rep_count=len(result.cycles),
        quality=ReportQuality(
            expected_supporting_samples=expected, valid_observed_samples=valid_signal,
            per_metric_coverage=_group_coverage(obs, groups, expected),
            usable_reps=usable, total_reps=len(entries),
        ),
        prototype_assessment=_pending_assessment("reference_calibration_pending"),
        coaching=_coaching(), warnings=warnings, provenance=provenance,
    )


def _load_baseline() -> dict | None:
    if not _BASELINE_PATH.exists():
        return None
    data = json.loads(_BASELINE_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("baseline config must be a JSON object")
    return data


def _canonical_hash(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _baseline_ok(cfg: dict) -> bool:
    return (
        cfg.get("version") == "exercise-reference-bands-v1"
        and cfg.get("author") is False
        and cfg.get("review") == "unreviewed"
        and _is_num(cfg.get("normalization_degrees"))
        and cfg["normalization_degrees"] == _NORMALIZATION_DEG
        and cfg["normalization_degrees"] > 0
        and _is_num(cfg.get("min_coverage"))
        and cfg["min_coverage"] == _MIN_COVERAGE
    )


def _band_ok(band: dict, ref_cycles: int) -> bool:
    vc = band.get("valid_count")
    return (
        band.get("unit") == "degrees"
        and _is_num(band.get("lower")) and _is_num(band.get("upper"))
        and band["lower"] <= band["upper"]
        and isinstance(vc, int) and not isinstance(vc, bool)
        and _MIN_REFERENCE_CYCLES <= vc <= ref_cycles
    )


def apply_reference_assessment(
    report: PrototypeAnalysisResult, config: dict | None = None
) -> PrototypeAnalysisResult:
    """Attach reference-band assessment; returns a new validated report.

    Bands come only from the explicitly selected primary reference for the
    report's exercise (no best-of/pooling). Deviation is signed: negative
    below the band, positive above it; the score uses abs(deviation)
    normalized by the configured 30 degrees (experimental, unreviewed),
    aggregated as equal_metric_mean_per_cycle_then_cycle_mean. Status is
    always partial (even at 100); the top-level technique score stays None.
    The input report is never mutated.
    """
    cfg = _load_baseline() if config is None else config
    if cfg is None:
        return report.model_copy(update={
            "prototype_assessment": _pending_assessment("reference_calibration_pending")
        })
    if not isinstance(cfg, dict) or not _baseline_ok(cfg):
        return report.model_copy(update={
            "prototype_assessment": _pending_assessment("reference_baseline_config_invalid")
        })
    ref = (cfg.get("references") or {}).get(report.exercise)
    if not isinstance(ref, dict) or not ref.get("primary", False):
        return report.model_copy(update={
            "prototype_assessment": _pending_assessment("reference_calibration_pending")
        })
    ref_cycles = ref.get("valid_reference_cycles")
    if not isinstance(ref_cycles, int) or isinstance(ref_cycles, bool) or ref_cycles < _MIN_REFERENCE_CYCLES:
        return report.model_copy(update={
            "prototype_assessment": _pending_assessment("reference_band_invalid_or_missing")
        })
    bands = ref.get("bands") or {}
    if not isinstance(bands, dict):
        return report.model_copy(update={
            "prototype_assessment": _pending_assessment("reference_band_invalid_or_missing")
        })
    keys = COMPARISON_KEYS[report.exercise]
    if any(k not in bands or not isinstance(bands[k], dict) or not _band_ok(bands[k], ref_cycles) for k in keys):
        return report.model_copy(update={
            "prototype_assessment": _pending_assessment("reference_band_invalid_or_missing")
        })

    norm = float(cfg["normalization_degrees"])
    completed = {r.id for r in report.reps if r.completion_status == CompletionStatus.COMPLETED}
    per_cycle: dict[str, dict[str, Metric]] = {rid: {} for rid in completed}
    new_metrics: list[Metric] = []
    for m in report.metrics:
        if m.rep_id in completed and m.id in keys and m.value is not None and (m.coverage or 0.0) >= _MIN_COVERAGE:
            band = bands[m.id]
            lo, hi = float(band["lower"]), float(band["upper"])
            if m.value < lo:
                dev = m.value - lo  # signed: negative below the band
            elif m.value > hi:
                dev = m.value - hi  # signed: positive above the band
            else:
                dev = 0.0
            m = m.model_copy(update={"reference_interval": (lo, hi), "deviation": dev})
            per_cycle[m.rep_id][m.id] = m
        new_metrics.append(m)

    eligible = {rid: vals for rid, vals in per_cycle.items() if all(k in vals for k in keys)}
    if len(eligible) < _MIN_USER_CYCLES:
        return report.model_copy(update={
            "metrics": new_metrics,
            "prototype_assessment": _pending_assessment("insufficient_eligible_cycles"),
        })
    cycle_scores = [
        sum(max(0.0, 100.0 - abs(vals[k].deviation or 0.0) / norm * 100.0) for k in keys) / len(keys)
        for vals in eligible.values()
    ]
    score = sum(cycle_scores) / len(cycle_scores)
    profile_omissions = list(_PROFILES[report.exercise].PROFILE.get("omitted_components", []))
    assessment = PrototypeAssessment(
        status="partial",
        policy_version=cfg["version"],
        estimated_match=score,
        included_components=list(keys),
        omitted_components=profile_omissions + [
            "view_unreviewed",
            "experimental_normalization_30deg_unreviewed",
        ],
        missing_reasons=["view_unreviewed", "experimental_normalization"],
    )
    provenance = dict(report.provenance)
    provenance.update({
        "match_normalization_degrees": str(cfg["normalization_degrees"]),
        "match_coverage_threshold": str(cfg["min_coverage"]),
        "match_aggregation": _AGGREGATION,
        "matched_cycles": str(len(eligible)),
        "omitted_cycle_count": str(len(completed) - len(eligible)),
        "reference_name": str(ref.get("reference_name", "")),
        "reference_id": str(ref.get("reference_id", "")),
        "reference_view_id": str(ref.get("view_id", "")),
        "reference_rep_count": str(ref.get("rep_count", "")),
        "calibration_status": "unreviewed",
        "reference_band_basis": _BAND_BASIS,
        "experimental_policy_version": cfg["version"],
        "experimental_policy_hash": _canonical_hash(cfg),
        "reference_source_url": str(ref.get("source_url", "")),
    })
    return PrototypeAnalysisResult.model_validate({
        **report.model_dump(),
        "metrics": [m.model_dump() for m in new_metrics],
        "prototype_assessment": assessment.model_dump(),
        "provenance": provenance,
    })
