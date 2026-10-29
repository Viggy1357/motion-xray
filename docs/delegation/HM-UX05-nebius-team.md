# HM-UX05 Nebius Team Plan (corrected)

Status: **in progress — pending verification**. Not all 35 parity rows are done; the ledger and final checks come later. No tests or builds have been run by this integration call, and none are claimed here.

## Authorization and scope (corrected)
Authorization for this bounded implementation comes from the **user's instruction**, not from this or any other document. This plan records scope; it does not grant anything. Frontend only: no backend models, scoring, pose timestamps, recognition rules, config, or quotas changed. TypeScript 5.6, React 19, Next 15.5; no new dependencies; no installation.

## Budget (corrected)
The 500k task-token allowance is **cumulative across the entire HM-UX05 batch**, not 500k per worker. Per-worker request cost ceilings (1.6 USD, input guard 3 USD/M, output guard 15 USD/M) are unchanged. Active 70 USD, backup 30 USD retained and never used.

## Worker dispatch (batch 1, completed drafts)
Three disjoint workers returned complete files under exact disjoint allowlists:

1. HM-UX05-CAM-001 — `apps/web/app/components/CameraRecorder.tsx`, `CameraRecorder.module.css`, `apps/web/app/lib/capture-controller.ts`, `apps/web/scripts/check-capture.cjs`.
2. HM-UX05-RES-002 — `apps/web/app/pose-replay.tsx`, `movement-report.tsx`, `movement-report.module.css`, `grounded-coaching.tsx`.
3. HM-UX05-MET-003 — `apps/web/app/lib/ux-metadata.ts`, `components/SettingsPanel.tsx`, `components/RegionActivity.tsx`, `components/SessionThumbnail.tsx`, `components/ProgressWidgets.module.css`, `apps/web/scripts/check-ux-metadata.cjs`.

## Integration notes (external writer, this call)
Integrated into `apps/web/app/page.tsx`, `globals.css`, `athlete-companion.tsx`, plus new wrapper `apps/web/app/settings/page.tsx` (re-exports the single-page app, same pattern as `analyse/page`; `/settings` is resolved by `parseRoute`).

Actual worker interfaces consumed:
- `CameraRecorder`: `{ onUse(file: File), onClose(), exerciseLabel, guidance, disabled? }`. Wired on Analyse via a "Record a set" button in a safe-area overlay; `onUse` passes the File to the existing `onPick` validation only — **no upload until explicit consent + Upload & analyse**. "Choose video" fallback always present. Close/unmount stops tracks, recorder, timers and object URLs (worker-owned teardown).
- `SettingsPanel`: `{ displayName, onNameChange, metadata: UxMetadata, onSave(settings) => boolean, onBack, error? }`. `onSave` applies `applyUxSettings` + `persistUxMetadata` atomically; the panel commits the display name only after `onSave` returns true, so a storage failure commits nothing partially. Defaults: goal disabled, target null, `weekMode: 'rolling7'`; target is an optional positive integer; calendar week is opt-in.
- `ux-metadata` (`mxr.ux.v1`): `loadUxMetadata`, `persistUxMetadata`, `applyUxSettings`, `withViewed`, `defaultUxMetadata`. Unknown keys preserved; unsupported versions rejected without erasing. `mxr.logs.v1` untouched.
- `RegionActivity`: `{ sets: { analysisId, exercise, recognitionVersion?, recognition? }[] }`; counts only proof-validated unique eligible analyses (recognition.analysisId === analysisId, exercise match). Used for region activity; the same deduped eligible set drives the goal widget and the milestone. Manual reps and legacy counts earn no credit.
- `SessionThumbnail`: `{ analysisId, sourceS?, label? }`; in-memory LRU 8 / 5 min, PTS-map aware, neutral SVG fallback, `mxr:media-revoked` cache drop. Rendered on Home recent-3 and Progress session rows.

Behaviours implemented:
- Home recent 3 + "View all" → `/progress?view=all`; Progress shows recent 3 by default, full history with existing Reopen/Manage under `view=all`.
- "Viewed" pill derives solely from `mxr.ux.v1.viewed[analysisId]`, recorded only after the report settled and loaded while the Results view was visible, and only after successful atomic persistence. Never labelled watched/reviewed.
- Last-focus cue: no cached coaching event exists in this slice, so the honest neutral "Last review · Reopen report" prompt is kept. No automatic provider/coaching calls anywhere.
- Milestone at 3 eligible unique saved analyses, derived from current logs so it is recalculated on deletion; non-punitive, no economy.
- Opt-in goal widget on Home (only when enabled with a valid target); framed as a local consistency target, not physical muscle growth.
- Front/back artwork: `AthleteCompanion` poster gains an explicit Front/Back toggle (`/companion/athlete.png` preserved as front; `/companion/athlete-back.png` back), subtle per-region overlay dots in the same scene, graceful fallback per asset, explicit "rendered views, not 360°" labelling. Secondary procedural map unchanged and optional.
- All original session/CSRF/XHR upload/abort/retention/poll/null-result/settled-callback/atomic-save/recognition-proof behaviour preserved verbatim.

## Art direction (corrected back-view prompt)
Interim decision stands: matching front/back rendered views of the same athlete, explicitly labelled; no 360 claim; the procedural map is not the parity deliverable. The original back-view prompt in the prior draft was wrong (grey sports bra, gym background). Corrected prompt:

> "Full-body rear view of the same athletic woman from the MotionXRay home poster, wearing the same full slate-blue tank top and matching slate-blue leggings and white shoes, full length, standing with arms relaxed at sides and feet shoulder-width apart, facing away from camera, neutral soft lighting, transparent background, no gym, no equipment, no text, no logo, illustrative fitness app style, consistent with the front poster character."

## Verification (corrected commands, run from `apps/web` cwd in Docker)
- `pnpm typecheck`
- `node scripts/check-capture.cjs`
- `node scripts/check-ux-metadata.cjs`
- `node scripts/check-pose-overlay.cjs`
- `pnpm build`

(Not `pnpm --filter web ...`.) These are wrapper-defined only; they have **not** been run yet. Ledger and final checks follow in a later step.

## Remaining verification / open items
- Run the five commands above; repair at most one targeted fix per issue, then stop and replan if unresolved.
- Confirm `athlete-back.png` asset generation against the corrected prompt and its graceful-fallback path.
- Confirm parity ledger row-by-row (P01–P35) after verification; several rows remain partial by design (e.g. P03 more-menu omitted deliberately, P29/P30 interim rendered views pending asset).


## Operator verification update — 23 October

The commands listed above have now passed in the container check image, including
all capture checks,13 metadata tests and12 pose-overlay tests. The final CSS-only
position repair was followed by another production build. Browser verification
confirmed the opaque recording panel, cancellation, front/back buttons clear of
the athlete's face, settings cancellation and preserved history. No browser screenshot
was sent to Nebius: automatic approval review rejected that payload; the repair used
only generated concept artwork and source. The screenshot requests incurred no paid call.

Settings integration was subsequently repaired to persist displayName and settings
in one mxr.ux.v1 write; legacy name is read-only fallback. Viewed requires a matching
non-null movement report and a visible Results screen. NVIDIA's final source gate
accepted these contracts. Device recording/fresh-report acceptance remains open;
this is a draft implementation candidate, not a fully accepted35-row release.
See HM-UX05-usage.json for actual cumulative accounting and HM-UX05-delivery.md
for explicit deviations. Raw responses and private browser screenshots stay ignored.
