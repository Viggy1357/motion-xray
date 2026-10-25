# Milo Pip — delivery plan and supervisor handoff

25 October 2026, Malaysia time. Planning only; no implementation or paid worker dispatch
performed by this document. Owner selected **Milo Pip**, the lilac pet concept, not the
robot, bear, Bloom or wooden character. Asset selection is approved; final animation
quality remains to be reviewed. This document records scope, not independent authority
to spend, publish, install tools or expand the product.

## 1. Outcome and boundaries

Deliver one quiet gym companion in the existing app with three bounded visual actions:
idle, attentive and cheer. No progression, XP, character selector, journal, new chat,
voice, exercise retargeting or autonomous advice. Keep analysis, coaching, privacy,
recording consent and quota behaviour intact. No new backend/public schema is expected.

Selected concept: `references/milo-pip-selected.png`. It is a generated static design
reference, not a rig, sprite animation or production asset. Lilac short fur, cream belly,
floppy ears, curved tail, dark eyes and pale mint markings define Pip. Keep one fixed
three-quarter view for MVP. The pictured full-body stretch is a future action; it is
not required to deliver the initial three reactions. Product name remains Motion X Ray;
character display name is Milo, with Pip used to identify this design internally.

Current foundation: `apps/web/app/page.tsx` owns route/job/upload/result state;
`athlete-companion.tsx` displays static athlete artwork and a separate illustrative map;
`components/ProgressCompanion.tsx` displays saved-set recognition. Latest inspected Git
checkpoint before planning: c051b6e. Recheck HEAD and dirty files at execution time.

The selected direction supersedes D024's hold on exploring a new companion, not its
constraints on measurement honesty. Home placement and replacement of existing art
are implementation proposals below. Historical audits must not be rewritten.

## 2. Interaction and placement specification

| Situation | Visual | Text / behaviour |
| --- | --- | --- |
| Home | Idle: breathing-like shift, occasional blink | Usually silent; optional one-time greeting |
| Upload accepted / queue / processing | Attentive: small head tilt and gaze | Existing true stage text remains authoritative; no invented ETA |
| Report successfully fetched and usable | Cheer once, then idle | “Your set is ready.” Not a technique judgement |
| Partial report / no measured cycles | Attentive pose, then idle | Existing factual limitation remains visible; no disappointed expression |
| Save confirmed | Brief acknowledgement | “Nice showing up.” Never inferred from form similarity |
| Failure / expired / cancelled | Static or calm attentive pose | Existing error and recovery controls; no victory animation |
| Recording | Static or hidden | No distracting movement; never overlays camera or controls |
| Background tab / hidden companion | Paused | Cancel loops and pending reactions |
| Reduced motion | Static expression change | No breathing, bounce, slide or forced animation |

Proposed placement: replace only the decorative Home athlete poster slot with Milo;
keep the separate exercise body-map function and its labels. Compact companion beside
processing/results; no floating obstruction of upload, consent, replay or coaching.
No duplicate character in the same view. Existing saved logs remain unchanged. Do not
rebuild the Progress page; changing ProgressCompanion is optional and cut first.
Provide a persisted same-browser Show Milo toggle using backward-compatible existing
UX settings defaults. It hides visuals without removing status/error text.

Three actions are visual primitives; there may be more logical states. Cancellation,
error, partial, recording and expiry must not be forced into “success”. Use existing
typed report validity/status fields; do not invent an accuracy threshold.

## 3. Asset workflow and first feasibility gate

Preferred hypothesis: layered raster artwork + CSS/React transforms, fixed view.
Soft fur means seams and occlusion can look poor: this route is **unproven for Pip**.
Do not promise arbitrary 3D motion or exact exercise imitation from the concept sheet.

1. Preserve the selected concept and generate ONE clean neutral reference/cutout.
2. Lock face, fur colours, ear length, paw count, tail shape, camera and lighting.
3. Produce head/body/forepaw/eye layers only where clean seams are achievable. Request
   hidden overlap pixels under moving parts; do not simply cut visible pieces out and
   leave holes. Generate/repair with the image tool rather than ad-hoc image editing.
4. Export layers with consistent canvas, alpha, anchors, z-order and filenames. Add a
   static fallback. Convert/optimise formats using existing container tools if needed;
   no host runtime installation. Record dimensions and decoded-memory estimates.
5. Build a standalone isolated preview: Idle / Attentive / Cheer / Stop / Reduced motion.
   No user video, upload, API or paid runtime calls.
6. Show a real browser recording or preview to the owner. Check 96px compact and 280px
   hero sizes on light backgrounds, including alpha edges, feet and shadow stability.
7. Only after the motion gate passes, freeze asset manifest and integrate.

Action draft: idle 4–6s gentle loop with infrequent blink; attentive 0.8–1.2s tilt,
then quiet hold; cheer 1.2–1.8s modest paw raise/nod, once. These are proposed timings,
not validated output. No whole-character wobble used to disguise broken anatomy.

If layered fur fails: permit one targeted repair. Then propose a simplified movement
or a consistent pre-rendered clip route, with evidence, before spending more. Separate
AI-generated poses are not smooth animation frames. Do not begin a full 3D modelling,
rigging or generative-video pipeline without a revised scope/time/tool proposal.
Static-only shipping requires an explicit product trade-off; never call it animated.

Asset manifest fields: version, reference path, file/hash, dimensions, alpha, layer,
pivot, stacking order, bounding box, supported actions, source/tool provenance and
redistribution notes. Production assets go in `apps/web/public/companion/milo-pip/`;
concepts and rejected candidates stay out of the public bundle. Do not claim legal
clearance from visual resemblance checks. No externally sourced character assets
without recorded licence/attribution review.

## 4. App architecture

Proposed files (adapt names to conventions; freeze allowlists before dispatch):

- `apps/web/app/components/MiloCompanion.tsx`: renderer, no fetches or paid calls.
- `apps/web/app/components/MiloCompanion.module.css`: animation and responsive sizing.
- `apps/web/app/lib/milo-state.ts`: pure state/event mapping and reaction priorities.
- `apps/web/app/lib/milo-assets.ts`: typed asset manifest/anchors, no private data.
- An isolated preview entry, kept out of ordinary navigation and production if practical.
- Existing `page.tsx`, `lib/ux-metadata.ts` and `components/SettingsPanel.tsx`: narrowly
  scoped event/placement/toggle integration; original data remains backward compatible.
- Focused checks in the existing web/browser harness rather than a second test framework.

Suggested component contract: visual state, event token, size, reduced-motion flag and
visibility. Parent derives state from current authoritative app state; Milo never
initiates analysis, retries, saves or coaching. Event token includes analysis ID and
event kind. Store only bounded session reaction keys if needed to survive remounts;
no new durable user profile. Render/reopen/poll refresh must not replay a cheer.

Priority: hidden/reduced motion/recording > failure/cancel/expiry > latest active
analysis > newly usable result/save > idle. Old job completion cannot override a new
job. Ignore stale responses through existing job identity mechanisms. Collapse closely
spaced ready/save reactions; do not queue an unbounded series of celebrations. Clear
timers/listeners on unmount and pause in background. Visual errors never block the app.

Do not derive encouragement from numeric confidence, similarity, manually corrected
rep counts, calorie estimates or inferred muscle activation. Existing Nemotron output
may remain beside Milo; canned acknowledgements must not be labelled AI coaching.

## 5. Agent roles: development team, not runtime agents

No permanent autonomous agent service is needed. The app uses a deterministic controller.
The following are bounded development roles; a role does not require a separate model
instance to remain running. Default sequential; at most three independent workers.

| Role | Provider/tool route | Ownership and output | Cannot do |
| --- | --- | --- | --- |
| Supervisor / integrating writer | Codex | Task packets, dependency graph, reservations, artifact inspection, selected diffs, container checks, integration and task evidence | Large silent replacement implementation after worker failure |
| Asset producer | Built-in image tool under supervisor direction | Selected-reference derivatives, layers, fallback and source manifest | Edit application logic or claim an image is rigged |
| Motion worker | Proven Nebius coding route | Isolated renderer, anchors, CSS and motion preview draft | Edit page.tsx, scoring, recorder or provider code |
| State worker | Nebius, after interface freeze | Pure controller, event tests and reaction deduplication | Change backend contracts or define posture thresholds |
| Integration worker | Nebius, dependent on accepted renderer/controller | Narrow patch to page/settings; exact event adapters | Rewrite the app or merge its own draft |
| Focused QA worker | Nebius if useful after a working candidate | Review transition failures, accessibility, source-line findings and minimal repairs | Duplicate full-repo audit or declare tests passed without outputs |
| Optional visual reviewer | Verified NVIDIA VL model via Nebius | Compare selected reference with synthetic preview contact sheet; list identity drift/seams | Generate a rig, certify motion from still frames, inspect private gym media |
| Product owner | User | Motion aesthetic acceptance and material trade-offs | No requirement to approve routine coding choices repeatedly |

NVIDIA VL is a possible image-understanding reviewer, not automatically an image or
video generator. It is optional, not an additional runtime dependency. Use direct
human/browser inspection first; dispatch only for a concrete unresolved visual question.
Exact model IDs, image support, rates and limits must be verified at dispatch. Reuse
the previously successful coding route; HM-RELEASE02 records MiniMax-M3 drafting and
DeepSeek-V4-Pro work, but those historical results are not a current availability claim.
Do not restart model tournaments or select models from unverified price tables.

## 6. Supervisor protocol

Task lifecycle: planned -> ready -> reserved -> dispatched -> draft_returned ->
reviewed -> integrated -> checks_passed -> accepted. Alternative states: repair_needed,
blocked or rejected. Generation completion is never acceptance. Only the supervisor
changes accepted state and integrates shared files.

Before each dispatch:

1. Recheck Git HEAD/status; identify user or other-agent changes and exact ownership.
2. Read latest accounting, reconcile known costs and unresolved reservations. Do not
   equate a repository estimate with the provider's remaining balance.
3. Check prerequisites and freeze interface/asset version. Record source hashes.
4. Prepare a compact packet: task/FR IDs, objective, inputs, allowlist, forbidden changes,
   acceptance cases, output format, cumulative token/cost cap, timeout and stop rule.
5. Reserve worst-case request cost using verified rates and input/output bounds.
6. Dispatch one proven bounded worker first. Parallel work only after usable output.

On return:

1. Capture model ID, finish reason, actual usage, elapsed time, billed or conservative
   cost, and unknown usage. Preserve truncated output without auto-applying it.
2. Check files against allowlist, base hash and dependencies. Reject fabricated assets,
   placeholder “success”, network calls and weakened tests.
3. Integrate sequentially, run relevant checks, inspect visible output.
4. At most one targeted repair request per packet by default, with actual failure text.
   Continued failure -> stop that packet, diagnose once, report blocker/replan.
5. Update task evidence, remaining budget and next dependency; report batch outcome.

Workers return patches or isolated files plus assumptions, checks actually run, known
limits and usage reference. They do not write shared app files concurrently. No recursive
delegation, background purchases, credentials in prompts, private media or raw session
logs. A supervisor rollback reverts only its own patch, never broad resets of user work.

## 7. Batches, task IDs and gates

Parent task HM-MILO01 (FR01/02/03/09/10/12 integration). Planning subtask P is delivered
by this document; all implementation subtasks remain planned.

| Task | Dependencies | Deliverable | Acceptance |
| --- | --- | --- | --- |
| HM-MILO01-A | Selected Pip | Neutral cutout/layers + manifest + motion preview | Three actions recognisable, stable identity, no visible tears at target sizes; owner motion gate |
| HM-MILO01-B | A interface frozen | State controller + focused tests | Correct priority, once-only events, stale job suppression, failure/partial/recording/reduced-motion cases |
| HM-MILO01-C | A and B accepted | App placement + Show Milo setting | No blocked controls, existing capture/upload/replay/log/coaching still operate |
| HM-MILO01-D | C integrated | Browser QA, fixes, delivery evidence, rollback | Container checks pass; actual rendered actions and fallback verified; honest release notes |

Batch 1: A only, one motion worker plus supervised asset creation. While waiting on the
owner motion decision, prepare B's state mapping offline; do not integrate unapproved art.
Batch 2: B and narrowly scoped independent asset packaging may overlap after A's contract
is frozen. C waits for B. Batch 3: D focused verification and release handoff. Never use
three workers merely because three slots exist. No multi-agent framework needs building.

## 8. Budget and stop rules

Use existing USD70 active / USD30 protected ceilings; backup remains untouched. Tavily
is unnecessary for this slice. Product runtime calls: zero added. Image-generation usage
is separate and must not be represented as included in Nebius dollar accounting.

Proposed initial cumulative Nebius envelope across HM-MILO01: **200,000 tokens total**,
including review/repair and optional VL. A:60k, B:45k, C:45k, D:30k; shared reserve:20k.
These are caps, not targets; do not multiply the parent cap by worker count. Any increase
requires documented demonstrated need within existing authority and remaining spend.
No dollars forecast until current rates/reservations are checked. Existing historical
costs remain counted; this task does not reset the shared budget.

Per packet initially one draft plus at most one focused repair; typically 16k–32k maximum
completion where supported (includes reasoning), compact input, streaming, zero hidden
SDK retries, 90s idle bound and 600s total deadline per existing policy. State changes
and provider errors are reported; no blind retries or treating timeout cost as zero.

Image budget: one neutral master plus required layer set; at most one targeted repair
round before asset gate/replan. Optional VL: one comparison plus one clarification only
if useful, within D allocation. Stop after a half-day motion proof timebox if the chosen
route cannot look credible; present a concrete reduced-action alternative.

## 9. Verification and delivery definition

Automated behaviour checks: repeated polling/reopen doesn't cheer; new job overrides
old result; ready vs partial vs failed/cancelled/expired; save acknowledgement only on
confirmed save; settings persistence and old metadata; unmount/background cleanup;
broken asset fallback; no extra API/coaching requests from visual events.

Run `./scripts/test.sh web` and `./scripts/check-browser.sh` using existing Docker
entrypoints. Add narrowly relevant cases to the existing harness; locate exact harness
files before dispatch. Python checks only if Python/contracts are unexpectedly changed
(normally reject that scope). No paid calls in CI or UI fixtures.

Visual checks: 360/375/1365 viewports; hero and compact sizes; idle/attentive/cheer;
reduced motion, disabled companion, failed asset; no clipped ears/tail, fur seams,
layout jumps or overlapping controls. Record actual payload and frame behaviour on
the test device. Proposed asset target <=2MiB initial compressed set, with decoded
memory recorded and no decoding of unused variants; justify any change before acceptance.
Small desktop checks do not prove all physical mobile performance.

Existing media/recording behaviour uses fixtures for regression and consented local
footage only if needed. No private frames in public screenshots or external QA prompts.
Fallback is same UI without animated Milo, with analysis still fully usable. Companion
failure must not fail upload, processing or report access.

Final handoff: base/final commits, accepted design/manifest hashes, files changed,
commands and exit codes, screenshot/preview paths, actual usage and reservations,
known limits, feature-disable/rollback steps, owner decisions and next release task.
Prepare one coherent commit per accepted slice; no publishing, remote push or final
submission implied by this planning task. Asset provenance included in release review.

## 10. Dependency sequence and future queue

Owner requested execution immediately with independent tasks in parallel, replacing
calendar estimates. Sequence: asset motion proof -> controller/packaging -> integration
-> browser checks and delivery evidence. The motion candidate was verified locally;
owner visual feedback follows delivery. Preserve HM-RELEASE03 judge-access work.
Cut Progress embellishments, extra poses and optional VL review before reliability.

Deferred explicitly: companion progression/selection, journal/social sharing, voice,
live pose feedback, wearable haptics, standalone camera, arbitrary exercise imitation,
full 3D character. Future camera work requires visible recording controls, placement,
consent, transfer/storage/battery evaluation. Future haptics require validated low-latency
signals and cooldown/visibility gates; current post-set analysis does not prove them.

Actual delivery update: docs/audit/HM-MILO01-delivery.md. Initial200k allocation increased
to300k for observed draft failures and integration verification;289,095 tokens used.
The app uses a direct state adapter plus renderer dedup, while the pure controller
utility remains separately tested. No separate save celebration, blink or paw wave.

## 11. First execution packet

Start with HM-MILO01-A only. Read AGENTS.md, this plan, TASKS.md, D025 and budget policy.
Inspect current Git state and dispatch helper; use the established authorised route,
not a new generic dispatcher. Preserve selected reference. Produce and inspect a neutral
master, then the minimum separable layers. Draft a preview renderer in isolated files;
no page.tsx edits, no runtime provider calls. Deliver a reviewable browser preview of
idle/attentive/cheer, provenance, sizes, usage and exact limitations. Stop at the motion
gate before main-app integration. If assets cannot support believable movement, report
the concrete defect and a bounded alternative rather than silently lowering fidelity.
