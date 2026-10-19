"""Pose estimation providers.

The :class:`~providers.pose.protocol.PoseProvider` Protocol defines the
provider-agnostic interface; :class:`~providers.pose.fake.FakePoseProvider`
is a deterministic test double; the real MediaPipe adapter lives in
``providers.pose.mediapipe_provider`` and imports its ML dependency lazily.
"""

from __future__ import annotations
