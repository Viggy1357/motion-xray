# HM05/HM07 exercise calibration and HM06 grounded coaching

Completed locally23 October2026 (run began22 October). Personal prototype,
provisional unreviewed reference resemblance; not a validated technique grade.

## Delivered

All four exercises now return actual deterministic movement reports through the
owner-scoped `/movement-report` route. Curl/press measure elbow and upper-arm/torso
angles; squat measures knee/hip angles directly. Each also measures the projected
torso axis. Estimated3D and camera-plane measurements stay separate. Squat does not
reuse elbow geometry. Missing/invalid/interpolated joints remain null with reasons.
Completed-cycle candidates and excluded fragments are separate, and logged reps
are never overwritten. Strict pose publication and legacy0.2 `/result` stay intact.

| Owned full clip | Candidate cycles used | Metric entries | Experimental resemblance |
|---|---:|---:|---:|
| Lat pulldown | 5 | 160 | 62.1/100 |
| Standing dumbbell curl | 2 | 64 | 81.6/100 |
| Bodyweight squat | 1 | 32 | 43.0/100 |
| Incline dumbbell press | 4 | 128 | 53.5/100 |

These are limited measured samples, especially the one squat cycle, not the actual
full-set rep count. Top-level technique `score` remains null. Experimental estimates
live separately under `prototype_assessment`, always partial and unreviewed.

## Actual reference-video workflow

Six publisher demonstration videos were downloaded locally, viewed as contact sheets
and passed through the existing MediaPipe container. Intro/outro/setup/camera-cut
regions were excluded using original video timestamps. No user set served as a reference.

| Exercise | Primary used | Usable primary windows | Secondary measured | Secondary usable cycles |
|---|---|---:|---|---:|
| Curl | [Muscle & Strength](https://www.muscleandstrength.com/exercises/standing-dumbbell-curl.html) | 2 | [Catalyst](https://www.catalystathletics.com/exercise/821/Dumbbell-Curl/) | 1 |
| Press | [Catalyst](https://www.catalystathletics.com/exercise/819/Dumbbell-Incline-Bench-Press/) | 5 | [Muscle & Strength](https://www.muscleandstrength.com/exercises/incline-dumbbell-bench-press.html) | 0 |
| Squat | [Muscle & Strength prisoner squat](https://www.muscleandstrength.com/exercises/bodyweight-squat.html) | 2 | [CrossFit air squat](https://www.crossfit.com/essentials/the-air-squat) | 1 |

All three secondaries are retained as descriptive evidence and excluded from numeric
baselines: fewer than two usable cycles. References are not pooled or selected by the
highest user score. The squat primary has a different arm position; camera/variant
compatibility remains explicitly unreviewed. Press bench inclination/contact is not
calibrated from these body landmarks. No source is claimed to be technique-approved.

Curl automatic reference segmentation fragmented. A Nebius visual reviewer examined
only two public-reference mosaics and proposed two coarse Muscle & Strength windows
(15/18/21s and21/24/27s). Actual pose measurements then passed the coverage/required
metric gates for both. These are unreviewed phase proposals, not independent ground
truth. Catalyst manual proposals were rejected by the visual review, not forced in.
The Vimeo landing-page downloader initially required login; the publisher's public
embedded player was subsequently retrieved with its actual embedding-page Referer,
without credentials/cookies. Reference media/pose arrays remain ignored and are not
redistributed in Git. Public source/pose hashes and labels are recorded instead.

Configuration: `packages/movement/movement/configs/exercise-reference-bands-v1.json`.
Reproduction manifest: `data/review_configs/exercise-reference-inputs-v1.json`.
Use the pinned development downloader in `infra/experiments/reference-download.Dockerfile`,
the existing `scripts/pose_smoke.py` container entrypoint, and then run
`scripts/calibrate_exercises.py --manifest data/review_configs/exercise-reference-inputs-v1.json --output packages/movement/movement/configs/exercise-reference-bands-v1.json`
inside a source-mounted container with contracts/providers/movement on PYTHONPATH.
The manifest contains original PTS windows, source URLs/hashes, pose hashes and origins.
The calibration audit preserves descriptive ranges even for rejected secondaries.

Reference and user windows use the same generic arithmetic: nearest event sample
within0.1s, min/max/excursion over observed samples, actual supporting-frame coverage.
New exercises require all four selected components with >=80% observed support per
eligible user cycle and >=2 usable reference windows. This is visibility, not accuracy.
Deviation outside each observed band is signed. Resemblance uses the same explicit
unreviewed30-degree normalization proposal as the lat experiment, with equal four-metric
means per cycle and then equal eligible-cycle means. Lat's three-family aggregation
and frozen trusted scoring gates remain unchanged. Missing required data yields null.

## Grounded coaching

`POST /v1/analyses/{id}/coaching` is an explicit user action, not an automatic model
call from GET/render. It rebuilds the checked owner-private movement report, joins
observed metrics to actual completed segment IDs/times/sides, and prepares at most
eight measured observations plus one sourced general cue. Angle event/range names,
units, reference limitations and original timestamps are preserved. Replay uses the
actual report segment, not model-written timestamps.

NVIDIA Nano selects candidate IDs only. Local code validates IDs and renders the
fixed text; the model cannot invent measurements, scores or claim IDs. Cue sources
are a local allowlist of IFA, ACE and Muscle & Strength summaries, not evidence that
the camera observed bench contact, wrist position, injury risk or muscle activation.
No raw video or pose arrays are sent to the runtime LLM.

The server pins `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`,500 output tokens,35s total
deadline and zero SDK retries. SQLite atomic reservation/cache survives restarts:
20 global reservations/UTC day,4 per owner/day,100 lifetime. Failed/expired reservations
are retained and fail closed; changing model/report/evidence changes the cache key.
No retries erase quota history. Wrong/foreign owner, CSRF, expired raw pose and deletion
are checked before cache use and again before returning the result. Cache does not
extend video/pose access. Physical cleanup of this new text-cache ledger is future work.
Local `ALLOW_LIVE_COACHING=true` is enabled in ignored `.env`; no paid hosting activated.

Actual owned lat set -> checked report -> NVIDIA -> validated candidate selection ->
browser feedback passed:1427 input/38 output tokens,1.103s. Replay clicked to26.96s
for the26.81s segment start. A duplicate after API restart returned200 with one
reservation before and after: no second model call. Browser curl result81.6 verified.
Three other reports also passed real same-origin HTTP checks through Next, not just
offline arithmetic. General guidance is not yet personalized prescriptive correction.

## Checks, review and costs

- Container Ruff/mypy71 sources and **971 Python tests** pass; existing upstream
  Starlette/AnyIO deprecation warning remains. Web typecheck/production build pass.
  OpenAPI/TS regenerated for the POST route; no new dependency or host installation.
- Deterministic repeated real reports match. Analytic geometry, knee/hip distinction,
  cycle gaps, null/zero, reference hashes/windows/configs, side/duplicate/coverage,
  family arithmetic, owner/CSRF/TTL/revocation, durable cache and atomic quotas tested.
  Harness uses `python -m pytest` so repository fixture namespaces resolve consistently.
- Independent Nebius method/UI/security reviews were read and checked against source.
  Fixed test geometry/aspect-ratio errors, generic summarizer accidentally using lat-only
  groups, synthetic coaching rep joins, signed deviations, source support gates,
  event-label ambiguity and dead UI model metadata. Added explicit cache precheck and
  lifetime quota. Reviewer claim that side ties choose right was incorrect: source
  and tests retain left ties. No test skip/suppression or scoring-gate weakening.
- Two output-budget failures were rejected. Two later malformed output envelopes
  contained complete source strings under exact allowed paths; recovered and reviewed
  locally, with original failures retained. A bad coaching draft was corrected before
  any live runtime call. Initial preparation/import/type/fixture failures were not
  represented as completed functionality.
- **14 direct Nebius development calls**,315,349 tokens across bounded tasks (largest
  task129,506, below200k), guard cost$2.459055. One actual runtime call guard$0.003044.
  Aggregate commitment$13.45014265 includes the historic$1 contingency once; account
  balance unverified, USD70 active/USD30 protected unchanged. No Tavily or paid hosting.

Evidence: `HM057-real-assessment.json`, `HM057-reference-calibration.json`,
`HM057-http-acceptance.json`, and `../development-usage-HM057-HM06-2026-10-23.json`.

## Next

HM02 durable guest profile/workout logs and ownership continuity, then HM09 synchronized
pose overlay/timeline, free-first hosting/judge upload acceptance and submission QA.
Reference/normalization accuracy and additional metrics remain future review work;
the owner can review the present personal prototype. Current derived reports still
depend on retained raw pose (up to24h). No cross-device sign-in or camera sensor product
was implemented in this run.
