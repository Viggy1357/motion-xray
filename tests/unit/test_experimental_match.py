"""Offline tests for the experimental lat reference-match estimate."""

from __future__ import annotations

import copy

import pytest

from contracts.analysis import Metric, Rep
from contracts.enums import CompletionStatus
from contracts.product import PrototypeAnalysisResult, PrototypeAssessment, ReportQuality
from movement.experimental_match import _validate_config, apply_experimental_match

# QMotion primary bands (from the versioned config; tests restate them to assert exact math).
TORSO = (22.175893967891938, 26.84034327316766)
ELBOW_EXC = (67.80057239455766, 76.12246048671858)
ELBOW_END = (156.96433349874334, 159.09039212657623)
UPPER_ARM = (49.32936462864003, 53.81956352706624)
KEYS = {
    "torso_axis_angle/projected_2d/excursion": TORSO,
    "elbow_angle/estimated_3d/excursion": ELBOW_EXC,
    "elbow_angle/estimated_3d/end": ELBOW_END,
    "upper_arm_torso_angle/estimated_3d/bottom": UPPER_ARM,
}


def _metric(key, value, rep="rep-001", side="right", unit="degrees", coverage=1.0, status=None):
    dim = key.split("/")[1]
    if status is None:
        status = "observed" if value is not None else "missing"
    return Metric(
        id=key, rep_id=rep, side=side, value=value, unit=unit, dimensionality=dim,
        coverage=coverage, status=status, reason=None if value is not None else "gap",
    )


def _report(values, exercise="lat_pulldown", variant="cable_seated_bilateral",
            extra_metrics=(), rep_id="rep-001", side="right"):
    reps = [Rep(id=rep_id, ordinal=1, side=side, start_s=0.0, end_s=2.0,
                completion_status=CompletionStatus.COMPLETED, scorable=False)]
    metrics = [_metric(k, v, rep=rep_id, side=side) for k, v in values.items()] + list(extra_metrics)
    return PrototypeAnalysisResult(
        analysis_id="a1", exercise=exercise, variant=variant,
        recipe_version="movement-lat-v1", reps=reps, metrics=metrics, detected_rep_count=1,
        quality=ReportQuality(expected_supporting_samples=1, valid_observed_samples=1,
                              usable_reps=1, total_reps=1),
        prototype_assessment=PrototypeAssessment(status="unavailable",
                                                 missing_reasons=["reference_pending"]),
    )


def _inside():
    return {k: (lo + hi) / 2 for k, (lo, hi) in KEYS.items()}


def test_inside_band_exact_100_partial():
    out = apply_experimental_match(_report(_inside()))
    a = out.prototype_assessment
    assert a.status == "partial" and a.estimated_match == 100.0
    assert a.policy_version == "lat-experimental-match-v1"
    assert a.included_components == ["torso_dynamic", "arm_rom", "shoulder_drive"]
    assert a.omitted_components == ["torso_start", "bar_endpoint"]
    assert "unreviewed_view" in a.missing_reasons
    assert "unreviewed_normalization" in a.missing_reasons
    assert "partial_metric_scope" in a.missing_reasons
    assert out.score is None
    assert out.recipe_version == "movement-lat-v1+matchv1"
    for m in out.metrics:
        assert m.deviation == 0.0
        assert m.reference_interval == KEYS[m.id]


def test_below_band_signed_deviation_and_formula():
    vals = _inside()
    vals["torso_axis_angle/projected_2d/excursion"] = TORSO[0] - 15.0
    out = apply_experimental_match(_report(vals))
    assert out.prototype_assessment.estimated_match == pytest.approx(250.0 / 3)
    m = next(m for m in out.metrics if m.id == "torso_axis_angle/projected_2d/excursion")
    assert m.deviation == pytest.approx(-15.0)


def test_above_band_zero_resemblance_positive_deviation():
    vals = _inside()
    vals["upper_arm_torso_angle/estimated_3d/bottom"] = UPPER_ARM[1] + 30.0
    out = apply_experimental_match(_report(vals))
    assert out.prototype_assessment.estimated_match == pytest.approx(200.0 / 3)
    m = next(m for m in out.metrics if m.id == "upper_arm_torso_angle/estimated_3d/bottom")
    assert m.deviation == pytest.approx(30.0)


def test_arm_rom_equal_family_weight():
    vals = _inside()
    vals["elbow_angle/estimated_3d/excursion"] = ELBOW_EXC[0] - 30.0  # resemblance 0
    out = apply_experimental_match(_report(vals))
    assert out.prototype_assessment.estimated_match == pytest.approx(250.0 / 3)


def test_fixed_primary_qmotion_not_cherry_picked():
    vals = _inside()
    vals["torso_axis_angle/projected_2d/excursion"] = 12.0  # inside catalyst, below qmotion
    out = apply_experimental_match(_report(vals))
    expected = 100.0 * (1.0 - (TORSO[0] - 12.0) / 30.0)
    assert out.prototype_assessment.estimated_match == pytest.approx((expected + 200.0) / 3)
    assert out.provenance["reference_id"] == "qmotion_roi"


def test_provenance_stable_strings():
    out = apply_experimental_match(_report(_inside()))
    p = out.provenance
    assert p["experimental_policy_version"] == "lat-experimental-match-v1"
    assert len(p["experimental_policy_sha256"]) == 64
    assert p["reference_view_id"] == "qmotion_roi_diagonal_unvalidated"
    assert p["reference_review_status"] == "unreviewed_algorithm_proposal"
    assert p["reference_rep_count"] == "4"
    assert p["reference_band_basis"] == "observed_min_max_not_tolerance"
    assert p["match_normalization_degrees"] == "30.0"
    assert p["match_coverage_threshold"] == "0.8"
    assert p["matched_cycles"] == "1" and p["omitted_cycle_count"] == "0"
    assert p["calibration_status"] == "uncalibrated_engineering_hypothesis_not_validated"


def _unavailable(out):
    a = out.prototype_assessment
    assert a.status == "unavailable" and a.estimated_match is None
    assert "no_eligible_cycles" in a.missing_reasons
    assert "excluded_cycles" in a.missing_reasons


def test_coverage_079_fails_080_passes():
    r = _report(_inside())
    r.metrics[0].coverage = 0.79
    _unavailable(apply_experimental_match(r))
    r2 = _report(_inside())
    r2.metrics[0].coverage = 0.8
    assert apply_experimental_match(r2).prototype_assessment.status == "partial"


def test_null_value_excluded():
    vals = _inside()
    vals["elbow_angle/estimated_3d/end"] = None
    _unavailable(apply_experimental_match(_report(vals)))


def test_wrong_unit_excluded():
    r = _report(_inside())
    r.metrics[0].unit = "radians"
    _unavailable(apply_experimental_match(r))


def test_wrong_dimensionality_excluded():
    r = _report(_inside())
    r.metrics[0].dimensionality = "estimated_3d"
    _unavailable(apply_experimental_match(r))


def test_duplicate_metric_excluded_not_silent():
    dup = _metric("torso_axis_angle/projected_2d/excursion", 24.0)
    _unavailable(apply_experimental_match(_report(_inside(), extra_metrics=[dup])))


def test_other_side_duplicate_does_not_corrupt():
    other = _metric("torso_axis_angle/projected_2d/excursion", 99.0, side="left")
    out = apply_experimental_match(_report(_inside(), extra_metrics=[other]))
    assert out.prototype_assessment.estimated_match == 100.0
    left = next(m for m in out.metrics if m.side == "left")
    assert left.reference_interval is None and left.deviation is None


def test_missing_rep_side_excluded():
    vals = _inside()
    r = _report(vals, side=None)
    r.metrics = [_metric(k, v, side=None) for k, v in vals.items()]
    _unavailable(apply_experimental_match(r))


def test_missing_arm_component_excluded():
    vals = _inside()
    del vals["elbow_angle/estimated_3d/excursion"]
    _unavailable(apply_experimental_match(_report(vals)))


def test_mismatched_variant_unavailable():
    out = apply_experimental_match(_report(_inside(), variant="machine_seated"))
    a = out.prototype_assessment
    assert a.status == "unavailable" and a.estimated_match is None
    assert "variant_not_comparable" in a.missing_reasons


def test_non_lat_passes_through():
    r = _report(_inside(), exercise="squat")
    assert apply_experimental_match(r) is r


def test_deterministic_repeat():
    r = _report(_inside())
    assert apply_experimental_match(r).model_dump() == apply_experimental_match(r).model_dump()


def test_recipe_suffix_idempotent():
    once = apply_experimental_match(_report(_inside()))
    twice = apply_experimental_match(once)
    assert twice.recipe_version == "movement-lat-v1+matchv1"
    assert twice.prototype_assessment.estimated_match == 100.0


def test_input_not_mutated():
    r = _report(_inside())
    snapshot = copy.deepcopy(r.model_dump())
    apply_experimental_match(r)
    assert r.model_dump() == snapshot
    assert all(m.reference_interval is None and m.deviation is None for m in r.metrics)


def _cfg():
    import json
    from pathlib import Path

    path = Path(__file__).parents[2] / "packages/movement/movement/configs/lat-experimental-match-v1.json"
    return json.loads(path.read_text())


def test_shipped_config_valid():
    assert _validate_config(_cfg())["version"] == "lat-experimental-match-v1"


@pytest.mark.parametrize("mutate", [
    lambda c: c.update(version="lat-experimental-match-v2"),
    lambda c: c.update(authoritative=True),
    lambda c: c.update(review_status="reviewed"),
    lambda c: c.update(normalization_degrees=True),
    lambda c: c.update(normalization_degrees=-30.0),
    lambda c: c.update(normalization_degrees=float("nan")),
    lambda c: c.update(normalization_basis="calibrated_tolerance"),
    lambda c: c.update(coverage_threshold=0),
    lambda c: c.update(coverage_threshold=1.5),
    lambda c: c.update(coverage_threshold=True),
    lambda c: c.update(primary_reference_id="catalyst_roi"),
    lambda c: c.update(omitted_components=["torso_start"]),
    lambda c: c["references"][0]["bands"]["torso_axis_angle/projected_2d/excursion"].update(value_min=99.0),
    lambda c: c["references"][0].update(rep_count=0),
    lambda c: c["references"][0]["bands"]["elbow_angle/estimated_3d/end"].update(valid_count=0),
    lambda c: c["references"][0]["bands"]["elbow_angle/estimated_3d/end"].update(valid_count=99),
    lambda c: c["references"][0]["bands"]["elbow_angle/estimated_3d/end"].update(provisional=False),
    lambda c: c["family_groups"].update(shoulder_drive=["elbow_angle/estimated_3d/end"]),
    lambda c: c["references"].append(copy.deepcopy(c["references"][0])),
])
def test_config_validation_rejects_bad(mutate):
    cfg = _cfg()
    mutate(cfg)
    with pytest.raises(ValueError):
        _validate_config(cfg)
