# TASKS.md — current status, acceptance, dependencies, evidence, next action

All dates Malaysia time, 2026. A date does not make an unfinished task complete.
Build the first usable curl flow before visual polish or additional exercises.

## Legend
- `todo` not started · `wip` in progress · `blocked` waiting · `done` evidence recorded

---

## T00 — Repo scaffold  ·  status: done
- **FRs:** (infrastructure)
- **Evidence:** Directory tree per spec §15, docs skeleton, contracts/providers stubs,
  Docker Compose skeleton, skills drafts, `.env.example`, git initialized.
- **Next:** T01 feasibility spike.

## T01 — Feasibility (Gate A)  ·  status: todo  ·  date: 16 Oct
- **FRs:** FR04, FR12
- **Goal:** Prove the chosen pose provider (MediaPipe) yields usable timestamped
  coordinates, correct anatomical sides, and synchronized playback on an authorized
  10–20s curl clip. Run ONE real Nemotron inference through Token Factory and verify
  structured output. Record hardware, model revision, cold/warm runtime, peak memory,
  artifact size, dependency licenses.
- **Blocked on:** (1) an authorized demo curl clip from product owner; (2) Docker
  Desktop installed; (3) confirmed Token Factory model ID.
- **Acceptance:** usable coordinates + synchronized playback + stable body identity
  demonstrated; one Token Factory coaching call returns valid JSON. Pass/fail and
  provider decision recorded in DECISIONS.md.
- **Next:** on pass → T02 lock environments; on fail → isolate + fallback.

## T02 — Scaffold hardening  ·  status: todo  ·  date: 16–17 Oct
- Locked dependency versions, working Compose, CI (fixtures only), contracts exported.

## T03 — Ingestion  ·  status: todo  ·  date: 17 Oct  ·  FR01, FR02, FR03
## T04 — Pose adapter  ·  status: todo  ·  date: 17–18 Oct  ·  FR04
## T05 — Curl engine  ·  status: todo  ·  date: 18–19 Oct  ·  FR05, FR06
## T06 — References  ·  status: todo  ·  date: 20 Oct  ·  FR07, FR11
## T07 — Scoring  ·  status: todo  ·  date: 20–21 Oct  ·  FR07, FR08
## T08 — Jobs & cloud  ·  status: todo  ·  date: 21–22 Oct  ·  FR03, FR12
## T09 — Coaching  ·  status: todo  ·  date: 22 Oct  ·  FR09
## T10 — Evidence  ·  status: todo  ·  date: 23 Oct  ·  FR11 (P1)
## T11 — X Ray UI  ·  status: todo  ·  date: 23–25 Oct  ·  FR10
## T12 — Other exercises  ·  status: todo  ·  date: 25–26 Oct  ·  FR06
## T13 — Evaluation  ·  status: todo  ·  date: 27–28 Oct
## T14 — Release  ·  status: todo  ·  date: 29 Oct
## T15 — Submission  ·  status: todo  ·  date: 30 Oct

---

## Immediate next action
Product owner to: (1) install Docker Desktop, (2) provide an authorized curl clip,
(3) confirm a Token Factory NVIDIA model ID. Then run the T01 feasibility spike.
