"""Round-trip + invariant tests for every Motion X Ray contract model.

Each model is built with valid example data, serialised to JSON, parsed back,
and asserted equal. We also assert the shared NaN/inf rejection and that the
schema export yields one entry per model.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest

from contracts import (
    AnalysisJob,
    AnalysisResult,
    CoachingResult,
    CoachingStatus,
    CompletionStatus,
    JobStage,
    JobState,
    JointObservation,
    Metric,
    PoseFrame,
    PoseSequence,
    Rep,
    ReferenceProfile,
    ReferenceType,
    ScoreBreakdown,
    SourceRecord,
    VideoAsset,
)
from contracts.schema_export import export_json_schema
from contracts.base import SCHEMA_VERSION

UTC_NOW = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def _examples() -> list:
    """One valid instance of every public model."""

    joint = JointObservation(
        xy=(0.5, 0.25),
        xyz=None,
        native_quality=0.9,
        valid=True,
        interpolated=False,
        quality_method="native",
    )
    rep = Rep(
        id="rep-1",
        ordinal=1,
        side="left",
        start_s=0.0,
        turnaround_start_s=1.0,
        turnaround_end_s=1.5,
        end_s=2.0,
        completion_status=CompletionStatus.COMPLETED,
        scorable=True,
        excluded_reasons=[],
    )
    metric = Metric(
        id="metric-1",
        rep_id="rep-1",
        side="left",
        value=42.0,
        unit="deg",
        dimensionality="angle",
        reference_interval=(30.0, 50.0),
        deviation=0.0,
        coverage=1.0,
        quality_method="native",
        status="ok",
        reason=None,
    )
    coaching = CoachingResult(
        status=CoachingStatus.OK,
        summary="Solid depth.",
        observations=["good tempo"],
        next_set_cue="brace harder",
        limitations=[],
    )
    return [
        VideoAsset(
            id="vid-1",
            owner_session_id="sess-1",
            storage_key="s3://bucket/vid-1",
            sha256="0" * 64,
            mime="video/mp4",
            bytes=1024,
            duration_s=12.5,
            width=1080,
            height=1920,
            rotation=0,
            timestamp_map_key=None,
            created_at=UTC_NOW,
            expires_at=None,
        ),
        joint,
        PoseFrame(
            frame_index=0,
            timestamp_s=0.0,
            subject_track_id="track-1",
            joints={"left_knee": joint},
        ),
        PoseSequence(
            schema_version=SCHEMA_VERSION,
            video_id="vid-1",
            provider="mediapipe",
            model_revision="rev-1",
            native_skeleton="mediapipe-33",
            joint_mapping_version="1.0",
            sample_rate_hz=30.0,
            units="normalized",
            coordinate_system="image",
            capabilities={"xyz": False},
            quality_method="native",
            frames_artifact_key="artifacts/vid-1/pose.parquet",
        ),
        rep,
        metric,
        coaching,
        AnalysisResult(
            schema_version=SCHEMA_VERSION,
            analysis_id="an-1",
            exercise="squat",
            variant="back",
            reps=[rep],
            metrics=[metric],
            score=88.0,
            best_rep_id="rep-1",
            worst_rep_id="rep-1",
            source_ids=["src-1"],
            coaching=coaching,
            warnings=[],
            provenance={"pose_provider": "mediapipe"},
        ),
        ReferenceProfile(
            id="ref-1",
            version="1.0",
            type=ReferenceType.EVIDENCE,
            scope="global",
            exercise="squat",
            variant="back",
            view="side",
            provider_compatibility=["mediapipe"],
            approved_by="reviewer-1",
            approved_date=UTC_NOW,
            source_ids=["src-1"],
            pose_key="refs/squat/pose.json",
            metric_rules={"knee_angle": {"lower": 30.0, "upper": 50.0}},
            approval_status="approved",
        ),
        SourceRecord(
            id="src-1",
            canonical_url="https://example.org/squat",
            title="Squat mechanics",
            publisher="Example Journal",
            retrieved_at=UTC_NOW,
            source_tier="peer_reviewed",
            relevant_claims=["knees track over toes"],
            review_status="reviewed",
            reviewer="reviewer-1",
            reviewed_date=UTC_NOW,
            reuse_terms="cc-by",
        ),
        ScoreBreakdown(
            profile_id="ref-1",
            profile_version="1.0",
            reference_version="1.0",
            component_values={"knee_angle": 42.0},
            component_weights={"knee_angle": 1.0},
            raw_score=88.0,
            displayed_score=88.0,
            coverage=1.0,
            missing_reasons=[],
        ),
        AnalysisJob(
            id="job-1",
            owner="sess-1",
            state=JobState.RUNNING,
            stage=JobStage.METRICS,
            attempt=1,
            lease_owner="worker-1",
            lease_until=UTC_NOW,
            cancel_requested=False,
            input_hash="hash-in",
            version_hash="hash-ver",
            created_at=UTC_NOW,
            updated_at=UTC_NOW,
            error=None,
            result_key=None,
        ),
    ]


@pytest.mark.parametrize("model", _examples(), ids=lambda m: type(m).__name__)
def test_json_roundtrip(model) -> None:
    """model -> JSON -> model must preserve equality for every model."""

    restored = type(model).model_validate_json(model.model_dump_json())
    assert restored == model


def test_nan_and_inf_rejected() -> None:
    """Float fields must reject NaN and infinity (AGENTS.md rule 3)."""

    with pytest.raises(Exception):
        Metric(
            id="m",
            rep_id="r",
            value=math.nan,
            unit="deg",
            dimensionality="angle",
            status="ok",
        )
    with pytest.raises(Exception):
        Metric(
            id="m",
            rep_id="r",
            value=math.inf,
            unit="deg",
            dimensionality="angle",
            status="ok",
        )


def test_naive_datetime_rejected() -> None:
    """UTC datetime fields must reject timezone-naive input."""

    with pytest.raises(Exception):
        AnalysisJob(
            id="job-1",
            owner="sess-1",
            state=JobState.QUEUED,
            stage=JobStage.VALIDATE,
            attempt=0,
            cancel_requested=False,
            input_hash="in",
            version_hash="ver",
            created_at=datetime(2024, 1, 1, 0, 0, 0),  # naive
            updated_at=UTC_NOW,
        )


def test_export_json_schema_has_entry_per_model() -> None:
    """export_json_schema() returns a JSON-Schema dict for every model."""

    schemas = export_json_schema()
    expected = {
        "VideoAsset",
        "JointObservation",
        "PoseFrame",
        "PoseSequence",
        "Rep",
        "Metric",
        "CoachingResult",
        "AnalysisResult",
        "ReferenceProfile",
        "SourceRecord",
        "ScoreBreakdown",
        "AnalysisJob",
        "AnalysisCreateRequest",
        "AnalysisStatus",
        "SessionInfo",
        "TimestampPair",
        "ProxyTimestampMap",
        "PoseJobInput",
        "PoseJobArtifacts",
    }
    assert set(schemas) == expected
    for schema in schemas.values():
        assert isinstance(schema, dict)
        assert "properties" in schema
