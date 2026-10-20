---
name: motion-xray-delivery
description: Resume, implement, audit or hand off one Motion X Ray work package using the repository's delivery gates and container checks. Use for this repository's build coordination, not generic fitness advice or changes to other projects.
---

# Motion X Ray delivery

Read `AGENTS.md`, `TASKS.md`, `docs/PRODUCT.md`, `docs/ARCHITECTURE.md` and relevant
`DECISIONS.md` entries. For recovery context read `docs/AUDIT-2026-10-19.md`.
Use `docs/DELIVERY.md` for the dependency order and acceptance criteria. The archived
`docs/SPECIFICATION-v2.0.md` supplies detailed formulas and UX behavior; later accepted
decisions override its original provider and reference scope. Its FR numbering differs
from PRODUCT.md: use the audit's mapping, never assume the numbers are interchangeable.

Read D009/D010 and the relevant section of `docs/INTEGRATION-REVIEW-2026-10-20.md`
for T04–T07/T13. Reuse methods selectively: Sports2D/Good-GYM patterns, conditional
tracking/pose alternatives, and a verified DTW kernel behind our wrapper. No reviewed
candidate is installed or validated merely because it appears in that report.

Use D011 and `docs/TOKEN-BUDGET.md` for development calls: 100k cumulative tokens per
task is authorized, heavier allocations may be justified. Request output must cover
reasoning plus final code within model limits; retain usage/finish reason on failure.
Do not repeat the historical tiny caps. Runtime coaching has separate controls.

## Resume one task

1. Inspect git status and the previous task's evidence. Identify existing unfinished
   changes before editing; do not overwrite or commit another agent's work.
2. Claim one bounded TASKS work package. State its FRs, concrete output and check.
   Execute prerequisites before adding consumers of unimplemented providers.
3. Implement the smallest usable path. Preserve measured outputs when an optional
   service fails; a stub, zero-exit dry run or health endpoint is not a passed feature.
4. Run the relevant container checks. Record exact command, exit status, observed
   result and limitations. A temporary diagnostic patch is not an unmodified pass.
5. Update TASKS with files, checks, assumptions, blockers and next task. Commit only
   the coherent owned changes after scanning staged changes for secrets.

## Project-specific routing

- Pose/coordinates/visibility: `skills/pose-pipeline/SKILL.md` and D002/D005.
- Coaching: `skills/nebius-token-factory/SKILL.md` and D001/D004.
- Evidence: `skills/tavily-search/SKILL.md` and D006/D007.
- Deterministic algorithms: specification sections 6–10 and versioned exercise configs.
- UI: specification section 3, actual generated schemas and real timestamped artifacts.

Do not replace these skills with downloaded generic instructions. If an upstream
example is reused, record its exact revision, governing license and the adapted files.

## Avoid the previous stalls

Use non-interactive shell execution with an explicit working directory. If a terminal
echoes a dangling heredoc or corrupts commands, stop after confirming the failure;
open a fresh execution session instead of retrying the same command in a review loop.
Write longer commands to a script and invoke that script inside Docker.

Keep one writer on the shared checkout. Reuse the task evidence rather than launching
another scaffold audit. If a check fails, fix the bounded defect or record the exact
blocker; do not wait indefinitely on a planner/reviewer loop. When progress stalls,
report the last completed check and the next concrete action.

Never treat a model-list response as successful inference. Never treat a successful
connectivity prompt as validated coaching. Live provider calls require authorization
for that environment and an explicit call/budget bound; offline checks use fixtures.

Reference construction must use measured trajectories and reviewed metric rules.
Do not implement the old scratch plan's keyed placeholder tolerance values. Experimental
or unapproved references cannot produce displayed valid scores. An owned video alone
does not establish that its technique or tolerances are suitable as a benchmark.

## Handoff

Provide task ID/status, changed files, commands/results, evidence location, outstanding
decisions and next task ID. Keep credentials, raw conversations and private clips out
of handoff artifacts. No external publishing is implied by a completed local check.
