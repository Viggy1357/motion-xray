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

## T01 — Feasibility (Gate A)  ·  status: wip  ·  date: 16 Oct
- **FRs:** FR04, FR12
- **Goal:** Prove the chosen pose provider (MediaPipe) yields usable timestamped
  coordinates, correct anatomical sides, and synchronized playback on the authorized
  **lat pulldown** test clip (`data/demo/lat_pulldown.mp4`, diagonal/side view, ~55s,
  464×832, ~60fps → downsample to 30Hz). Run ONE real Nemotron inference through Token
  Factory and verify structured output. Record hardware, model revision, cold/warm
  runtime, peak memory, artifact size, dependency licenses.
- **Unblocked:** ✅ Docker Desktop running; ✅ test clip provided; ✅ Token Factory key
  present (model ID to confirm from catalog during the spike).
- **Acceptance:** usable coordinates + synchronized playback + stable body identity
  demonstrated (note: a second person is in the clip background — verify single-track
  stability); one Token Factory coaching call returns valid JSON. Pass/fail and provider
  decision recorded in DECISIONS.md.
- **Next:** on pass → T02 lock environments; on fail → isolate + fallback.

## T01b — Lat pulldown exercise + evidence/reference flows  ·  status: wip  ·  date: 18 Oct
- **FRs:** FR06, FR11
- **Goal:** (1) lat pulldown is the first exercise wired end-to-end (spec added:
  `data/exercise_specs/lat_pulldown.yaml`); (2) Tavily evidence-discovery flow that finds
  credible technique sources + candidate video URLs and extracts guidance text for
  operator review; (3) a reference-build script that turns product-owner-downloaded clips
  in `data/demo/` into a trajectory + tolerance ranges, flagged `authoritative=false`
  unless an owned/authorized reference (DECISIONS.md D005/D006/D007).
- **Acceptance:** `evidence/refresh` returns a reviewable shortlist from a real Tavily
  call; reference build produces a trajectory from an owned clip; experimental references
  are flagged non-authoritative and cannot yield a displayed valid score.

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
Infrastructure ready (Docker running, lat pulldown clip in data/demo/, Token Factory key
present). Next: build the pose container, run MediaPipe on the lat pulldown clip
(feasibility spike T01), and make one real Nemotron call. In parallel, wire the Tavily
evidence-discovery flow and the reference-build script (T01b).
