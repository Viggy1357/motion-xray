# Motion X-Ray UI draft — review guide

This is the **analysis-first, lightly gamified** direction requested on 23 October
2026. It is a separate design prototype, not a replacement for the working app.

- Preview: http://localhost:3000/ui-draft/index.html
- Working app: http://localhost:3000/
- Blueprint: [HM-UX01-experience-blueprint.md](HM-UX01-experience-blueprint.md)
- Draft source: `apps/web/public/ui-draft/`.

## Review sequence

1. Home: inspect the companion, rotate it, switch the exercise target and consider
   whether the analysis action is more prominent than progression.
2. Analyse: pick one of the four release exercises and read the filming guidance.
   Any chosen video is a local preview only. Example results do not analyse that video.
3. Results: inspect the illustrative replay, rep navigation, observation, visibility
   and separate provisional comparison details. All numbers are example data.
4. Save the example once, then revisit/save it again: it must not award progress twice.
5. Progress: inspect regional illustrative progress and saved example history.
6. Review the limited-visibility, coaching-unavailable, expired-video and failed
   analysis examples. Each must communicate what remains available and the next step.

## Decisions being reviewed

- Warm light surfaces, ink text and restrained terracotta highlights.
- Generic 3D companion on Home, separate from analysis replay.
- Regional progress as a secondary acknowledgement of analysed activity.
- No Power/form-confidence number, economy, penalties or trading in this MVP.
- Proposed recognition rules and milestones need owner review before live integration.

## Technical boundaries

The prototype performs no upload, analysis, provider request or production API call.
Its browser storage key is isolated from the existing app. It uses local vendored
Three.js 0.170.0; licence and provenance are retained beside the renderer module.
The original procedural character is illustrative, not a body reconstruction.

Run the existing web service with `./scripts/dev.sh web` (Docker). Static draft assets
are served by that service; no additional host runtime or dependency installation.
Browser storage and WebGL failures must remain recoverable without inventing results.

The older HM00 and HM09 briefs are retained as historical design context. The latest
owner steering is analysis first with a lightly gamified customer experience; this
draft and blueprint are the current proposal, pending visual review.
