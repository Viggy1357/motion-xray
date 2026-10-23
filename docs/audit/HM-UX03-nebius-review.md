# HM-UX03 Review — page.tsx / pose-replay / pose-overlay / companion (first pass)

Scope: read-only context files only. No backend/Pose/scoring files touched. No network, media, or paid runtime calls. This is a first-pass audit, not a final-pass claim.

## Typecheck failures (fixed)
- `page.tsx:575,590` TS2503 `Cannot find namespace JSX` (React 19): switched to `import type { ReactElement }` for `navItems`/`navBtn`.
- `page.tsx:607` `status.state === 'processing'`: actual enum is `running`; banner now tests `running`.

## Contract-critical fixes (in manifest)
1. **Recognition eligibility** no longer consults legacy pose-only `result.metrics` and no longer falls back to `result.analysis_id` when `movement.analysis_id` is absent. Requires: exact `movement.analysis_id === result.analysis_id`, same exercise, ≥1 `completed` detected rep in `movement.reps`, and ≥1 measured non-null `movement.metrics` value. User-corrected rep counts can never mint recognition; legacy logs stay un-recognised. Save remains atomic (localStorage write before state/navigation).
2. **Route reconciliation**: `popstate` now reconciles job id/exercise from the restored URL, so a prior report cannot render under a different analysis id (the existing per-job clear effect then wipes stale report state). Restored `createdAt` is corrected from `status.created_at` on the first poll, so elapsed time reflects the real submission time.
3. **Expired/revoked jobs (404)**: forget local job metadata only (no server delete), show an explicit failure message, and never permanently lock new uploads. `startUpload` now guards `jobActive` itself, not just via the disabled button.
4. **Upload lifecycle**: in-flight XHR is aborted on unmount; existing fetch polling already aborts via `AbortController` and re-checks `ctrl.signal.aborted` after `await r.json()`.
5. **A11y**: removed `aria-hidden="true"` from the hero wrapper that contained the interactive companion iframe.
6. **Pose parsing**: `parsePoseText` now rejects out-of-order/duplicate `frame_index` and non-increasing timestamps instead of silently sorting; regression tests added.
7. **Bounded reads**: new `readBoundedText` streams artifact bodies (32 MiB pose / 8 MiB map), cancels the reader and errors past the cap — actual read-size bound, not Content-Length trust.
8. **Timestamp map**: `sourceTimeAt` returns `null` outside the measured proxy range (no indefinite edge-pose hold). New pure inverse `proxyTimeAt(map, sourceS)`; `pose-replay` handles `window` `CustomEvent` `mxr:seek-source` (finite seconds detail) and seeks via the map, so nonzero source offsets are honoured. No joint interpolation anywhere.
9. **Overlay staleness**: a ready+overlay-on effect draws immediately after refs update (paused enable no longer waits for `timeupdate`); `drawFrame` bails when `video.error` is set so the overlay stays clear even after later seek events.
10. **Tests**: existing Node CJS checks preserved; added boundary/regression cases (monotonic rejection, out-of-range null, `proxyTimeAt` nonzero offset).

## Companion (athlete.js)
Reviewed: region whitelist, render-on-demand, IntersectionObserver/visibility pause, and full disposal on `pagehide` (geometries, materials, textures, renderer) are already correct. No critical bounded issue found; no changes made, no redesign, no new claims.

## Honest limitations / not fixed
- `movement-report.tsx` / `grounded-coaching` still seek with raw source PTS; they are not context files, so only the `mxr:seek-source` listener + `proxyTimeAt` were added here — the integrator must switch the old helpers to dispatch the event.
- `detectedReps` still falls back to `result.reps` when the movement report is absent (display-only; recognition never uses it).
- Transient poll errors still surface a retry banner; there is no backoff cap.
- `PrototypeAnalysisResult` field access uses a narrowed `unknown` cast because the generated schema shape isn't in context; if the generated types expose `analysis_id`/`reps`/`metrics` directly, the cast can be dropped.
- Patches are sequential, exact-match replacements; they were not executed here (no shell), so `tsc` and `check-pose-overlay.cjs` should be re-run after applying.
