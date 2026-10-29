> **29 October publication preparation:** The release update brings `main` to the current implementation. The owner must still make GitHub public; visibility is intentionally unchanged. Standard MIT text is in LICENSE, with third-party notices separate. The 2:30 local video is finished; latest recorded coaching returned unavailable after validation. No hosted app or public YouTube URL has been verified here. See [current release checklist](PUBLIC-RELEASE.md). The dated matrix below is historical and may describe superseded branch/video status.

# READINESS — Motion X Ray

> Release requirements and remaining actions for the Nebius x NVIDIA Global AI Hackathon.

Verified 25 October 2026. Local candidate commit `25ec8f3`. GitHub repo
`Viggy1357/motion-xray` (currently private). Implementation branch
`codex/hm-ux05-mockup-implementation` matches remote; `main` is older
(`c395ecf`). Draft PR #1 open, mergeable, prior CI green at `25ec8f3`.

---

## 1. Requirements matrix (primary sources)

Sources: [official rules](https://nebiusglobalaihackathon.devpost.com/rules) and [event overview](https://nebiusglobalaihackathon.devpost.com/), rechecked 25 Oct 2026. Submission deadline
**30 Oct 2026, 10:00 PDT = 31 Oct 2026, 01:00 MYT**. Judging access
window **15 Dec 12:00 PST = 16 Dec 04:00 MYT**.

### R1 — Public, licensed repo with setup
Source: Rules. Status: **Blocked — repository is private**. Owner to authorise public release before submit.

The implementation branch contains canonical MIT text. GitHub still reports licence
`Other` on older default `main`; verify visible licence detection after the reviewed
release/default-branch update, before providing the public link.

### R2 — Working demo / hosted app / test build URL
Source: Rules. Status: **Unknown — owner action**. No hosting purchased or activated in prep. Local Docker is the only verified run path.

### R3 — English description
Source: Rules. Status: **Verified (draft)**. `docs/submission/DEVPOST-DRAFT.md` prepared; final Devpost form not inspected from prep.

### R4 — Public YouTube video under 3 min
Source: Rules. Status: **Unknown — owner action**. Script in `docs/submission/DEMO-SCRIPT.md`; capture not authorised by prep.

### R5 — Show actual working device
Source: Rules. Status: **Pending demo capture**. Apple Silicon macOS is locally verified; actual-device demo footage has not been recorded.

### R6 — Free access through judging window
Source: Rules. Status: **Unknown — owner action**. Depends on R2 hosting choice. Current safeguards: 20 global/day, 4 per owner/day, 100 lifetime. Remaining capacity and a durable judge-access plan must be established; these quotas alone do not establish access.

### R7 — Feedback tools available
Source: Rules. Status: **Verified (draft)**. Devpost draft includes grounded feedback section; no invented praise.

### R8 — Significant update if pre-26 Aug
Source: Rules. Status: **N/A — confirmed**. First commit `09d0ca7` dated 16 Oct 2026 23:30:56 +08; GitHub API `created_at` 16 Oct 2026 15:50:33Z. New project within period; no pre-existing update block required.

### R9 — Four criteria: implementation, design, impact, idea
Source: Rules. Status: **Verified (draft)**. Devpost draft maps content to all four.

### R10 — Track selection
Source: Rules. Status: **Verified (proposed)**. "Best Apps and Agents" proposed; owner to confirm on form.

### R11 — Tavily bonus (functional runtime call)
Source: Rules. Status: **Not claimed**. `SEARCH_PROVIDER=cached` default; no Tavily call in submitted runtime path.

### R12 — Cloud hosting not mandatory if suitable test build
Source: Rules. Status: **Test-build route available under the rules, delivery unverified**. Docker setup is verified locally; no publicly accessible judge test-build URL is ready.

### R13 — Formal rules precedence
Source: Rules. Status: **Verified**. Rules cited above; no claim overrides them.

### R14 — Form mapping
Source: Rules. Status: **Proposed**. Live Devpost form not inspected from prep; mapping is best-effort.

### R16 — Runtime: Token Factory call or Nebius compute plus NVIDIA open model
Source: Rules. Status: **Verified (historical, local)**. One real owned-lat runtime call documented historically (1427 in / 38 out, 1.103s) — see `docs/audit/HM057-HM06-delivery.md`. Not current hosted proof. Model candidate ID: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`.

---

## 2. Verified vs unknown — at a glance

**Verified (local, offline):**
- Full Docker Python lint/mypy/tests + web types/build pass this run.
- 108/108 browser fixture cases pass across 360 / 375 / 1365 viewports.
- 1109 Python tests recorded; aggregate offline checks and contract drift pass.
- Generated contracts regenerated with no diff.
- Apple Silicon macOS is the only locally verified host.
- One real owned-lat runtime call documented historically (1427 in / 38 out, 1.103s) — see `docs/audit/HM057-HM06-delivery.md`. Not current hosted proof.
- Coaching path is **off** by default; only enabled when `ALLOW_LIVE_COACHING=true` with a valid `NEBIUS_API_KEY`.
- Model candidate ID: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` (from README).
- Coding agents are distinct: Codex performed the final source/contract gate and narrow integration corrections; Nebius produced UI and diagnostic drafts. No merged agent identity.

**Unknown / owner pending:**
- Public repo URL (repo currently private).
- Hosted demo / test build URL.
- Public YouTube demo URL.
- IRL event attendance/city, only if seeking the City award. Project start is confirmed by the owner and corroborated by 16 October history.
- Public reference video redistribution and authorisation (D007 public boundary).
- Devpost form field mapping (live form not inspected).
- Public demo clip permission (footage not yet selected or authorised).
- Coaching account balance (unknown; not verified).

**Explicit non-claims:**
- No clinical accuracy, technique grading, or injury-risk claims.
- No muscle-activation or nutrition/recovery claims.
- No user counts, paid-customer metrics, or third-party praise.
- No claim that paid development calls satisfy product runtime.
- No 3D skeleton in main app (separate diagnostic, not a feature).
- No real-time / live / hardware claims.
- No retention metrics.
- No chat or safety advice from the model.

---

## 3. Priority next actions (no exact schedule)

Ordered by dependency, not by date. Owner decides timing.

1. **Owner: select and authorise a public demo clip.** Until this is done, no footage capture or upload is authorised. Separate from any live call.
2. **Owner: record the demo per `docs/submission/DEMO-SCRIPT.md`** (target 2:40, under 3:00). Insert the "[real-time wait — edited]" card over the processing screen. Record one real `Generate coaching` click; do not pre-render the note.
3. **Owner: decide hosting.** Free-first hosting for judge access is the proposed path; no hosting purchased in prep. Local Docker alone is not a public judge link.
4. **Review the release diff, third-party reference policy and artwork rights; then authorise public visibility** and verify the licence and setup on the release/default branch.
5. **Owner: create the Devpost submission** using `docs/submission/DEVPOST-DRAFT.md` as the content source. Confirm field mapping against the live form.
6. **Owner: paste the three URLs** (repo, hosted app, YouTube) into the Devpost form. No fake URLs in the draft.
7. **Owner: confirm track** ("Best Apps and Agents" proposed).
8. **Owner: fill the optional firsthand-feedback placeholders** in the Devpost draft from personal experience only. Do not invent.

**Deadline gate:** 30 Oct 2026, 10:00 PDT = 31 Oct 2026, 01:00 MYT. All of the above must complete before this gate.

---

## 4. Release / publishing / rights / quota gates

- **Release:** Repo must be public before submit. Branch `codex/hm-ux05-mockup-implementation` is the demonstrated build; `main` is older. Owner to merge a release or document the branch choice in the Devpost description.
- **Publishing:** No MP4 render produced in prep. Demo video export is an owner action (1080p, H.264, audio normalised).
- **Rights:** Public reference videos are not bundled; redistribution and authorisation are unreviewed (D007). Owner to resolve before any public reference clip is shown.
- **Quota:** Atomic coaching quota is in place. Current safeguards: 20 global/day, 4 per owner/day, 100 lifetime. Access/capacity through judging remains unverified. Account balance not verified; protected 30 untouched.
- **Evidence budget:** No invented metrics, no invented feedback, no invented praise. Reference resemblance and measurement accuracy remain unreviewed.

---

## 5. Platform note

Apple Silicon macOS is the only locally verified host. Linux Docker is
the documented run path. Windows native is not verified (use WSL2). No
x86_64-only claims are made.

---

## 6. Registration and remaining owner inputs

Owner confirms registration and a Devpost project draft have not been started and will be completed later. Motion X-Ray started last week; first commit and repository creation corroborate 16 October 2026.

- Public repo authorisation.
- Hosting decision and URL.
- Demo clip selection and authorisation.
- Devpost form field confirmation.
- Track confirmation.
- Optional firsthand feedback (personal experience only).
- IRL city (if the owner wishes to include it).

No submission, no visibility change, no live inference, and no private
footage publication is authorised by this prep document.
