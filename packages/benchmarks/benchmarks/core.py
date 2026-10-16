from __future__ import annotations

"""Reference-compatibility checks (SCAFFOLD — no real logic).

Benchmarks decide whether a given pose provider's capabilities are sufficient
to compare against a particular reference profile, so scoring never runs an
unsupportable comparison (AGENTS.md rule 3). Implementations are deferred to
TODO(T06); each raises :class:`NotImplementedError`.
"""

from contracts.reference import ReferenceProfile

from providers.capabilities import PoseCapabilities


def check_reference_compatibility(
    pose_capabilities: PoseCapabilities,
    reference_profile: ReferenceProfile,
) -> bool:
    """Return whether ``pose_capabilities`` can satisfy ``reference_profile``.

    E.g. a reference that requires estimated 3D cannot be scored from a 2D-only
    provider; this gate prevents a fabricated comparison and surfaces an honest
    reason instead.
    """
    # TODO(T06): implement the deterministic compatibility check.
    raise NotImplementedError(
        "check_reference_compatibility is a scaffold stub — TODO(T06)."
    )


def load_reference_profile(profile_id: str) -> ReferenceProfile:
    """Load an approved :class:`ReferenceProfile` by ``profile_id``.

    Reads a reviewed, versioned profile from the local reference library; a
    missing or unapproved profile is an error, never a synthesized default.
    """
    # TODO(T06): implement reference profile loading from the local library.
    raise NotImplementedError(
        "load_reference_profile is a scaffold stub — TODO(T06)."
    )
