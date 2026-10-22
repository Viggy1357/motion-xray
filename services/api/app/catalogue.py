"""Public exercise catalogue (FR05/FR06).

Static, honest metadata: pose-only capability is claimed; no rep counting,
scoring, or coaching is advertised. Views are human-usable capture guidance,
not verified scoring views. Target muscles are static exercise anatomy
illustration, not measured activation. No secrets; safe to expose publicly.
"""

from __future__ import annotations

from fastapi import APIRouter

from contracts.product import ExerciseInfo

router = APIRouter(prefix="/v1")

_POSE_ONLY = ["pose_only"]
_VIEWS = ["front", "side"]

_EXERCISES: list[ExerciseInfo] = [
    ExerciseInfo(
        id="lat_pulldown",
        display_name="Lat Pulldown",
        variant="cable_seated_bilateral",
        supported_views=list(_VIEWS),
        target_muscles=["latissimus_dorsi", "biceps_brachii", "rhomboids"],
        capabilities=list(_POSE_ONLY),
        reference_status="provisional",
        profile_version=None,
    ),
    ExerciseInfo(
        id="dumbbell_curl",
        display_name="Dumbbell Curl",
        variant="standing_both_arms",
        supported_views=list(_VIEWS),
        target_muscles=["biceps_brachii", "brachialis"],
        capabilities=list(_POSE_ONLY),
        reference_status="unavailable",
        profile_version=None,
    ),
    ExerciseInfo(
        id="squat",
        display_name="Squat",
        variant="bodyweight",
        supported_views=list(_VIEWS),
        target_muscles=["quadriceps", "gluteus_maximus", "hamstrings"],
        capabilities=list(_POSE_ONLY),
        reference_status="unavailable",
        profile_version=None,
    ),
    ExerciseInfo(
        id="incline_chest_press",
        display_name="Incline Chest Press",
        variant="incline_dumbbell_bilateral",
        supported_views=list(_VIEWS),
        target_muscles=["pectoralis_major", "anterior_deltoid", "triceps_brachii"],
        capabilities=list(_POSE_ONLY),
        reference_status="unavailable",
        profile_version=None,
    ),
]


@router.get("/exercises", response_model=list[ExerciseInfo])
def list_exercises() -> list[ExerciseInfo]:
    """List supported exercises and their default variants. FR06."""
    return list(_EXERCISES)
