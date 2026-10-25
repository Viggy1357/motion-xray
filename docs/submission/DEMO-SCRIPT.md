# Demo script — 2 minutes 40 seconds

Target: UNDER 3 min per official rules. Real-time pipeline waits are
**visibly marked** as edited; do not present them as instant.

## Opening (0:00–0:25)

**Title card:** "Motion X Ray — short-clip review with grounded coaching."

**Voiceover:** "When you train alone, a workout video can be easy to record and hard to act on. Motion X Ray reviews one set you just filmed, shows what the camera could measure, and gives one grounded cue for the next set."

**Screen:** Home screen with the athlete illustration and Pip resting beside her. Solo audience framing — one person, one set, one decision.

## Problem and audience (0:25–0:40)

**Voiceover:** "This is for someone training alone who wants to review a single set without a coach, an account, or a clinical claim."

**Screen:** Brief text overlay: "Solo. One set. One cue."

## Upload and processing (0:40–1:25)

**Action:** Click Analyse, pick a short owned clip (≤60s).

**Voiceover:** "We pick a short clip — under sixty seconds, under a hundred megabytes."

**Screen:** Upload progress, then status polling.

**Voiceover:** "The worker extracts pose on CPU, segments completed reps, and measures joint angles."

**Screen:** **[real-time wait — edited]** card over a 5-second clip of the processing screen showing Pip's three local encouragement bubbles (home + processing state, no LLM, no chat).

**Voiceover:** "This is a real pipeline wait — edited for length. Pip shows three local encouragement bubbles while the worker runs."

## Results and replay (1:25–2:00)

**Screen:** Results screen: 2D pose overlay aligned to source time, completed-cycle chips with thumbnails.

**Voiceover:** "Results show a source-time-aligned 2D overlay and thumbnails for each completed cycle."

**Action:** Click a cycle chip → replay seeks to measured segment start.

**Voiceover:** "Clicking a chip seeks the replay to the measured segment start."

## Coaching — Nemotron functional, not technical lecture (2:00–2:30)

**Action:** Click "Generate coaching" → real Nebius Nemotron call (model `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`).

**Voiceover:** "Coaching is an explicit user action. The model only picks a candidate ID from a fixed list. Local code validates the ID and renders the text — the model never invents numbers."

**Screen:** Coaching note appears; click the coaching replay link; separately show cached coaching only if verified.

**Voiceover:** "The coaching links back to the measured segment. Reopening an unchanged report can reuse cached coaching."

## Closing (2:30–2:40)

**Closing card:** "Similarity to a reference, not a technique grade. Containerised prototype."

**Voiceover:** "Similarity to a reference, not a technique grade. Containerised prototype."

## Capture checklist

- [ ] Use an owned clip; redact any faces or private surroundings if needed.
- [ ] Show the real upload + status polling UI; do not fake the spinner.
- [ ] Insert the "[real-time wait — edited]" card over the processing screen.
- [ ] Show Pip's home and processing states for ~5 seconds total; do not show chat or progression.
- [ ] Record one real `Generate coaching` click; do not pre-render the note.
- [ ] Record the cached-replay click immediately after; verify cache via sanitized server metadata; absence of a spinner is not proof.
- [ ] Do not show `NEBIUS_API_KEY`, `SESSION_SECRET`, or any `.env` value.
- [ ] Do not show raw pose arrays, internal IDs, or other owners' data.
- [ ] Keep total runtime UNDER 3:00; target 2:40.
- [ ] Export at 1080p, H.264, audio normalised.

## Genuine runtime proof (what to actually capture)

- One real owned-lat `Generate coaching` interaction — distinct from any cached result shown earlier.
- One cached-result replay click — verified using sanitized cache metadata if shown. Replay alone does not prove caching, and the app has no assumed token counter.
- Safe screen redaction: blur any browser tab titles, bookmarks bar, and OS dock that could leak personal context.

## What NOT to do

- Do not claim real-time when a wait was edited.
- Do not show private frames, raw pose, or other owners' data.
- Do not paste API keys, session secrets, or model checkpoints on screen.
- Do not present the 3D diagnostic as an app feature (it is a separate diagnostic, not in the main app).
- Do not claim clinical accuracy, technique grading, or injury-risk output.
- Do not show Pip chatting, levelling up, or walking.
- Do not present the Nemotron call as a technical lecture — show it as a functional user action.

Do not record or publish private source footage until the owner selects
and authorises the exact clip for public use. This script is prepared;
no media capture/upload or new paid runtime coaching call is authorised
by preparation alone.
