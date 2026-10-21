# API

**21 October implementation note:** session, upload and private video metadata routes
are implemented; 10 other product handlers remain 501 placeholders. Response
models now expose domain schemas through OpenAPI. Cached evidence discovery is partial;
selecting live Tavily returns 503 until T10 operator/spend controls exist. The checked-in
OpenAPI is generated with `scripts/export-contracts.sh`, with a drift check in CI.

Motion X Ray exposes a single versioned HTTP surface under `/v1`, served by the FastAPI
app at `app.main:app` (`services/api`). This document lists every endpoint, the uniform
error envelope, and the canonical error codes. The route shapes here are the contract the
web client and tests build against; unfinished handlers return HTTP 501 until their
owning task lands. FastAPI serves `GET /openapi.json` automatically
from these declarations — the OpenAPI document is generated, not hand-written.

A liveness probe `GET /healthz` exists outside the `/v1` surface for Compose/CI.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/session` | Establish/reuse an anonymous signed cookie and obtain CSRF token (implemented). |
| GET | `/v1/exercises` | List supported exercises and their variants (FR06). |
| POST | `/v1/videos` | Register/upload a source video asset for analysis (FR01, FR02). |
| GET | `/v1/videos/{video_id}` | Read unexpired video metadata for its session owner (implemented). |
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

That is fourteen `/v1` endpoints in total.

## Implemented private upload protocol (T03a)

Configure a persistent `SESSION_SECRET` of at least 32 bytes and the exact browser
`APP_ORIGIN`. Missing/invalid session configuration returns503. Production requires
HTTPS and Secure cookies; development/test allows local HTTP. No accounts are needed.

1. GET `/v1/session` establishes/reuses an HttpOnly, SameSite=Strict cookie and returns
   `SessionInfo {csrf_token, expires_at}`. The signed identity currently expires after
   24 hours; reload does not extend it. Keep the secret stable across API restarts.
2. POST `/v1/videos` sends raw video bytes with `Content-Type: video/mp4`,
   `video/quicktime` or `video/webm`, `X-Upload-Consent: true`, `X-CSRF-Token`, the cookie
   and exact `Origin`. This is a binary body, not multipart. Actual stream size is bounded
   independently of Content-Length. Default maxima:100MiB,30s,1920px per encoded axis,
   240fps. Settings may reduce the size/duration limits, not silently raise them.
3. A201 `VideoAsset` records actual bytes/hash and ffprobe duration/dimensions/rotation.
   GET `/v1/videos/{video_id}` returns the owner's metadata; other owners, expired and
   missing assets receive404. Every implemented route response has Cache-Control:no-store.

No original bytes are served. `timestamp_map_key` remains null until the worker builds
an audio-free proxy and original/proxy PTS mapping. Metadata acceptance does not prove
all frames can decode or an analysis succeeded. Job/lifecycle/artifact routes remain
their later work package. New route failures use the flat ErrorEnvelope; session/CSRF
failures403, consent/length400, size413, MIME415, invalid media422, configuration/storage503.

## Planned integration behaviour (T04–T11; not new routes)

- Artifact responses must preserve observation timestamps, validity and provenance.
  Expose alignment paths and per-rep/set breakdowns only through implemented, versioned
  contracts and private artifact access. Do not add guessed fields to generated clients.
- Unapproved/experimental/incompatible references and missing required metrics must not
  expose valid-looking score or best/worst values in either the API or UI.
- A 2D-only fallback reports lost capabilities explicitly; it cannot satisfy current
  3D-required exercise profiles. Preserve usable measurements/playback on partial output.
- Operator reference approval must check rights and technical suitability separately;
  discovery, upload ownership and dataset availability do not automatically approve form.
- Internal numerical or tracking libraries add no public endpoints. Keep their native
  objects/indices out of response schemas. See DATA_MODEL and D009/D010.

## Error envelope fields

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

## Implemented local pose lifecycle (21 October 2026)

Create a session with `GET /v1/session`; retain the HttpOnly cookie. Mutations require
the exact configured Origin and returned X-CSRF-Token. Upload raw video through the
existing consent-gated `/v1/videos` route. Then:

| Method and route | Behavior |
| --- | --- |
| POST `/v1/analyses` | 202; body video_id, exercise_id, optional variant, request_key. Same request is idempotent; conflicting reuse409. |
| GET `/v1/analyses/{id}` | Owner-only status; analysis_scope=pose_only, lease_owner/result_key=null. |
| POST `/v1/analyses/{id}/cancel` | Owner/CSRF-gated cancellation. |
| DELETE `/v1/analyses/{id}` | 204; immediate access revocation, physical cleanup pending. |
| GET `/v1/analyses/{id}/result` | Owner-only committed report; unfinished409, unavailable/corrupt503, foreign/deleted/expired404. |

All lifecycle responses use no-store and nosniff. Processing versions are server-owned.
Results currently contain real pose provenance and warnings, null scores, and empty
rep/metric arrays. Report retention defaults to7 days independently of raw-media TTL.
Artifact streaming remains unimplemented; these routes do not yet provide a browser
video/overlay experience. See generated OpenAPI for current request schemas.

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
