"""Offline tests for the exercise catalogue and variant resolution."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.analyses import _resolve_variant
from app.catalogue import router as catalogue_router
from contracts.lifecycle import AnalysisCreateRequest
from contracts.product import ExerciseInfo


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(catalogue_router)
    return TestClient(app)


def test_catalogue_returns_exactly_four_honest_entries() -> None:
    resp = _client().get("/v1/exercises")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 4
    items = [ExerciseInfo.model_validate(e) for e in body]
    assert [e.id for e in items] == [
        "lat_pulldown",
        "dumbbell_curl",
        "squat",
        "incline_chest_press",
    ]
    defaults = {e.id: e.variant for e in items}
    assert defaults == {
        "lat_pulldown": "cable_seated_bilateral",
        "dumbbell_curl": "standing_both_arms",
        "squat": "bodyweight",
        "incline_chest_press": "incline_dumbbell_bilateral",
    }
    for e in items:
        # Pose-only: never claim rep counting, scoring, or coaching.
        assert e.capabilities == ["pose_only"]
        assert not ({"rep_counting", "scoring", "coaching"} & set(e.capabilities))
        assert set(e.supported_views) <= {"front", "side"}
        assert e.target_muscles  # static anatomy illustration, non-empty
    by_id = {e.id: e for e in items}
    assert by_id["lat_pulldown"].reference_status == "provisional"
    for eid in ("dumbbell_curl", "squat", "incline_chest_press"):
        assert by_id[eid].reference_status == "unavailable"
        assert by_id[eid].profile_version is None


def test_press_variant_resolution_valid_and_invalid() -> None:
    from fastapi import HTTPException

    assert _resolve_variant("incline_chest_press", None) == "incline_dumbbell_bilateral"
    assert (
        _resolve_variant("incline_chest_press", "incline_dumbbell_bilateral")
        == "incline_dumbbell_bilateral"
    )
    with pytest.raises(HTTPException) as exc:
        _resolve_variant("incline_chest_press", "barbell")
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "UNSUPPORTED_VARIANT"


def test_old_lateral_raise_request_still_model_valid() -> None:
    req = AnalysisCreateRequest.model_validate(
        {
            "video_id": "0" * 32,
            "exercise_id": "lateral_raise",
            "variant": "standing_both_arms",
            "request_key": "rk-1",
        }
    )
    assert req.exercise_id == "lateral_raise"
    assert _resolve_variant("lateral_raise", req.variant) == "standing_both_arms"
