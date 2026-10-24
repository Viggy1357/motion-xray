# Demo script — 2 minutes 40 seconds

Target: UNDER 3 min per official rules. Real-time pipeline waits are
**visibly marked** as edited; do not present them as instant.

## Time / action / voiceover table

| Time | Action on screen | Voiceover |
|---:|---|---|
| 0:00–0:10 | Title card: "Motion X Ray — short-clip review with grounded coaching" | "Motion X Ray reviews a single workout set you just filmed. Record or upload a set, then review what the camera could measure." |
| 0:10–0:25 | Home screen, static athlete illustration | "Choose your exercise and record a set or upload an existing clip." |
| 0:25–0:40 | Click Analyse, pick a short owned clip (≤60s) | "We pick a short clip — under sixty seconds, under a hundred megabytes." |
| 0:40–0:55 | Upload progress, then status polling | "The worker extracts pose on CPU, segments completed reps, and measures joint angles." |
| 0:55–1:25 | **[real-time wait — edited]** card over a 5–8s clip of the processing screen | "This is a real pipeline wait — edited for length. Pose extraction, rep segmentation, and reference comparison run here." |
| 1:25–1:45 | Results screen: 2D pose overlay aligned to source time, completed-cycle chips with thumbnails | "Results show a source-time-aligned 2D overlay and thumbnails for each completed cycle." |
| 1:45–2:00 | Click a cycle chip → replay seeks to measured segment start | "Clicking a chip seeks the replay to the measured segment start." |
| 2:00–2:15 | Click "Generate coaching" → real Nebius Nemotron call | "Coaching is an explicit user action. The model only picks candidate IDs; local code validates and renders the text." |
| 2:15–2:30 | Coaching note appears; click the coaching replay link; separately show cached coaching only if verified | "The coaching links back to the measured segment. Reopening an unchanged report can reuse cached coaching." |
| 2:30–2:40 | Closing card: "Similarity to a reference, not a technique grade. Containerised prototype." | "Similarity to a reference, not a technique grade. Containerised prototype." |

## Capture checklist

- [ ] Use an owned clip; redact any faces or private surroundings if needed.
- [ ] Show the real upload + status polling UI; do not fake the spinner.
- [ ] Insert the "[real-time wait — edited]" card over the processing screen.
- [ ] Record one real `Generate coaching` click; do not pre-render the note.
- [ ] Record the cached-replay click immediately after; verify cache via sanitized server metadata; absence of a spinner is not proof.
- [ ] Do not show `NEBIUS_API_KEY`, `SESSION_SECRET`, or any `.env` value.
- [ ] Do not show raw pose arrays, internal IDs, or other owners' data.
- [ ] Keep total runtime UNDER 3:00; target 2:40.
- [ ] Export at 1080p, H.264, audio normalised.

## Genuine runtime proof (what to actually capture)

- One real owned-lat `Generate coaching` interaction — distinct from any
  cached result shown earlier.
- One cached-result replay click — verified using sanitized cache metadata if shown. Replay alone does not prove
  caching, and the app has no assumed token counter.
- Safe screen redaction: blur any browser tab titles, bookmarks bar, and
  OS dock that could leak personal context.

## What NOT to do

- Do not claim real-time when a wait was edited.
- Do not show private frames, raw pose, or other owners' data.
- Do not paste API keys, session secrets, or model checkpoints on screen.
- Do not present the 3D diagnostic as an app feature (it is a separate
  diagnostic, not in the main app).
- Do not claim clinical accuracy, technique grading, or injury-risk output.

Do not record or publish private source footage until the owner selects and authorizes
the exact clip for public use. This script is prepared; no media capture/upload or
new paid runtime coaching call is authorized by preparation alone.
