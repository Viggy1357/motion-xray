# HM-UX03 — Art direction: athlete companion & home scene

## Concept
A calm, sport-focused training companion. Near-white cool-blue surfaces,
dark ink text, and a single cobalt accent (#3158e8). The athlete artwork is
the only illustrative element; everything else is typography, whitespace and
restrained 12/18px radii. No borders on every surface — separation comes from
soft shadows and tinted backgrounds.

## Athlete artwork
- Single original generated transparent PNG (`/companion/athlete.png`), rendered as a
  static `<img>`. It never rotates, animates, or responds to input.
- Two presentations via `AthleteCompanion`:
  - `variant="poster"` — borderless, frameless artwork for the home hero
    scene. Sizing is owned by CSS (`.athimg`), not inline styles, so the hero
    can place it bottom-right without overlapping the headline (copy is
    bounded to approximately270px on phones; the subheading has a narrower measure).
  - `variant="map"` — one quiet secondary disclosure labelled “Explore body map”,
    below the actual weekly summary/last review. No duplicate poster panel.
    The separate interactive iframe mounts only when opened; it has a static
    fallback for browsers without WebGL.
- No front/back image toggle controls; the 3D view handles orientation.
- The “generic exercise targets, not measured activation” disclaimer appears
  exactly once per panel.

## Home hero (375px phone first)
- Scene ~430px tall, soft cool-blue gradient,18px radius.
- Headline upper-left at28px on small phones, two deliberate lines; athlete image
  in a300×430px box anchored bottom-right. The subheading stays clear of the figure.
- Full-width “Analyse a set” CTA directly under the scene — visible within a
  375×812 viewport.
- Home has one compact weekly summary and a Progress action, avoiding redundant stats.
- Desktop: restrained 230px rail, content max 1020px, hero becomes a
  two-column text-left / art-right composition.

## Progress
- Real data only: seven-day strip computed from actual saved timestamps
  (count + weekday + date labels), analysed-set bars relative to the actual
  per-exercise maximum, and a single “Recent sessions” panel with separated
  rows.
- “Reopen report” is the primary row action; destructive actions (revoke
  server analysis, remove from history) live inside a “Manage” disclosure,
  with `window.confirm` guarding history removal.
- Null vs 0 reps, manual vs detected, load and notes rendering are preserved
  unchanged. No invented streaks, goals, scores, or coaching copy.

## System-wide decisions
- Native system font stack; 15px dark-ink body, 12–13px metadata.
- Elevated centre camera button in the mobile bottom nav without a coloured
  glow (neutral shadow only).
- Native file input is visually hidden but keyboard-focusable; the parent
  label shows focus via `:focus-within` and keeps a ≥44px hit area.
- Wide tables scroll horizontally inside their container (`overflow-x:auto`
  on cards/details) with `white-space:nowrap` cells — no mid-word breaking.
- `prefers-reduced-motion` disables all transitions/animations.

## Limits
- Artwork is illustrative only; no activation, strength, growth or health
  claims are made anywhere.
- The 3D body map is a generic exercise-target illustration, not a
  measurement of the user's body.
