# Motion X Ray — submission execution plan

Planning checkpoint:22 October2026, Malaysia time. No implementation delegation or
paid model call is launched by this document. User requests the detailed plan first.
Use this plan over historical T-stage dates/next pointers. Implementation remains in
small work packages linked below to the existing FRs. Current source checkpoint1548920.

## 1. Product to deliver

An analysis-first gym companion: choose exercise -> upload/record -> processing ->
review video/pose and estimated movement feedback -> receive a short Nemotron cue ->
save the set -> see workout history and training activity on an illustrative body.

Four exercise targets: lat pulldown, dumbbell curl, bodyweight squat and incline chest
press. Incline implement/bench/view variant is confirmed at intake before its contract
ID is frozen. Lateral raise remains future scope, not a fifth promised demo exercise.

Confirmed owner preferences: same-browser profile first, sign-in later; aim for free
hosting and flag unavoidable cost. No hosting purchase or publication is authorised
by this planning step. Further benchmark assessment/accuracy research stays frozen.

### Must work for release

- One coherent responsive app, not diagnostic scripts as the main experience.
- Private full-set upload, status, cancellation, replay, deletion and clear retention.
- Real pose -> best-effort reps -> exercise metrics -> provisional reference output.
- Estimated reference-match results where supported, explicit unavailable components,
  and observation coverage displayed separately. No universal correct-form claim.
- Actual runtime NVIDIA Nemotron through Nebius; useful structured coaching from metrics.
- Editable rep count, load and notes; persistent same-browser profile/history.
- Four exercise paths demonstrated on real inputs; unsupported view/components degrade
  honestly rather than show a convincing invented score.
- Working judge-access path, public licensed source, setup guide and demo video.

### Include after the first complete loop passes

- Rotatable illustrative muscle avatar and exercise-targeted highlighting.
- Small routines: upper body, lower body and full body using supported exercises.
- Weekly training totals, recent sessions and same-exercise comparable trends.

### Explicitly later

Cross-device sign-in, social features, adaptive training programmes, nutrition, physique
reconstruction, inferred muscle growth/activation, new pose-model tournaments, reference
multi-angle3D, live external-camera hardware and further biomechanics calibration.

## 2. Verified starting point and gaps

| Area | Current evidence | Work remaining |
| --- | --- | --- |
| Foundation | Docker, typed contracts,767 offline Python tests, web build | Preserve checks and migrate new payloads coherently |
| Upload/jobs | Private uploads, durable queue, supervised pose worker, lifecycle | Full-set limits, report stages, web integration |
| Playback/storage | Authenticated proxy ranges/pose/map; manual completed-file cleanup | Library/listing, deletion completion, scheduled retention, deployed persistence |
| Measurements | Lat offline labelled reps and torso/arm components | Automatic best-effort segmentation, runtime assembly, other exercises |
| Benchmark | Frozen provisional source ranges and conditional component engine | Prototype policy/config integration; no new calibration campaign |
| LLM | Nebius provider interface; runtime implementation still raises NotImplementedError | Real bounded Nemotron call, validation, caching and failure path |
| Frontend | Next.js main page still only a scaffold | All four product screens and actual network-driven states |
| Personal log | No workout/profile product flow | Ownership, models, mutations, history and summaries |
| Release | MIT licence exists; public/deployed readiness unverified | Verify repo access/third-party terms, demo access and submission assets |

Metadata checked in the existing container22 October:

| Clip | Duration | Size (decimal MB) | Upload implication |
| --- | --- | --- | --- |
| lat_pulldown.mp4 |55.111678s|6.70| Exceeds current30s limit |
| Incline Chest Press.mov |39.923333s|44.70| Exceeds current30s limit |
| Bicep Curls.MOV |20.653333s|46.01| Fits duration; orientation/metadata still matter |
| Squat.MOV |14.248333s|27.81| Existing real pose/job proof |

Proposed full-set limit:60s/100MiB, subject to the all-four-clip CPU/memory acceptance
test. Change API config, ingestion, proxy/provider, PoseJobInput, model recipe and
fixtures together; increasing only an environment variable cannot fix hard-coded30s
validators. Preserve original PTS; bound sampled frames, decoding time and memory.

## 3. Screen and interaction specification

### Dashboard (/)

- Name/nickname, weekly sessions/sets/reps and a clear Start new set action.
- Recent workouts with exercise, date, estimated/logged reps and analysis status.
- Muscle view: latest exercise targets or weekly exercise activity; labelled illustrative.
- Empty first-run state and one permission-cleared sample path if available.
- No fake streak, progress graph, strength gain or populated sample claimed as user data.

### New set (/new)

- Four supported exercise cards, variant and concise camera-placement guidance.
- File picker/drag-drop; mobile camera recording is progressive enhancement, not the
  only upload path. Camera failure/unsupported codec retains ordinary file upload.
- Consent, real file metadata/size/duration errors, preview and selected exercise.
- Optional load, kg/lb, per-hand vs total load, notes and routine association.
- Upload progress, cancel, retry/idempotency and queued/processing stages.
- Refresh resumes the job. Processing screen says what stage is actually running;
  elapsed time is real, ETA omitted until measured. No invented progress percentage.

### Results (/sets/[id])

- Responsive video +2D overlay + rotatable estimated3D skeleton, sharing source PTS.
- Play/pause, scrub, playback speed and rep selection; missing joints stay missing.
- Observed/reference values, direction of deviation, source/profile version and
  estimated match where the prototype policy permits it. No revival of the old92 trial.
- Observation coverage/usable-rep counts, view limitations and missing-component reasons.
- Short coaching: observations, one next-set cue and relevant limitations/source links.
- Save/edit logged reps/load/notes; Retry coaching does not rerun pose or multiply billing.
- Loading/partial/no-person/failed/expired-video/expired-report/deleted/coaching-unavailable
  states. A saved workout can remain readable after its source video expires.

### History (/workouts, /workouts/[id])

- Group sets by workout/date; filter by exercise; replay while video is retained.
- Manual sets allowed without a video; detected count and user-entered count remain
  distinct. Manual correction updates the log, not the measured timeline or form score.
- Compare only same exercise/variant/profile version. Source range/recipe changes
  break the trend line or are explicitly labelled; do not silently mix incompatible scores.
- Remove a set/workout, delete video separately, and explain which data remains.
- Small editable routine templates and simple completed/planned set counts.

Design first: create desktop/mobile wireframes using these real states and actual
example measurements, review the flow, then implement. No new permanent app UI in
the planning task. Theme: clean gym dashboard with a distinctive muscle-view accent;
do not build avatar customisation or gamification economies.

## 4. Data, API and storage boundaries

### Contracts (schema source remains packages/contracts)

- Exercise catalogue: stable id, variant, supported view, capabilities, profile version,
  display name, targeted muscle groups and reference/source status.
- Analysis request/status: selected exercise/variant, capture-source metadata, scope and
  actual stages; preserve owner fencing and do not expose filesystem keys.
- Prototype report: reps/phase timestamps, metrics with reasons, provisional assessment
  status, component breakdown, coverage, provenance and coaching status.
- Quality: expected sample count, valid observed supporting samples, per-metric coverage,
  usable/total reps, missing reasons and whether view compatibility was reviewed.
- PersonalProfile, Workout, WorkoutSet, RoutineTemplate and RoutineExercise.
- Correction: detected_rep_count vs logged_rep_count, count_source, load_value/unit,
  load_basis (total/per_hand/bodyweight), notes and optional analysis_id.
- Aggregate workout volume only when load semantics are known; bodyweight missing load
  stays unavailable, not measured zero. Do not double dumbbell load without its basis.

Add new public models deliberately; plan a coordinated0.3.0 report schema if the report
shape changes, regenerate OpenAPI/TS/JSON schema and update consumers in one package.
Read old0.2.0 pose manifests through explicit format dispatch; never relax the existing
PoseJobArtifacts validator to make a scored report pretend to be pose-only.

### Proposed routes to finalise in HM01

- GET/PATCH /v1/profile.
- GET /v1/exercises (replace scaffold); exercise/variant capability details.
- GET /v1/videos and existing upload/metadata routes; no public storage keys.
- Existing analyses create/status/cancel/delete/result/artifacts routes, with a new
  explicitly typed prototype-report scope and backward-compatible pose-only dispatch.
- GET/POST /v1/workouts; GET/PATCH/DELETE /v1/workouts/{id}.
- POST /v1/workouts/{id}/sets; PATCH/DELETE /v1/workout-sets/{id}.
- GET /v1/routines; store a customised routine only if editing needs persistence.
- GET /v1/dashboard (or a bounded summary on workouts; decide once, not duplicate).
- Optional POST /v1/analyses/{id}/coaching/retry: owner/CSRF protected, cached/capped.

Endpoint names are planning proposals until HM01 freezes the contract. Every list and
mutation is owner-scoped, paginated/bounded where needed, and covered by cross-owner,
invalid input and deletion tests. No unauthenticated operator evidence/LLM refresh.

### Persistence and ownership

- Keep SQLite plus private files on one durable Docker host for the first release;
  do not add an ORM, vector DB, message broker or cloud bucket without a demonstrated need.
- Same-browser owner credential must survive normal refresh/restart. Current anonymous
  session defaults to24h and can create a new owner after expiry; this is not yet a
  persistent profile. HM02 defines a durable, revocable anonymous device credential
  in Secure/HttpOnly/SameSite cookies and a short mutation session/CSRF token. Proposed
  device lifetime90 days, explicit clear-browser/no-recovery message; no localStorage key.
- Session secret must persist across deploys. Test expiry, renewal, owner continuity,
  revocation and cross-owner access; sign-in/recovery/cross-device merging are deferred.
- Keep current raw/pose24h and report7-day defaults unless changed explicitly. Store
  workout summaries/profile/log entries separately so video/report expiry does not
  silently erase the user's log. Show retention and delete actions in the UI.
- Handle cancelled/failed attempts only after the supervisor has proved reaping;
  add a durable ownership/reaping record or equivalent fencing proof before erasure.
  Never turn the existing conservative deferral into a time-based destructive guess.

## 5. Exact analysis path and estimates

1. Upload validates actual media, orientation, size, duration and consent.
2. Durable job runs real pose; original/source-proxy timestamps and transforms persist.
3. Infer visible-side valid observations; keep estimated3D separate from projected2D.
4. Best-effort completed-cycle segmentation uses real observed samples and return;
   partial/occluded intervals remain flagged. No hard-coded ten-rep labels for uploads.
5. Existing geometry measures per-rep exercise quantities. All thresholds live in
   versioned exercise config; deterministic fixtures accompany changes.
6. Load one frozen provisional profile for the chosen exercise/variant/view.
7. Emit source-band differences and an estimated reference-match result under a
   documented prototype policy. No source/unsupported quantity => honest unavailable.
8. Compute observation coverage from recorded expected vs actually valid supporting
   samples. Filled/interpolated/predicted joints never count as observed evidence.
9. Nemotron receives only the structured evidence needed for a short coaching answer.
10. Validate and publish the final report through lease/deletion fencing, then save
    a workout summary only once, using an idempotent owner-scoped link to analysis_id.

### Prototype scoring/quality policy — bounded integration, not new research

- Keep the current per-component distance formula and source-specific baseline.
- HM04 writes one explicit versioned prototype policy covering included metrics,
  scales/tolerances, weights, eligible reps and coverage. Record engineering hypotheses
  as provisional. Do not silently select convenient constants or tune to this user's
  desired lower score; do not restart a broad calibration study.
- Use a separate status such as prototype_reference_match. The existing full-technique
  aggregate may stay unavailable while a declared subset estimate is shown. A subset
  profile must name its required components; no renormalising missing metrics into a
  better comparable score. Show included/omitted components and profile version.
- Where no usable comparison exists, metrics/rep/log/coaching can still be functional;
  show score unavailable. Four exercise workflows do not imply equal measurement support.
- Quality display: for each metric,100 * valid observed supporting frames / expected
  supporting frames, plus usable/total reps and view-review state. Zero expected frames
  gives unavailable with a reason. This is data coverage, not probability of correctness.
- No combined accuracy/confidence probability, no arbitrary multipliers hidden inside
  form scoring, and no LLM-created angles, rep counts or numerical scores.

### Exercise expansion packet

For each of curl, squat and incline press: confirm actual implement/variant and visible
side/view; reuse existing exercise specs/repo notes; consolidate a small credible cue
matrix; retain a permission-checked provisional reference/profile; implement a minimal
set of observable quantities and phase signal; run the provided clip; record measured
coverage, detector count and limitations. Do not copy lat tolerances into other exercises.

| Exercise | First observable quantities | Excluded unsupported claims |
| --- | --- | --- |
| Lat pulldown | Existing torso/arm ROM and extension; provisional source comparison | Automatic chest contact, lat activation, true world lean |
| Curl | Elbow ROM/return, upper-arm movement and torso excursion | Muscle activation or wrist/grip claims without observations |
| Squat | Visible-side knee/hip ROM, phase timing, view-qualified depth proxy | Unobserved frontal knee mechanics, forces or injury judgement |
| Incline press | Visible-side elbow ROM/extension and upper-arm/torso movement | True bench angle/contact/shoulder safety unless measured |

A local visual intake may be needed; private footage/pose/point arrays are not sent to
Nebius coding workers. Use structured source-only packets. References stay separate
from user sets. Release rights checks apply to any bundled media/profile; do not ship
downloaded reference videos by default. If a profile cannot ship, preserve the useful
metrics and say its comparison is unavailable instead of blocking all app functions.

## 6. Runtime Nemotron work

- Discover an available NVIDIA model ID in the actual account at implementation time;
  start with the smallest model meeting the structured coaching requirement.
- Implement the existing provider boundary. Prompt only with structured evidence,
  observable quantities, missing-data limits and permission-checked source cues.
- Response schema: short summary, up to3 observations, one next-set cue, limitations;
  every numerical/timestamp claim must correspond to supplied evidence.
- Server-side key, fixed provider/model allowlist, bounded input/output and deadline;
  SDK automatic retries off. Proposed validation request <=2,500 input/500 output tokens,
 30s request deadline; any single transient retry must fit a60s total budget and ledger.
- Cache by evidence/profile/prompt/model versions. User refresh/retry must not silently
  generate new bills. CI never calls paid providers; structured fixtures cover failures.
- Per-session/global quotas, one active job/session, queue bounds and actual cost ledger
  before a public endpoint. Operator-controlled live smoke is separate from development
  coding spend. No raw media or persistent device credential enters prompts/logs.
- Provider outage returns measured results plus coaching_unavailable; never pretend a
  canned local explanation came from a live NVIDIA call. A real successful app-path
  inference with redacted model/usage/latency evidence is a release requirement.

## 7. Work packages and delegation map

All HM tasks start todo; this document completes only T23 planning. Target files are
proposed boundaries, not requests to create scaffolding in advance. Each worker gets
one exact allowlist, a frozen input contract, valid fixture and concrete acceptance.

| ID | Deliverable / FRs | Dependencies | Owned implementation boundary | Acceptance / stop condition |
| --- | --- | --- | --- | --- |
| HM00 | UX flow + intake + hosting feasibility; FR01/02/06/10/12 | Plan | docs, mockups, read-only clip/deployment checks | Four screens incl failure/mobile states; correct press variant; free-host/judge-access feasibility and cost risks recorded before dependency commitment |
| HM01 | Public contracts and migration; FR01–12 | HM00 | packages/contracts, generated API/TS/JSON schema, data-model decisions |0.2 pose fixtures still read;0.3 prototype scope/workout/quality types round-trip; no schema drift; one schema integrator |
| HM02 | Same-browser profile, library and workout storage; FR02/03/12 + product log scope | HM01 | app/session.py, store/migrations, app/workouts.py, app/profile.py | Profile survives refresh/restart/renewal; CRUD/idempotency/owner isolation; history survives video expiry; migration rollback/backup documented |
| HM03 | Full-set60s media + lifecycle; FR01/02/03/04/12 | HM01 | ingest/proxy/provider caps, pose job/config/child, supervisor/retention | All four original clips accepted within caps;55s lat/40s press truly processed; PTS/rotation/hash, timeout/memory/cancel tested; no silent trim |
| HM04 | Lat runtime report + count/quality/prototype policy; FR04/05/07/08/12 | HM01, HM03 | movement runtime adapter, scoring policy, report assembly/validation | Fresh upload uses automatic candidates, not canned labels; metrics/coverage/profile versions in published result; partial score honest; deterministic rerun; current offline work reused |
| HM05 | Curl runtime profile and real clip; FR04/05/06/07/08 | HM04 interface | curl config + narrow exercise module/tests/permission-checked profile | Real curls clip produces eligible metrics and count or explicit partial; no copied lat limits; one accepted report before next exercise |
| HM06 | Real runtime Nemotron coaching; FR09/11/12 | HM01 evidence contract; integrate after HM04 | providers/llm, coaching evidence validator/cache/quota tests | One real app-path NVIDIA call via Nebius; fields grounded; no score generation; timeout/cache/quota/private-data tests |
| HM07 | Squat and incline runtime profiles; FR04/05/06/07/08 | HM04, HM05 pattern; HM00 variant | Separate squat/press configs/modules/tests, reviewed catalogue entries | Each provided clip passes a distinct report; view limits and unavailable comparisons explicit; no unsupported lateral-raise release claim |
| HM08 | App shell/new set/library/history UI; FR01/02/03/06/10/12 | HM00 mockup, HM01 contracts; wire HM02/03 | apps/web routes, API client/session state, upload/status/log components | No scaffold landing; real network upload/status/save/history; refresh/cancel/error/mobile/keyboard flows work without fake data |
| HM09 | Results viewer and report UI; FR07/08/09/10/12 | HM04/HM06, HM08 | apps/web viewer/timeline/metric/quality/coaching components | Source-time video/2D/estimated3D sync; gaps shown; breakdown/partial/expiry readable; no-memory-leak renderer fallback |
| HM10 | Muscle view, simple routines and dashboard; product log scope/FR06/10 | Core loop HM02/08/09 green | Avatar/muscle mapping + templates/summary UI | Illustrated target map/weekly sets from real logs; no inferred physique; template edits persist; optional elements removable independently |
| HM11 | Early deployment/access spike, then release deployment; FR02/03/04/09/12 | Feasibility starts HM00; complete after HM04/08 | infra/release, same-origin HTTPS, persistent state, secrets/checkpoint packaging | Remote browser upload->real result + live coaching; persistent restart; quotas/retention; no inaccessible local-only dependencies; no paid activation without cost approval |
| HM12 | End-to-end QA and submission honesty; FR01–12 | Each slice continuously; final HM05/07/09/11 | tests/integration/browser checks + release evidence | All four selected clips through actual UI; two owners isolated; no-person/bad media/LLM outage/cancel/restart/expiry/delete covered; advertised features match proof |
| HM13 | Submission package and judge runbook; release | Start narrative HM00; finish HM11/12 | README/licence/notices/docs/demo assets/release tag | Public repo/working demo or test build/under3min video/track/feedback/readme complete; judge can run without personal developer key |

### First delegation batches (next turn, not started now)

1. **Batch A — prepare boundaries:** one Nebius worker drafts HM00 screen flow/mockup;
   a second drafts HM01 schema changes against current contracts; a third performs the
   read-only HM00 hosting/runtime-model feasibility review. Contracts are draft until
   mockup/intake review; no dependent implementation is applied yet.
2. **Integration gate:** Codex reviews the small decisions/mockup; one integrator freezes
   contracts/variant/routes. Resolve schema changes before the backend/frontend split.
3. **Batch B — working foundations:** HM02 storage/profile, HM03 full-set media, and HM08
   UI shell against frozen types in disjoint paths. One writer integrates; validate an
   actual owner upload/status/library path before any avatar/routine batch.
4. **Batch C — first full analysis:** HM04 lat runtime report; HM06 coaching provider in
   parallel against the frozen evidence contract; HM09 viewer consumes accepted reports
   or explicit schema fixtures labelled only as tests. Integrate one real lat UI report.
5. **Batch D — widen proven flow:** HM05 curl then separate HM07 squat/press adapters;
   an independent worker tests the accepted previous slice. Avoid editing shared
   catalogue/contracts simultaneously; the integrator applies those changes.
6. **Batch E — product finish:** HM10 only after core green; HM11 deployment finalisation
   and HM12 real-browser QC can overlap in separate files. HM13 draft assets prepared
   alongside, public release/submission remain final reviewed actions.

Maximum3 independent calls concurrently; batches at most3–4 tasks; no child-agent
trees, duplicate broad audits or whole-repo prompts. Use direct Nebius workers for
substantive drafting/tests/first-pass QC; Codex coordinates, checks and integrates.

## 8. Worker packet and resource rules

Every packet includes: task ID+FRs; one output behaviour; exact read-only sources and
allowed output paths; actual relevant contract/fixture; prerequisites; config versions;
forbidden scope; acceptance commands; current task token/cost reservation; next task.

- Prefer the K3 route that produced accepted outputs in T047; the Code route emitted
  unstructured reasoning/exhaustion and is not the default for another large draft.
  Recheck availability/caps at use, not a new model tournament.
- Split implementation and tests when one JSON response cannot reliably contain both;
  avoid repeating a500-line source plus its whole test suite in one response.
- Source contracts and fixtures first; no invented Store methods/model_construct
  shortcuts. Returned files are private drafts, never executed or auto-applied.
- Strict output allowlist/envelope; rejected/truncated results still count in usage.
- Up to200k cumulative tokens per bounded task, not per request or a target. Keep the
  existing USD70 active ceiling/USD30 protected backup; verify actual account balance
  before assuming remaining credit. T047 recorded aggregate commitmentUSD7.96125365
  including historic unknown-call contingency, not verified billed spend/balance.
- Working forecast for the next implementation tranche: roughlyUSD4–10 incremental
  coding guard cost, subject to the first accepted vertical slice; not a purchase or
  guarantee. Track runtime inference and Tavily separately. No new search/model/data
  spend solely to exhaust allowances. Reforecast on results, not token consumption.
- No automatic provider retries. After two failed attempts on the same route, inspect
  root cause, shrink/change the packet once or mark the bounded blocker; do not spend
  the entire submission window on another generic framework. No large Codex fallback.
- Independent QC targets new critical boundaries, not another whole-repo review.
- All setup/builds/tests/model/media tools remain inside Docker. No host ML/runtime
  installs, no raw media/pose arrays/credentials in coding prompts.

## 9. Library and asset choices

Keep Next.js/React/TypeScript/Tailwind, FastAPI/Pydantic, SQLite, MediaPipe/FFmpeg and
the existing OpenAI-compatible provider boundary. Existing lockfiles remain authoritative.

Candidate3D layer: Three.js + React Three Fiber for the React19 client. Official docs
pair Fiber9 with React19; do not adopt the alpha release. HM09 verifies a compatible
exact pinned version set inside Docker, terms, bundle size and sample rendering before
adding it. Optional controls/helpers only when needed; avoid installing a whole UI or
avatar ecosystem. Generate a simple original/clearly licensed muscle mesh or use SVG
front/back fallback; record source licence, revision and notices for downloaded assets.

Use native forms/fetch/CSS and SVG/simple charts initially. Add a form/schema, upload,
chart or UI-component package only for a concrete accepted interaction it materially
simplifies. No ffmpeg-WASM browser bundle, new state framework, vector DB or biometric
body-generation SDK for the hackathon. Mockups/assets can be drafted before code.

## 10. Free-first hosting and release operations

Vercel Hobby is a candidate for the Next.js frontend: it is free within usage limits
and restricted to personal, non-commercial use. It does not by itself resolve our
Docker pose worker, durable database and private video storage requirements. Evaluate
Vercel frontend + separately hosted Docker API/worker/persistent storage alongside
the single-host option. Vercel Functions have a 4.5 MB request/response payload limit;
our current clips exceed that, so validate a direct authenticated backend/storage
upload path rather than routing video bodies through a Function. Validate cookies,
CSRF, CORS and private playback across the chosen domains. Do not assume that Function
limits describe every external rewrite, or that a free frontend makes the whole app
free. No deployment has been performed by this planning checkpoint.

Sources: [Hobby terms and limits](https://vercel.com/docs/plans/hobby),
[Function limits](https://vercel.com/docs/functions/limitations).

NVIDIA/Nebius inference is mandatory; hosting the entire web/CPU stack on Nebius AI
Cloud is not. Token Factory promotional credit is not a published AI Cloud hosting
grant. Evaluate the smallest deployment that runs this actual Docker/CPU worker and
preserves SQLite/private files, rather than choosing a fashionable free frontend tier.

Early feasibility packet must answer: available always-on owned/free host, CPU/RAM,
storage quota, stable HTTPS/domain, model/checkpoint packaging, egress/upload limits,
background processing limits, restart/sleep behaviour and judge access duration.

- Prefer one same-origin Docker host with persistent disk and CPU pose for this release.
  NoGPU/cloud database/domain purchase unless the concrete deployment evidence needs it.
- A free frontend does not solve persistent backend/worker storage. Ephemeral free
  filesystems and sleeping workers are unacceptable without an explicit tested design.
- An existing machine/tunnel is only a candidate if uptime/secure exposure and access
  through judging are demonstrated; do not promise a temporary tunnel as durable hosting.
- A runnable Docker test build is an allowed submission route, but cannot bundle a
  personal provider key or require judges to pay/provide their own Nebius account.
  It still needs a safe owner-funded runtime path and complete setup/test instructions.
- If no zero-recurring-cost route satisfies the above, return a concrete smallest-cost
  option, monthly duration and shutdown plan for owner decision. Do not activate it.
- Release config: stable secret, HTTPS cookies/CSRF/origin, request/body/time limits,
  private storage, global/per-session inference and queue caps, non-secret logs, backup,
  restore, restart/reclaim, scheduled safe cleanup and completed deletion evidence.
- Public sample videos require specific approval of the exact final public assets;
  private user uploads and downloaded reference videos are not automatically publishable.

## 11. Delivery targets and cut line (MYT, targets not promises)

| Target | Required evidence before advancing |
| --- | --- |
|22–23 Oct| Flow/mockup and contracts settled; full-set limit/variant identified; hosting feasibility; first bounded real Nemotron structured response |
|24 Oct| One real lat upload -> published prototype report -> browser playback/quality/coaching -> saved log |
|25–26 Oct| Remaining three exercise paths through the same flow; persistent history; deployed/access spike validated |
|27 Oct| Muscle-view/routine/dashboard polish only if the core remains green |
|28 Oct| Feature freeze: all four uploads/partial failures work; no new libraries/features after this gate |
|29 Oct| Final remote browser QA, release candidate, permissions/README/notices, recorded demo, completed submission draft |
|30 Oct14:00| Internal submission target, leaving11h before the official deadline; final owner submission/verification |

If behind: remove adaptive/advanced avatar work, chart decoration and routine extras
first. Preserve upload/status/results/log, required runtime inference and honest missing
states. Any missing exercise or advertised capability must be explicitly removed from
copy/demo rather than silently considered complete. Do not cut owner isolation,
server-side keys, media limits, real inference evidence or reproducible judge access.

Official deadline:31 October2026,01:00MYT (30 October10:00PDT). Judging ends15 December
at12:00Pacific, corresponding to16 December04:00MYT; budget and test access must account
for that period rather than only the submission day.

## 12. Final release checklist

- [ ] All four real exercise inputs complete through the release browser/UI; reported
  limitations, rep counts and coverage recorded, with no claim of validated accuracy.
- [ ] Wrong exercise/no person/poor framing/corrupt file/unsupported codec/too-large/
  too-long/slow upload/refresh/duplicate submission/provider outage tested.
- [ ] Play/scrub/rep selection/speed/2D/3D alignment checked; fallback usable on WebGL
  failure; mobile layout, keyboard access, labels/contrast and reduced motion checked.
- [ ] Profile/history/edits persist across refresh/restart and valid credential renewal;
  clear-browser limitation visible; two independent owners cannot access each other.
- [ ] Raw expiry, report expiry and explicit deletion are distinct; cancelled child
  cannot resurrect files; safe retention/reaping proof complete for the deployed paths.
- [ ] Numerical fixtures and recipe versions frozen; quality is observation coverage;
  manual log edits cannot fabricate measured quality/score improvement.
- [ ] Runtime NVIDIA/Nebius model/usage/latency evidence comes from the application;
  quota/cache/timeout/outage/secret-redaction tests pass; CI pays nothing.
- [ ] Docker Python lint/type/unit/contract/integration, generated types/schema drift,
  frontend typecheck/build and real browser acceptance pass for the tagged release.
- [ ] Remote free/approved-cost judge path survives restart and uses persistent storage;
  public runtime abuse/cost limits and monitoring are active; judge instructions tested.
- [ ] GitHub visibility and MIT licence verified; no secrets/private media/keys; exact
  third-party code/model/asset/reference terms and attribution checked; clean setup works.
- [ ] English description covers problem, user, implemented features, architecture,
  NVIDIA/Nebius role, limitations, future camera roadmap and what changed during event.
- [ ] Public YouTube demo under3min shows the working app, live inference evidence,
  saved history and a clear outcome; no unapproved private footage/music/assets.
- [ ] Working demo/test-build URL, public repo, track and tool feedback populated;
  owner approves final public assets/submission; confirmation captured; release tag kept.

## Sources checked22 October2026

- [Hackathon overview/requirements/judging](https://nebiusglobalaihackathon.devpost.com/)
- [Official dates, submission and testing rules](https://nebiusglobalaihackathon.devpost.com/rules)
- [FAQ: Token Factory runtime vs whole-app hosting and credit scope](https://nebiusglobalaihackathon.devpost.com/details/faqs)
- [React Three Fiber: React19 compatibility and stable major](https://r3f.docs.pmnd.rs/getting-started/introduction)
- [Three.js documentation](https://threejs.org/docs/)

Next action after the owner starts delegation: Batch A only. Do not dispatch every HM
task at once or count this plan as completion of the product work.
