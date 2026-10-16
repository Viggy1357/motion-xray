from __future__ import annotations

"""Error contract for the Motion X Ray API.

A single ``ErrorEnvelope`` shape is returned for every failure so clients can
branch on a stable, machine-readable ``code`` rather than parsing prose. Per
AGENTS.md rule 3 (never fabricate), a failure is an honest, typed signal — not a
silently-degraded success. The ``retryable`` flag tells the client whether the
same request may succeed later (e.g. a transient provider timeout) versus a
permanent rejection (e.g. unsupported variant).

STRUCTURE-ONLY: this defines the envelope and the canonical code constants. The
handlers that raise them are wired by their owning tasks (see app.main).
"""

from typing import List, Optional

from pydantic import BaseModel

# Canonical error codes. Kept as module-level string constants so handlers and
# tests reference one spelling; the value is the wire contract.
INVALID_MEDIA = "INVALID_MEDIA"
UNSUPPORTED_VARIANT = "UNSUPPORTED_VARIANT"
INCOMPATIBLE_REFERENCE = "INCOMPATIBLE_REFERENCE"
INSUFFICIENT_VISIBILITY = "INSUFFICIENT_VISIBILITY"
PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
RATE_LIMITED = "RATE_LIMITED"
JOB_EXPIRED = "JOB_EXPIRED"


class ErrorEnvelope(BaseModel):
    """Uniform error body returned by every API endpoint on failure.

    Fields:
        code: one of the module-level error-code constants above.
        message: human-readable explanation; safe to surface to the client.
        retryable: whether retrying the identical request may later succeed.
        request_id: correlation id for tracing a single request through logs.
        field_errors: optional per-field validation messages, keyed by field.
    """

    code: str
    message: str
    retryable: bool = False
    request_id: Optional[str] = None
    field_errors: Optional[dict[str, List[str]]] = None
