# HM-RELEASE02 — judge-local setup (25 October2026)

Baseline794a578; existing codex/hm-ux05-mockup-implementation branch.
Owner asks for a clean navigable GitHub repository and straightforward local run.
FR01/02/03/04/09/10/12 operational acceptance. One integrating writer, substantive
Nebius drafts, targeted repairs and review; no public release or deployment.

## Changes

- scripts/quickstart.sh: Docker/Compose/daemon prerequisites, canonical configuration
  preparation, image builds/start, bounded internal API/web checks and worker-running
  checks. Docker stays on host; only bootstrap Python runs in pinned container.
  Scripts work outside repo cwd and quote paths, including spaces. --prepare-only
  prepares environment/model without starting services. No Docker socket exposure.
- scripts/bootstrap_local.py: persistent generated session secret, existing nonempty
  configuration preservation, duplicate/symlink rejection, exact pinned official
  model URL/hash/size, verified cache reuse and failed-download cleanup. Existing
  corrupt models fail clearly rather than being overwritten. No model bytes committed.
- README now leads with actual branch/clone/start commands; docs/QUICKSTART.md and
  docs/INDEX.md separate current setup from historical audit records. Optional live
  coaching needs explicit server-side key/flag and API recreation. Core perception
  needs no provider key. First builds/downloads require internet and time.
- .env.example fixes stale adapter comment and supplies actual pinned Nano model ID;
  live coaching stays false. Existing developer.env was not changed.
- Standard MIT text retained; embedded third-party paragraph moved unchanged to
  THIRD_PARTY_NOTICES.md. GitHub detection still needs verification on eventual
  default/public release; no relicensing of external assets/models implied.
- Full regression exposed installed-package cue lookup missing source-tree ancestors.
  services/api/app/coaching.py now reads the bundled providers.llm resource when the
  source path is absent. Existing cue data, score/threshold rules, ownership, quotas
  and model behavior unchanged. Seven packaging regressions added; original happy
  path assertion retained. Malformed/missing sources remain fail-closed.

## Verification actually performed

- bash -n scripts/quickstart.sh and --help pass. Relative README/quickstart/index
  file links resolve. git diff --check passes.
-19 bootstrap cases pass, including generated/preserved secrets, duplicate/symlink
  handling, pinned manifest/cache integrity, failed-download cleanup.
- ./scripts/test.sh python: clean rebuilt image, exit0, Ruff clean, mypy71 sources,
  **1,071 tests passed in11.40s**, one existing Starlette/AnyIO deprecation warning.
  Provider smoke commands are dry runs, not paid/runtime proof.
- Tracked-files-only export to a fresh /tmp directory whose name contains spaces.
  No developer.env, models, database, private footage or node_modules copied.
  Actual official9,398,198-byte model download/hash verification and generated secret
  pass. Isolated Compose project, fresh volumes and alternate host ports13000/18000
  avoid touching the live3000/8000 app. Scratch-only APP_ORIGIN matches13000.
- Canonical final quickstart builds and starts api/web/worker. API /healthz, internal
  web, worker-running and host-facing /api/session status200 verified. Model itself
  successfully initializes in the worker image. Repeat prepare leaves .env/model
  SHA256 unchanged. Installed cue resource also available after rebuild.
- Synthetic blank video: session200 -> upload201 -> enqueue202 -> queued/running ->
  failed CHILD_FAILED. This proves job handoff/terminal handling, not successful
  human-pose analysis or a calibrated zero-cycle report. No private footage used.
- Git-history recognised credential-pattern scan returned0 matches; tracked media
  inventory contains original artwork/concepts, no user videos/model/database.
  Pattern scanning is not exhaustive secrets or rights certification.

## Boundaries

Verified locally on Apple Silicon Docker only. Windows/WSL2, Linux and AMD64 are
instructions, not passed device/platform certifications. First-time image pulls may
be slow; no instant/cold-cache timing guarantee. Existing54 Chromium viewport tests
are prior UX09 evidence, not rerun for docs/bootstrap-only changes.

Repository remains private; default main remains older. Judge instructions pin the
implementation branch until reviewed release. Public demo/video/registration and
public-release decisions remain outstanding. Local no-key analysis alone is not
NVIDIA/Nebius runtime proof; hosted/full coaching judge access still needs a plan.
Temporary test stack/volumes are cleaned separately from the user's live stack.

Six Nebius calls90,507 reported tokens, USD0.744717 conservative cost (not invoice),
including rejected drafts and repairs. Aggregate ceiling useUSD32.37368365<70;
protected30 untouched. No product-runtime/Tavily calls or private-media context.
Next HM-RELEASE03: public release branch/visibility, platform matrix and judge access.
