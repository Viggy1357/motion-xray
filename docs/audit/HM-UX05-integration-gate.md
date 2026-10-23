# HM-UX05 Integration Gate — New Contracts Only

Scope: settings persistence, display-name readback, Viewed marker, goal/milestone counting, camera file handoff. Not a repeat component audit; excludes UI styling, pose math, and coaching.

Evidence: Docker typecheck/build passed before latest targeted settings/viewed repair. 13 ux-metadata pure tests passed; all capture controller checks and 12 pose checks passed. Browser verified: Home, settings Cancel, progress, camera education Cancel. Camera opaque CSS repaired. Saved owner report expired shows honest failure. No actual device permission/recording tested; no paid coaching.

Contract checks

1. One-write settings name failure atomicity — accept. saveSettings merges settings and displayName into one mxr.ux.v1 record, serializes once, and persists before any React state update. persistUxMetadata failure returns false and leaves existing storage untouched. SettingsPanel calls onNameChange only after onSave returns true; Cancel discards drafts and never calls onSave.

2. Legacy name readback — accept. Page reads mxr.displayName.v1 only as fallback when mxr.ux.v1 displayName is absent or invalid. No writes to the legacy key occur in this slice.

3. Viewed only matching non-null visible movement report — accept. The Viewed effect requires route results, a result, movementSettled true, movement non-null, movement analysis_id equals result.analysis_id, and document.visibilityState visible. It persists withViewed to mxr.ux.v1 before setUxMeta; storage failure records nothing. Failed or missing movement, including POSE_ONLY, never marks Viewed. Label remains Viewed, not Reviewed.

4. Goal counts eligible unique proof/manual separate — accept. weekAnalysed counts deduplicated analysed sets keyed by recognition.analysisId where recognitionVersion is analysed-set-v1 and recognition is present. Manual entries and legacy logs without recognition are excluded from goal/milestone credit but may remain in the saved-log total. No retrospective recognition for edits.

5. No metrics/scoring/API changes — accept. No new endpoints, no scoring changes, CoachingResult schema unchanged, no automatic paid coaching calls.

6. Real camera use only passes file — accept. CameraRecorder hands a File to onUse; no camera permission is silently treated as upload consent; Choose video remains the fallback when camera is unavailable or denied.

Remaining tests to run honestly (not yet passed)

- Real device: camera permission grant, denial, no hardware, and busy states; recording to a valid file within 60s/100MiB.
- Fresh report end-to-end: upload → analysis create → poll → result → movement report non-null → save log → Viewed marker set only when visible.
- Storage failure atomicity: quota error on mxr.ux.v1 settings write and mxr.logs.v1 save; previous values unchanged, no partial commit.
- Legacy name readback when mxr.ux.v1 is absent or corrupt.
- Viewed marker not set when movement is null, mismatched analysis_id, or the Results tab is backgrounded.

Blockers: none.

Delivery acceptance: implementation candidate. Runtime limits: device validation outstanding; not clinical; not full 35-row acceptance. Merge only after the remaining real-device and fresh-report tests pass.