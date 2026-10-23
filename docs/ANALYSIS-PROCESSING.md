# ANALYSIS PROCESSING — canonical resize & measurement policy

Latest checkpoint: `docs/audit/HM-FAST02-delivery.md` (HM-FAST02, all-four resize).
This document is the canonical statement of the current upload/decode/resize and
measurement policy. Historical audit sections elsewhere are retained for traceability
and are not rewritten; the active policy follows D021 in DECISIONS.md.

## Scope

- Setting `POSE_ANALYSIS_RESIZE=1` in the local environment enables bounded-resize
  decoding for **all four release exercises**: standing dumbbell curl, cable lat
  pulldown, bodyweight squat and incline dumbbell press.
- Template default is `1`; code fallback is `0` when the variable is unset, so an
  explicit setting always wins and behavior is deterministic per environment.
- Earlier curl-only resize (HM-FAST01) is superseded by this all-four policy.

## Decode and resize rules

- Bounds: at most 720 px on the short side and 1280 px on the long side.
- Rotation-aware: source rotation metadata is applied before measuring sides.
- Aspect ratio is preserved; there is **no upscaling** — smaller sources pass through
  at native resolution.
- Frame cadence: 30 Hz sampling using original source presentation timestamps (PTS);
  **no frame interpolation** is performed.
- The pipeline decodes to RGB frames in memory; it does **not** produce a new encoded
  video file.
- Originals, uploaded bytes and replay behavior are unchanged: the stored upload,
  its hash and the existing full-resolution playback proxy are preserved.

## Hashing and regeneration

- The resize scope/flag/bounds are included in the recipe hash. New uploads and new
  jobs therefore run under the new recipe; **old reports are not regenerated** and
  remain valid records of the recipe that produced them.

## Operational rollout

- Apply config changes with an empty queue, then recreate the API and worker
  containers together (synchronized restart) so both sides agree on the recipe.
- Standalone/direct-provider diagnostics default to resize **off** (`False`) unless
  explicitly set `True`, so diagnostic runs remain distinguishable from the app
  upload policy.

## Known limitations and accepted results

- Resized squat currently yields **0 complete cycles** versus 1 on the original
  resolution for the supplied squat clip. The owner accepts this: the squat
  cycle is partial/unavailable under resize rather than a regression to fix silently.
- No thresholds, scoring logic or reference trajectories were changed by HM-FAST02.
- The only paired full-path comparison is the curl baseline: 96.071 s original vs
  90.740 / 92.882 s resized — a small **3–6%** improvement. There is no universal
  latency promise and no 2.8x claim; the earlier isolated pose-only speedup figure
  does not apply to the full path.
- A fresh incline-press guest upload passed: 122.406s, 4 usable candidates,
  provisional resemblance59.9962 versus earlier original53.4859. No paired speedup
  or improved-accuracy claim. The lat clip is already below cap; no fresh run claimed.
- Full offline checks passed: 1,034 tests, Ruff and mypy71 sources. See the
  HM-FAST02 audit for runtime verification and limits.

## Explicit non-changes

- No 15 fps mode was added.
- No cross-workout routine feature was added.
- External camera hardware remains deferred.

## Related documents

- `docs/audit/HM-FAST02-delivery.md` — delivery audit for this change.
- `docs/audit/HM-FAST01-delivery.md` — earlier curl-only resize (superseded scope).
- `docs/audit/HM057-HM06-delivery.md` — four exercise movement profiles, unreviewed
  reference resemblance estimates and grounded coaching checkpoint.
- `docs/ARCHITECTURE.md` — pipeline overview; its processing section links here.
