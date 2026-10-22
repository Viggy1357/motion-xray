# Steps4–7 checkpoint and benchmark freeze

22 October2026. FR02/03/04/07/08/10/12. Owner redirects further work to a functional
Nebius hackathon application and feature discussion; see D015. No new benchmark
assessment or product feature generation follows this checkpoint.

## Accepted implementation

- T08.1c.2: signed-owner proxy/pose/timestamp streaming. Committed manifest identity,
  input/version/model provenance and payload hashes checked; proxy supports single
  byte ranges. Source/report retention, deletion, invalid ranges, malformed/symlinked
  paths and resource closure covered. Original media is never served.
- T08.1d bounded slice: manual container cleanup of expired known completed raw/pose/
  proxy/report artifacts. Separate report TTL preserved; no-follow file operations;
  durable private receipt permits retry after partial attempt deletion. Cancelled,
  failed-without-committed-result and ambiguous attempts remain conservatively deferred;
  this is not a complete autonomous retention daemon.
- T06.2: pure source/frame-bound manual endpoint geometry and a local review page for
  twelve rough visual point proposals (eight user/four QMotion). These are Codex visual
  proposals, not independent ground truth or automated bar detection. Upper-chest target
  is approximate. Contact/depth remains unavailable. Coordinates/images stay local.
- T07.1 bounded slice: deterministic event-level source-band differences and conditional
  component scoring with explicit view/metadata/review/tolerance gates. Owner-prototype
  similarity is distinct from a valid technique claim. No aggregate or DTW integration.
- Real diagnostic packet: eight user reps, three separate sources,120 comparisons;
  current tracked policy has no approved tolerances and yields zero numeric scores.
  Current public reports still contain pose-only output, not these offline components.

## Verification

- Full offline Python suite767 passed; Ruff clean; mypy61 source files. Existing AnyIO
  deprecation warning only. Frontend typecheck/build passed against regenerated API types.
- API OpenAPI/TS regenerated together; artifact0.2.0 schema retained and prior operation
  ID preserved. Binary/JSON media and206/416 response behaviour documented.
- Repeated real comparison JSON/HTML and endpoint HTML reproduce identical SHA256
  hashes from the same frozen inputs. Browser comparison table inspected locally.
- Real10.01s lat excerpt: signed upload -> separate local worker ->300 pose samples ->
  private full/range proxy, pose and timestamp access. Proxy hash matches the map;
  foreign owner denied. Raw expiry revokes playback while retaining report, then report
  expiry removes committed artifacts. ASGI TestClient plus separate Docker worker, not
  a deployed TCP/browser product-flow claim. Temporary proof worker stopped/removed.
- Independent Nebius QC exposed a real partial-rmtree retry gap; persistent receipts
  and regression tests now cover it, invalid receipts and write failure. Two generated
  test setups were corrected to use the actual Store/fixture and I/O failure boundary.
- Earlier rejection/repair details and the final source-draft statuses are preserved
  in `../development-usage-T047-2026-10-22.json`. No skipped gates or relaxed masks.

## Review artifacts

- Local comparison: http://localhost:8865/t047.html
- Local endpoint proposals: http://localhost:8865/endpoint-review.html
- Original rep seek page: http://localhost:8865/t052c.html
- Numeric evidence: `T047-component-comparison.json`, `T047-local-flow.json`.
- The video-derived measurement checkpoint remains `T05.2c-rep-review.md`; this run
  does not approve its camera compatibility or convert observed ranges into norms.

## Resume

Read `../HACKATHON-MVP-DIRECTION.md`. Discuss the app feature slice, then mock up the
screen flow before implementation. Proposed core: upload -> analysis -> report with
quality/estimate labels -> runtime Nemotron cue -> workout log. Exercise expansion is
three additional uploaded sets (four videos total). Hardware and deeper calibration
are later work. Hosting, public repo/licence readiness and submission still need work.
