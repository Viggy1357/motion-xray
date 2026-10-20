# T21.1 / T04 resumed implementation batch

20 October 2026, Malaysia time. Three local pose components delivered; T01 runtime
coaching remains open. This is not full analysis/MVP acceptance.

## Inputs and local preflight

Four private clips are present. Verifiable metadata and intended short diagnostic
segments are recorded in `data/demo-clips.json`; none is an approved reference.
Curl (20.653333s) and squat (14.248333s) fit the duration limit. Incline chest press
(39.923333s) and lat pulldown (55.111678s) require explicitly identified segments;
the full inputs have not passed the product's 30-second upload limit.

Containerized ffprobe reports display rotation -90 degrees for curl/squat and -180
for press. FFmpeg autorotation produced upright 1080x1920 curl/squat images and an
upright 1920x1080 press image, inspected locally. No footage was sent to Nebius.

The existing Linux/aarch64 worker imports MediaPipe 0.10.14, NumPy 2.1.2 and
opencv-contrib-python 5.0.0.93. The versioned Full checkpoint loads in about 0.064s
in one diagnostic run; this is initialization only, not an end-to-end performance
benchmark. Source, checksum and terms are in `data/pose_models/mediapipe-full-v1.json`.
The [official model card](https://storage.googleapis.com/mediapipe-assets/Model%20Card%20BlazePose%20GHUM%203D.pdf)
states Apache-2.0 and describes limitations. No GHUM body-model assets were downloaded.

One-frame IMAGE-mode diagnostics at lat-pulldown 10s and each new clip 5s detect one
pose each. Lat-pulldown far elbow/wrist visibility is approximately 0.091/0.103,
versus 0.930/0.777 for the visible side. Curl and press also have occluded far arms;
curl feet are cropped. Squat includes other people/mirrors. These observations do
not validate tracking identity, depth, temporal synchronization or rep accuracy.
Local JPEGs and raw diagnostic output stay in ignored `artifacts/`.

## Development route and budget

Codex coordinates and reviews; Nebius generates substantive drafts. No draft is
automatically applied or executed. Private media and credentials are excluded from
coding prompts. The $70 active ceiling and protected $30 remain separate; no Tavily
calls or paid product coaching calls are made in this batch so far.

The initial three draft outcomes are:

| Request | Input | Completion | Outcome |
| --- | ---: | ---: | --- |
| T21.1 Kimi Code broad handler | 975 | 24,576 | Truncated; 20,787 reasoning tokens; rejected |
| T21.1 Qwen 235B compact handler | 923 | 5,455 | Malformed envelope and incorrect placeholder/accounting logic; rejected |
| T21.1 Kimi Code pure core | 709 | 24,576 | Reasoning-only exhaustion; rejected |
| T21.1 Kimi K2.6 generic thinking-disabled | 709 | 16,384 | No visible content; length finish; control compliance not established |
| T21.1 Kimi K2.6 template thinking-disabled | 710 | 3,796 | Complete but rejected: incorrect validation, locking, accounting and weak tests |
| T21.1 Kimi Code focused repair | 973 | 11,836 reported so far | 600s deadline, no visible content; final billed usage unknown |

The request policy was diagnosed before parallel dispatch. The fifth request used
the upstream-documented `chat_template_kwargs.thinking=false` for Kimi K2.6, but
source review rejected its output. A focused Code repair had 49,152 completion space
and a justified 150k task allocation, but exceeded the 600s deadline. API acceptance
is not proof a reasoning control was honored. No generic accounting code was applied.
To keep supporting tooling from replacing T04, the next request is one small mapping
task using Qwen JSON mode and the manually bounded bootstrap. Dispatch stays sequential,
under $0.35 maximum per request and reconciled far below the $70 operating ceiling.
The reusable dispatcher entrypoint was removed because its required core is unavailable.

Usage records include request IDs and finish reasons, including failures, under
ignored `artifacts/development/`. Conservative dispatch accounting uses USD2 per
million input and USD5 per million completion tokens; those are reservation rates,
not claimed invoice prices. Reasoning is part of completion and is not added again.
Historical four unknown calls remain unknown, with $1 contingency, not a claimed
balance reconciliation. The earlier known Kimi call remains approximately $0.02094.

## Component acceptance

### T04.1 accepted mapping component

Qwen 235B in JSON mode returned the small mapping draft in 35.28s (1,233 input,
2,308 completion). Source/syntax inspection found a test syntax error and finite/type
mask defects. One targeted repair took 50.60s (3,255 input, 3,387 completion).
Codex reviewed and integrated small corrections for invalid-derived provenance,
test regex/threshold expectations and missing/no-detection regressions.

`./scripts/test.sh python` exits 0: Ruff clean, mypy clean over 37 files, 78 tests pass
(17 new mapping tests), one existing dependency deprecation warning. Offline provider
smokes remain dry-run. Public contracts and exercise thresholds are unchanged.

### T04.2 accepted artifact component

Qwen artifact generation took 78.73s (1,277 input, 2,385 completion); one source-guided
repair took 106.86s (3,313 input, 3,814 completion). Codex integrated bounded fixes for
the tempfile import/cleanup, exclusive-link installation race, line-size comparison
and tests that previously conflated independent bounds or corrupted JSON before hashing.
`./scripts/test.sh python` exits 0: Ruff/mypy clean over 38 files and 94 tests pass,
including 16 artifact tests. Symlinks, traversal, duplicate JSON, malformed/gapped
ordering, conflicting writes, hash tampering and failed-generator cleanup are covered.

### T04.3 accepted local provider and diagnostic

The Qwen adapter draft completed but violated its file allowlist and source requirements;
it was rejected. A Kimi K2.6 template-control repair supplied the working adapter.
Its oversized, faulty tests were replaced by a smaller focused draft and one targeted
repair. Codex integrated bounded fixes for contract fields, original-PTS parsing,
source clock quantization, lazy runtime injection, actual fixture semantics and cleanup.
The generated diagnostic needed real Pydantic/Path arguments, correct normalized-XY
projection, animation-frame updates, hash-verified local video seeking and removal of
an unintended extra inference. No generic helper code was substituted into the product.

`./scripts/test.sh python` exits0: Ruff clean, mypy clean over38 files,131 tests pass
(37 adapter cases). Existing Starlette/AnyIO warning remains. MediaPipe emits upstream
feedback-tensor/protobuf warnings during actual inference; these did not prevent output.
No public schema, exercise threshold, score weight or dependency was changed.

All commands used the existing worker image
`sha256:c7f177e304d6fbc8ef85fd01bdfdfb197a42a91c991d3918e1ea59dbf48e9e02`
with mounted provider source SHA256
`48c873d9f2425e70963b7732b6f6f97911f51e1f590fc0083d37bfaa3eab4d9f`.
Environment: Linux/aarch64, Python3.12.15, MediaPipe0.10.14, NumPy2.1.2,
opencv-contrib-python5.0.0.93. Inference is CPU-local with no network or credentials.

| Source / explicit segment | Frames / actual Hz | All-invalid frames | Inference elapsed |
| --- | --- | --- | --- |
| Lat pulldown10–20s | 300 /29.96 | 0 | first-process9.8039s; second8.9130s |
| Curl0–10s | 300 /30.00 | 3 | 23.0409s |
| Squat0–10s | 300 /30.00 | 24 | 18.3054s |
| Incline press0–10s | 299 /29.89 | 3 | 23.5255s |

These are small owned-clip diagnostics, not general accuracy or speed benchmarks.
Lat's left elbow coverage is100%, left wrist98.67%; far right elbow31.33%, wrist36.67%.
Other clips predominantly expose the right side; far-arm/cropped-foot failures remain
in the artifact. A visibility/presence mask is not measured depth accuracy.

Lat artifacts are1,555,317 bytes. Two fresh landmarker instances in the same process
produced the same content hash
`ceb52406971fe89772ed8bd4cd12a9a1a96297d5a0778d195099ea66503d05f9`.
This is evidence for that backend/input only. Self peak RSS379,600KiB and child peak
323,312KiB are separate measurements, not a summed whole-system peak. Full per-clip
coverage/provenance is in `T04-pose-results-2026-10-20.json`.

The first202-frame run exposed microsecond rounding in FFprobe PTS. Greedy30Hz sampling
mistakenly skipped timestamps0.33us below1/30s. Comparison now permits1us formatting
tolerance, with a regression fixture and explicit sampling-v1 provenance; raw times
remain untouched. The initial private artifact/manifest was preserved, not rewritten.

Browser verification used the original source clock at10.005s,15.045s and19.717s,
plus playback and3D yaw drag. Visible joints aligned with the foreground subject in
those inspections; automatic identity verification is still false. The loopback preview
is `http://localhost:8765/diagnostic.html` while its local container runs. Source video
is read locally and checked against the analysis SHA before display; it is never uploaded.
Screenshot proof remains private at `artifacts/pose-smoke/lat-pulldown/viewer-proof.png`.
The viewer is a diagnostic; the main web app and durable job loop remain scaffolds.

## Accounting and next work

`../development-usage-2026-10-20.json` records all15 direct coding requests, including
rejected drafts. Known-final usage162,809 tokens; timeout partial usage12,809 tokens
is not treated as final billing. Conservative known-final costUSD0.694483 plus the
full timeout reservationUSD0.263922 gives new-batch commitmentUSD0.958405. Including
the old estimatedUSD0.02093765 andUSD1 unknown-history contingency yieldsUSD1.97934265
of dispatch accounting, not a verified balance or invoice. Four old calls remain
unreconciled. No backup activation, Tavily call or paid runtime-coaching call occurred.

Three pose components used83,996 reported development tokens. T21.1 used91,622 reported
tokens including its timeout partial usage, but produced no accepted reusable helper.
Defer that loop. Continue sequential bounded requests and explicit usage checkpoints;
the remaining MVP forecast stays provisional after this first small calibration.

Next: T03/T08.1 private upload and durable lifecycle invoking this adapter; T05 visible-side
measurements/quality/calibration/full-cycle reps. Keep missing outputs unavailable.
T01 structured runtime Nemotron, reviewed references, scores and the product viewer
remain unfinished. Incline press is still a T17 candidate, not supported scoring.
