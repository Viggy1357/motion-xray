# Brag repository static security audit

25 October2026 · BRAG-AUDIT01 · audit only, not skill invocation/installation.

**Verdict: no malicious behaviour found in the inspected source. Reasonable to trial
locally with pinned, isolated dependencies; not an unconditional end-to-end clean bill.**

Repository https://github.com/latent-spaces/brag at exact commit
`669ab9286aa28b6c3ee30e75f181ee74319d012a` (plugin version0.5.0).
Future repository/package updates are outside this verdict.

## What it does

The classic skill reads selected app source, plans a15–25second launch video, prepares
an HTML/motion composition through external Hyperframes tools, then renders a video,
poster and draft share copy into brag-output (timestamped for repeated runs). Optional
voiceover uses Kokoro through Hyperframes. The slim variant supplies a single-file
workflow using available tools and asks before installing missing essentials. Neither
skill was invoked for this audit; their instructions were treated as untrusted data.

## Scope and evidence

GitHub commit/tree API pinned an untruncated411-entry tree. All76non-media text/code
blobs (1,273,794bytes) fetched from that exact commit and verified against Git blob SHA1;
SHA256 recorded in local temporary inventory. Six symlinks were stored as text rather
than created; all resolve to the repository's own skills. All10JSON files parsed.
Detailed inspection covered both skill variants, workflow references, three shipped
CLI scripts, browser JS/inline examples and plugin manifests; remaining documentation,
CSS, audio metadata and dependency lock were scanned/parsed for suspicious patterns.

All294media/image files were inventoried but not downloaded/decoded/malware-scanned.
Their contents, decoder safety, historical commits and external package source are
not certified. No source script, package installer, plugin or skill was executed.
Trusted stdlib code fetched/hashed/parsed source; TOML parsing ran in a network-disabled,
read-only existing container. The project's dirty working tree was preserved.

One bounded source-only Nebius reviewer supplied a first-pass threat review. Its claims
were checked against local line-numbered source; it did not inspect every static HTML
file itself, and dependency artifact hashes were not checked against downloaded wheels.

## Findings

### Medium: unpinned external renderer execution

`skills/brag/references/step-4-deliver.md:7,33` and step-3 call `npx hyperframes` without
an exact version. The Hyperframes package and its transitive/runtime dependencies are
not included in this repository. Npx may download and execute registry code with the
process's permissions. Likewise, the README's npx skills installer is a separate tool.
This is a supply-chain boundary, not evidence of malicious Brag code. Before actual
use, pin/review the chosen renderer/installer and run without project secrets in an
isolated container. A pinned Git commit does not pin these external packages.

### Medium: Python dependency reproducibility is not forced by the workflow

`skills/brag/scripts/pyproject.toml:7-12` uses lower bounds for librosa/numpy/scipy/
soundfile; `references/audio.md:260` suggests `uv run --project` without --locked or
--frozen. A checked-in uv.lock has exact versions/artifact hashes and standard PyPI
sources, but it can be refreshed if out of sync. Use a reviewed locked dependency
set with --locked (reject drift) or --frozen after confirming consistency. Do not
install this ML/audio stack onto the Motion X-Ray host.

The30registry packages in the lockfile were queried by exact name/version against
OSV's public batch API on the audit date; all30returned no advisories. This means no
matches returned by that database, not proof of vulnerability-free packages. No wheels,
source distributions or native libraries were downloaded/audited.

### Low: output overwrites are documented, not covert destruction

The audio helper writes explicit --output-json/--output-md destinations, creating
parent directories. The video poster step uses ffmpeg -y and replaces brag.mp4
(`step-4-deliver.md:68-72`). Use a fresh timestamped output directory. No recursive
filesystem deletion, shell-profile modification, credential search or persistence
mechanism was found in shipped code.

### Privacy boundary: source-to-public-video workflow

Source read into a storyboard may later appear on screen or in copy. Positively,
`references/step-1-inspect.md:125-132` excludes .env/credentials/keys and prohibits
carrying private data into output. `brag-slim/SKILL.md:39-55` has equivalent protection,
treats fetched pages as untrusted data and says downloaded markup must be inert.
This is instruction-level protection, not an OS sandbox. Website rendering can run
third-party page JS in a browser, and arbitrary URL fetching needs normal browser/
network isolation. We should provide sanitized Motion X-Ray source/assets and demo
content, not our .env, private user footage or unrestricted home directory.

`step-3-compose.md:88,193` requires separate explicit user requests for remote/publishing
workflows. The optional letsbrag.app service is advertised in README; no automatic
upload to it was found in local code. Its server was not audited. Docs/examples make
ordinary Google Fonts/Unsplash/star-history asset requests if viewed; no covert data
collection endpoint or embedded remote executable was found.

### Non-security submission caveat: accuracy and music licensing

This tool can recreate an app UI as an animated composition. Its successful render is
not evidence of a functioning app or faster analysis. For the submission, ground all
claims in actual Motion X-Ray behaviour; keep provisional assessment labels and do
not portray accelerated animation as real processing speed. The skill itself discusses
this limitation in step-3's factual-claims section.

Repo software is MIT. Its music README separately labels the bundled tracks CC BY4.0
and requests credit `Music: Sascha Ende, ende.app (CC BY 4.0)`. Do not assume music is
covered by the software license; verify chosen assets/terms before public submission.
This review records the repository's attribution statement, not independent rights
verification of all bundled media.

## Benign code and permissions

- The Python audio analyzer imports argparse/json/math/pathlib/typing/librosa/numpy;
  reads a chosen track, computes signal metadata and writes selected output files.
  No direct network clients, eval/exec, subprocess or environment/secret access found.
  Dependencies may have additional behaviour; they were not executed/audited here.
- The two Node maintenance scripts read local files and report consistency failures.
- docs/main.js implements video controls and click-triggered clipboard copy; no hidden
  upload, credential capture, persistence or remote fetch found in that script.
- Plugin metadata advertises Read/Write/Execute, which is expected for video rendering
  but broad. No bundled hooks, MCP server config, .gitmodules, npm package manifest,
  npm install lifecycle scripts or external symlink targets were present in the tree.
- Model-based workflow dispatch and skipping Hyperframes' generic creative/review steps
  are workflow preferences; no instruction to override host security policies or
  silently publish was found. They remain subordinate to project/user requirements.

## Recommended disposition

Suitable for a pinned local trial after the external renderer/runtime is pinned and
reviewed, in a container without credentials/private footage, with fresh output dirs
and a human review of video claims and selected audio credits. Brag-slim has fewer
predefined external tool assumptions; that does not guarantee what tools an agent
might choose. No installer was run and no global or project skill was activated.

Evidence: BRAG-AUDIT01-evidence.json. Provider usage is recorded separately in
`docs/development-usage-BRAG-AUDIT01-2026-10-25.json` (19,198tokens, USD0.078210
conservative guard, not invoice price). No app tests required for this audit-only work.
