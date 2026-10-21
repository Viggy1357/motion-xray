# T03a — signed sessions and private validated uploads

21 October 2026, Malaysia time. FR02/FR12 ingestion prerequisite for FR03. T03 remains
in progress: proxy/PTS mapping and real job execution are separate T03b/T08.1b work.

## Delivered

- Stateless HMAC-SHA256 anonymous identity in an HttpOnly SameSite=Strict cookie,
  exact-origin mutation checks and a session-bound CSRF token. Duplicate/invalid
  cookies and security headers fail closed. Production requires HTTPS/Secure cookies;
  missing or short SESSION_SECRET returns503. No credentials are generated silently.
- GET `/v1/session`, binary POST `/v1/videos`, owner-only GET `/v1/videos/{video_id}`
  metadata. Consent and identity are checked before receiving media. Implemented routes
  return no-store responses, with sanitized machine-readable errors.
- Bounded streaming with actual-byte limits, SHA256, body deadline, independent
  Content-Length checks and real ffprobe metadata validation. Container/protocol/codec,
  duration, dimensions, frame-rate and rotation rules are explicit; process errors do
  not disclose stderr or filesystem paths. Defaults remain100MiB/30s.
- Private0600 originals, atomic placement followed by T08.1a metadata registration,
  and cleanup of owned staging/final files on rejection or failure. Existing collision
  directories and other assets are preserved. Controlled parent symlinks are rejected.
- SessionInfo is additive to contracts0.2.0. OpenAPI, JSON Schema and frontend types
  are regenerated together. FFmpeg7:5.1.9-0+deb12u1 in the API reuses existing container
  tooling for metadata validation; ML dependencies remain isolated in the worker.

Implementation: `services/api/app/{session,ingest,uploads}.py`, router wiring in main;
contracts/session and generated exports; API image, Compose VIDEO_ROOT and env example.
Tests: session/ingestion unit cases, upload HTTP integration, baseline/schema inventory.
API/ARCHITECTURE/OPERATIONS/DELIVERY/TASKS and the project delivery skill record status.

## Verification

- `./scripts/export-contracts.sh`: exit0, generated OpenAPI/JSON Schema/TypeScript.
- `./scripts/test.sh all`: exit0, Ruff clean, mypy43 files clean,340 tests pass,
  web TypeScript check and production build pass. One pre-existing Starlette/AnyIO
  deprecation warning and the empty scaffold's Tailwind warning remain.
- Final bounded asset-ID validation adds one regression case; `./scripts/test.sh python`
  exits0 with341 tests, lint/types clean. Overlong metadata IDs return private404 rather
  than an unhandled storage-validation exception. No frontend/schema change follows it.
- Provider smoke commands ran offline with no credentials/network, not live inference.
- Real HTTP acceptance ran an isolated API subprocess on container loopback, using a
  throwaway session secret and private state. No media or credentials went to Nebius.
  Owned Squat.MOV uploaded201:27,808,876bytes,14.248333s,rotation-90, actual stored
  SHA256 matched the original, source permissions0600. Owner metadata persisted across
  API process restart; another session404, badCSRF403, invalid media422, full55s lat
  pulldown422. No staging/rejected-file leaks. Sanitized evidence:
  `T03a-upload-results-2026-10-21.json`.

Initial checks exposed draft/test-harness defects, including incorrect generated paths,
imports, cookie-jar misuse, timestamp handling, malformed rotation fallback, missing
cleanup and invented SessionInfo fields. They were corrected before the final pass;
no model-generated assertion of executed tests was accepted as evidence.

## Delegation and cost

Eight direct Nebius Kimi-K2.6 draft/repair calls across three scoped tasks:
session34,325tokens; ingestion63,017; HTTP24,312. Each is below its100k allowance.
Total121,654 reported tokens, conservative USD0.440195 at the existing USD2/M input
and USD5/M completion guard rates. This is not verified invoice pricing or balance.
See `../development-usage-T03a-2026-10-21.json`; format-rejected drafts remain counted.
One local JSON preflight failure made no network request. No hidden SDK retries.

After the user's parallelism clarification, independent API and ingestion repair
workers overlapped, with one integrating writer. Codex reviewed relevant diffs, made
bounded integration/test corrections and ran container checks. There is no measured
Codex savings claim. No Tavily, paid runtime coaching or protected-backup activation.
Earlier four unknown provider calls and account balance remain unreconciled.

## Remaining

T03b/T08.1b must build an audio-free proxy and original/proxy timestamp map, invoke
actual MediaPipe from the durable worker, and implement private lifecycle/artifact
access plus physical TTL cleanup with cancellation/deletion/restart races. Metadata
acceptance does not prove every frame decodes, pose identity or completed analysis.
`timestamp_map_key` stays null and original media is never served by these routes.

The user-facing web upload/capture viewer remains T11.1. Anonymous identities currently
expire after24h without renewal/recovery, an explicit release limitation independent
of report retention. The real smoke used isolated private state, not a deployed app or
a populated user's `.env`. Keep a persistent SESSION_SECRET when enabling local uploads.
No thresholds, scores, exercise scope, reference approval or runtime coaching changed.
