# HM08 focused review

- Fourth exercise card: disabled 'Overhead press / Coming soon' placeholder removed; 'Incline dumbbell press' (incline_chest_press, variant incline_dumbbell_bilateral handled server-side) added to EXERCISES so it renders as a normal selectable card via the existing map, reusing the existing 'pull' artwork (no fake art). All 4 cards selectable once backend catalogue migrates.
- POSE_ONLY honesty: detected-rep count is null (displayed as em-dash + 'Unavailable for this report') when warnings include POSE_ONLY, instead of showing 0 from an empty reps array; otherwise counts only reps with completion_status==='completed'. Same logic used for saveLog detectedReps and the rep-count input placeholder, keeping 0 vs null distinct in local history.
- Warnings rendered human-readable: POSE_ONLY mapped to 'video and pose data are ready, but a movement report is not yet available'; other codes de-snaked. Removed the false claim that pose-only reports contain 'rep detection and joint-angle metrics from 2D tracking'.
- Coaching fallback no longer says 'metrics below are still real' (false when metrics array is empty).
- Polling: effect now guards on session readiness and depends on [job, session]; job metadata is kept in localStorage after success so a refresh can restore an unsaved report; network failures surface a message with an explicit user-driven Retry button that resumes polling (no automatic resend).
- cancelJob checks r.ok and surfaces server/network errors via resultErr instead of swallowing them.
- Video element gains onError -> meaningful 'expired or removed' indicator; flag resets on new upload and on resume.
- Remote DELETE copy is honest: 'Revoke access... does not guarantee physical erasure'; button renamed 'Revoke server analysis'; on success the open report/selection for the deleted job is cleared and JOB_KEY removed, while the local history entry is preserved.
- loadLogs validator: loggedReps must be a finite integer 0..10000, exercise must be in the known catalogue, analysisId must be a valid UUID or null, createdAt must parse as a date, detectedReps null or non-negative integer, notes/load bounded strings; invalid entries dropped. No secrets are stored (only logs, display name, active-job metadata).
- Active-job restore validates UUID-shaped id, known exercise and parseable date.
- saveLog rejects non-integers, Infinity and values >10000 with a visible message instead of Math.floor coercion; localStorage write failure surfaces a visible error rather than implying success.
- Camera guidance strings describe the required view only and do not promise measurement.

Integrator: corrected generated JSX condition, enabled Retry before first successful status read, replaced capability claims in hero, and retained explicit pose-only limitations at the result. Production build/browser checks remain acceptance evidence.
