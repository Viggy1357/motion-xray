# T03b proxy checkpoint and blocked worker handoff

21 October 2026, Malaysia time. FR02/FR04/FR10/FR12 supporting component.
Only the standalone proxy component is accepted. T03/T08.1 service acceptance is open.

## Accepted change

`packages/providers/providers/pose/proxy.py::build_proxy(video, source_root, output_dir)`
verifies the original bytes/hash/metadata, creates a private audio-free H264 proxy,
and writes `proxy.mp4` plus `timestamp_map.json`. It preserves actual frame counts and
records both ffprobe timelines, rather than calculating timestamps from nominal FPS.
Rotation is applied and right/bottom padding to even dimensions is explicit. Unexpected
rotation, padding, frame loss or timestamp drift fails clearly. The2ms encoding guard
is versioned as `ffmpeg-proxy-v1`; no exercise threshold/scoring policy changed.

Typed models are in `packages/contracts/contracts/proxy.py`, with generated JSON Schema
for TimestampPair/ProxyTimestampMap. They are private artifact contracts, not newly
enabled HTTP responses. Existing OpenAPI/frontend contracts remain unchanged.

Files use private permissions and exclusive creation; existing outputs are preserved,
and owned partial outputs are removed on failure. Lexical symlinks and source escape
paths are rejected. The encoder and probes have finite timeouts. No ML/LLM is used here.

## Observed verification

- `./scripts/test.sh python`: exit0;369 tests pass, Ruff clean, mypy45 files clean.
  This includes28 proxy cases and the existing upload, store, pose and contract checks.
  One pre-existing Starlette/AnyIO deprecation warning remains. Provider smoke commands
  ran offline, without credentials; they are not live coaching acceptance.
- Real owned Squat.MOV in an isolated worker container:427 frames,1080x1920 output,
  6,235,104 proxy bytes. All recorded source/proxy PTS match after start-time normalization;
  maximum observed error0s. Output has exactly one video stream and no other streams.
  Original input is unchanged. Evidence: `T03b-proxy-results-2026-10-21.json`.
- The private output is `artifacts/development/proxy-real/proxy.mp4`, with its typed map
  alongside it. Footage, proxy bytes, private drafts and raw receipts are gitignored.

The real check rebuilt the worker image to include the delivered T04 adapter, then used
the reviewed proxy modules. A separate real stream inspection confirmed video-only
output after tightening that validator. The helper is not invoked automatically by
uploads; uploaded VideoAsset.timestamp_map_key still remains null.

## Why the queued flow did not land

The worker task produced three rejected code drafts; a fourth request with reasoning
enabled exhausted32,768 completion tokens and returned no final source. Total worker
usage is99,574/100,000 task tokens. Defects included:

- Confusing model/checkpoint hashes with content-addressed pose frame hashes.
- Cleaning directories without proving ownership, missing symlink checks and unsafe
  artifact resolution that could cross job boundaries.
- Not reaping terminated child processes, missing fencing/cleanup error handling and
  incomplete cancellation/deletion/timeout behavior.
- Invented Store APIs, invalid/missing fixture fields, wrong hashes and syntax defects.

Independent API/retention drafts also failed review (including invalid database state
strings and unsafe/mis-scoped artifact paths). None of those drafts is applied or
registered. `services/pose/worker.py` remains the existing stub, job routes remain501,
and no physical janitor is enabled. The working T03a upload and T08.1a store are intact.

This follows AGENTS.md's execution policy: "stop and report a blocked worker rather
than silently doing a large Codex rewrite." It is a blocked implementation route,
not exhausted account credit or a claim that the planned workflow is impossible.
Do not repeat the same large generation request or silently increase the allocation.

## Concrete next acceptance packet

Revise the approach before more paid dispatch. Keep these pieces separate and accept
each against real contracts before adding its consumer:

1. **Parent only:** one small subprocess supervisor around existing Store.claim,
   heartbeat/checkpoint/finish. A controlled fixture subprocess is sufficient to prove
   cancellation, deletion, timeout, reclaim fencing and process reaping. No ML, HTTP,
   new database schema or retention implementation in this piece. Preserve an existing
   attempt directory on collision; publish only after validated output exists.
2. **Child only:** call the accepted proxy helper, then the delivered MediaPipe adapter
   on the original video. Publish a typed manifest and honest pose-only AnalysisResult
   with empty measurements and null score. Use the actual pose artifact key, not the
   checkpoint hash. Validate one authorized <=30s lat segment and an eligible full clip.
3. **Consumers last:** authenticated lifecycle/artifact routes and physical retention,
   with coordinated schemas and ownership checks. Test raw/media expiry separately from
   report expiry. No cancelled/deleted worker may publish or expose outputs.

The private drafts under `artifacts/development/` are diagnostic material, not an
implementation baseline. In particular, do not copy `job-worker-final` or `job-api`
into services. Store/media/pose/proxy contracts and committed code remain authoritative.

## Accounting

Four scoped tasks,10 direct Nebius generations including failures:193,333 reported
tokens and conservative USD0.734405 at the existing USD2/M input and USD5/M completion
guard rates. Per-task totals: proxy41,036; worker99,574; HTTP20,425; retention32,298.
Ledger: `../development-usage-T03b-2026-10-21.json`. Independent tasks ran in parallel
within the existing concurrency cap; only one writer integrated accepted files.

No private media/credentials were used as model context. No Tavily, product-runtime
coaching or protected-backup activation. Pricing/account balance and four historical
unknown calls remain unreconciled. Codex usage is separate; no numerical savings claim.
