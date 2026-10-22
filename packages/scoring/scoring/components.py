"""Internal typed deterministic EVENT-LEVEL component comparison engine.

No DTW, no production report integration, no public schema change. Compares
one measured component value against a :class:`ReferenceBand` interval
``[lower, upper]`` with tolerance ``T`` using::

    d = max(L - x, 0, x - U); score = 100 * max(0, 1 - d / T)

A numeric score is emitted ONLY when comparability is explicitly confirmed
with a reviewer AND the band is owner-reviewed (``owner_prototype`` or
``qualified``) with a positive tolerance AND the band's ``view_id`` equals
the context's ``reference_view_id`` (the confirmed pair may still use
different user/reference views when a reviewer explicitly confirmed them).
Owner-prototype bands are never authoritative; their score is labeled
``owner_reviewed_reference_similarity``. ``valid_technique_score`` is ALWAYS
``None``: reference-band similarity is not a certified technique-correctness
claim, even for qualified bands. Pending bands or missing tolerance yield
``score=None`` with a clear reason — never a fabricated normalization of
observed min/max. Non-finite arithmetic (overflow) is rejected with reason
``non_finite_deviation``; no Inf/NaN ever reaches a result field.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Literal, Mapping, Sequence

ReviewStatus = Literal["pending", "owner_prototype", "qualified"]
CompatStatus = Literal["confirmed", "unknown", "incompatible"]

REQUIRED_FAMILIES: tuple[str, ...] = (
    "torso_start",
    "torso_dynamic",
    "arm_rom",
    "shoulder_drive",
    "bar_endpoint",
)

# arm_rom is one combined family: M3 (elbow ROM) and M6 (return extension)
# are reported together and must not be double-counted or substituted.
ARM_ROM_REQUIRED_METRICS: tuple[str, ...] = ("M3", "M6")

FAMILY_METRICS: Mapping[str, tuple[str, ...]] = {
    "torso_start": ("M1",),
    "torso_dynamic": ("M2",),
    "arm_rom": ARM_ROM_REQUIRED_METRICS,
    "shoulder_drive": ("M4",),
    "bar_endpoint": ("M5",),
}


def _finite(x: object) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _nonempty(s: object) -> bool:
    return isinstance(s, str) and bool(s.strip())


@dataclass(frozen=True, slots=True)
class ReferenceBand:
    metric_id: str
    unit: str
    lower: float
    upper: float
    tolerance: float | None
    reviewer: str | None
    review_status: ReviewStatus
    source_id: str
    version: str
    authoritative: bool
    view_id: str
    variant: str
    provider: str
    mapping_version: str

    def __post_init__(self) -> None:
        if not _nonempty(self.metric_id) or not _nonempty(self.unit):
            raise ValueError("metric_id and unit must be non-empty strings")
        if not _finite(self.lower) or not _finite(self.upper):
            raise ValueError("lower/upper must be finite non-bool numbers")
        if self.lower > self.upper:
            raise ValueError("require lower <= upper")
        if not math.isfinite(self.upper - self.lower):
            raise ValueError("band span must be finite (no overflow)")
        if self.tolerance is not None and (
            not _finite(self.tolerance) or self.tolerance <= 0.0
        ):
            raise ValueError("tolerance must be a finite non-bool number > 0 when present")
        if self.review_status not in ("pending", "owner_prototype", "qualified"):
            raise ValueError("invalid review_status")
        if self.review_status in ("owner_prototype", "qualified") and not _nonempty(
            self.reviewer
        ):
            raise ValueError("approved review_status requires a non-empty reviewer")
        if self.reviewer is not None and not _nonempty(self.reviewer):
            raise ValueError("reviewer must be non-empty when present")
        if not isinstance(self.authoritative, bool):
            raise ValueError("authoritative must be a bool")
        if self.review_status != "qualified" and self.authoritative:
            raise ValueError("only qualified bands may be authoritative")
        for name in ("source_id", "version", "view_id", "variant", "provider", "mapping_version"):
            if not _nonempty(getattr(self, name)):
                raise ValueError(f"{name} must be a non-empty string")


@dataclass(frozen=True, slots=True)
class ComparisonContext:
    """Caller-declared user/reference metadata. The engine never guesses side
    or auto-matches views; selection is the caller's symmetric responsibility.
    A confirmed pair may explicitly use different user/reference view IDs when
    a reviewer confirmed that pairing; the band must still match the
    reference view."""

    user_variant: str
    reference_variant: str
    user_provider: str
    reference_provider: str
    user_mapping_version: str
    reference_mapping_version: str
    user_view_id: str
    reference_view_id: str
    compatibility: CompatStatus
    compatibility_reviewer: str | None
    compatibility_version: str

    def __post_init__(self) -> None:
        for name in (
            "user_variant", "reference_variant", "user_provider", "reference_provider",
            "user_mapping_version", "reference_mapping_version", "user_view_id",
            "reference_view_id", "compatibility_version",
        ):
            if not _nonempty(getattr(self, name)):
                raise ValueError(f"{name} must be a non-empty string")
        if self.compatibility not in ("confirmed", "unknown", "incompatible"):
            raise ValueError("invalid compatibility status")
        if self.compatibility_reviewer is not None and not _nonempty(self.compatibility_reviewer):
            raise ValueError("compatibility_reviewer must be non-empty when present")
        if self.compatibility == "confirmed" and not _nonempty(self.compatibility_reviewer):
            raise ValueError("confirmed compatibility requires an explicit reviewer")


@dataclass(frozen=True, slots=True)
class ComponentComparison:
    metric_id: str
    value: float | None
    reason: str | None
    unit: str
    observed_interval: tuple[float, float]
    delta_low: float | None
    delta_high: float | None
    signed_deviation: float | None
    absolute_distance: float | None
    score: float | None
    score_kind: str | None
    score_reason: str | None
    comparability: CompatStatus
    valid_technique_score: float | None
    policy_id: str
    reference_id: str


def _metadata_compatible(band: ReferenceBand, ctx: ComparisonContext) -> bool:
    """Band must bind to the confirmed reference view and match variant,
    provider and mapping version on both sides of the declared pair."""
    return (
        band.view_id == ctx.reference_view_id
        and band.variant == ctx.user_variant == ctx.reference_variant
        and band.provider == ctx.user_provider == ctx.reference_provider
        and band.mapping_version == ctx.user_mapping_version == ctx.reference_mapping_version
    )


def compare_component(
    value: float | None,
    reason: str | None,
    unit: str,
    band: ReferenceBand,
    context: ComparisonContext,
) -> ComponentComparison:
    """Compare one event-level value against ``band``. Deterministic; no I/O."""
    if not isinstance(band, ReferenceBand) or not isinstance(context, ComparisonContext):
        raise ValueError("band and context must be typed instances")
    if (value is None) != (reason is not None):
        raise ValueError("value is None iff reason is not None")
    if reason is not None and not _nonempty(reason):
        raise ValueError("reason must be a non-empty string when present")
    if value is not None and not _finite(value):
        raise ValueError("value must be a finite non-bool number when present")
    if not _nonempty(unit):
        raise ValueError("unit must be a non-empty string")

    base = ComponentComparison(
        metric_id=band.metric_id,
        value=value,
        reason=reason,
        unit=unit,
        observed_interval=(band.lower, band.upper),
        delta_low=None,
        delta_high=None,
        signed_deviation=None,
        absolute_distance=None,
        score=None,
        score_kind=None,
        score_reason=None,
        comparability=context.compatibility,
        valid_technique_score=None,  # ALWAYS None: similarity != technique claim
        policy_id="component_comparison_policy:v1",
        reference_id=f"{band.source_id}:{band.version}:{band.metric_id}",
    )

    if unit != band.unit:
        return replace(base, score_reason=f"unit_mismatch:{unit}!={band.unit}")

    meta_ok = _metadata_compatible(band, context)
    effective: CompatStatus = (
        "incompatible"
        if (context.compatibility == "incompatible" or not meta_ok)
        else context.compatibility
    )
    if effective != context.compatibility:
        base = replace(base, comparability=effective)

    if effective == "incompatible":
        # Raw deltas may be reported descriptively when units match; never scored.
        if value is None:
            return replace(base, score_reason="incompatible_metadata")
        dl, dh = value - band.lower, value - band.upper
        if not (math.isfinite(dl) and math.isfinite(dh)):
            return replace(base, score_reason="non_finite_deviation")
        dev = dl if dl < 0.0 else (dh if dh > 0.0 else 0.0)
        return replace(
            base, delta_low=dl, delta_high=dh, signed_deviation=dev,
            absolute_distance=abs(dev), score_reason="incompatible_metadata",
        )

    if effective == "unknown":
        if value is None:
            return replace(base, score_reason="comparability_unknown")
        dl, dh = value - band.lower, value - band.upper
        if not (math.isfinite(dl) and math.isfinite(dh)):
            return replace(base, score_reason="non_finite_deviation")
        dev = dl if dl < 0.0 else (dh if dh > 0.0 else 0.0)
        return replace(
            base, delta_low=dl, delta_high=dh, signed_deviation=dev,
            absolute_distance=abs(dev), score_reason="comparability_unknown",
        )

    # compatibility == "confirmed" (reviewer enforced by context validation).
    if value is None:
        return replace(base, score_reason=f"missing_value:{reason}")

    dl, dh = value - band.lower, value - band.upper
    if not (math.isfinite(dl) and math.isfinite(dh)):
        return replace(base, score_reason="non_finite_deviation")
    dev = dl if dl < 0.0 else (dh if dh > 0.0 else 0.0)
    dist = abs(dev)
    if not (math.isfinite(dev) and math.isfinite(dist)):
        return replace(base, score_reason="non_finite_deviation")
    base = replace(
        base, delta_low=dl, delta_high=dh,
        signed_deviation=dev, absolute_distance=dist,
    )

    if band.review_status == "pending":
        return replace(base, score_reason="reference_review_pending")
    if band.tolerance is None:
        return replace(base, score_reason="tolerance_absent")

    ratio = dist / band.tolerance
    if not math.isfinite(ratio):
        return replace(base, score_reason="non_finite_deviation")
    raw = 100.0 * max(0.0, 1.0 - ratio)
    if not math.isfinite(raw):
        return replace(base, score_reason="non_finite_deviation")
    score = float(raw)
    if band.review_status == "owner_prototype":
        # Owner-reviewed reference similarity only; never a technique claim.
        return replace(
            base, score=score,
            score_kind="owner_reviewed_reference_similarity",
            score_reason="owner_prototype_not_authoritative",
        )
    return replace(
        base, score=score, score_kind="reference_band_deviation",
        score_reason="qualified_reference",
    )


def validate_family_mappings(
    mappings: Mapping[str, Sequence[str]],
) -> dict[str, tuple[str, ...]]:
    """Validate caller-provided family mappings: required families present,
    no metric assigned to two families, and arm_rom is exactly the combined
    (M3, M6) family — arbitrary family substitution is rejected so required
    coverage cannot be fooled."""
    seen: dict[str, str] = {}
    out: dict[str, tuple[str, ...]] = {}
    for fam in REQUIRED_FAMILIES:
        metrics = mappings.get(fam)
        if not metrics:
            raise ValueError(f"missing required family: {fam}")
        ids: list[str] = []
        for m in metrics:
            if not _nonempty(m):
                raise ValueError("metric ids must be non-empty strings")
            if m in seen:
                raise ValueError(f"metric {m} assigned to both {seen[m]} and {fam}")
            if m in ids:
                raise ValueError(f"duplicate metric {m} within family {fam}")
            seen[m] = fam
            ids.append(m)
        out[fam] = tuple(ids)
    extra = set(mappings) - set(REQUIRED_FAMILIES)
    if extra:
        raise ValueError(f"unknown families: {sorted(extra)}")
    if out["arm_rom"] != ARM_ROM_REQUIRED_METRICS:
        raise ValueError(
            "arm_rom must be exactly the combined metrics "
            f"{ARM_ROM_REQUIRED_METRICS} (M3 elbow ROM + M6 return extension)"
        )
    return out


def aggregate_score(
    comparisons: Mapping[str, ComponentComparison],
    family_mappings: Mapping[str, Sequence[str]] | None = None,
) -> float | None:
    """Aggregate numeric score is NOT approved yet; always returns ``None``.

    Required families (torso_start, torso_dynamic, arm_rom combined M3/M6,
    shoulder_drive, bar_endpoint) are validated when mappings are provided,
    but no aggregate number is fabricated while policy is unapproved.
    Reason: 'aggregate_policy_not_approved'.
    """
    if family_mappings is not None:
        validate_family_mappings(family_mappings)
    return None


AGGREGATE_UNAVAILABLE_REASON = "aggregate_policy_not_approved"
