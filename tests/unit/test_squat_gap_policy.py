"""Regression tests for the squat-measure-v2 missing-gap policy.

All tests run the real ``build_exercise_report`` on deterministic analytic
squat PoseFrames (no monkeypatching, no imputed joints). Timestamps are
binary-exact multiples of 1/32 s so dwell/gap comparisons are exact, not
float-fragile. The signal is the measured knee_angle/estimated_3d; missed
knee samples are produced by omitting the knee joint from the frame, so the
observation stays ``value=None`` with an explicit reason.

Anchor semantics (runtime Cycle): ``start_s``/``end_s`` are the confirmed
HIGH plateau *entry* times and ``bottom_s`` (reported as
``turnaround_start_s``) is the confirmed LOW plateau *entry* time, not the
H->L transition boundary and not the kinematic extremum. Accepted missing
spans are recorded endpoint-to-endpoint: from the last valid sample before
the None run to the first valid sample after it.

Note on reference assessment: the v1 reference-band baseline is not rewritten
here. If a baseline gates on the squat-measure-v1 profile version, v2 reports
must remain honestly unavailable (``reference_calibration_pending``) rather
than reusing v1 bands; these tests assert the pending status only.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from contracts.enums import CompletionStatus
from contracts.pose import JointObservation, PoseFrame
from movement import profile_curl, profile_press, profile_squat
from movement import runtime_exercises as rt
from movement.review_cycles import ReviewConfig, find_cycles

WIDTH = 100
HEIGHT = 100
SHA = "b" * 64
DT = 0.03125  # 1/32 s, exactly representable in binary floating point
HIGH_ANGLE = 170.0
LOW_ANGLE = 60.0

CONFIG_DIR = (
    Path(__file__).resolve().parents[2]
    / "packages"
    / "movement"
    / "movement"
    / "configs"
)


def _joint(xy, xyz):
    return JointObservation(xy=xy, xyz=xyz, valid=True, interpolated=False)


def _squat_joints(knee_angle_deg, *, omit_knee=False):
    """Analytic left-side squat pose with an exact knee interior angle.

    Knee at origin; hip straight above; ankle placed so the interior angle
    at the knee is exactly ``knee_angle_deg`` (z=0 plane, so projected 2D
    and estimated 3D agree). Shoulder straight above the hip gives a 180
    degree hip angle and a vertical torso axis.
    """
    theta = math.radians(knee_angle_deg)
    ax, ay = math.sin(theta), math.cos(theta)
    joints = {
        "left_shoulder": _joint(xy=(0.5, 0.3), xyz=(0.0, 2.0, 0.0)),
        "left_hip": _joint(xy=(0.5, 0.4), xyz=(0.0, 1.0, 0.0)),
        "left_knee": _joint(xy=(0.5, 0.5), xyz=(0.0, 0.0, 0.0)),
        "left_ankle": _joint(
            xy=(0.5 + 0.1 * ax, 0.5 - 0.1 * ay), xyz=(ax, ay, 0.0)
        ),
    }
    if omit_knee:
        del joints["left_knee"]
    return joints


def _frames(spec):
    """Build PoseFrames from [(angle_or_None)] at binary-exact timestamps."""
    frames = []
    for i, angle in enumerate(spec):
        joints = _squat_joints(HIGH_ANGLE if angle is None else angle,
                               omit_knee=angle is None)
        frames.append(PoseFrame(frame_index=i, timestamp_s=i * DT, joints=joints))
    return frames


def _build(frames):
    return rt.build_exercise_report(
        frames,
        analysis_id="gap-t1",
        exercise_id="squat",
        variant="bodyweight",
        width=WIDTH,
        height=HEIGHT,
        pose_sha256=SHA,
        processing_version="pv1",
    )


def _signal(frames):
    out = []
    for f in frames:
        for o in profile_squat.observe(f, side="left", width=WIDTH, height=HEIGHT):
            if o.metric == "knee_angle" and o.space == "estimated_3d":
                out.append((o.timestamp_s, o.value))
    return out


def _strict_config():
    # squat-measure-v1 semantics: no missing-gap bridging.
    return ReviewConfig(
        version="squat-measure-v1",
        low_degrees=100.0,
        high_degrees=150.0,
        dwell_s=0.1,
        max_gap_s=0.1,
    )


# H x5 (span 0.125 >= dwell), L x11 with the middle knee sample missed,
# H x5. The missed sample is bracketed by two LOW samples 2*DT = 0.0625 s
# apart (<= missing_gap_s), same band, so v2 bridges it; strict v1 resets.
#
# Derived anchors (dwell_s = 0.1 = 3.2*DT, confirmed at plateau entry + 4*DT):
#   initial HIGH plateau enters at 0*DT, confirmed at 4*DT -> start_s = 0*DT.
#   LOW plateau enters at 5*DT (first low sample), confirmed at 9*DT
#     -> bottom_s (turnaround_start_s) = 5*DT, the low-plateau ENTRY, not
#     the post-gap transition boundary at 11*DT.
#   return HIGH plateau enters at 16*DT, confirmed at 20*DT -> end_s = 16*DT.
#   accepted missing span is endpoint-to-endpoint: last valid LOW at 9*DT
#     to first valid LOW at 11*DT -> (9*DT, 11*DT).
BRIDGED_SPEC = (
    [HIGH_ANGLE] * 5
    + [LOW_ANGLE] * 5
    + [None]
    + [LOW_ANGLE] * 5
    + [HIGH_ANGLE] * 5
)
MISS_INDEX = 10  # the None sample inside the low plateau


def test_profile_v2_constants_and_config_match():
    assert profile_squat.PROFILE["version"] == "squat-measure-v2"
    assert profile_squat.PROFILE["missing_gap_s"] == 0.1
    # Segmentation bounds unchanged from v1.
    assert profile_squat.PROFILE["low_degrees"] == 100.0
    assert profile_squat.PROFILE["high_degrees"] == 150.0
    assert profile_squat.PROFILE["dwell_s"] == 0.1
    assert profile_squat.PROFILE["max_gap_s"] == 0.1
    cfg = json.loads((CONFIG_DIR / "squat-measure-v2.json").read_text())
    assert cfg == profile_squat.PROFILE
    # Torso axis version tracks the profile version; geometry preserved.
    assert profile_squat.SQUAT_TORSO_AXIS.version == "squat-measure-v2"
    assert profile_squat.SQUAT_TORSO_AXIS.up_xy == (0.0, -1.0)
    assert profile_squat.SQUAT_TORSO_AXIS.positive_cross_sign == 1


def test_v1_config_file_preserved_unchanged():
    v1 = json.loads((CONFIG_DIR / "squat-measure-v1.json").read_text())
    assert v1["version"] == "squat-measure-v1"
    assert "missing_gap_s" not in v1
    assert v1["low_degrees"] == 100.0
    assert v1["high_degrees"] == 150.0
    assert v1["dwell_s"] == 0.1
    assert v1["max_gap_s"] == 0.1


def test_same_band_short_gap_bridged_recovers_cycle():
    frames = _frames(BRIDGED_SPEC)
    report = _build(frames)
    assert report.detected_rep_count == 1
    completed = [
        r for r in report.reps if r.completion_status == CompletionStatus.COMPLETED
    ]
    assert len(completed) == 1
    rep = completed[0]
    # Real recovered candidate (not an accuracy claim): H-L-H anchors.
    # turnaround_start_s is the confirmed LOW plateau ENTRY (5*DT), which
    # precedes the missed sample; it is not the 11*DT resume boundary.
    assert rep.start_s == pytest.approx(0.0)
    assert rep.turnaround_start_s == pytest.approx(5 * DT)
    assert rep.end_s == pytest.approx(16 * DT)
    assert "contains_unmeasured_gap" in rep.excluded_reasons
    # Coverage warning and provenance retained.
    assert any("MISSING_OBSERVATIONS_RETAINED" in w for w in report.warnings)
    policy = report.provenance["missing_observations_policy"]
    assert policy.startswith("squat-measure-v2:bridge_same_band_endpoints_only")
    # Span is endpoint-to-endpoint: last valid LOW (9*DT) to resume (11*DT).
    trace = json.loads(report.provenance["missing_spans_trace"])
    assert trace == [[round(9 * DT, 9), round(11 * DT, 9)]]
    # The missed knee sample remains unmeasured (None), never imputed.
    missing_obs = [
        o
        for o in profile_squat.observe(
            frames[MISS_INDEX], side="left", width=WIDTH, height=HEIGHT
        )
        if o.metric == "knee_angle"
    ]
    assert all(o.value is None and o.reason == "missing_joint" for o in missing_obs)
    # Knee coverage reflects the genuinely missing frame.
    knee_cov = report.quality.per_metric_coverage["knee_angle/estimated_3d"]
    assert knee_cov == pytest.approx((len(frames) - 1) / len(frames))
    # Assessment stays honestly pending; the v1 baseline is not rewritten.
    assert report.prototype_assessment.status == "unavailable"
    assert (
        "reference_calibration_pending"
        in report.prototype_assessment.missing_reasons
    )


def test_strict_policy_does_not_bridge_same_gap():
    frames = _frames(BRIDGED_SPEC)
    strict = find_cycles(_signal(frames), _strict_config())
    assert strict.cycles == ()
    assert strict.partial_spans  # fragments retained as partials, not cycles
    bridged = find_cycles(
        _signal(frames),
        ReviewConfig(
            version="squat-measure-v2",
            low_degrees=100.0,
            high_degrees=150.0,
            dwell_s=0.1,
            max_gap_s=0.1,
            missing_gap_s=0.1,
        ),
    )
    assert len(bridged.cycles) == 1
    # Exact observed anchors: low plateau entry at 5*DT, return high entry
    # at 16*DT; accepted span endpoints 9*DT -> 11*DT.
    cycle = bridged.cycles[0]
    assert cycle.start_s == pytest.approx(0.0)
    assert cycle.bottom_s == pytest.approx(5 * DT)
    assert cycle.end_s == pytest.approx(16 * DT)
    assert bridged.cycle_missing_spans == (((9 * DT, 11 * DT),),)


def test_cross_band_gap_rejected():
    # Missing sample bracketed by HIGH then LOW: different bands, never bridged.
    spec = [HIGH_ANGLE] * 5 + [None] + [LOW_ANGLE] * 5 + [HIGH_ANGLE] * 5
    report = _build(_frames(spec))
    assert report.detected_rep_count == 0
    assert not any("MISSING_OBSERVATIONS_RETAINED" in w for w in report.warnings)


def test_overlong_gap_rejected():
    # Three consecutive missed samples: bracketing elapsed 4*DT = 0.125 > 0.1.
    spec = (
        [HIGH_ANGLE] * 5
        + [LOW_ANGLE] * 2
        + [None] * 3
        + [LOW_ANGLE] * 5
        + [HIGH_ANGLE] * 5
    )
    report = _build(_frames(spec))
    assert report.detected_rep_count == 0


def test_trailing_gap_rejected():
    # Trailing missed samples during the unconfirmed return HIGH: no cycle.
    spec = [HIGH_ANGLE] * 5 + [LOW_ANGLE] * 5 + [HIGH_ANGLE] * 2 + [None] * 3
    report = _build(_frames(spec))
    assert report.detected_rep_count == 0


def test_missing_frames_never_count_toward_dwell():
    # Alternating valid HIGH / missed samples: the high plateau never reaches
    # dwell because each None clears the plateau candidate, so the initial
    # HIGH is never confirmed and no cycle can start.
    spec = [HIGH_ANGLE, None] * 6 + [LOW_ANGLE] * 5 + [HIGH_ANGLE] * 5
    report = _build(_frames(spec))
    assert report.detected_rep_count == 0


def test_repeat_determinism():
    frames = _frames(BRIDGED_SPEC)
    a = _build(frames)
    b = _build(frames)
    assert a.model_dump() == b.model_dump()


def test_other_profiles_unchanged():
    # Curl already opted in under its own v2 profile; press stays strict.
    assert profile_curl.PROFILE["version"] == "curl-measure-v2"
    assert profile_curl.PROFILE["missing_gap_s"] == 0.1
    assert "missing_gap_s" not in profile_press.PROFILE
    # Squat is the only profile whose version changed.
    assert profile_press.PROFILE["version"] == "press-measure-v1"
