"""Anonymous session ownership contract for Motion X Ray.

SessionInfo is returned on establishment so the client knows its CSRF token
and when the session expires. No other model changes are introduced.
"""

from __future__ import annotations


from contracts.base import MXRModel, UTCDateTime


class SessionInfo(MXRModel):
    """Public session contract returned to the client on establishment.

    The CSRF token is returned on establish/reload and remains valid until
    the session expires.
    """

    csrf_token: str
    expires_at: UTCDateTime
