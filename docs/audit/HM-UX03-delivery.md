# HM-UX03 — Connected cobalt experience

23 October2026. FR02/03/04/05/06/07/08/09/10/12 presentation and local-history
extension. Working baseline: `f47e09d`. This delivers the UI slice, not clinical
validation, every planned product feature, or a public production launch.

## Delivered flow

Home `/` → Analyse `/analyse` → local preview/consent → actual upload bytes →
queued/processing with real server stage and time since submission → Results
`/analyse/results?analysis=…&exercise=…` → actual video/pose/segments/report →
explicit optional coaching → save → Progress `/progress` → reopen.

- White/cool-blue/cobalt styling follows the approved four-screen concept. A
  separate visual reviewer compared the concept directly with375px screenshots;
  Nebius drafted the implementation. Home became an athlete scene rather than a
  nested companion card; mobile branding/camera navigation returned; Capture has
  one compact exercise selector; Progress has real dates and quieter management.
- Four existing exercise profiles remain. No fixture report, simulated timer or
  synthetic skeleton is promoted from `/ui-draft` into the live app.
- Actual signed-owner session, consent, CSRF, upload limit100MiB/60s, polling,
  cancellation, request-key reuse after upload/create failure, and private media
  endpoints are preserved. No backend/config/model/threshold changes.
- Canonical observed valid joints draw over the actual proxy video. Invalid,
  interpolated or distant samples do not draw. Bounded artifact reads32MiB/8MiB;
  original/proxy timestamps map in both directions. Segment IDs remain original.
- Static original athlete artwork is distinct from the optional procedural 3D
  target map. No measured muscle activation/body growth claims. Asset provenance:
  `apps/web/public/companion/README.md`.
- Local history is validated and written before state/toast changes. One record
  per analysis; corrections stay separate from detected counts; editing preserves
  the original record ID/date. Eligible recognition requires a measured completed
  report with exact analysis/exercise proof. Legacy/manual entries do not receive it.
- Save waits for the movement GET to settle. A failed reload may retain already
  saved metadata for the same analysis, with an explanation; it cannot mint a new
  award. Loading no longer flashes the legacy pose-only failure message.
- Expired/revoked analyses release the local active-job lock and retain history;
  browser-local removal and server access revocation remain distinct actions.

## Executed checks

All project runtimes/checks ran in Docker. Final source was copied read-only into
an isolated checks container, preserving the running dev server's `.next` directory.

| Check | Result |
|---|---|
| `pnpm typecheck` | Pass, including generated route types |
| `node scripts/check-pose-overlay.cjs` |12 passed,0 failed |
| `node --check public/companion/athlete.js` | Pass |
| `pnpm build` | Pass; Home/Analyse/Results/Progress prerender;123kB first-load JS reported |
| Real lat upload → processing → report | Pass; real elapsed exceeded1.8s, pipeline stage updated |
| Actual report/video/overlay |5 completed cycles,18 fragments,93% visibility; observed overlay visually aligned |
| Segment evidence seek | Original segment14 sought26.81s; segment6 also played; source-offset cases covered by helper checks |
| Save/reopen/refresh | Pass; browser persistence and saved rep prefill observed |
| Corrected vs detected | Logged6 retained detected5; restored test entry to5 |
| Duplicate save/recognition | Same analysis remained one eligible set and one history record; date retained |
| Expired/unowned ID404 | Explanation persisted; new upload available; history retained |
| One active job | Intake blocked a second upload while server job ran |
| Job cancellation | Synthetic20s colour-only fixture uploaded; actual processing then confirmed cancelled; intake unlocked |
| Browser back/forward | Checked across Home/Progress and nested Results/cancellation; URLs and visible screens reconciled |
| Responsive layout |360px/375px phones and1365px desktop; no page-level horizontal overflow on checked views |
| Optional map | Mounted on opening; Front/Back controls exercised; collapsed by default |
| Rollback dry run | Baseline client from `git archive f47e09d apps/web/app` typechecked and production-built in an isolated container; live browser history untouched |
| Whitespace | `git diff --check` |

The12 helper checks cover malformed/non-finite input, monotonic timestamps/indices,
nonzero source offset, inverse seeking, out-of-range samples, long visibility gaps,
invalid/interpolated joints, odd padding, letterboxing and degenerate geometry.
They do not certify pose accuracy or clinical correctness.

Late in testing macOS denied reads of the original demo file (including a local
copy attempt), so a later browser upload failed before reaching the API. The first
real-video run had already succeeded. Cancellation was then checked using a clearly
synthetic local fixture, without fake detections or a saved workout. No private
footage/pose was sent to coding/design workers or included in this commit.

## Scope map against UX2 planning tasks

| Task | Delivered / boundary |
|---|---|
|01 baseline | Committed baseline retained; old static simulation preserved |
|02 shell/nav | Live routes, mobile header/nav, desktop rail, refresh/back/forward |
|03 companion | Original static poster plus separate optional rotatable illustrative map; high-quality rotating mesh remains future art work |
|04 intake | Local preview/clear, actual bytes, single-job UI guard, cancel/retry/create-recovery code |
|05 real results | Actual owned report/video/coaching entry; reference provenance and missing reasons accessible |
|06 overlay | Live2D overlay capability observed; user toggle/error state; no estimated3D motion replay |
|07 save/progress | Atomic browser save, dedupe, correction, dates, eligible recognition, actual weekly history |
|08 QA/rollback | Container checks and selected real flows above; rollback client build verified |
|09 polish | Mockup-fidelity composition pass completed; richer mesh/animation remains independent future scope |

## Limits and remaining validation

- Browser quota/storage-write failure and the upload-success/create-failure branch
  were source-reviewed but not failure-injected in this run. Their error handlers
  are not claimed as browser-tested. Failed reload preservation is source-reviewed.
- No exhaustive browser/device or WCAG certification, measured mobile FPS/Core Web
  Vitals, cross-tab job lock, durable server workout ledger, accounts or cross-device
  sync. Corrupt local entries are skipped; there is no dedicated corruption notice.
- Artifact expiry is explained on reopen; history is not proactively polled to mark
  every expired entry. Server access revocation is not a promise of physical erasure.
- Squat's known zero-completed-cycle/partial limitation and provisional/null score
  semantics remain. No new inference, accuracy, anti-cheat or professional-review
  claim follows from the design or an eligible local activity count.
- The scoped state machine still lives primarily in `page.tsx`; overlay/helper and
  companion are isolated. Further extraction can follow observed maintenance needs.
- Recording, estimated3D movement replay, high-quality rotatable character mesh,
  challenges/cosmetics and accounts remain in the future gates in the design plan.

## Delegation and accounting

Twelve bounded source-only Nebius requests, Kimi-K3, one integrating writer. A
separate visual subagent reviewed imagery/layout; no model tournament. Failed calls
and exact complete-patch recovery are retained in the ledger.229,998 reported tokens;
one provider error had unknown usage, reserved at its full bound. Known conservative
guard USD1.933422; task maximum commitment USD2.559354; aggregate maximum including
prior uncertainty USD18.19174165. These are not verified invoice/account balances.
The owner-authorized500k one-off allowance covers the added design/repair scope;
USD70 active/USD30 protected boundaries remain. No runtime coaching or Tavily calls.

See `docs/development-usage-HM-UX03-2026-10-23.json` and first-pass review notes.
UI UX Pro Max guidance was used within its previously authorized scope; no Addy
skill pack was loaded. Do not infer measured Codex-credit savings.

## Rollback

Use a clean branch/worktree or `git revert` the UI commit; do not reset unrelated
technical work. The baseline client build was reproduced without changing the live
checkout or browser data. History keys remain `mxr.logs.v1`/`mxr.activeJob.v1`;
new recognition fields are optional. Reverting the client does not delete history,
server analyses or private artifacts. Rebuild/restart only the web service after a
reviewed rollback. Future recording/3D/account work must not be inferred as shipped.

Next: owner visual feedback; optional targeted failure-injection QA and real-device
checks; the technical thread continues reference/professional-validation work.
