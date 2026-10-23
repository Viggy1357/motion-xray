# HM-UX03 Route Review — apps/web/app/page.tsx

Integrator note: this was a source-only worker review. The navigation cause was a
hypothesis, not an instrumented proof; final browser back/forward/refresh checks
passed after integration. `navigate` also synchronizes from the current URL for
query-only pushes. The expired-state and stale-await issues were source-confirmed.
See HM-UX03-delivery.md for executed checks rather than the reasoning-only claims below.

## Symptom
Clicking Home / Analyse / Resume changed the URL correctly, but a few seconds later the browser returned to `/` while the job kept processing. No console errors.

## Source findings and navigation hypothesis addressed by the patch

1. **Independent React route state fighting the Next.js router.** `navigate()` called native `history.pushState` and then set a private `route` state. In Next 15 App Router, `window.history.pushState` is patched and integrated with the router; the page is also mounted through four real route entrypoints (`/`, `/analyse`, `/analyse/results`, `/progress`) that all re-export the same component. The private route state and the router's URL state could therefore disagree, and any router-driven re-render of the matched entrypoint (e.g. `/` for the Home page) presented the Home view again — looking like a silent "navigate back". Fix: the URL is now the single source of truth. `navigate()` only pushes the URL; a `usePathname()` + `popstate` effect derives `route` via `parseRoute()` and reconciles the active job. `useSearchParams` was deliberately avoided (CSR-bailout build failure without a Suspense boundary); the query string is read from `window.location.search` inside the effect, which is safe in this `"use client"` component.

2. **Expired-analysis message erased by the job-reset effect (race).** On a 404 the poll did `setJob(null)` and `setResultErr(...)` in the same batch; the `job?.analysisId` effect then ran and unconditionally cleared `resultErr`, so the "expired or revoked" notice disappeared. Fix: `expiredRef` is set before `setJob(null)` and the effect skips clearing `resultErr` once when the flag is set.

3. **Stale result stored across an await boundary.** The `/result` body was parsed and stored without re-checking that the job was still current; a job switch during the parse could attach a result to the wrong analysis. Fix: after parsing, bail out if aborted or `parsed.analysis_id !== jobId`; the error branch also respects the abort signal.

## Hypotheses (not proven, no change made)

- **Browser/user interference** (back button, gesture, another tab via the BFCache) cannot be excluded from the report, but the dual route-state issue above is sufficient to explain the revert and is fixed regardless.
- A Next.js internal refetch of the shared page entrypoints resetting component state was considered; state survived in practice (the job kept processing), so this was not the primary cause.

## Behaviour preserved / verified by design

- File, local preview, consent, load/notes and upload state are retained across navigation. The checked page guards a second active upload; this is not a cross-tab lock or an anti-cheat guarantee.
- CSRF token use, coaching/companion components, polling cadence, retry-after-upload-failure (`pendingCreate`), and the existing result Retry (`setJob({ ...job })`) are unchanged. No backend changes, no new dependencies.

## Light additions (as requested)

- **Clear file** button next to the selected file name: clears file/preview/notes, resets the input via `fileInputRef` so the same file can be re-selected, invalidates in-flight validation via `pickTokenRef`, and is disabled while busy.
- **Reopen report** now restores the saved rep count, load and notes for that set (bounded: values come from the already-validated `LogEntry`), applied via `prefillRef` when the job identity changes or directly when it does not.

## Residual risk

- Query-only `pushState` to the same pathname relies on Next's patched `history.pushState` emitting a router update; the `popstate` listener covers back/forward. If a future Next version stops reflecting native pushes in `usePathname`, the sync effect would need a `hashchange`/manual dispatch fallback — no such fallback was added to keep the change narrow.
