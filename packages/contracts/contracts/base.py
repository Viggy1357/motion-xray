"""Shared Pydantic v2 base model and reusable validators for Motion X Ray.

This module is the foundation of the contracts package (AGENTS.md rule 4).
Every domain model subclasses :class:`MXRModel` so the whole schema shares
one configuration: unknown fields are rejected and non-finite floats refuse
to serialise. Per AGENTS.md rule 3 (never fabricate), a value is either a
real measured number or an explicit ``None`` with a machine-readable reason;
silent NaN/inf is never allowed to masquerade as data.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Final

from pydantic import AfterValidator, BaseModel, ConfigDict

SCHEMA_VERSION: Final = "0.2.0"


class MXRModel(BaseModel):
    """Base model for every Motion X Ray contract.

    Configuration:
        * ``allow_inf_nan=False`` — validation rejects non-finite floats.
        * ``extra='forbid'`` — unknown input fields are a validation error, so
          schema drift is caught at the boundary rather than silently dropped.
    """

    model_config = ConfigDict(
        allow_inf_nan=False,
        extra="forbid",
        protected_namespaces=(),
    )


def ensure_utc(value: datetime) -> datetime:
    """Return a timezone-aware UTC datetime, rejecting naive datetimes.

    A naive datetime has no offset, so it cannot be compared across systems
    without guessing a timezone. We refuse to guess. Aware datetimes in other
    zones are normalised to UTC.

    Raises:
        ValueError: if ``value`` is timezone-naive.
    """

    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError("datetime must be timezone-aware (UTC)")
    return value.astimezone(timezone.utc)


def ensure_finite_float(value: float) -> float:
    """Return ``value`` if it is a finite float, else raise.

    Rejects NaN and +/-inf so that a non-finite number can never stand in for
    a real measurement (AGENTS.md rule 3). ``None`` is handled by the field's
    ``Optional`` typing, not here.

    Raises:
        ValueError: if ``value`` is NaN or infinite.
    """

    numeric = float(value)
    if numeric != numeric:  # NaN is the only value that is not equal to itself.
        raise ValueError("float must be finite, got NaN")
    if numeric in (float("inf"), float("-inf")):
        raise ValueError("float must be finite, got infinity")
    return numeric


# Reusable annotated field types. Using these in model definitions keeps the
# NaN/inf and UTC guarantees in one place instead of repeating validators.
FiniteFloat = Annotated[float, AfterValidator(ensure_finite_float)]
UTCDateTime = Annotated[datetime, AfterValidator(ensure_utc)]
