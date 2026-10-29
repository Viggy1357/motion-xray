# HM-FINAL01 — final QC and submission preparation

25 October 2026. FR01–12. Baseline `25ec8f3` on
`codex/hm-ux05-mockup-implementation`; this package adds a dependency repair,
browser-test synchronization repair and updated submission materials.

## Findings and changes

Nebius workers reviewed separate runtime and background-worker boundaries, drafted
the submission pack and supplied the two small repairs. Coordinator checked actual
helpers/tests and integrated one set of changes. Ten initial source-review candidates
were adjudicated: no material application defect proved in the inspected scope.
False CSRF/lease claims were rejected; paid-call reservation history was preserved.
Two optional diagnostic hardening items remain. See `HM-FINAL01-source-review.md`;
this is not a whole-system security certification.

The fresh package audit found four PostCSS advisories, including two high. Exact
PostCSS8.5.23 pin and transitive override clear them from the production graph.
The native pnpm9.12.1 lock was regenerated in Docker; framework versions and runtime
logic remain unchanged. Production audit now has zero advisories. One moderate
selector-parser issue remains in build tooling; trusted project CSS only, major
tool-chain migration deferred. Details: `HM-FINAL01-security.md`.

One post-patch full browser run returned107 passes and one first-use-intro test
failure. Its helper took an immediate visibility snapshot before the intro mounted.
Nebius replaced the conditional snapshot with an awaited expected intro, then the
existing Skip/hidden assertions. No test disabled, timeout raised, arbitrary sleep
added or production UI changed. Final full rerun result is recorded below.

## Verification

- `scripts/test.sh all`: exit0; Ruff/mypy,1,109 Python tests, web types and production
  build passed on the baseline. Provider smokes were dry runs, not paid inference.
- `scripts/export-contracts.sh`: exit0; generated OpenAPI/schemas/TS have no drift.
- After the dependency repair, `scripts/test.sh web`: exit0, frozen install,
  types/framework lint/production build pass.
- Final `scripts/check-browser.sh`:108/108 across360/375/1365 on patched dependencies
  and repaired helper. Full suite, not only the earlier54 Milo tests.
- Frozen install in the existing web container's dependency volume, followed by web
  restart; resolved PostCSS verified8.5.23. API/worker/storage/config unchanged.
- Production package audit exit0; all-dependency audit retains the single moderate
  build-tool finding. GitHub Dependabot alerts are disabled; no setting changed.
- Known-secret-pattern scan over all local Git refs returned zero matches; tracked
  inventory contains no video, model checkpoint, database or `.env`. This is a
  bounded pattern/inventory check, not proof every secret/IP issue is absent.

No fresh human-video analysis, coaching runtime call, hosting deployment, public
visibility change, footage publication or final Devpost submission in this task.
Offline checks do not prove calibrated biomechanics or hosted judge access.

## GitHub and submission handoff

Existing draft PR1: https://github.com/Viggy1357/motion-xray/pull/1 . Update the
implementation branch and rewrite its description around the final build and QC.
The private repository's default `main` remains older at `c395ecf`; do not silently
merge or change visibility. Canonical MIT text is on the implementation branch;
GitHub still reports `Other` on the old default branch. Verify licence display after
the reviewed release update. Current CI result is visible on the PR.

Updated `docs/submission/DEVPOST-DRAFT.md`, `READINESS.md`, `DEMO-SCRIPT.md` and README.
Draft highlights solo-set review, replayable measured evidence, bounded Nemotron
candidate selection and Pip's quiet companionship. Real-time video waits stay visibly
edited; main-app3D and a walking/LLM pet are not claimed.

Owner confirms registration/project draft not started and will register later.
Owner confirms the project began last week. First commit `09d0ca7` and GitHub creation
both corroborate16 October2026, within the submission period. This is supporting
project history, not an eligibility certification. No unverified event/city declaration.

Rules rechecked25Oct: https://nebiusglobalaihackathon.devpost.com/rules . Deadline
30Oct10:00PDT =31Oct01:00MYT. Public licensed code, working demo/hosted/test-build URL,
public YouTube demo under3minutes and access through15Dec12:00PST remain release
requirements. No public URLs invented. Select permitted demo footage, resolve D007
reference/artwork public-use boundaries, and establish judge access/capacity under
current20global/day,4owner/day,100lifetime coaching safeguards. Do not weaken quotas.

## Usage and limitations

Ten Nebius requests,149,607 cumulative tokens of200k; USD1.304793 conservative guard
cost, including all failed/invalid requests. Shared known maximumUSD36.89465965<70
after adding BRAG-SETUP01 once; protected30 untouched, balance not verified.
Ledger: `docs/delegation/HM-FINAL01-usage.json`. Runtime/Tavily calls0.

Three requests exhausted reasoning before useful output. Official model-specific
thinking control restored bounded output. One worker response had a trailing fence;
recovered candidates were reviewed, never executed or accepted as proven findings.
One dispatch was auto-review blocked before launch, then allowed after its exact
source-only packet was inspected. No bypass or paid call for the blocked attempt.
Writing-style connector unavailable; drafts follow supplied preferences without
claiming a retrieved personal style match. Uncommitted BRAG task notes preserved.

Next: HM-RELEASE03 public release/judge access and permissioned demo capture;
owner completes Devpost registration and reviews the prepared fields.
