# First delegation batch — prepared, not dispatched

Read `../HACKATHON-EXECUTION-PLAN.md` and current AGENTS.md. Three maximum concurrent
direct Nebius requests; one integrating writer. No private clips, pose arrays, cookies,
credentials or point proposals in prompts. Each packet returns reviewable drafts only.
The owner asked for planning first; dispatch only when the next turn starts delegation.

## A1 — HM00 screen flow and reviewable mockup

**FRs:**01/02/03/06/07/08/09/10/12. **Role:** product/UI draft worker.

Read-only context: agreed flow/screen sections from the execution plan, web package
manifest, current globals/layout, generated report type excerpts supplied by integrator.
Do not preload the whole repository or unrelated skills. Addy pack remains opt-in.

Exact proposed outputs:

- `artifacts/development/hm00-motion-xray-mockup.html`
- `docs/design/HM00-screen-flow.md`

Deliver a compact standalone desktop/mobile mockup of Dashboard, New Set, Results and
History, with simple local navigation. Include upload/status/partial-result/coaching
unavailable/expired-video/empty-history states. Use illustrative values clearly marked
as mock data, not fabricated analysis evidence. Include the muscle view as an original
simple silhouette/mock illustration, not a purported personalised body reconstruction.
No CDN, tracking, remote assets, new dependency or app source mutation. Model/provider
API credentials are not UI settings. Explain the exercise-selection->upload->result->
log flow and the smallest reusable components. Keep the mockup scoped, not a design system.

Acceptance: local mockup opens without services/network; desktop/mobile states are
reviewable, primary action clear, keyboard navigation and text readable. It is never
called a working product. Integrator/user review before production UI implementation.

## A2 — HM01 contract/data migration proposal

**FRs:**01–12 plus personal log scope. **Role:** contract draft worker.

Read-only context: current contracts analysis/lifecycle/scoring/media, exact Store
public signature summary, report/quality/data sections from the execution plan.
Current pose artifacts are0.2.0 and their strict pose-only validator must stay intact.

Exact proposed outputs:

- `docs/design/HM01-contract-and-migration-proposal.md`
- `docs/design/HM01-api-acceptance-matrix.md`

Specify new typed profile/workout/set/routine/quality/report fields and route methods,
units/load semantics, enums, partial/missing rules, idempotency and ownership. Propose
format-dispatched0.3 report migration with old0.2 reader compatibility and generated TS/
OpenAPI/JSON schema updates. Identify pending incline-press implement variant rather
than invent one. Same-browser profile is the target; no cross-device authentication.
Separate durable profile/log summaries from raw24h/report7-day retention. Distinguish
detected reps from logged correction, estimated reference similarity from coverage,
and user-facing statuses from internal lease/storage fields.

No source/model/schema files edited in this proposal batch. No model_construct bypass,
invented Store methods, default score, silent threshold change or claim that reports
are already integrated. List exact follow-up implementation files, migration tests,
valid fixture construction and which frontend/backend callers change together.

Acceptance: integrator can freeze one coherent interface for HM02/03/04/06/08/09;
matrix covers normal/partial/invalid/foreign/deleted/expired cases and generated-type
drift. Resolve proposal conflict with A1 before source implementation begins.

## A3 — HM00 deployment/runtime readiness decision packet

**FRs:**02/03/04/09/12 and submission access. **Role:** read-only feasibility worker.

Read-only context: current Compose/services/dependency summaries, operations retention
notes, verified clip metadata, approved free-first preference and supplied official
hackathon/hosting source excerpts. Integrator retrieves bounded public-source facts
and runs safe read-only local/account checks separately; the model does not gain shell,
network or credential access merely by receiving this packet.

Exact proposed outputs:

- `docs/design/HM00-deployment-and-runtime-readiness.md`
- `docs/design/HM00-release-blockers.md`

Rank at most two feasible deployment routes for a real CPU pose worker, private files,
SQLite and HTTPS,
including Vercel Hobby frontend plus a separate Docker backend/storage versus a
single Docker host. Vercel's free frontend does not establish a free full stack;
validate direct authenticated uploads outside Functions' 4.5 MB payload boundary,
domain/cookie/CSRF behaviour and persistent worker/storage availability.
Aim for zero recurring cost. Separate checked facts from
assumptions: available host/uptime, CPU/RAM/disk, sleep/restart, persistent volumes,
codec/worker/checkpoint support, upload limits, stable URL and access through judging.
Do not assume Token Factory credit pays for AI Cloud, or that a free frontend is a
free persistent backend. If the supplied evidence cannot support a free route, state
the exact unanswered checks and smallest cost decision; do not invent free-tier claims.

List a bounded runtime Nemotron readiness check: model catalog availability, NVIDIA
identity, structured output, input/output/deadline/cache/quota controls and sanitized
evidence capture. A catalogue result or development worker call is not runtime proof.
No paid inference, account change, tunnel, deployment, upload or secret printing in
this proposal. Provide commands/checks for review, not an auto-executed shell script.

Acceptance: clear go/no-go/dependent questions for deployment and live coaching; no
unsupported vendor/pricing assertions; judge path cannot depend on a personal API key
embedded in public code or a judge buying credits. Cost activation remains a final
concrete owner decision after the feasibility work.

## Shared generation and integration rules

- Each packet<=200k cumulative task tokens including failed requests; start with a
  much smaller request sized to the returned files. Reserve cost/output before calling.
- Prefer a source-only K3 request that fits the demonstrated output envelope; split
  long mockup and notes if necessary instead of truncating both into one failed response.
- Return only the exact allowed paths in the strict draft envelope. No automatic edits
  or execution. Store usage/finish reason on success and failure, no SDK auto-retries.
- Codex checks concise outputs, runs the mockup/browser/document checks, resolves
  contract conflicts and applies accepted files. No extra broad review in this batch.
- Batch A makes decisions and reviewable designs; it does not finish HM01 source work
  or authorise dependent production implementation. Next is the explicit integration
  gate, then Batch B against frozen contracts.
