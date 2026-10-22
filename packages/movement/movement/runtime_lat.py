"""Deterministic lat-pulldown prototype runtime report (schema 0.3).

Pure arithmetic over existing pose artifacts. No I/O except the package-owned
versioned config. No scores, no technique verdicts, no reference intervals:
the frozen component policy stays pending, so assessment is unavailable.
"""

from __future__ import annotations

import hashlib
import json
import math
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
from movement.observations import AngleObservation, measure_frame
from movement.posture import ProjectionAxis, measure_torso_frame
from movement.rep_observations import RepWindow, measure_rep
from movement.review_cycles import ReviewConfig, find_cycles

MAX_FRAMES = 10000
MAX_DIMENSION = 1920
_CONTRACT_EXERCISES: tuple[ExerciseId, ...] = (
    "lat_pulldown",
    "dumbbell_curl",
    "squat",
    "incline_chest_press",
)
_LAT_VARIANT = "cable_seated_bilateral"
_UNAVAILABLE_RECIPE = "movement-unavailable-v1"
Side = Literal["left", "right"]
_SIDES: tuple[Side, Side] = ("left", "right")
_GROUPS = (
    ("elbow_angle", "projected_2d"),
    ("elbow_angle", "estimated_3d"),
    ("upper_arm_torso_angle", "projected_2d"),
    ("upper_arm_torso_angle", "estimated_3d"),
    ("torso_axis_angle", "projected_2d"),
)
_AXIS = ProjectionAxis(
    "camera-plane-axis-v1", "image_up_unverified_not_gravity", (0.0, -1.0), 1
)


def _is_num(v: object) -> bool:
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def _load_config() -> dict:
    path = Path(__file__).parent / "configs" / "lat-runtime-v1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("lat runtime config must be a JSON object")
    for key in ("version", "pipeline_version", "reference_policy_version", "reference_status"):
        if not isinstance(data.get(key), str) or not data[key]:
            raise ValueError(f"config {key} must be a nonempty string")
    if data["reference_status"] != "pending":
        raise ValueError("config reference_status must remain pending")
    for key in ("low_degrees", "high_degrees", "dwell_s", "max_gap_s"):
        if not _is_num(data.get(key)):
            raise ValueError(f"config {key} must be a finite non-bool number")
    ms = data.get("minimum_signal_samples")
    if isinstance(ms, bool) or not isinstance(ms, int) or ms < 1:
        raise ValueError("config minimum_signal_samples must be a positive integer")
    fam = data.get("omitted_score_families")
    if not isinstance(fam, list) or not all(isinstance(x, str) and x for x in fam):
        raise ValueError("config omitted_score_families must be nonempty strings")
    ReviewConfig(  # validates ranges; rejects bool/non-finite
        version=data["version"],
        low_degrees=data["low_degrees"],
        high_degrees=data["high_degrees"],
        dwell_s=data["dwell_s"],
        max_gap_s=data["max_gap_s"],
    )
    return data


def _config_sha256(data: dict) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_inputs(
    frames: Sequence[PoseFrame], width: object, height: object,
    pose_sha256: object, processing_version: object,
) -> None:
    if isinstance(width, bool) or isinstance(height, bool):
        raise ValueError("width and height must be non-bool integers")
    if not isinstance(width, int) or not isinstance(height, int):
        raise ValueError("width and height must be integers")
    if not (0 < width <= MAX_DIMENSION) or not (0 < height <= MAX_DIMENSION):
        raise ValueError("width and height must be in (0, 1920]")
    if not isinstance(pose_sha256, str) or len(pose_sha256) != 64:
        raise ValueError("pose_sha256 must be 64 hex characters")
    if any(c not in "0123456789abcdefABCDEF" for c in pose_sha256):
        raise ValueError("pose_sha256 must be 64 hex characters")
    if not isinstance(processing_version, str) or not processing_version.strip():
        raise ValueError("processing_version must be a nonempty string")
    if len(frames) > MAX_FRAMES:
        raise ValueError(f"at most {MAX_FRAMES} frames per artifact")
    prev_i = prev_t = None
    for f in frames:
        if prev_i is not None and f.frame_index <= prev_i:
            raise ValueError("frame_index must be strictly increasing")
        if prev_t is not None and f.timestamp_s <= prev_t:
            raise ValueError("timestamp_s must be strictly increasing")
        prev_i, prev_t = f.frame_index, f.timestamp_s


def _assessment(cfg: dict) -> PrototypeAssessment:
    return PrototypeAssessment(
        status="unavailable",
        policy_version=cfg["reference_policy_version"],
        omitted_components=list(cfg["omitted_score_families"]),
        missing_reasons=["reference_pending", "view_unreviewed", "bar_endpoint_unavailable"],
    )


def _coaching() -> CoachingResult:
    return CoachingResult(
        status=CoachingStatus.UNAVAILABLE,
        limitations=[
            "measurement only: uncalibrated image-up axis, provisional cycle "
            "candidates, no approved reference policy; no technique verdict"
        ],
    )


def _provenance(cfg: dict, sha: str, side: str, pose_sha256: str, pv: str) -> dict:
    return {
        "pose_sha256": pose_sha256,
        "processing_version": pv,
        "config_sha256": sha,
        "side": side,
        "segment_config_version": cfg["version"],
        "pipeline_version": cfg["pipeline_version"],
        "automatic_window_origin": "find_cycles:estimated_3d_elbow_signal",
        "axis": "image_up_unverified_not_gravity",
        "count_source": "automatic_segmentation_signal_only",
        "global_coverage_meaning": "segmentation_signal_visibility_only",
    }


def _group_coverage(obs: Sequence[AngleObservation], total: int) -> dict:
    if total == 0:
        return {}
    out = {}
    for g in _GROUPS:
        valid = sum(
            1 for o in obs if (o.metric, o.space) == g and o.value is not None
        )
        out[f"{g[0]}/{g[1]}"] = valid / total
    return out


def _profile_unavailable(
    analysis_id: str, exercise: ExerciseId, variant: str,
    pose_sha256: str, pv: str, warnings: list[str],
) -> PrototypeAnalysisResult:
    """Generic unavailable report; carries no lat policy/axis/threshold data."""
    return PrototypeAnalysisResult(
        analysis_id=analysis_id,
        exercise=exercise,
        variant=variant,
        recipe_version=_UNAVAILABLE_RECIPE,
        detected_rep_count=None,
        detected_rep_count_unavailable_reason="exercise_profile_unavailable",
        quality=ReportQuality(
            expected_supporting_samples=0,
            valid_observed_samples=0,
            per_metric_coverage={},
            usable_reps=0,
            total_reps=0,
            missing_reasons=["exercise_profile_unavailable"],
        ),
        prototype_assessment=PrototypeAssessment(
            status="unavailable",
            missing_reasons=["exercise_profile_unavailable"],
        ),
        coaching=CoachingResult(
            status=CoachingStatus.UNAVAILABLE,
            limitations=["exercise-specific movement profile is unavailable"],
        ),
        warnings=warnings,
        provenance={
            "pose_sha256": pose_sha256,
            "processing_version": pv,
            "profile_status": _UNAVAILABLE_RECIPE,
        },
    )


def _unavailable(
    analysis_id: str, exercise: ExerciseId, variant: str, cfg: dict, sha: str,
    reason: str, expected: int, valid: int, obs: Sequence[AngleObservation],
    side: str, pose_sha256: str, pv: str, warnings: list[str],
) -> PrototypeAnalysisResult:
    return PrototypeAnalysisResult(
        analysis_id=analysis_id,
        exercise=exercise,
        variant=variant,
        recipe_version=cfg["pipeline_version"],
        detected_rep_count=None,
        detected_rep_count_unavailable_reason=reason,
        quality=ReportQuality(
            expected_supporting_samples=expected,
            valid_observed_samples=valid,
            per_metric_coverage=_group_coverage(obs, expected),
            usable_reps=0,
            total_reps=0,
            missing_reasons=[reason],
        ),
        prototype_assessment=_assessment(cfg),
        coaching=_coaching(),
        warnings=warnings,
        provenance=_provenance(cfg, sha, side, pose_sha256, pv),
    )


def build_movement_report(
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
    if exercise_id not in _CONTRACT_EXERCISES:
        raise ValueError(f"unsupported exercise_id: {exercise_id!r}")
    exercise = cast(ExerciseId, exercise_id)
    _validate_inputs(frames, width, height, pose_sha256, processing_version)
    if exercise != "lat_pulldown":
        # No lat config is loaded for unsupported profiles: the generic
        # unavailable report must not copy lat policy/axis/threshold provenance.
        return _profile_unavailable(
            analysis_id, exercise, variant, pose_sha256, processing_version,
            ["EXERCISE_PROFILE_UNAVAILABLE: no movement profile for exercise"],
        )
    cfg = _load_config()
    sha = _config_sha256(cfg)
    base_warnings = [
        "PROVISIONAL_CYCLE_CANDIDATES: automatic windows are provisional, not ground truth",
        "IMAGE_AXIS_NOT_GRAVITY: torso axis is uncalibrated image-up, not gravity",
    ]
    if variant != _LAT_VARIANT:
        raise ValueError(f"unsupported lat variant: {variant!r}")

    counts: dict[Side, int] = {"left": 0, "right": 0}
    for f in frames:
        for s in _SIDES:
            if measure_frame(f, side=s, width=width, height=height)[1].value is not None:
                counts[s] += 1
    side: Side = "left" if counts["left"] >= counts["right"] else "right"

    obs: list[AngleObservation] = []
    for f in frames:
        obs.extend(measure_frame(f, side=side, width=width, height=height))
        obs.append(measure_torso_frame(f, side=side, width=width, height=height, axis=_AXIS))
    obs.sort(key=lambda o: (o.timestamp_s, o.metric, o.space))

    signal = [
        (o.timestamp_s, o.value)
        for o in obs
        if o.metric == "elbow_angle" and o.space == "estimated_3d"
    ]
    valid_signal = sum(1 for _, v in signal if v is not None)
    expected = len(frames)
    if expected == 0 or valid_signal < cfg["minimum_signal_samples"]:
        return _unavailable(
            analysis_id, exercise, variant, cfg, sha,
            "insufficient_valid_signal_samples", expected, valid_signal, obs,
            side, pose_sha256, processing_version, base_warnings,
        )

    seg = ReviewConfig(
        version=cfg["version"],
        low_degrees=cfg["low_degrees"],
        high_degrees=cfg["high_degrees"],
        dwell_s=cfg["dwell_s"],
        max_gap_s=cfg["max_gap_s"],
    )
    result = find_cycles(signal, seg)
    completed_spans = [(c.start_s, c.end_s) for c in result.cycles]
    partials = [
        (a, b)
        for a, b in result.partial_spans
        if b > a and not any(a < ce and b > cs for cs, ce in completed_spans)
    ]

    entries: list[tuple[float, float, bool, float | None]] = [
        (c.start_s, c.end_s, True, c.bottom_s) for c in result.cycles
    ]
    entries.extend((a, b, False, None) for a, b in partials)
    entries.sort(key=lambda e: (e[0], e[1]))

    reps: list[Rep] = []
    metrics: list[Metric] = []
    usable = 0
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
        window = RepWindow(rep_id=rep_id, side=side, start_s=start, bottom_s=bottom, end_s=end)
        comps = measure_rep(obs, window, max_gap_s=seg.max_gap_s)
        window_frames = sum(1 for f in frames if start <= f.timestamp_s <= end)
        for key, comp in comps.items():
            if key.endswith("_duration_s"):
                dim, cov = "temporal", 1.0
            else:
                metric_name, space = key.split("/")[0], key.split("/")[1]
                dim = space
                series = [
                    o for o in obs
                    if o.metric == metric_name and o.space == space
                    and start <= o.timestamp_s <= end
                ]
                valid_in = sum(1 for o in series if o.value is not None)
                cov = (valid_in / window_frames) if window_frames else 0.0
            metrics.append(Metric(
                id=key, rep_id=rep_id, side=side, value=comp.value, unit=comp.unit,
                dimensionality=dim, reference_interval=None, deviation=None,
                coverage=cov, status="observed" if comp.value is not None else "missing",
                reason=comp.reason,
            ))
        e3d = comps["elbow_angle/estimated_3d/excursion"].value
        torso = comps["torso_axis_angle/projected_2d/excursion"].value
        if e3d is not None and torso is not None:
            usable += 1

    warnings = list(base_warnings)
    if partials:
        warnings.append(
            f"PARTIAL_MOTION: {len(partials)} incomplete motion span(s) excluded from count"
        )
    return PrototypeAnalysisResult(
        analysis_id=analysis_id,
        exercise=exercise,
        variant=variant,
        recipe_version=cfg["pipeline_version"],
        reps=reps,
        metrics=metrics,
        detected_rep_count=len(result.cycles),
        quality=ReportQuality(
            expected_supporting_samples=expected,
            valid_observed_samples=valid_signal,
            per_metric_coverage=_group_coverage(obs, expected),
            usable_reps=usable,
            total_reps=len(entries),
        ),
        prototype_assessment=_assessment(cfg),
        coaching=_coaching(),
        warnings=warnings,
        provenance=_provenance(cfg, sha, side, pose_sha256, processing_version),
    )
