# Hackathon product direction — discussion draft

22 October2026. The owner explicitly freezes further benchmark assessment and
prioritizes a functional Nebius global hackathon application. Feature choices below
are proposals for discussion, not an approved UI build or completed functionality.

## Confirmed direction

- Keep the current lat-pulldown reference methodology and descriptive baseline.
  Further accuracy work, added measurements and reference-derived3D are later work.
- The personal prototype may present clearly labelled estimates. A quality indicator
  should explain observation coverage/gaps, not claim a calibrated probability that
  the technique judgement is correct. No confidence formula is implemented by this doc.
- Reuse the workflow for the available exercise inputs. Current folder contains four
  total: lat pulldown, incline chest press, dumbbell curls and squat. Three remain to
  receive exercise-specific measurement/reference work; uploaded sets are not references.
- Brainstorm the product features before implementing the redesign. The external tiny
  camera is a future capture source feeding the same clip/analysis pipeline.

## Recommended first usable flow

Choose exercise -> upload/record a set -> processing status -> synchronized playback
and estimated3D pose -> estimated reference comparison + observation-quality badge ->
short Nemotron coaching cue -> save to workout history.

The public API currently publishes pose-only reports. Offline comparison pages are
diagnostics, not evidence that product score/coaching integration is already done.

## Feature options for discussion

| Candidate | Proposed hackathon scope | Later expansion |
| --- | --- | --- |
| Upload and video library | Private upload, processing, replay, delete; clear retention | Optional long-term video vault and cloud sync |
| Set report | Video/pose timeline, estimated components, quality badge, short cue | More validated metrics and accuracy studies |
| Rep counter and exercise log | Best-effort count with user correction; manual weight, reps, date, notes | Robust counting across views and progression analytics |
| Workout routine | Small editable exercise templates and mark sets complete | Adaptive programming, recovery/load recommendations |
| Character/muscle view | Rotatable illustrative avatar with exercise-targeted muscle groups | Personalisation; no inferred physique or measured activation claims |
| Progress dashboard | Recent sessions, sets/reps/volume and comparable exercise history | Long-term trends and adaptive plans |
| Tiny external camera | Explain roadmap and preserve capture-source interface | Pairing, placement, consent, transfer, battery and live-stream experiments |

Suggested screens: Dashboard, New set, Set results, Workout history. Put the analysis
flow first and use the avatar as a visual companion, rather than making it a second
unrelated product. Choose libraries only after agreeing on the interaction; prefer
the existing stack and one necessary library per missing capability.

## Submission facts checked22 October

- Deadline30 October2026,10:00a.m.PDT =31 October2026,01:00MYT.
- App must use an NVIDIA open-source model on Nebius Token Factory or AI Cloud.
  Development coding calls do not prove the product runtime integration.
- Working demo/test build, public open-source repository with setup instructions,
  public YouTube demo under3 minutes, description/track and tool feedback required.
- Best Apps and Agents is the proposed fit; hardware is future scope.
- Judge access, deployment costs, licence/publication and final submission need explicit
  implementation/review. Nothing in this draft publishes or purchases hosting.

Primary sources: [overview and judging criteria](https://nebiusglobalaihackathon.devpost.com/)
and [official rules](https://nebiusglobalaihackathon.devpost.com/rules).

## Next discussion

Agree on analysis-first vs character-first presentation; prioritise the small feature
set; then prepare a screen-flow mockup before implementation. Keep Nebius-led bounded
drafting and light Codex integration/QC. Submission integration, not further benchmark
assessment, becomes the next implementation priority once this product slice is agreed.
