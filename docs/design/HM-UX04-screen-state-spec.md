# HM-UX04 Screen & State Specification

Status: planning only. Implementation NOT approved by this document.
Baseline: 80a3978 clean main. Planning commits may follow; see README and TASKS continuation.
Mockup reference: [approved four-screen board](previews/HM-UX02-concept.png). Illustrative, generated, no private footage. SHA256: cb2084e1f1ca07e6d6a6aafad8f415612f10bb7a1ee05e4b79c79f6bf2b92842.
Target audience: casual/beginners; analysis first; understated game feel.
Boundaries: no paid product calls, no accounts, no LLM scores, no injury/safety/anti-cheat claims.

## 1. Source of truth and honesty rules

CoachingResult schema is fixed and public: status, summary:string|null, observations:string[], next_set_cue:string|null, limitations:string[]. There is NO public structured rep_ids, metric_ids, source_ids, or thumbnail_url. The UI must not claim structured links that are not exposed.

The existing helper recognises only the strict observation prefix 'Segment N (' where N matches ORIGINAL Rep.ordinal in PrototypeAnalysisResult.reps. Presentation may use that validated prefix exactly when it matches actual reps; otherwise default to noReplay. Robust typed evidence-card IDs are a backend contract gate requiring versioned generated types and tests.

Existing backend coaching validates compact evidence internally. The explicit paid POST is unchanged and is not automatic on render or home. Existing PTS map and private proxy routes are already implemented; reuse them, do not start a new backend project.

When one actual cue is available, do not force a second. When no cue is available, render a neutral measured summary; do not fabricate an elbow claim. The lat example (5 cycles, 18 fragments, 93% visibility) is a fixture test value, not a universal app number; avoid all numeric fixture UI except in test cases.

Source actual partial fragments are different from partial visibility. Do not force rep-counter renumbering. A completed cycle is not a manual confirmed rep; visibility is not confidence or accuracy; null is not 0; 0 segmented cycles is not performed 0 reps.

## 2. Screen and state IDs

- HM-UX04-HOME — Home screen
- HM-UX04-CAPTURE — Capture screen
- HM-UX04-RESULTS — Results screen
- HM-UX04-PROGRESS — Progress screen
- HM-UX04-SETTINGS — Settings / guest profile screen (supporting)
- HM-UX04-STATE-SETUP — pre-record permission and framing
- HM-UX04-STATE-COUNTDOWN — 3s setup countdown
- HM-UX04-STATE-RECORDING — live capture up to 60s / 100MiB
- HM-UX04-STATE-REVIEW — review / retake / cancel
- HM-UX04-STATE-UPLOAD — XHR byte progress, stable request_key
- HM-UX04-STATE-PROCESSING — server stages, time since created_at, poll / cancel
- HM-UX04-STATE-SAVED — post-save confirmation
- HM-UX04-STATE-ERROR — functional messages for 404 / unavailable / network

## 3. Camera state transition table

| ID | State | Trigger | Data | Actions | Next | Back | Recovery |
|----|-------|---------|------|---------|------|------|----------|
| C00 | Entry | User opens Analyse | selected exercise; consent | Show Choose video and Record a set. Capability detection alone never requests the camera. If a job is active, offer Resume/Cancel instead of another upload. | Choose → C07; Record → C01 | Home | Upload fallback remains available |
| C01 | Education | First record attempt | permission state | Show permission education + consent; keep Choose video enabled | C02 | C00 | Re-show education on repeat denial |
| C02 | Permission pending | User grants/denies camera permission | permission result | If granted: initialize camera; if denied: stay in education, enable Choose video fallback | C03 / C01 | C01 | Functional message; no auto-retry |
| C03 | Live ready | Permission granted; camera stream ready | video-only track; facing mode | Rear/environment preferred; front switch only when available; mirror selfie preview only; framing corners are guidance, not verified posture. Start recording is explicit. | Record → C04 | C00; release camera | Switch failure retains working camera or offers Choose video |
| C04 | Countdown | Start recording | 3s monotonic countdown | Announce countdown accessibly; allow Cancel; send no bytes. | Elapsed → C05; Cancel → C00 | C00 | Re-enter Record to reacquire camera; no auto-start |
| C05 | Recording | Countdown completes | actual elapsed; chunks and bytes | Show recording indicator, timer and Stop; stop at60s or observed byte guard. No network upload. | Stop/limit/interruption → C06 | Stop/discard confirmation, not countdown | Finalized clip must still satisfy60s/100MiB server limits; chunk overshoot is possible |
| C06 | Finishing | Recorder stopped | final chunks; playable blob | Finalize once; stop camera/timers; validate nonempty blob, supported type, duration/size. Release obsolete URLs only. | Valid → C07; invalid → C00 with error | Cannot resume old recording | Retake or Choose video; no upload of invalid blob |
| C07 | Review | Recorded or chosen clip ready | local blob/file; preview URL | Recorded clip: Play/Retake/Use this video/Cancel. Use selects the clip; explicit Upload & analyse remains consent-gated. Retake/discard confirms unsaved material, releases it and returns to setup. | Upload + consent → C08; Retake → C00 | C00 with discard confirmation | Nothing uploaded on Use alone; preview/codec fallback remains honest |
| C08 | Upload | Explicit Upload & analyse with consent | file/blob; actual XHR bytes | Apply single-active-job guard; show bytes sent; Cancel aborts XHR. |201 → C09; failure → C07 + E06 | Abort upload; ambiguous server receipt must be explained | Keep clip while page stays open; no claim of upload deduplication |
| C09 | Creating | Upload accepted | video asset ID + stable request_key | Create analysis once; creation retry reuses both values. | Success → C10; failure → recovery panel | Analyse recovery panel, never automatic re-upload | Retry creation only; keep upload receipt in current page memory |
| C10 | Processing | Analysis created | owned job ID; server created_at/stage | Poll actual lifecycle; show time since submission, no ETA. Cancel stays pending until terminal response. | Success → C11; failed/cancelled → recovery | Home/Progress; job continues | Resume status without uploading/creating again |
| C11 | Report | Server success, possibly partial | owned report + proxy/pose/map | Navigate to Results; release unneeded local recording resources. | Results review/save | Analyse | Report retry never silently reruns analysis; local clip may be lost after reload |

Camera error/interruption rows:
- C-E01 Permission denied: trigger deny/block; actions show education, keep Choose video; next C01; back C00; recovery functional message, manual retry.
- C-E02 No hardware: trigger no camera device; actions hide Record, show Choose video; next C01; back C00; recovery functional message.
- C-E03 Busy: trigger camera in use by another app; actions release and wait; next C02; back C02; recovery user retry.
- C-E04 Unsupported capture: trigger unsupported codec/format; actions disable Record; next C01; back C00; recovery functional message.

| ID | State | Trigger | Action | Next | Back | Recovery |
|----|-------|---------|--------|------|------|----------|
| C-E05 | Codec | Encoding/muxing fails | Stop and validate; reject invalid blob | C00 | C00 | Retake or Choose video |
| C-E06 | Empty blob | Zero-length recording | Explain failure; release unusable clip | C00 | C00 | Retake or Choose video |
| C-E07 | Limit | 60s or 100MiB reached | auto-stop and finalize | C06 | C05 | none (expected) |
| C-E08 | Background | app backgrounded | stop tracks/timers, no auto-resume | C06 | C05 | honest state if blob lost |
| C-E09 | Orientation | Device rotates | If track/encoder remains valid, continue with one orientation mapping; otherwise finalize as interrupted | C05 or C06 | Stop | Device test must verify no double rotation or stretching |
| C-E10 | Navigation | leaving page | stop tracks/recorder/object URLs/timers; beforeunload warning where permitted | C00 | — | no BFCache persistence guarantee |
| C-E11 | Discard | Retake/cancel with unsaved media | Confirm before discard | C00 | C07 | Ordinary product confirmation |
| C-E12 | Retry | Network/server failure | Retry the failed operation only | Upload → C08; create → C09; poll → C10 | Review/status | Never re-upload for a poll failure |

## 4. Error matrix (E01–E16)

| ID | Error | Trigger | Safe user copy | Recovery | Auto-retry? |
|----|-------|---------|----------------|----------|-------------|
| E01 | Permission denied | Camera permission blocked; microphone is not requested | "Camera access is not available. You can still choose a video file." | Enable Choose video; manual retry in settings | No |
| E02 | No hardware | No camera device detected | "No camera found on this device." | Choose video remains enabled | No |
| E03 | Capture unsupported | Browser cannot capture video | "Video capture is not supported here." | Choose video fallback | No |
| E04 | Codec | Encoding or muxing fails | "Could not encode the recording. Please try again." | Discard invalid blob; retake with confirm | No |
| E05 | Clip validation | Over60s/100MiB, invalid type or unreadable preview | "Trim this clip to60seconds and100MiB or less." For preview-only failure: "Preview unavailable; the server will validate the upload." | Replace/trim invalid clip; allow server validation when only local preview is unsupported | No |
| E06 | Network upload ambiguous | Upload response unclear | "Upload status unclear. Your file is kept locally." | Retain blob; user-triggered retry only | No |
| E07 | Video success, create failure | Upload succeeded, job creation failed | "Upload completed, but analysis could not start." | Reuse asset + stable request_key; manual retry | No |
| E08 | Poll retry | Status connection lost | "Connection interrupted. The analysis may still be running." | Retry status; preserve job ID; do not resubmit | User retry; resume normal polling after success |
| E09 | Cancel race | Job finishes while cancellation is pending | "Cancellation requested; waiting for confirmation." | Trust terminal server state: cancelled or completed; never label completed as cancelled | Poll confirmation only |
| E10 | Partial / zero cycles / null | Deterministic movement report has gaps or zero completed cycles | "No completed cycles were detected. Available pose data is still shown." | Preserve measured values/reasons; zero detections does not mean zero performed reps; LLM does not determine count | No |
| E11 | Coaching quota/network/unavailable | Coaching endpoint fails | "Coaching is unavailable right now." | Show measurements only; no auto paid retry | No |
| E12 | Storage failure | Existing browser-history write fails | "Local history could not be written." | No increment; preserve existing record | No |
| E13 | Corrupt record | Stored history entry unreadable | "An old session could not be read and was skipped." | Skip corrupt entry; do not erase valid history | No |
| E14 | Expired thumbnail/report | Thumbnail or report URL expired | "This preview is no longer available." | Re-generate from source if allowed; drop cache | No |
| E15 | Recording interruption | Recording interrupted by call/background | "Recording was interrupted. The clip may be incomplete." | Retain valid in-memory blob only after finalization; honest state if lost | No |
| E16 | Guest owner404 | Resource unavailable under current owner session | "This analysis is unavailable in this browser session; it may have expired or been removed." | Keep local log; release dead active-job lock; offer new analysis without exposing other owners | No |

Current media access lasts up to24h; access expiry/revocation is distinct from guaranteed physical erasure. Removing a local entry must not delete server analysis. No automatic paid retry on any error.

## 5. Mockup parity matrix (35 rows)

| ID | Screen / control | Current status | Proposed task ID | Data owner | Acceptance |
|----|------------------|----------------|------------------|------------|------------|
| P01 | Home/Progress: profile entry | Missing; display-name field exists separately | UX4-05 | UX | Opens settings; guest/local only; no accounts |
| P02 | Capture: settings icon | Missing | UX4-05 | UX | Same destination as profile entry |
| P03 | Results: more menu | Missing (purpose pending) | UX4-05 | UX | Only useful report actions; omit if none |
| P04 | Home: brand camera elevated nav | Implemented (decorative) | UX4-02 | UX/Eng | Opens Analyse only; not a capture control |
| P05 | Home: last focus cue + thumbnail | Partial (text only) | UX4-05 | UX/Eng | Thumbnail from real video; text fallback if absent; neutral Last review label when coaching absent |
| P06 | Home: weekly target opt-in | Missing | UX4-05 | UX | Opt-in only; show actual saved counts without a target until chosen; no automatic goal of3 |
| P07 | Home: calendar week vs rolling 7 | Implemented rolling 7 | UX4-05 | UX | Default recommended Mon-Sun local calendar week; explicit decision required; rolling 7 unchanged until implemented |
| P08 | Capture: crop framing corners | Missing | UX4-02 | Eng | Guidance corners visible; no auto-verified full body |
| P09 | Capture: manual check guidance | Missing | UX4-02 | UX/Eng | Text guidance only; user initiates check |
| P10 | Capture: permission UI | Missing | UX4-02 | Eng | Education before first record; deny keeps Choose video |
| P11 | Capture: live video preview | Missing | UX4-02 | Eng | Mirrored selfie preview; normalized oriented frames |
| P12 | Capture: Record / Choose | Missing Record | UX4-02 | Eng | Record leads to countdown; Choose opens file picker |
| P13 | Capture: countdown | Missing | UX4-02 | Eng | 3s accessible; cancellable; releases resources and sends 0 bytes |
| P14 | Capture: stop / retake / use / cancel | Missing | UX4-02 | Eng | Stop at 60s/100MiB; retake discards with confirm; cancel discards |
| P15 | Results: instructional caption | Missing | UX4-03 | UX | Plain instruction explains tapping a detected segment; active state follows real playback |
| P16 | Results: chip strip | Partial: click selection exists; playback-follow missing | UX4-03 | UX | Tap seeks the original segment start and plays; active selection follows mapped playback; no page-load autoplay |
| P17 | Results: partial segment labels | Missing | UX4-03 | UX | Labels reflect actual partial fragments; not visibility |
| P18 | Results: evidence thumbnail | Missing | UX4-03 | UX/Eng | From PTS map; default noReplay if unlinked; privacy alt |
| P19 | Results: next cue | Partial: actual cue exists after explicit coaching; highlight presentation missing | UX4-03 | UX | One highlight card with actual observation/optional next-set cue; neutral summary if none |
| P20 | Results: measurements link | Partial: existing disclosure | UX4-03 | UX | Full-width link; actual completed cycles/fragments only |
| P21 | Results: Save | Implemented (form) | UX4-03 | UX | One primary action per state; saved/unsaved/edit label |
| P22 | Progress: small companion | Missing | UX4-05 | UX | Real date counts; no fake milestones |
| P23 | Progress: calendar week vs rolling 7 | Implemented rolling 7 | UX4-05 | UX | Same as P07; explicit decision gate |
| P24 | Progress: body regions row values | Missing | UX4-05 | UX/Eng | Primary region per exercise: lat back, curl arms, squat legs, press chest; denominators actual counts |
| P25 | Progress: recent session thumbnail | Missing | UX4-05 | UX/Eng | Real video only; text placeholder if absent; no stock screenshots |
| P26 | Progress: date viewed / View all | Partial | UX4-05 | UX | View all opens existing all-history list with Reopen/Manage |
| P27 | Progress: milestone | Missing | UX4-05 | UX | First three eligible unique actual saved sets; non-punitive; no economy |
| P28 | Progress: local disclaimer | Implemented | UX4-05 | UX | Local-only disclaimer; no all-time awards |
| P29 | Character: front/back visibility | Missing (static poster) | UX4-01 | Art/UX | Front/back visible parity is a design contract; asset choice pending = explicit gate, no dummy placeholder |
| P30 | Character: highlights/captions | Missing | UX4-01 | Art/UX | Illustrative highlights follow exercise-target mapping, not measured activation; same character across views |
| P31 | Empty / permission / partial / failure / expired / saved / corrupt | Partial | UX4-02/03/05 | UX/Eng | Functional messages; no silent cuts |
| P32 | Layout mobile 375/360 and desktop 1365 | Partial | UX4-05 | UX | Header/hero/CTA order; 12–30px type; 44px targets; no fixed heights if content wraps |
| P33 | LCP poster budget | Implemented (1.4MiB) | UX4-01 | Art | Fallback state; asset license pair; high-quality mesh art gate; not measured FPS |
| P34 | Accessibility | Partial | UX4-05 | UX | Focus/error announcements via caption, not color alone; reduced motion; drag alternatives |
| P35 | Capture: empty preview frame | Partial: current basic placeholder | UX4-03 | UX | Empty guidance shown; no stock pose video |

## 6. Per-screen layout specification

### HM-UX04-HOME
Mobile375/360: compact brand/profile header about56px; hero about430px high, bounded by available width; primary Analyse a set directly below hero, then last-focus card, weekly summary/optional goal, bottom nav. Desktop1365: existing side rail, bounded two-column hero and supporting cards; do not stretch a phone layout. Profile/settings is secondary, never the main CTA. Type scale 12–30px. Touch targets ≥44px. No fixed height if content wraps. Relevant frame before user footage: show empty guidance; never stock pose video. LCP poster budget: current 1.4MiB fallback state; asset license pair; high-quality mesh/art gate; not measured FPS.

### HM-UX04-CAPTURE
Exercise selector (4 existing IDs: lat_pulldown, dumbbell_curl, squat, incline_chest_press), guidance text, Choose video, Record a set (proposed), consent visible, optional load notes, Upload Analyse. States: SETUP → COUNTDOWN → RECORDING → REVIEW → UPLOAD. Default rear/environment camera; front toggle where available; no guarantee device. Mirrored selfie preview vs unmirrored review. No audio default. Countdown 3s, real monotonic, cancellable. Recording hard stop 60s / 100MiB. Stop tracks/recorder/object URLs/timers on leaving. Retake/discard confirm only if unsaved material exists.

### HM-UX04-RESULTS
Video overlay toggle, playback speed, chip strip, partial fragments disclosure, summary actual completed cycles/fragments/signal visibility, coaching button, measurements & reference, manual save form. Coaching highlight card: exactly one card, one actual observation plus an optional existing next-set cue; the prefix links a segment ordinal, NEVER a source ID, replay thumbnail only when linked; default noReplay. Credible explanation is a Must for parity; graceful no-data render allowed. Selected segment follows playback vs manual selection precedence defined by actual current time source PTS; overlapping fragments never invent rep events. One primary action per state: Save unsaved / Saved edit label. Accessible focus and error announcements via caption, not colored pill alone. Thumbnail alt privacy. Reduced motion respected. Drag button alternatives.

### HM-UX04-PROGRESS
7-day real date counts; analysed sets by exercise bars; recent sessions with thumbnails/reviewed/View all; milestone first three eligible unique actual saved sets. Body regions: one primary region per exercise (lat back, curl arms, squat legs, press chest); secondary future only if defined; regions are activity, not measured muscle development. Bar max actual; fixed known week period labels; denominators actual counts, no fake percent muscle power. Empty state when no history; no fake milestones or comparable-set trends. View all opens existing all-history list.

### HM-UX04-SETTINGS and supporting states
Guest display name, local goals, consent, retention. Not accounts. Empty/permission/partial/failure/expired/saved/corrupt storage: functional messages, no silent cuts. Post-save: separate confirmation and next action; no auto-save browser media.

## 7. Data and metadata table

| Field / concept | Current | Proposed | Gate / notes |
|-----------------|---------|----------|--------------|
| CoachingResult fields | status, summary, observations, next_set_cue, limitations | Unchanged | No public rep_ids/metric_ids/source_ids/thumbnail_url |
| Local weekly goal | None | Opt-in flag + target | User opts in only; no automatic goal |
| Review marker | None | Explicit: report opened vs viewed video | Definition required before use |
| Focus cue cache | None | References only, not LLM auto-calls | Backend contract gate |
| Milestone counts | None | Unique eligible current saved set history | Recompute on delete/clear; loses local state; no all-time awards |
| Metadata namespace | None | Versioned migration; unknown fields preserved | Atomic; preserve legacy proof |
| Thumbnails | None | Owner-scoped in-memory; PTS map; canvas fallback | Revocation/expiry; revoke URLs/drop cache; durable endpoint is backend gate |
| localStorage | mxr.logs.v1 | Unchanged | No raw thumbnails/base64/faces; no unsafe expiring private image URLs |
| Last focus label | Last review | Neutral when coaching absent | No invented cue |
| Region mapping | None | lat back / curl arms / squat legs / press chest | Primary unique; denominators actual counts |
| Saved date | Preserved | Preserved on edit; count not retimed today | — |

## 8. Layout and accessibility

Mobile 375/360 and desktop 1365. Screen header, hero, heights, aspect, CTA order and types 12–30px; 44px touch targets. No literal height for everything if content wraps. Sticky primary CTA on Capture and Results. Visible upload consent on Capture; explain browser-local persistence beside Save without inventing a second consent requirement. Reduced motion respected. Accessible focus and error announcements via caption, not just colored pill. Thumbnail alt text for privacy. Drag button alternatives. No WCAG certification claim.

## 9. MVP must / should / future and pending decisions

Must: existing upload/analyse/save; consent; error messages; region bars as activity; local history v1; camera record flow as proposed next MVP for mockup parity; coaching highlight card with credible explanation and graceful no-data render; main character front/back visible parity as design contract with explicit gate (asset choice pending, no dummy placeholder pass).

Should: progress thumbnails and View all; weekly target opt-in.

Future: high-quality rotatable 3D mesh independently gated (future or art decision), not fulfilled by current procedural map; full estimated 3D movement replay as a separate future feature, not the generic companion mesh; clinical/PT review; export guidance.

Pending decisions (max 5, recommended defaults):
1. Companion asset: choose one controllable high-quality athlete mesh or explicitly accept matching front/back rendered views as an interim deliverable. Recommended interim: matching views of the same athlete with illustrative target overlays. This recommendation is not an approved cut of rotation; owner resolves the art gate before implementation. The current single poster is not a front/back parity pass.
2. Evidence linking: use the existing validated segment-prefix adapter for the first card, or approve a versioned structured-evidence contract. Recommended first slice: reuse the exact validated prefix; omit unsupported replay/source links. A matched segment ordinal never supplies a source ID.
3. Week default: recommended local calendar week Mon–Sun; rolling 7 alternative. Default: rolling 7 unchanged until implementation.
4. Facing mode: recommend rear/environment for gym full-body; offer front camera where available. Device capability determines the actual option.
5. Audio default: off / no audio; no microphone permission by default.

## 10. Acceptance gates (Given / When / Then)

1. GIVEN camera is missing, WHEN user opens Capture, THEN Record is hidden and Choose video remains enabled.
2. GIVEN camera permission denied, WHEN user taps Record, THEN education shows and Choose video stays enabled; no upload occurs.
3. GIVEN countdown started, WHEN user taps cancel, THEN resources release and 0 bytes are sent.
4. GIVEN recording reaches 60s or 100MiB, WHEN limit hits, THEN recording stops and moves to REVIEW.
5. GIVEN review with unsaved media, WHEN user taps retake, THEN confirmation appears and media is discarded; nothing persisted.
6. GIVEN user leaves Capture mid-recording, WHEN unload occurs, THEN tracks/recorder/object URLs/timers stop; beforeunload warning where permitted.
7. GIVEN video upload succeeds but job creation fails, WHEN retrying creation, THEN reuse its video asset ID and the SAME request_key; do not re-upload. An ambiguous failed upload does not claim upload-level deduplication.
8. GIVEN processing poll fails, WHEN retry occurs, THEN poll is retried; upload is not resubmitted.
9. GIVEN coaching returns no eligible observation, WHEN Results opens, THEN neutral measured summary shows; no fabricated cue.
10. GIVEN an explicit coaching request returned one eligible observation, WHEN presenting it, THEN show that actual observation and optional next_set_cue; add replay only for a validated segment association, never invent source IDs.
11. GIVEN a segment chip is tapped, WHEN video plays, THEN seek its original mapped start, update active state from actual playback and allow normal continuous playback; bounded looping is not implied.
12. GIVEN no history exists, WHEN Progress opens, THEN empty state shows; no fake milestones.
13. GIVEN session lacks thumbnail, WHEN Progress renders, THEN text placeholder shows; no stock screenshot.
14. GIVEN localStorage write fails, WHEN saving, THEN no increment; error message shown; existing record preserved.
15. GIVEN 375px width, WHEN any screen renders, THEN touch targets ≥44px and type 12–30px; no content-wrap height overflow.
16. GIVEN 1365px width, WHEN desktop rail renders, THEN header 64px and side rail present; layout does not break.
17. GIVEN reduced motion enabled, WHEN transitions occur, THEN motion is reduced or disabled.
18. GIVEN thumbnail URL expired, WHEN report opens, THEN functional message shows; cache dropped; no silent erase of server analysis.
19. GIVEN weekly goal not opted in, WHEN Home opens, THEN illustrative companion shows; no goal of 3 and no penalty.
20. GIVEN user taps more menu, WHEN menu opens, THEN only useful report actions appear; if none, menu purpose is omitted/pending.

21. GIVEN upload consent is unchecked, WHEN choosing/recording/previewing a clip, THEN no upload starts and no consent is silently inferred from camera permission.
22. GIVEN completed and excluded intervals overlap, WHEN playback advances, THEN select an actual completed interval if present; otherwise an actual excluded interval; outside intervals select none. Do not fabricate boundaries. Tapping selects immediately, then playback time becomes authoritative.
23. GIVEN an eligible analysis was already saved, WHEN corrected counts or notes change, THEN update that record without changing its original date or incrementing recognition. Legacy/manual records receive no retrospective recognition.
24. GIVEN a valid clip has no measurable completed cycles, WHEN showing Results, THEN preserve any usable pose/video and missing reasons; omit unsupported coaching claims and eligibility awards.
25. GIVEN coaching is idle or quota-blocked, WHEN opening Home/Results/Progress, THEN zero new paid coaching requests occur. Only an explicit request can call the existing endpoint.
26. GIVEN thumbnail extraction fails or access is revoked, WHEN rendering a session, THEN use a neutral icon/text fallback, dispose cached object URLs, retain the local record, and never substitute a generated exercise frame.

## 11. Supporting destinations and exact action contracts

These destinations are **proposed**, not installed routes. Keep the three main nav
destinations. A profile/settings entry opens an auxiliary `/settings` page; Back
returns to the originating screen without discarding a selected local clip silently.
Recent sessions show the most recent three records; View all opens
`/progress?view=all`, retaining existing Reopen/Manage actions and a Back affordance.
Do not add a nonfunctional More icon: reserve it for useful report actions after
their scope is agreed, otherwise omit it and record that deliberate mockup deviation.

First-use introduction: one concise explanation of supported exercises, upload vs
recording, provisional observations and local history. Continue opens Analyse; Skip
does not grant camera/upload consent. Display-name entry is optional.

Settings: edit local display name; optionally set a weekly analysed-set target (positive
whole number, user-chosen, no preselected target); Cancel discards edits; Save reports
success only after storage succeeds. Show local-history/access-expiry explanations.
Provide camera troubleshooting instructions, not a fake switch that changes browser
permission. Do not add microphone, account, cloud-sync or irreversible history-clear
controls to this slice. A settings save failure preserves the previous values.

Home last-focus card: when an eligible previous coaching response is available in
the current session, show its actual cue with the exercise/date and validated replay
association if one exists. Otherwise say Last review and link the report; do not call
it a corrective focus or automatically generate coaching. Refresh may lose the cue
cache; the neutral fallback remains useful.

Viewed marker: proposed local metadata means the owned report finished loading while
its Results view was visible. It does not mean the entire video was watched, the user
agreed with feedback, or technique was approved. Label it Viewed rather than Reviewed.
Record only after successful metadata persistence; reopening does not earn progress.

Milestone: proposed copy is “3 analysed sets saved” once the current browser history
contains three unique eligible analyses. Recompute from eligible saved records after
removal; clearing history loses this local state. It is not an all-time award, a
weekly goal, or evidence of improved strength. Use a small acknowledgement, no modal
reward screen, currency, penalty or paid provider call.

Coaching card sourcing: the public `limitations` strings may contain source URLs.
Only render validated URLs actually supplied by the existing response; keep them in
the sources disclosure. Segment-prefix validation provides replay association only.
Never create citation/claim identifiers or evidence links from the narrative summary.

Shared interaction rules: errors have clear recovery and are announced using
`role=alert`/appropriate live regions; field errors reference their field. Return
focus to the triggering control after a cancelled modal. Sticky actions must not
obscure consent, media controls, keyboard focus or validation messages; reserve safe
area/content padding. At200% text zoom, preserve reading order and action access.
Recording orientation changes must pass a device test; if valid orientation cannot
be maintained, finalize the clip as interrupted rather than stretching or guessing.

Proposed metadata boundary: keep `mxr.logs.v1` records and recognition proof intact.
Use a separate versioned `mxr.ux.v1` namespace for optional goal settings and per-analysis
Viewed timestamps, with an explicit migration/validation fixture before adding fields.
Absent goal = disabled with null target; absent Viewed = unknown, never false evidence
that the report was not seen. Preserve unknown keys during a supported migration;
reject unsupported versions without erasing existing history. Store no media, base64,
expiring private image URL or copied pose array there. A focus cue may remain in memory
for the current owned session; durable caching requires a separate privacy decision.
One eligible saved analysis counts as one analysed set. Do not call it a multi-set
training session or infer workouts/routines that the current history does not model.
Goal progress and milestones count eligible analyses only. A separately labelled
saved-log total may include legacy records, but manual edits and legacy entries do
not retrospectively earn goal/milestone credit. Persist settings before showing a
goal as enabled; a storage error leaves the previous goal state intact.
