# BRAG-VIDEO01 — Plan

## Product & claim contract
- App: Motion X Ray (commit 4f7adb2). 25s local launch teaser, 1920x1080, 30fps.
- Audience: solo gym beginner reviewing one recorded set.
- Core loop: upload set → CPU pose measurement + cycle segmentation → source-time replay → grounded cue.
- Four exercises only: lat pulldown, dumbbell curl, bodyweight squat, incline dumbbell press.
- Forbidden claims: instant speed, clinical accuracy, safety/technique grade, 3D, sign-in, live hardware, muscle activation, progression, unsupported workout logs.
- Palette: off-white #f8fafd, navy #142039, cobalt #3158e8, border #e2e8f3, muted #5b657d.
- Persistent readable label: "UI recreation · MVP".
- No private footage, no numeric demo scores/reps/angles, no invented skeleton.
- Result cards only show real feature labels: Movement report, Source-time replay, Measured segments, Reference comparison, Provisional estimate, Generate coaching.
- Coaching copy: "One grounded cue for your next set." with label "Evidence-linked coaching".
- Honest disclosure: "Reference resemblance is provisional. Missing measurements stay unavailable."
- Closing: "Solo. One set. One cue." + Motion X Ray + athlete/Pip + "Powered by Nebius Token Factory · NVIDIA Nemotron" + badge "Personal training MVP" + CTA text "Analyse a set" (not a link).

## Scene breakdown (4 scenes, 25s total)
1. **hero** (0–5.5s) — Actual home UI card with athlete + sleeping lilac Pip, headline "Make your next set count.", subline "Movement insights for your next set.", CTA "Analyse a set". Left rail nav (Home active). Subtle scale-in on app surface only.
2. **upload** (5.5–12.5s) — Exercise chooser (4 exercises) + upload panel. Static progress stage "Measuring movement" with Pip beside it. "Processing sequence condensed" label on stage transition.
3. **review** (12.5–20s) — Report/replay interface. Abstract video placeholder explicitly labeled "Replay interface" (no fake skeleton, no footage). Source-linked coaching selection. Honest small disclosure line.
4. **outro** (20–25s) — "Solo. One set. One cue." + Motion X Ray + athlete/Pip small + runtime credit + "Personal training MVP" badge + CTA "Analyse a set". Music credit small readable.

## Motion language
- 4 distinct scene entrances, clean holds, short exits.
- Subtle scale on app surface allowed only at entry; no continuous drifts.
- No floating/pulsing UI, no decorative graphs, no generic gradients, no dark AI neon.
- Editorial type (Roboto), large text, ample whitespace.
- Safe margins: 192px L/R, ≥108px T/B for essential content.
- Type scale: titles 76–100px, body 32–38px, labels ≥24px.

## Audio
- Music: assets/music.mp3 (Happy Beats Business Moves Vol12, Sascha Ende, CC BY4.0). Volume 0.32, fade-in 0.7, fade-out 1.2, duration 25.
- SFX: assets/drop.ogg @5.5, assets/select.ogg @12.5, assets/drop.ogg @20, volume 0.18–0.25.
- No voice. No audio-reactive tooling.

## Hyperframes contract
- index.html root: paused main gsap timeline, data-duration 25.
- 4 subcompositions in compositions/{hero,upload,review,outro}.html.
- Each scene: template wrapper, #root inset:0, data-composition-id matching host and timeline key.
- Unique element IDs across scenes (prefixed).
- Hosts: class clip, data-start, data-duration, data-track-index, data-track-kind="graphics", width 1920, height 1080.
- Animate inner children, not clip display/visibility/autoAlpha.
- fromTo for seek safety. No timers/random/network.
- Relative assets root 'assets/...'. GSAP at assets/vendor/gsap.min.js.
- Palette + headline variables declared on root html.
- Image CSS: explicit width/height/object-fit/position.

## Assets (all exist)
- assets/athlete.png, assets/pip-sleeping.webp, assets/pip.webp
- assets/music.mp3, assets/drop.ogg, assets/select.ogg
- assets/vendor/gsap.min.js

## Disclosure
- "Animated UI recreation of the current MVP; no real workout footage or measured result is depicted." in share-copy and in-video small readable credit.

## Final integration
- Layout repaired against actual browser findings. Navigation uses Progress. Playback controls are illustrative, no results or private footage shown. Upload stage appears at8.2s, coaching CTA15.5s, generic cue16.3s. Music cue alignment optional, omitted in favour of reading time. No registry transition cache available offline; local GSAP only. Audio reactive extraction omitted; no new model/tool install.
