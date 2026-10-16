from __future__ import annotations

"""The provider-agnostic pose estimation interface.

Downstream movement analysis depends only on this Protocol, never on a
concrete provider's joint indices or SDK types (see skills/pose-pipeline:
"map by anatomical name, not index"). MediaPipe is the primary provider for
this build; GEM-X is a documented stretch (DECISIONS.md D002).
"""

from typing import Protocol, runtime_checkable

from contracts.media import VideoAsset
from contracts.pose import PoseSequence

from providers.capabilities import PoseCapabilities


@runtime_checkable
class PoseProvider(Protocol):
    """A source of canonical, timestamped pose from a decoded video."""

    def capabilities(self) -> PoseCapabilities:
        """Return the honest capabilities of this provider.

        Consumers use this to decide whether a comparison is supportable
        (e.g. whether estimated 3D is available) rather than assuming.
        """
        ...

    def infer(self, video: VideoAsset) -> PoseSequence:
        """Estimate pose for ``video`` and return a canonical sequence header.

        The large per-frame data is stored out of band; the returned
        :class:`~contracts.pose.PoseSequence` is the versioned descriptor that
        points at it via ``frames_artifact_key``.
        """
        ...
