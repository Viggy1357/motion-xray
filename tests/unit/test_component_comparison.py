"""Analytic tests for the event-level component comparison engine.

Fixture literals are analytic (hand-computed), not implementation mirrors.
"""

from __future__ import annotations

import math

import pytest

from scoring.components import (
    AGGREGATE_UNAVAILABLE_REASON,
    FAMILY_METRICS,
    ComparisonContext,
    ComponentComparison,
    ReferenceBand,
    aggregate_score,
    compare_component,
    validate_family_mappings,
)


def band(**kw) -> ReferenceBand:
    base = dict(
        metric_id="M2", unit="degrees", lower=0.0, upper=10.0, tolerance=5.0,
        reviewer="rev_a", review_status="qualified", source_id="S4",
        version="0.1", authoritative=True, view_id="side", variant="strict",
        provider="mediapipe", mapping_version="mv1",
    )
    base.update(kw)
    return ReferenceBand(**base)


def ctx(**kw) -> ComparisonContext:
    base = dict(
        user_variant="strict", reference_variant="strict",
        user_provider="mediapipe", reference_provider="mediapipe",
        user_mapping_version="mv1", reference_mapping_version="mv1",
        user_view_id="side", reference_view_id="side",
        compatibility="confirmed", compatibility_reviewer="rev_b",
        compatibility_version="cv1",
    )
    base.update(kw)
    return ComparisonContext(**base)


# --- analytic fixture: band [0,10], T=5 -> score = 100*max(0, 1-d/5) ---
FIXTURE = [
    # (value, signed_deviation, absolute_distance, score)
    (5.0, 0.0, 0.0, 100.0),    # inside
    (0.0, 0.0, 0.0, 100.0),    # on lower edge
    (10.0, 0.0, 0.0, 100.0),   # on upper edge
    (-2.5, -2.5, 2.5, 50.0),   # below
    (12.5, 2.5, 2.5, 50.0),    # above
    (-5.0, -5.0, 5.0, 0.0),    # at tolerance
    (20.0, 10.0, 10.0, 0.0),   # beyond tolerance
]


@pytest.mark.parametrize("value,dev,dist,score", FIXTURE)
def test_analytic_deviation_and_score(value, dev, dist, score):
    r = compare_component(value, None, "degrees", band(), ctx())
    assert r.signed_deviation == dev
    assert r.absolute_distance == dist
    assert r.delta_low == value - 0.0
    assert r.delta_high == value - 10.0
    assert r.score == score
    # valid_technique_score is ALWAYS None: reference similarity is not a
    # certified technique-correctness claim, even for qualified bands.
    assert r.valid_technique_score is None
    assert r.score_kind == "reference_band_deviation"


def test_monotonic_perturbation():
    scores = [
        compare_component(x, None, "degrees", band(), ctx()).score
        for x in (5.0, 10.5, 11.0, 12.0, 14.0, 15.0, 16.0)
    ]
    assert all(a >= b for a, b in zip(scores, scores[1:]))
    lows = [
        compare_component(x, None, "degrees", band(), ctx()).score
        for x in (5.0, -0.5, -1.0, -2.0, -4.0, -5.0, -6.0)
    ]
    assert all(a >= b for a, b in zip(lows, lows[1:]))


def test_missing_value_never_scores_100():
    r = compare_component(None, "no_sample_in_tolerance", "degrees", band(), ctx())
    assert r.score is None
    assert r.valid_technique_score is None
    assert r.signed_deviation is None and r.delta_low is None
    assert "missing_value" in r.score_reason


def test_repeat_equality():
    a = compare_component(12.5, None, "degrees", band(), ctx())
    b = compare_component(12.5, None, "degrees", band(), ctx())
    assert a == b


# --- ReferenceBand validation ---

@pytest.mark.parametrize("kw", [
    {"lower": True}, {"lower": float("nan")}, {"upper": float("inf")},
    {"lower": 11.0},  # lower > upper
    {"lower": -1e308, "upper": 1e308},  # span overflows to inf
    {"tolerance": 0.0}, {"tolerance": -1.0}, {"tolerance": float("nan")},
    {"tolerance": True},
    {"metric_id": ""}, {"unit": " "}, {"source_id": ""}, {"version": ""},
    {"view_id": ""}, {"variant": ""}, {"provider": ""}, {"mapping_version": ""},
    {"review_status": "qualified", "reviewer": None},
    {"review_status": "owner_prototype", "reviewer": "  "},
    {"review_status": "owner_prototype", "authoritative": True},
    {"review_status": "pending", "authoritative": True},
    {"authoritative": 1},
])
def test_band_validation_rejects(kw):
    with pytest.raises(ValueError):
        band(**kw)


def test_band_tolerance_missing_ok():
    b = band(tolerance=None, review_status="pending", reviewer=None, authoritative=False)
    assert b.tolerance is None


# --- context validation ---

@pytest.mark.parametrize("kw", [
    {"compatibility": "confirmed", "compatibility_reviewer": None},
    {"compatibility": "bogus"},
    {"user_view_id": ""},
    {"compatibility_version": ""},
])
def test_context_validation_rejects(kw):
    with pytest.raises(ValueError):
        ctx(**kw)


# --- compare_component input validation ---

@pytest.mark.parametrize("value,reason,unit", [
    (None, None, "degrees"),          # null value requires reason
    (1.0, "x", "degrees"),            # valued must not carry reason
    (None, "", "degrees"),            # empty reason
    (float("nan"), None, "degrees"),
    (float("inf"), None, "degrees"),
    (True, None, "degrees"),
    (1.0, None, ""),
])
def test_compare_input_rejects(value, reason, unit):
    with pytest.raises(ValueError):
        compare_component(value, reason, unit, band(), ctx())


def test_unit_mismatch_no_score():
    r = compare_component(5.0, None, "seconds", band(), ctx())
    assert r.score is None and "unit_mismatch" in r.score_reason
    assert r.signed_deviation is None


# --- comparability gates ---

def test_unknown_compatibility_descriptive_only():
    c = ctx(compatibility="unknown", compatibility_reviewer=None)
    r = compare_component(12.5, None, "degrees", band(), c)
    assert r.score is None and r.valid_technique_score is None
    assert r.signed_deviation == 2.5  # raw descriptive delta allowed
    assert r.score_reason == "comparability_unknown"


def test_incompatible_metadata_mismatch():
    c = ctx(user_provider="other_provider")
    r = compare_component(12.5, None, "degrees", band(), c)
    assert r.score is None and r.score_reason == "incompatible_metadata"
    assert r.comparability == "incompatible"
    assert r.signed_deviation == 2.5  # raw descriptive delta retained


def test_incompatible_metadata_missing_value_preserves_reason():
    c = ctx(user_provider="other_provider")
    r = compare_component(None, "no_sample_in_tolerance", "degrees", band(), c)
    assert r.score is None and r.score_reason == "incompatible_metadata"
    assert r.reason == "no_sample_in_tolerance"
    assert r.delta_low is None and r.signed_deviation is None


def test_band_view_must_match_reference_view_even_when_confirmed():
    # Arbitrary band from a source view not in the confirmed pair is refused.
    b = band(view_id="front")
    r = compare_component(5.0, None, "degrees", b, ctx())
    assert r.score is None
    assert r.comparability == "incompatible"
    assert r.score_reason == "incompatible_metadata"
    assert r.valid_technique_score is None


def test_confirmed_pair_with_explicit_different_views_can_score():
    # Reviewer-confirmed pair with different user/reference views is allowed;
    # the band binds to the reference view.
    c = ctx(user_view_id="diagonal", reference_view_id="side")
    r = compare_component(5.0, None, "degrees", band(view_id="side"), c)
    assert r.score == 100.0
    assert r.valid_technique_score is None


def test_view_difference_ok_only_with_explicit_confirmation():
    c = ctx(user_view_id="diagonal")  # confirmed + reviewer, metadata matches
    r = compare_component(5.0, None, "degrees", band(), c)
    assert r.score == 100.0
    # view match alone is not enough: unknown stays unscored even same view
    c2 = ctx(compatibility="unknown", compatibility_reviewer=None)
    r2 = compare_component(5.0, None, "degrees", band(), c2)
    assert r2.score is None


# --- finite overflow guards ---

def test_finite_inputs_overflowing_deviation_rejected():
    # 1e308 - (-1e308) overflows to inf; must never emit Inf JSON fields.
    b = band(lower=-1e308, upper=0.0, tolerance=5.0)
    r = compare_component(1e308, None, "degrees", b, ctx())
    assert r.score is None
    assert r.score_reason == "non_finite_deviation"
    assert r.delta_low is None and r.delta_high is None
    assert r.signed_deviation is None and r.absolute_distance is None
    assert r.valid_technique_score is None


def test_overflow_guard_applies_on_all_paths():
    b = band(lower=-1e308, upper=0.0, tolerance=5.0)
    for c in (
        ctx(),
        ctx(compatibility="unknown", compatibility_reviewer=None),
        ctx(user_provider="other_provider"),
    ):
        r = compare_component(1e308, None, "degrees", b, c)
        assert r.score is None
        assert r.score_reason in ("non_finite_deviation",)
        for f in (r.delta_low, r.delta_high, r.signed_deviation, r.absolute_distance):
            assert f is None or math.isfinite(f)


def test_large_but_finite_deviation_clamps_to_zero_score():
    b = band(lower=0.0, upper=10.0, tolerance=5.0)
    r = compare_component(1e300, None, "degrees", b, ctx())
    assert r.score == 0.0
    assert math.isfinite(r.absolute_distance)


# --- review gates ---

def test_pending_reference_no_score():
    b = band(review_status="pending", reviewer=None, authoritative=False)
    r = compare_component(5.0, None, "degrees", b, ctx())
    assert r.score is None and r.score_reason == "reference_review_pending"
    assert r.signed_deviation == 0.0


def test_unreviewed_tolerance_absent_null_score():
    b = band(tolerance=None)
    r = compare_component(5.0, None, "degrees", b, ctx())
    assert r.score is None and r.score_reason == "tolerance_absent"
    assert r.valid_technique_score is None


def test_owner_prototype_gate():
    b = band(review_status="owner_prototype", authoritative=False)
    r = compare_component(12.5, None, "degrees", b, ctx())
    assert r.score == 50.0
    assert r.score_kind == "owner_reviewed_reference_similarity"
    assert r.valid_technique_score is None  # never a technique claim


def test_owner_prototype_still_requires_confirmed_context():
    b = band(review_status="owner_prototype", authoritative=False)
    c = ctx(compatibility="unknown", compatibility_reviewer=None)
    r = compare_component(12.5, None, "degrees", b, c)
    assert r.score is None


def test_qualified_score_still_not_valid_technique_score():
    r = compare_component(5.0, None, "degrees", band(), ctx())
    assert r.score == 100.0
    assert r.score_kind == "reference_band_deviation"
    assert r.valid_technique_score is None


# --- dynamic metadata construction (no dict-cast suppression) ---

def test_dynamic_metadata_fields_propagate():
    b = band(source_id="SRC9", version="2.3", metric_id="M4", unit="cm",
             lower=1.0, upper=3.0, tolerance=2.0, view_id="front")
    c = ctx(reference_view_id="front", user_view_id="front")
    r = compare_component(4.0, None, "cm", b, c)
    assert r.reference_id == "SRC9:2.3:M4"
    assert r.metric_id == "M4"
    assert r.observed_interval == (1.0, 3.0)
    assert r.score == 50.0  # d=1, T=2 -> 100*(1-1/2)
    assert r.valid_technique_score is None


# --- family mappings and aggregate ---

def test_default_family_mappings_valid_and_no_double_count():
    m = validate_family_mappings(FAMILY_METRICS)
    assert m["arm_rom"] == ("M3", "M6")
    flat = [x for v in m.values() for x in v]
    assert len(flat) == len(set(flat))


def test_family_mapping_duplicate_across_families_rejected():
    bad = {k: list(v) for k, v in FAMILY_METRICS.items()}
    bad["shoulder_drive"] = ("M3",)
    with pytest.raises(ValueError):
        validate_family_mappings(bad)


def test_family_mapping_missing_family_rejected():
    bad = {k: v for k, v in FAMILY_METRICS.items() if k != "bar_endpoint"}
    with pytest.raises(ValueError):
        validate_family_mappings(bad)


@pytest.mark.parametrize("arm_rom", [
    ("M3",),            # missing M6
    ("M6",),            # missing M3
    ("M3", "M9"),       # arbitrary substitution
    ("M9", "M6"),       # arbitrary substitution
    ("M6", "M3"),       # wrong order
    ("M3", "M6", "M7"),  # extra metric
])
def test_arm_rom_must_be_exactly_m3_m6(arm_rom):
    bad = {k: list(v) for k, v in FAMILY_METRICS.items()}
    bad["arm_rom"] = list(arm_rom)
    with pytest.raises(ValueError):
        validate_family_mappings(bad)


def test_aggregate_returns_none_with_reason_constant():
    assert aggregate_score({}) is None
    assert aggregate_score({}, FAMILY_METRICS) is None
    assert AGGREGATE_UNAVAILABLE_REASON == "aggregate_policy_not_approved"


def test_result_is_frozen_typed():
    r = compare_component(5.0, None, "degrees", band(), ctx())
    assert isinstance(r, ComponentComparison)
    with pytest.raises(Exception):
        r.score = 0.0  # type: ignore[misc]
    assert math.isfinite(r.absolute_distance)
