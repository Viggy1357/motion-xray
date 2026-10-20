# T21.1 / T04 resumed implementation batch

20 October 2026, Malaysia time. Work in progress; this is not a Gate A pass.

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

## Pending acceptance

### T04.1 accepted mapping component

Qwen 235B in JSON mode returned the small mapping draft in 35.28s (1,233 input,
2,308 completion). Source/syntax inspection found a test syntax error and finite/type
mask defects. One targeted repair took 50.60s (3,255 input, 3,387 completion).
Codex reviewed and integrated small corrections for invalid-derived provenance,
test regex/threshold expectations and missing/no-detection regressions.

`./scripts/test.sh python` exits 0: Ruff clean, mypy clean over 37 files, 78 tests pass
(17 new mapping tests), one existing dependency deprecation warning. Offline provider
smokes remain dry-run. Public contracts and exercise thresholds are unchanged.

Validated artifacts and the real timestamped adapter must land before a real
pose-sequence acceptance claim; reusable T21.1 tooling remains deferred. The single-frame
preflight is useful runtime evidence, not a substitute for those requirements.
