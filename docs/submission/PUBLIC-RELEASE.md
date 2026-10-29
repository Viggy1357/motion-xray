# Public release preparation — 29 October 2026

## Judge entry points

- Repository: https://github.com/Viggy1357/motion-xray (owner must make public).
- Default branch: `main`, updated with the reviewed implementation release.
- Setup: root README and docs/QUICKSTART.md; run `./scripts/quickstart.sh` with Docker running.
- Use your own short workout clip. No private videos, reference clips or model checkpoints are bundled.
- Core pose processing runs locally on CPU; optional paid Nemotron coaching requires a server-side key.
- No hosted app URL is supplied. A local build is not a remotely accessible demo.
- Owner supplies the public YouTube URL in Devpost. The rendered local film is documented in brag-video03/README.md.

## Submission requirements

Standard MIT LICENSE covers original project code. THIRD_PARTY_NOTICES.md preserves separate component terms. README explains NVIDIA Nemotron 3 Nano 30B A3B, runtime Token Factory API use, separate Nebius coding-worker development and services not used. No runtime Tavily award is claimed.

The final walkthrough's coaching request failed local validation; the app returned unavailable without invented guidance. Historical successful calls do not establish present hosted reliability. Reference resemblance remains experimental; technique scores are not validated grades.

## Publication review

A pattern-based scan covers reachable local history. No credential-pattern candidates were detected. Private media appears in local Codex checkpoint refs only, not release/main history; those local refs are preserved and must never be mirror-pushed. Only named branch refs are pushed. Pattern scans are not proof of absence.

`Videos/`, local film outputs, secrets, model files, downloaded reference media and generated artifacts remain excluded from Git. Videos and film outputs are also excluded from Docker build contexts. Public artwork and mockup images are intentional project assets. Local filesystem paths in historical evidence are metadata, not bundled files.

## Owner actions after preparation

1. Change repository visibility to Public on GitHub; do not publish `.env`, private media or local checkpoint refs.
2. Open the repository while signed out and confirm README and MIT licence are visible.
3. Add the public YouTube URL and GitHub URL to Devpost.
4. Provide a working demo/test-build route under the organizer requirements. Hosting and judge API access remain unresolved; do not describe localhost as a public app.
5. Review the submission and submit personally. No form submission is performed by this release task.

## Release checks

1,109 Python tests, Ruff and mypy passed. Docker web typecheck and production build passed; all tracked frontend files matched the cached check image byte-for-byte. Quickstart help and whitespace checks passed. No paid runtime inference was performed. Evidence: ../audit/HM-PUBLISH01-release.json.
