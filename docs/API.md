# API

Motion X Ray exposes a single versioned HTTP surface under `/v1`, served by the FastAPI
app at `app.main:app` (`services/api`). This document lists every endpoint, the uniform
error envelope, and the canonical error codes. The route shapes here are the contract the
web client and tests build against; in the current scaffold each `/v1` handler returns
HTTP 501 until its owning task lands. FastAPI serves `GET /openapi.json` automatically
from these declarations — the OpenAPI document is generated, not hand-written.

A liveness probe `GET /healthz` exists outside the `/v1` surface for Compose/CI.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/exercises` | List supported exercises and their variants (FR06). |
| POST | `/v1/videos` | Register/upload a source video asset for analysis (FR01, FR02). |
| GET | `/v1/references` | List approved reference profiles (FR07, FR11). |
| POST | `/v1/analyses` | Enqueue an analysis job for a video + exercise/variant (FR03). |
| GET | `/v1/analyses/{analysis_id}` | Fetch an analysis job's state/stage (FR03, FR12). |
| GET | `/v1/analyses/{analysis_id}/result` | Fetch the completed `AnalysisResult` (FR07, FR08). |
| GET | `/v1/analyses/{analysis_id}/artifacts/{kind}` | Fetch a private artifact for the X Ray UI (FR10). |
| POST | `/v1/analyses/{analysis_id}/cancel` | Request cooperative cancellation of a running job (FR03, FR12). |
| DELETE | `/v1/analyses/{analysis_id}` | Delete an analysis and its private artifacts (FR03). |
| POST | `/v1/references` | Create a draft reference profile from curated sources (FR07, FR11). |
| POST | `/v1/references/{reference_id}/approve` | Approve a reference profile for use in scoring (FR07). |
| POST | `/v1/evidence/refresh` | Refresh cached evidence sources for references (FR11). |

That is twelve `/v1` endpoints in total.

## Error envelope

Every failure returns the same `ErrorEnvelope` body (`services/api/app/errors.py`) so
clients branch on a stable, machine-readable `code` rather than parsing prose. A failure
is an honest, typed signal — never a silently-degraded success (AGENTS.md rule 3).

| Field | Type | Meaning |
| --- | --- | --- |
| `code` | string | One of the canonical error codes below. |
| `message` | string | Human-readable explanation; safe to surface to the client. |
| `retryable` | bool | Whether retrying the identical request may later succeed. |
| `request_id` | string / null | Correlation id for tracing one request through logs. |
| `field_errors` | map / null | Optional per-field validation messages, keyed by field. |

## Error codes

| Code | When it is returned |
| --- | --- |
| `INVALID_MEDIA` | The uploaded media is unreadable or fails validation. |
| `UNSUPPORTED_VARIANT` | The requested exercise/variant is not supported. |
| `INCOMPATIBLE_REFERENCE` | The selected reference is incompatible with the request. |
| `INSUFFICIENT_VISIBILITY` | Pose visibility is too low to analyze reliably. |
| `PROVIDER_TIMEOUT` | A downstream provider timed out (transient; retryable). |
| `RATE_LIMITED` | The caller or a provider budget hit a rate limit. |
| `JOB_EXPIRED` | The job or its artifacts passed the retention window. |
