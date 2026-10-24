# HM-UX06 Acceptance Plan (26 cases)

Status: worker planning inventory only, NOT the original numbered 26 acceptance gates. Actual execution and the unchanged original numbering are recorded in HM-UX06-delivery.md. This inventory is not a pass report.

Original planning text follows. Status: planning only. Harness is local-only (`/qa-acceptance.html`), same-origin iframe of the real app at `/`. Never committed/published. No storage, history, cookie, or upload modifications. No automatic Record/Upload clicks. Operator drives the real app; harness only patches `navigator.mediaDevices` on the iframe after load and before the recorder opens.

Evidence levels (honest):
- **browser-synthetic** — exercised in this harness with synthetic canvas stream (no human pose, labelled QC).
- **hardware** — requires a real device + user grant; not run in this harness.
- **unit** — covered by existing unit tests; not re-run here.
- **pending** — not run yet; awaiting owner/operator.

All 26 cases below are marked **not run yet** unless explicitly noted.

## Cases

| # | ID | Given / When / Then | Evidence level | Status |
|---|----|---------------------|----------------|--------|
| 1 | C00-Entry | GIVEN Analyse opens, WHEN no active job, THEN Choose video and Record a set are shown; capability detection alone never requests camera. | browser-synthetic | not run yet |
| 2 | C01-Education | GIVEN first record attempt, WHEN user taps Record, THEN permission education + consent appear; Choose video stays enabled. | browser-synthetic | not run yet |
| 3 | C02-Permission | GIVEN user grants/denies camera, WHEN result returns, THEN granted → live ready; denied → education stays, Choose video enabled. | browser-synthetic (denied mode) + hardware (granted) | not run yet |
| 4 | C03-LiveReady | GIVEN permission granted, WHEN stream ready, THEN rear/environment preferred; front switch only when available; mirror selfie preview only; framing corners are guidance, not verified posture. | browser-synthetic | not run yet |
| 5 | C04-Countdown | GIVEN Start recording, WHEN countdown runs, THEN 3s monotonic, accessible, cancellable; 0 bytes sent. | browser-synthetic | not run yet |
| 6 | C05-Recording | GIVEN countdown completes, WHEN recording runs, THEN indicator + timer + Stop shown; auto-stop at 60s/100MiB; no network upload. | browser-synthetic | not run yet |
| 7 | C06-Finishing | GIVEN recorder stopped, WHEN finalizing, THEN finalize once; stop camera/timers; validate non-empty blob, supported type, duration/size; release obsolete URLs. | browser-synthetic | not run yet |
| 8 | C07-Review | GIVEN clip ready, WHEN review opens, THEN Play/Retake/Use this video/Cancel; Use selects clip; Upload & analyse remains consent-gated; nothing uploaded on Use alone. | browser-synthetic | not run yet |
| 9 | C08-Upload | GIVEN explicit Upload & analyse with consent, WHEN upload runs, THEN single-active-job guard; bytes shown; Cancel aborts XHR; ambiguous server receipt explained. | hardware (real network) | not run yet |
| 10 | C09-Creating | GIVEN upload accepted, WHEN create runs, THEN create once; retry reuses asset ID + stable request_key. | hardware | not run yet |
| 11 | C10-Processing | GIVEN analysis created, WHEN polling, THEN show time since created_at, no ETA; Cancel stays pending until terminal. | hardware | not run yet |
| 12 | C11-Report | GIVEN server success (possibly partial), WHEN Results opens, THEN navigate; release unneeded local resources; retry never silently reruns. | hardware | not run yet |
| 13 | E01-PermissionDenied | GIVEN camera blocked, WHEN user taps Record, THEN education shows; Choose video stays enabled; no upload. | browser-synthetic (denied mode) | not run yet |
| 14 | E02-NoHardware | GIVEN no camera device, WHEN Capture opens, THEN Record hidden; Choose video enabled. | browser-synthetic (missing mode) | not run yet |
| 15 | E03-CaptureUnsupported | GIVEN browser cannot capture, WHEN Capture opens, THEN Record disabled; Choose video fallback. | browser-synthetic (missing mode) | not run yet |
| 16 | E04-Codec | GIVEN encoding/muxing fails, WHEN stopped, THEN invalid blob rejected; retake or Choose video. | browser-synthetic | not run yet |
| 17 | E05-ClipValidation | GIVEN >60s/>100MiB or invalid type, WHEN validating, THEN functional message; replace/trim; allow server validation when only local preview unsupported. | browser-synthetic | not run yet |
| 18 | E06-NetworkAmbiguous | GIVEN upload response unclear, WHEN shown, THEN "Upload status unclear. Your file is kept locally."; user-triggered retry only. | hardware | not run yet |
| 19 | E07-VideoOkCreateFail | GIVEN upload ok, create failed, WHEN retrying create, THEN reuse asset + same request_key; do not re-upload. | hardware | not run yet |
| 20 | E08-PollRetry | GIVEN poll connection lost, WHEN retrying, THEN poll retried; upload not resubmitted. | hardware | not run yet |
| 21 | E09-CancelRace | GIVEN job finishes while cancel pending, WHEN polling, THEN trust terminal server state; never label completed as cancelled. | hardware | not run yet |
| 22 | E10-PartialZero | GIVEN zero completed cycles / null, WHEN Results opens, THEN "No completed cycles were detected. Available pose data is still shown."; no LLM count. | hardware | not run yet |
| 23 | E11-CoachingQuota | GIVEN coaching endpoint fails, WHEN opening Home/Results/Progress, THEN "Coaching is unavailable right now."; measurements only; no auto paid retry. | hardware | not run yet |
| 24 | E12-StorageFailure | GIVEN localStorage write fails, WHEN saving, THEN no increment; error shown; existing record preserved. | unit | not run yet |
| 25 | E13-CorruptRecord | GIVEN stored entry unreadable, WHEN reading, THEN skip corrupt entry; do not erase valid history. | unit | not run yet |
| 26 | E14-ExpiredThumbnail | GIVEN thumbnail URL expired, WHEN report opens, THEN functional message; cache dropped; no silent erase of server analysis. | hardware | not run yet |

## Explicit non-cases (honesty guards)

- **Oversize / encoded invalid file**: harness cannot claim Review pass. Marked **pending**; requires hardware + real encoder.
- **Explicit paid coaching test**: unauthorized in this harness. Marked **stub / previous unit evidence pending**. Do not fabricate scores, coaching, or poses in the live app.

## Harness behaviour summary

- Same-origin iframe of `/` at CSS widths 360 / 375 / 1365, height 820.
- Buttons: Home, Analyse, Progress, Settings, Reload iframe.
- Parent patches `navigator.mediaDevices` on the iframe **only after iframe load** and **before operator opens recorder**.
- Modes:
  - **synthetic** — returns a real `MediaStream` from `canvas.captureStream(30)`; moving colour frames labelled `QC`; no human pose; simulated front/rear toggle is explicit, not physical hardware.
  - **denied** — `getUserMedia` rejects with `NotAllowedError`.
  - **missing** — `mediaDevices` is `undefined` (no `getUserMedia`).
  - **real** — explicitly restores the original property descriptor; real device grant requires user approval.
- Original property descriptor is retained and restored on mode change.
- Generated stream cleanup: stop tracks, cancel animation frame on reload / unload / mode change.
- No storage / history / cookie writes. No fake analyses, scores, coaching, or poses. No automatic Record/Upload clicks. Operator interacts with the real app; harness never uploads.
- Optional read-only DOM metrics: iframe viewport, no horizontal overflow, control rects ≥44px.

## Evidence level legend

- **browser-synthetic** — exercised here with synthetic canvas stream.
- **hardware** — requires real device + user grant; not run in this harness.
- **unit** — covered by existing unit tests; not re-run here.
- **pending** — not run yet; awaiting owner/operator.
