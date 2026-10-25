<!-- GUARD OVERLAY: integrator inserts this block immediately after the skill frontmatter. Upstream files otherwise preserved; record original+overlay SHA hashes. -->

## Brag Guard (supersedes generic upstream instructions)

- Run **only** `./scripts/brag.sh <command>`. Never invoke host `npx`, `npm`, Python, or FFmpeg directly.
- Sandbox: network **none** (preview exception: bridge `127.0.0.1:4173` output only), read-only root, all capabilities dropped, no-new-privileges, no host Docker socket, no privileged mounts. Mount **only** the brag-output directory — never the repo, `.env`, or keys.
- Env enforced: `HYPERFRAMES_NO_TELEMETRY=1`, `DO_NOT_TRACK=1`, `HYPERFRAMES_NO_UPDATE_CHECK=1`, `HYPERFRAMES_NO_AUTO_INSTALL=1`, `CI=1` (disables warm daemon).
- Forbidden: auto-update, installing new models, paid API calls, HeyGen login, remote feedback/usage/cloud/publish/uploads. Broad classic guidance suggesting cloud/feedback/HeyGen paid toolchains is blocked; this Brag-specific guide supersedes external generic instructions.
- Never read `.env`, private videos, or personal data into output.
- UI text must be factual: MVP, provisional reference estimate, non-medical, processing-time labels. No fake "10x" claims.
- Workflow: setup only now. Future `/brag`: storyboard first, preview before final render, never publish without explicit permission. All supports require explicit invocation — never automatic use.
- Skills install to `.agents/skills` (local, git-ignored); no global installs.
- Licenses: Brag MIT; Hyperframes Apache-2.0; bundled music CC-BY-4.0 (Sascha Ende — credit required).