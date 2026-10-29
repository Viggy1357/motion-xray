# BRAG-SETUP01 — project-local Brag ready

25 October2026. User authorizes installation/preparation using Nebius, not video
creation or publishing. Submission tooling only; app source/settings unchanged.

## Installed

Trusted skill-installer helper installs audited latent-spaces/brag at
669ab9286aa28b6c3ee30e75f181ee74319d012a into .agents/skills/brag. Four supporting
Hyperframes skills installed from heygen-com/hyperframes at
1776b42736110e29397cd4512cfb1a609c6bbe28: hyperframes,hyperframes-cli,
hyperframes-registry,media-use. No global plugin or skill changes.

Local guards inserted after frontmatter and agents/openai.yaml disables implicit
invocation for all five. Installed original/overlay hashes recorded in
infra/brag/installed-skills.json. Skills are ignored local files; pinned restore
commands and overlay instructions are in docs/BRAG-QUICKSTART.md. Available next turn.

## Runtime and isolation

Nebius drafts the wrapper/image/guard, then repairs observed command/test and offline
scaffold errors. Hyperframes0.8.195 npm archive SHA512 verified against registry
metadata. Exact source identity in infra/brag/sources.json. Npm lock pins126 package
entries; npm audit reports0 advisories. Npm lifecycle scripts disabled. Pinning and
an advisory result do not constitute complete source/native-library security proof.

Docker uses the existing project's pinned Node22 image digest, exact Debian Chromium/
FFmpeg/certificates versions; image ID recorded. Build context infra/brag only,
not app repository or .env. All setup/runtime package installs inside Docker; only
trusted skill-installer/download/metadata orchestration uses the existing host tools.

./scripts/brag.sh allowlists local commands and blocks cloud/publish/paid/upgrade/
login commands and remote execution flags. Container ro root, caps dropped,
no-new-privileges, no Docker socket, host home, repo or .env mount. Only a validated
output folder is mounted. Networknone for checking/rendering. Preview alone uses
bridge with localhost4173 publication; outbound is possible in that exception, so
no credentials are passed. CI disables warm daemon; telemetry, automatic updates,
auto-install and init skill-refresh disabled. Home tmpfs ephemeral, frame cache output-local.

Actual init initially revealed remote CDN GSAP and attempted skill freshness check.
New prepare-init.mjs copies the locked renderer's bundled GSAP3.15.0 into assets and
replaces the exact generated3.14.2 CDN tag. Known template only; symlink protection,
idempotence and preservation tests. No alternate renderer or new JS library installed.
Project guards added to generated scaffold instructions. Source script needed a tiny
literal-newline syntax repair and init-help routing correction at integration.

## Verified

- Wrapper Bash and entrypoint shell syntax; Ruff;38 fake-Docker security regressions.
-9 Node built-in tests for local dependency preparation, idempotence and symlink guards.
- CLIversion0.8.195, Node22.23.3, system Chromium, FFmpeg/FFprobe5.1.9 present.
- Blank init from wrapper succeeds offline without a skill freshness install attempt.
- Actual Hyperframes check: oktrue, browserSkippedfalse, no lint/runtime/layout/motion/
  contrast/craft errors. One expected static-placeholder layout warning. This proves
  the browser check ran rather than just a zero-exit dry run.
- Preview onlocalhost4173 returns HTTP200; clean shutdown after test.
- FFmpeg/FFprobe wrapper commands report versions. No MP4 or submission content made.

Doctor overall okfalse due optional whisper/Kokoro/MusicGen, archive extractor for
managed Chrome, and nested Docker absent. Those are not needed for this system-Chromium
local no-voice path; required tools checked separately and actual browser validation
passed. No heavyweight voice/media model, HeyGen login or API provider activated.
No full MP4 render claimed. Final video content/claims/audio credits remain for explicit
subsequent authoring. Existing app and other Milo work were preserved.

## Files and next use

Canonical docs/BRAG-QUICKSTART.md; infra/brag contains sourcepins, lock, Dockerfile,
entrypoint, offline helper/tests, licenses and guard overlay. scripts/brag.sh is the
only execution entrypoint. Brag outputs ignored. Original audit notes retained.
Evidence in BRAG-SETUP01-readiness.json and usage ledger. Five source-only Nebius calls;
no private media/app source/secrets in prompts; no paid product runtime or publishing.

Next turn, invoke /brag with a factual Motion X-Ray brief. Storyboard first; use
sanitized source and assets, provisional assessment labels and measured timings.
Review before final rendering/publication. Bundled music attribution is separate
from the Brag MIT/Hyperframes Apache software licenses.
