"""Motion X Ray HTTP API — the public /v1 surface.

This module constructs the FastAPI application and declares every route the
product exposes. It is STRUCTURE-ONLY: each /v1 handler is a placeholder that
returns HTTP 501 (Not Implemented) until its owning task lands. Path shapes and
path-parameter signatures here are the contract the web client and tests build
against; the real request logic is filled in per the TODO(Txx) markers.

Functional requirements served by this surface (see TASKS.md / spec §):
  - FR01/FR02/FR03  Ingestion & jobs — POST /v1/videos, POST /v1/analyses,
                    analysis lifecycle (get/cancel/delete) and status (FR03/FR12).
  - FR05/FR06       Exercise catalogue — GET /v1/exercises.
  - FR07/FR08       Scoring & result — GET /v1/analyses/{id}/result.
  - FR07/FR11       References — GET/POST /v1/references, approve.
  - FR10            X Ray artifacts — GET /v1/analyses/{id}/artifacts/{kind}.
  - FR11            Evidence refresh — POST /v1/evidence/refresh.

FastAPI serves GET /openapi.json automatically from these declarations; do not
hand-write it. The importable ASGI target is ``app.main:app``.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import errors
from contracts.analysis import AnalysisResult
from contracts.jobs import AnalysisJob
from contracts.media import VideoAsset
from contracts.reference import ReferenceProfile, SourceRecord
from providers.search.protocol import SearchProvider

app = FastAPI(
    title="Motion X Ray API",
    version="0.1.0",
    description="Turns a short workout video into a rep-by-rep movement report.",
)


def _not_implemented() -> HTTPException:
    """Return the 501 raised by every placeholder route in this scaffold."""
    return HTTPException(status_code=501, detail="Not implemented")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness probe used by Compose/CI; returns a static ok with no I/O."""
    return {"status": "ok"}


@app.get("/v1/exercises")
def list_exercises() -> None:
    """List supported exercises and their variants. FR06. TODO(T12)."""
    raise _not_implemented()


@app.post("/v1/videos", response_model=VideoAsset, status_code=201)
def create_video() -> None:
    """Register/upload a source video asset for analysis. FR01, FR02. TODO(T03)."""
    raise _not_implemented()


@app.get("/v1/references", response_model=list[ReferenceProfile])
def list_references() -> None:
    """List approved reference profiles. FR07, FR11. TODO(T06)."""
    raise _not_implemented()


@app.post("/v1/analyses", response_model=AnalysisJob, status_code=202)
def create_analysis() -> None:
    """Enqueue an analysis job for a video + exercise/variant. FR03. TODO(T08)."""
    raise _not_implemented()


@app.get("/v1/analyses/{analysis_id}", response_model=AnalysisJob)
def get_analysis(analysis_id: str) -> None:
    """Fetch an analysis job's state/stage. FR03, FR12. TODO(T08)."""
    raise _not_implemented()


@app.get("/v1/analyses/{analysis_id}/result", response_model=AnalysisResult)
def get_analysis_result(analysis_id: str) -> None:
    """Fetch the completed AnalysisResult (reps, metrics, score). FR07, FR08. TODO(T07)."""
    raise _not_implemented()


@app.get("/v1/analyses/{analysis_id}/artifacts/{kind}")
def get_analysis_artifact(analysis_id: str, kind: str) -> None:
    """Fetch a private artifact (e.g. pose frames) for the X Ray UI. FR10. TODO(T11)."""
    raise _not_implemented()


@app.post("/v1/analyses/{analysis_id}/cancel")
def cancel_analysis(analysis_id: str) -> None:
    """Request cooperative cancellation of a running job. FR03, FR12. TODO(T08)."""
    raise _not_implemented()


@app.delete("/v1/analyses/{analysis_id}")
def delete_analysis(analysis_id: str) -> None:
    """Delete an analysis and its private artifacts. FR03. TODO(T08)."""
    raise _not_implemented()


@app.post("/v1/references", response_model=ReferenceProfile, status_code=201)
def create_reference() -> None:
    """Create a draft reference profile from curated sources. FR07, FR11. TODO(T06)."""
    raise _not_implemented()


@app.post("/v1/references/{reference_id}/approve", response_model=ReferenceProfile)
def approve_reference(reference_id: str) -> None:
    """Approve a reference profile for use in scoring. FR07. TODO(T06)."""
    raise _not_implemented()


class EvidenceRefreshRequest(BaseModel):
    """Body for POST /v1/evidence/refresh — one exercise technique query."""

    exercise_id: str
    technique_question: str
    allowlist: list[str] | None = None


class EvidenceRefreshResponse(BaseModel):
    provider: str
    drafts: list[SourceRecord]


@app.post("/v1/evidence/refresh", response_model=EvidenceRefreshResponse)
async def refresh_evidence(body: EvidenceRefreshRequest):
    # TODO(operator-auth): gate on operator credentials per docs/API.md before
    # enabling live refresh. The cached default keeps this route credit-safe; a
    # live Tavily refresh must be restricted to an authenticated operator.
    """Refresh evidence source drafts for a reference. FR11.

    Returns DRAFT SourceRecords (never approved). SEARCH_PROVIDER selects the
    provider: 'tavily' makes a bounded live call; anything else uses the cached
    offline default so the route spends zero credits by default.
    """
    from benchmarks.evidence import discover_evidence

    provider_name = os.environ.get("SEARCH_PROVIDER", "cached").strip().lower()
    provider: SearchProvider
    if provider_name == "tavily":
        # T10 must add operator authentication and spend limits before live use.
        raise HTTPException(status_code=503, detail="Live evidence refresh is not enabled")
    else:
        provider_name = "cached"
        from providers.search.cached import CachedSearchProvider

        provider = CachedSearchProvider()

    try:
        drafts = await discover_evidence(
            body.exercise_id,
            body.technique_question,
            provider=provider,
            allowlist=body.allowlist,
        )
    except Exception as exc:  # provider timeout/failure -> honest typed signal.
        envelope = errors.ErrorEnvelope(
            code=errors.PROVIDER_TIMEOUT,
            message=f"Evidence provider '{provider_name}' failed: {exc}",
            retryable=True,
        )
        return JSONResponse(status_code=504, content=envelope.model_dump(mode="json"))

    return {
        "provider": provider_name,
        "drafts": [record.model_dump(mode="json") for record in drafts],
    }
