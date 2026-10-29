# Composition Brief — Motion X Ray launch teaser

## Canvas
- 1920×1080, 30fps, 25s, off-white #f8fafd base.

## Scene 1 — hero (0–5.5s)
- Left rail (white, 280px): brand "Motion X Ray", nav Home(active)/Analyse/History/Settings.
- Center card: headline "Make your next set count." (92px navy), subline "Movement insights for your next set." (34px muted), CTA pill "Analyse a set" (cobalt).
- Right: athlete illustration with sleeping lilac Pip beside her (assets/athlete.png + assets/pip-sleeping.webp).
- Persistent label top-left: "UI recreation · MVP" (24px muted).
- Entry: card scale 0.96→1, opacity 0→1, 0.5s ease power4.out. Headline blur 8→0, 0.18s.
- Hold 4s. Exit: card opacity 1→0, 0.6s.

## Scene 2 — upload (5.5–12.5s)
- Same left rail, Analyse active.
- Exercise chooser: 4 cards (lat pulldown, dumbbell curl, bodyweight squat, incline dumbbell press) — first selected (cobalt border).
- Upload panel: dashed border, "Drop a set recording" label, file-name chip.
- Progress stage: static "Measuring movement" with Pip beside it (assets/pip.webp). "Processing sequence condensed" label appears at stage transition (~10s).
- Entry: chooser cards stagger 0.08s, opacity+translateY(16→0). Upload panel scale 0.97→1.
- Hold. Exit: panel opacity 1→0, 0.5s.

## Scene 3 — review (12.5–20s)
- Same left rail, Analyse active.
- Left: abstract replay placeholder (rounded rect, navy 8% fill, label "Replay interface" centered, no skeleton, no footage).
- Right: report card with feature labels only — Movement report, Source-time replay, Measured segments, Reference comparison, Provisional estimate, Generate coaching.
- Coaching selection: "One grounded cue for your next set." with label "Evidence-linked coaching".
- Small honest line: "Reference resemblance is provisional. Missing measurements stay unavailable."
- Entry: replay placeholder scale 0.97→1, report card translateX(24→0). Feature labels stagger 0.06s.
- Hold. Exit: card opacity 1→0, 0.5s.

## Scene 4 — outro (20–25s)
- Centered: "Solo. One set. One cue." (88px navy).
- Below: Motion X Ray wordmark + small athlete/Pip (assets/athlete.png + assets/pip.webp, ~180px tall).
- Badge: "Personal training MVP" (rounded, navy border).
- Runtime credit: "Powered by Nebius Token Factory · NVIDIA Nemotron" (24px muted).
- CTA text: "Analyse a set" (34px cobalt, not a link).
- Music credit small readable: "Music: Happy Beats Business Moves Vol12 — Sascha Ende (CC BY 4.0)".
- Disclosure small: "Animated UI recreation of the current MVP; no real workout footage or measured result is depicted."
- Entry: headline blur 8→0 + opacity, 0.4s. Athlete/Pip scale 0.9→1, 0.5s.

## Type & color tokens (CSS vars on :root)
- --bg #f8fafd, --navy #142039, --cobalt #3158e8, --border #e2e8f3, --muted #5b657d.
- Font: Roboto (bundled).

## Audio cues
- Music bed 0–25, vol 0.32, fade-in 0.7, fade-out 1.2.
- drop.ogg @5.5 vol 0.22 (upload panel appears).
- select.ogg @12.5 vol 0.20 (review reveal).
- drop.ogg @20 vol 0.22 (outro badge lands).
