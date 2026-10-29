# HM-UX06 delivery and acceptance ledger

24 October 2026, Malaysia time. Baseline 5ebe828. Candidate; not full device acceptance.
This document supersedes the outstanding implementation notes in HM-UX05, without
rewriting historical evidence or changing HM-UX04's original gates.

## Delivered changes

- Recorder adapter serializes asynchronous Blob conversions and delivers stop only
  after the final dataavailable conversion. The controller accepts the final chunk
  while finishing, records actual stop-request time, and finalizes once. Blob-conversion failures tear down encoding and surface an error instead of hanging or finalizing a corrupt partial clip.
- Three-second countdown uses a monotonic deadline with separate display ticks.
  Cancel releases the stream. Dialog focus restores to its original opening control.
  Retake/discard confirmations, generation-safe late permission cleanup, track-end,
  visibility and pagehide teardown remain explicit.
- Capture schedules a stop at 59 seconds, leaving one second below the strict
  60-second upload limit. This is safety headroom, not permission to invent a
  60-second duration or a guarantee against a stalled browser event loop. Server
  validation remains authoritative. Oversized encoded clips are rejected intact.
- Thumbnails use memory-only per-analysis/per-cue ownership, generation invalidation,
  expiration and cross-instance notifications. Parallel same-key extractions preserve
  the original held URL and revoke the redundant URL. Expiry clears displayed pixels;
  revocation does not remove the local history entry or assert physical server erasure.
- One shared local-calendar week implementation: rolling seven dates ends today;
  calendar option is Monday through Sunday. Both exclude future timestamps. DST
  regressions use local-date arithmetic.
- Removed unsolicited dark styling from the Progress modules; restored the existing
  white/cobalt composition and made small primary controls at least 44px high.
- Added first-use introduction (Continue opens Analyse; Skip stays on Home; neither
  grants camera/upload consent), small generic-athlete Progress companion, actual
  session coaching cache and Home Last focus with neutral Last review fallback.
- Settings returns to its originating route and preserves a selected local clip.
  Unreadable/unsupported UX metadata blocks writes instead of overwriting that record.
- Missing browser camera APIs hide Record while keeping Choose video available.
- Fresh real Results testing exposed an intrinsic grid-width bug. The grid now uses
  zero-minimum tracks; the segment strip scrolls inside the available page width.

No scoring thresholds, exercise policy, schemas, perception model, fabricated poses,
measured muscle-growth claims, economy or automatic paid coaching were introduced.

## Checks executed

Docker-only checks, no host runtime installation:
- Capture controller and asynchronous recorder-adapter checks, including genuinely
  deferred final-chunk delivery, repeated stop, teardown and oversize final chunks.
- 29 metadata/week/cache tests (the original 26 plus three URL ownership regressions).
- 13 session-coaching cache tests; 12 pose-overlay/mapped-time checks.
- Web typecheck and Next production build/lint.
- 87 selected API integration tests: upload, analysis, grounded coaching, movement
  reports and artifact streaming. Provider responses are fixtures, not paid calls.
  One existing AnyIO deprecation warning.
- The earlier 1,045 Python tests belong to HM-SQ01; they were NOT all rerun for UX06.

All listed final checks passed. The final controller regressions exercise deferred delivery rather than only advancing time after a synchronous stop.

Actual logs remain local under artifacts/development/ux6-final-web-checks.log.
Test success does not establish physical-device, clinical or accuracy validation.

## Browser execution

The in-app browser exercised the actual app in a same-origin local iframe at
360x820, 375x820 and 1365x820 CSS pixels. Its canvas MediaStream is explicitly
synthetic; the browser's actual MediaRecorder is used. Denial and API absence were
injected only in the temporary harness. These are not iOS/Android hardware tests.
The harness is removed from public assets before committing.

A retained public reference qmotion.mp4 (38.081s, 1,168,788 bytes) went through real
browser selection, explicit consent, upload, queued processing and a fresh measured
report. Result: six completed candidates, three partial fragments and 96% signal
visibility. These are observed outputs, NOT independently verified counting accuracy.
No coaching generation was clicked and the report was not saved into workout history.
Its local analysis ID is fb6cba66-ef96-4321-af21-2d3050563e47.

Tapping segment 4 sought to 20.633333s and played. Playback later reached 27.127012s
with segment 5 highlighted: normal continuous playback, not an invented loop.
After the recorder repair, the deadline take reached Review with decoded duration58.9977s, readyState4 and no media error. Confirm discard & retake removed it. Escape from a dialog control closed the idle modal and restored focus to Record a set.

The repaired 360px Results page measured document width 360px with a 328px strip
containing 733px of scrollable chips. Home/Analyse/Progress/Settings were also
inspected; 375px and 1365px page widths matched their viewports.

A generated five-second no-person test pattern went through the real pipeline.
It returned CHILD_FAILED, with an honest failure message and no invented pose/count
or coaching. This does NOT prove the usable-pose/zero-completed-cycle partial-report
branch; that remains a separate acceptance requirement.

The user explicitly approved a local physical-camera test and confirmed permission.
The in-app browser nevertheless stayed at Waiting for camera permission; no real
stream or physical clip was obtained. The request was cancelled; no real camera clip was recorded or uploaded. A native Safari
inspection was attempted but its tool observation stalled; no Safari page, settings
or account was changed. No permission bypass was attempted. Physical recording,
hardware facing changes and mobile browser interruption still need device execution.

Existing server reports were unavailable in the freshly rebuilt local Docker stack.
The prior local browser history was preserved. No volume/history deletion was run.
The rebuild followed an initially empty current Docker context; it was not a migration
or recovery of previous server analyses.

## Original 26 acceptance gates

Numbering is copied from HM-UX04 section 10, not the worker's separate state inventory.
**Browser** means this browser/fixture only. **Partial** means evidence exists but the
full stated gate is not closed. A source assertion is not a device pass.

| Gate | Requirement | Current result and evidence |
|---|---|---|
| 1 | Missing camera hides Record, Choose remains | Browser API-absence fixture passes. No-camera physical hardware detection remains untested; API availability cannot prove hardware presence before permission. |
| 2 | Denial education and file fallback, no upload | Browser NotAllowedError fixture passes; education and Choose remain. Physical OS denial still needs device coverage. |
| 3 | Cancel countdown releases resources, sends nothing | Browser synthetic countdown cancellation returns idle with empty video src and null srcObject. Controller/adapter teardown checks pass. No upload consent or upload action occurred. |
| 4 | Duration/byte limit stops into Review | OPEN. Browser synthetic duration path now reaches Review automatically; decoded duration58.9977s, readyState4, no media error. A chunk reaching/exceeding 100MiB is safely rejected, rather than Review. This does not meet the original byte-limit Review wording. |
| 5 | Retake confirms discard without persistence | Browser confirmation and Keep clip/Use paths exercised. Final deadline clip confirmed discarded via Confirm discard & retake, returning idle. No synthetic clip saved as a workout. |
| 6 | Leaving mid-recording stops all resources | Partial: source + controller teardown/race checks. OS background/unload and device camera indicator not fully exercised. |
| 7 | Create retry reuses video ID and request_key | Partial: existing request-key API integration tests and source retry path. Real browser creation-failure fault injection not executed. |
| 8 | Poll retry never resubmits upload | Partial: source isolation and selected API tests. Real browser dropped-connection injection not executed. |
| 9 | No eligible coaching yields neutral measured summary | Fresh actual Results shows measured summary and explicit Generate coaching. No-person fixture fails honestly; successful empty-coaching response not exercised in live browser. |
| 10 | Actual eligible observation/cue and validated replay | Partial: 13 grounded session-cache regressions and API fixture tests. No new paid coaching generation; live response presentation/replay still requires an authorized runtime exercise. |
| 11 | Segment seeks original mapped start and follows playback | Browser passes on fresh public report: segment 4 at20.633333s; later segment5 at27.127012s while playing. Existing timestamp/overlay checks pass. |
| 12 | Empty Progress without fake milestones | Fresh separate localhost-IP origin used to avoid clearing existing history; hydrated Progress shows Nothing logged yet and Begin analysis, no milestone or fabricated history. No retrospective rewards granted. |
| 13 | Missing thumbnail shows neutral fallback | Browser preserved old local records with icon fallback; source and cache checks confirm no generated/stock exercise frame substitution. |
| 14 | Storage failure does not increment or replace history | Partial: atomic persistence failure regression passes; full browser quota fault injection not executed. Corrupt/unsupported metadata is write-blocked in the integration. |
| 15 | 375px targets/type/wrapping on every screen | Partial: Home/Analyse/Progress/Settings and fresh Results inspected at375/360; overflow fixed and primary controls44px. Not every expanded/error/modal/native-player target and type size independently audited. |
| 16 | 1365px layout, rail and64px header | Partial:1365px width/no overflow and rail observed. Existing desktop composition does not independently establish the exact64px header contract. |
| 17 | Reduced motion respected | Partial: CSS reduced-motion rules retained; actual OS preference toggle not exercised. |
| 18 | Expired media feedback/cache drop, analysis preserved | Browser expired-report message and retained local entry observed; cache invalidation regressions pass. No server deletion was implied by opening an expired report. |
| 19 | No target until opted in, no penalty | Browser Home/Settings show goal off and actual saved counts; no default target3. Defaults and goal-disable regressions pass. |
| 20 | More menu has purpose or is omitted | Source/browser pass: no empty Results More menu added; actual actions remain explicit. |
| 21 | No upload from preview/permission without consent | Browser synthetic Use selects local video, checkbox remains unchecked and Upload disabled. Separate public fixture uploaded only after explicit checkbox and button. |
| 22 | Completed/excluded overlap precedence, real playback | Partial: fresh completed-interval playback-follow verified. An actual overlapping completed/excluded and outside-all-intervals browser case not exercised. |
| 23 | Updating saved analysis preserves original date/recognition | Partial: proof/unique-eligibility helpers pass, source preserves update semantics. Corrected-count browser save/update not run; existing history untouched. |
| 24 | Usable video/pose with zero completed cycles stays honest | Partial: no-person upload fails honestly with CHILD_FAILED, no made-up output. Successful usable-pose/zero-cycle branch not proved by this failure. |
| 25 | Idle/quota-blocked views cause zero paid coaching calls | Source, API fixtures and actual navigation retain explicit-only generation. No Generate coaching click, paid product or Tavily call during UX06. Live quota UI remains unexercised. |
| 26 | Failed/revoked thumbnails dispose URLs, preserve logs | URL-ownership/revocation/TTL tests pass; browser fallback and preserved history observed. Actual user-server revocation not triggered solely for testing, since that is irreversible. |

## Remaining release gates and merge decision

Keep PR #1 draft; do not merge based on this report. The original byte-limit gate is
not satisfied; physical camera/mobile interruption, browser fault/quota cases and
remaining exact-layout/accessibility cases have not all passed. These are specific
unfinished acceptance cases, not claims that all 26 failed or that unit tests are useless.

Next bounded task HM-UX07: resolve the byte-limit product contract/encoder strategy;
run the outstanding cases on a real desktop and iOS/Android device; use offline
controlled fixtures for network/storage/quota UI faults; authorize any paid runtime
coaching test separately. Preserve existing null/partial measurements and history.

## Agent allocation and accounting

Substantive implementation and test drafts came from Nebius APIs (Kimi, MiniMax,
DeepSeek; NVIDIA attempts retained with their failures). Codex dispatched, checked
literal diffs, integrated, ran Docker/browser checks and wrote this evidence ledger.
Small coordinator corrections included import/type/literal-context fixes, Continue
navigation and metadata guard wiring, rejecting an invented recorder prop, replacing
an invented scheduled-duration fallback with the actual clock, and releasing the
stream on error. No measured Codex savings are claimed.

Worker output was not accepted on assertion alone: some drafts invented contexts,
claimed tests they did not output, changed expiry semantics or exhausted reasoning
without files. Those drafts/parts were rejected, their usage retained. The source
review's no-findings statement missed the later-discovered cache collision and
controller deferred-final-chunk bugs; it is retained as dated worker evidence,
not as a merge approval.

See ../delegation/HM-UX06-usage.json for request-level accounting and unknown-call
reservations. Source-only prompts; no credentials, private media, browser history,
screenshots or pose artifacts sent to coding workers. No paid product coaching,
Tavily, extra infrastructure purchase, protected backup activation or merge occurred.

Reported development usage: 496,622 tokens; USD4.072890 conservative known cost plus USD1.622052 reserved for three unknown-usage529 failures. Aggregate prior maximum plus this task: USD29.022438, below USD70 active ceiling. Backup untouched. Reported tokens are below500k but unknown failed-call usage prevents certifying the complete billed-token total; no more calls dispatched.


## Lower-overhead QC follow-up

Owner asked to reduce repeated computer use because of Codex allowance consumption.
Use existing container unit/API checks first; prepare a reusable Docker browser-test
harness as HM-UX07 work, then return compact failure summaries to Nebius. Reserve
interactive computer use for a small final visual/device-permission pass or a
specific unresolved browser defect. No new Playwright dependency or CI browser suite
was installed in UX06. Running tests does not itself establish measured credit savings;
Codex orchestration/context still consumes allowance. Do not conflate Nebius development
spend with Codex allowance or paid product coaching.


## 24 October follow-up: HM-UX07A

The reusable Docker browser suite is now implemented; the earlier lower-overhead
section described the plan at UX06 delivery time. See HM-UX07A-delivery.md and
../BROWSER-QC.md. Thirty Chromium fixture-browser cases cover selected onboarding,
settings, camera fallback/countdown/short-review/consent and layout behavior.
They do not mean the original26 gates or actual device tests all passed.
