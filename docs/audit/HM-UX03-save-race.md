# HM-UX03 — Save race: late movement-report load downgrades saved record

## Bug
Reopening a saved analysed report prefills the save form (5 reps) while the
movement-report GET is still in flight. During that window `movement === null`,
so `detectedReps` falls back to the legacy `/result` path (null for POSE_ONLY)
and `recognitionEligible` is false. Saving immediately replaced the existing
record with `detectedReps: null` and stripped `recognitionVersion`/`recognition`.
Additionally, the legacy POSE_ONLY warning block flashed "movement report not
available" before the GET had even completed.

## Fix (bounded, MVP)
1. **Settled callback contract** — `MovementReport.onReport(report|null, settled)`:
   - `(null, false)` on mount/reset/retry (fetch in flight),
   - `(data, true)` on success, `(null, true)` on error,
   - abort checks before every callback so a superseded fetch never leaks a
     settled state into a newer job. `onReport` remains a stable `useCallback`.
2. **Page state** — `movementSettled`, reset to `false` in the job-identity
effect alongside `setMovement(null)`.
3. **Save gating** — Save button disabled while `!movementSettled`, with hint
   "Loading movement report before saving…"; `saveLog` has a matching
   function-level guard so no invocation path can bypass it.
4. **Transient-failure preservation** — if the fetch settled but failed and a
   previously saved record exists for the *same* analysis id and exercise, its
   `detectedReps` and validated `analysed-set-v1` recognition are carried over
   (shape enforced by `loadLogs`: recognition.analysisId === analysisId,
   exercise match). No recognition is minted for new/unreadable analyses; a
   first-time save with a failed report stays an honest unrecognised entry with
   `detectedReps: null`. Manual rep counts never award recognition.
5. **Warning gating** — legacy POSE_ONLY warning block now renders only when
   `movementSettled && movement === null`; the MovementReport loading status
   covers the pending state.

## Not changed
- No backend, CSS, or layout changes; no record migration (integrator restores
  the downgraded test record via the UI once the real report loads).
- Atomic localStorage-then-state save order, unique-analysis dedupe, and the
  `result.analysis_id === job?.analysisId` render gate are preserved.
- Retry-on-error flow unchanged; abort semantics unchanged for status polling.

## Verification (offline reasoning)
- Reopen + immediate save: button disabled and `saveLog` guard returns early —
  record untouched.
- Save after successful load: unchanged behaviour, recognition eligible only on
  exact analysis/exercise proof with ≥1 completed rep and ≥1 measured metric.
- Save after failed load on previously recognised record: prior detected/proof
  preserved; on a new analysis: honest null, no recognition.
- Job switch mid-fetch: abort prevents stale settled callbacks; new job starts
  at `movementSettled=false`.
