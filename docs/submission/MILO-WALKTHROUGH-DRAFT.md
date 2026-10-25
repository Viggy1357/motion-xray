# MILO walkthrough draft — 100s (0:30–2:10)

Narration is written, not generated. 176 spoken words across 6 blocks, leaving time for clicks and pauses. Capture requirements distinguish real actions from edited waits. No actual footage captured or published by this task.

## 0:30–0:42 — Intro (relative 0–12s, ~22 words)
**On-screen:** "Motion X Ray — short-clip review with grounded coaching." Home screen, athlete illustration, Pip resting.
**Voiceover:** "When you train alone, a workout video is easy to record and hard to act on. Motion X Ray reviews one set you just filmed."
**Capture:** Real home screen render; no fake spinner.

## 0:42–1:00 — Upload (relative 12–30s, ~36 words)
**On-screen:** "Solo. One set. One cue."
**Action:** Click Analyse, pick owned clip ≤60s, ≤100MiB.
**Voiceover:** "This is for someone training alone who wants a single set reviewed — no coach, no account, no clinical claim. We pick a short clip, under sixty seconds, under a hundred megabytes."
**Capture:** Real upload UI; show real progress and status polling.

## 1:00–1:15 — Processing (relative 30–45s, ~30 words)
**On-screen card:** "[real-time wait — edited]"
**Voiceover:** "The worker extracts pose on CPU, segments completed reps, and measures joint angles. This is a real pipeline wait, edited for length. Pip shows three local encouragement bubbles while the worker runs."
**Capture:** Real processing screen ~5s; show Pip home + processing states only; no chat, no progression.

## 1:15–1:40 — Results + replay (relative 45–70s, ~46 words)
**On-screen:** 2D pose overlay aligned to source time; completed-cycle chips with thumbnails.
**Voiceover:** "Results show a source-time-aligned 2D overlay and a thumbnail for each completed cycle. Clicking a chip seeks the replay to the measured segment start. Some repetitions may be unmeasurable; missing measurements stay unavailable."
**Capture:** Real results screen; click a cycle chip; replay seeks to measured start.

## 1:40–2:00 — Coaching (relative 70–90s, ~40 words)
**Action:** Click "Generate coaching" → real Nebius Token Factory call (`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`).
**Voiceover:** "Coaching is an explicit user action. NVIDIA Nemotron, hosted on Nebius Token Factory, picks a candidate ID from a fixed list. Local code validates the ID and renders the text — the model never invents measurements. The note links back to the measured segment."
**Capture:** One real owned-clip `Generate coaching` click; one cached-replay click verified via sanitized server metadata; absence of spinner is not proof.

## 2:00–2:10 — Limitations (relative 90–100s, ~20 words)
**On-screen:** "Similarity to a reference, not a technique grade. Containerised prototype."
**Voiceover:** "Similarity to a reference, not a technique grade. Containerised prototype."
**Capture:** Static card.

## Limitations (walkthrough only, not teaser)
- Real pipeline wait is edited for length; on-screen card marks it.
- Reference resemblance is experimental/provisional, not a technique grade or safety claim.
- Missing data may be unavailable; segmented completed cycles are not guaranteed for all reps.
- Coaching is grounded text from a fixed candidate list; deterministic measurements are not LLM output.
- 3D diagnostic is separate, not a main-app feature.

## Capture checklist
- [ ] Owned clip only; redact faces/private surroundings.
- [ ] Real upload + status polling UI; no fake spinner.
- [ ] "[real-time wait — edited]" card over processing screen.
- [ ] Pip home + processing states ~5s total; no chat, no progression.
- [ ] One real `Generate coaching` click; do not pre-render the note.
- [ ] One cached-replay click immediately after; verify via sanitized metadata.
- [ ] No `NEBIUS_API_KEY`, `SESSION_SECRET`, or `.env` values on screen.
- [ ] No raw pose arrays, internal IDs, or other owners' data.
- [ ] Blur browser tab titles, bookmarks, OS dock.
- [ ] Export 1080p H.264, audio normalised; total runtime under 3:00.

## 2:10–2:30 — Future direction (20s)
**On-screen:** Persistent "Planned" badge. Milo leads across three cards: "More exercises + stronger calibration" → "Progress and routines" → "Optional camera integration". Close on Motion X Ray.
**Voiceover:** "Next, we want to expand exercise coverage, strengthen calibration, and connect each review to progress and routines. Further ahead, an optional compact camera could make recording simpler. These are planned capabilities."
**Capture:** Clearly labelled roadmap animation, separate from the actual app walkthrough. No hardware demonstration or shipped-feature claim.

## Timing and next capture step
30s teaser + 100s walkthrough + 20s future = 150s (2:30). Narration is a draft; fit with pauses at recording. Select the exact owned clip for public use before capturing the walkthrough. No private workout footage, narration audio or new paid runtime call has been produced for this task.
