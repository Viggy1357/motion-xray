# HM-UX05 Component Review — Adjudication (thumbnail repair)

Scope of this pass: apps/web/app/components/SessionThumbnail.tsx repaired; prior findings adjudicated as true fixes vs false findings. No contract/API/backend changes; no tests weakened.

## True findings — FIXED in SessionThumbnail.tsx

### 1. Unhandled rejection on abort (TRUE — fixed)
The async effect IIFE had no try/catch; aborting the in-flight fetch escaped as an unhandled AbortError rejection. Fixed: the whole pipeline is wrapped in try/catch; AbortError and all fetch/decode failures settle to the fallback icon, never an unhandled rejection.

### 2. Shared-cache revocation races (TRUE — fixed)
cacheSet revoked the existing URL for a key while another mounted instance rendered it, and the cache key was analysisId only, so parallel instances for the same analysis at different cues clobbered each other. Fixed:
- Cache entries are reference-counted (acquire/release). Eviction, expiry, dropThumbnail and clearThumbnailCache only revoke URLs with refs === 0; in-use URLs are marked stale and revoked on release. A URL is never revoked under a rendering instance.
- Cache key is analysisId AND sourceS (`keyFor`), so same-analysis/different-cue instances hold distinct entries.
- The dead ownedUrlRef (assigned, never revoked or cleared) is removed; ownership is now the held-key ref released in effect cleanup.

### 3. Global media-revoked invalidated every thumbnail (TRUE — fixed)
`if (!detail || detail.analysisId === analysisId)` matched detail-less events. Fixed: mxr:media-revoked only invalidates when detail.analysisId === this analysisId (scoped delete). A global wipe requires the explicit mxr:thumbnails-clear event, which calls clearThumbnailCache.

### 6. Invalid invented endpoints and assumed timestamps (TRUE — fixed)
The component fetched invented `/api/analyses/{id}/pts-map` and `/proxy` endpoints and an unvalidated `Array<{sourceS,proxyS}>` schema, and fell back to `proxyTime = sourceS` (source==proxy assumption) when the map was missing. Fixed to match the actual contract used by PoseReplay:
- Map: GET `/api/analyses/{id}/artifacts/timestamps`, bounded-streamed (8 MiB cap, reader cancelled past the cap), parsed and validated by the existing `parseTimestampMap` from pose-overlay.ts (no assumed arrays).
- Video: `/api/analyses/{id}/artifacts/proxy`.
- Cue mapping via existing `proxyTimeAt`; when sourceS is given and the map is missing/invalid or the cue is outside the measured range, the component shows the fallback icon — never a source==proxy guess.

### 7. Unbounded loading and seek-to-zero hang (TRUE — fixed)
Fixed: a 15 s bounded-load timeout aborts the controller; seek-to-zero no longer waits for a 'seeked' event that never fires (currentTime already 0) — it waits for 'loadeddata' when readyState < 2. Seek target is clamped to [0, duration-0.05] with non-finite duration guarded.

## Adjudicated FALSE findings (verified, no change made)

### 5. "CaptureController.destroy() does not prevent post-teardown finalize" — FALSE
Verified against the code: destroy() detaches `rec.onChunk/onStop/onError = null` BEFORE calling `rec.stop()`. The deferred adapter path in CameraRecorder (`inner.onstop` -> `setTimeout(() => adapter.onStop?.(), 0)`) invokes `adapter.onStop?.()` on the adapter object, whose onStop is already null by then, so finalize() is never reached after destroy. The synchronous-flush adapter contract (`stop()` flushes via onChunk then onStop) also no-ops on null callbacks. No post-teardown finalize or onFinalized emission is possible. Finding rejected; no fix applied and none needed.

### 4. SettingsPanel settings/name persist non-atomically — integrator responsibility, NOT claimed fixed
onSave (settings storage) and onNameChange (name storage) are separate injected callbacks; atomic two-store commit cannot be guaranteed inside this presentational component. Ordering (name persisted only after onSave returns true) is the correct integrator-facing contract; rollback/compensation across the two stores remains the integrator's responsibility. This pass makes no claim of having fixed it.

## Invariants confirmed held
- Memory-only cache: LRU max 8 entries, 5 min max age, revocation on eviction/expiry/drop/clear; nothing (URLs or image data) written to localStorage or any persistent storage.
- No private URLs or images in storage; only same-origin blob: object URLs held in module memory.
- No changes to contract/API/backend; endpoints used are exactly the existing PoseReplay artifact endpoints.
- No test weakening.

## Confirmed controls (unchanged from prior review)
- No microphone: CameraRecorder requests audio: false; RecorderAdapter has no audio.
- No automatic paid coaching: generate fires only on click, guards busy, aborts on change/unmount.
- Coaching segment provenance requires the 'Segment N (' prefix and an actual Rep.ordinal.
- Metadata: version !== 1 -> null; corrupt/unsupported payloads keep defaults and never erase storage; persist serializes once and leaves storage untouched on failure.

## Unknown runtime behavior (still untested)
- localStorage access denied/quota in getStorage/persistUxMetadata; MediaRecorder codec support and stop/flush timing across browsers; parseUxMetadata with 'ok' payloads missing observations/limitations arrays.