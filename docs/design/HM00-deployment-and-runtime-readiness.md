HM00 Deployment and Runtime Readiness
Deployment routes (ranked, zero recurring cost goal):

1. SINGLE DOCKER HOST (preferred)
   - Same-origin host, persistent disk, CPU pose worker, SQLite, private video
   - Requirements: always-on, CPU/RAM/disk, stable HTTPS/domain, upload/egress limits,
     restart/sleep behaviour, judge access duration
   - Acceptance: physical host identified; existing machine/tunnel only if uptime/secure
     exposure/judge access demonstrated

2. VERCEL HOBBY FRONTEND + SEPARATE DOCKER BACKEND/STORAGE
   - Free within quotas, personal/non-commercial; Functions 4.5 MB payload limit
   - All four clips exceed the 4.5 MB Function limit (6.70–46.01 MB)
   - Must validate direct authenticated uploads outside Function boundary
   - Must validate cookies, CSRF, CORS, private playback across domains
   - Does NOT resolve Docker pose worker, durable DB, private video storage
   - Ephemeral free filesystems and sleeping workers unacceptable without tested design

Runtime Nemotron readiness (bounded checks, no paid inference):
- Model catalog: NVIDIA-Nemotron-3-Nano-30B-A3B, Nemotron-3_5-Lightning,
  Nemotron-3.5-Super-VL (verified)
- Structured evidence; input <=2,500 tokens; output <=500 tokens; 30s deadline;
  single retry fits 60s total budget
- Cache by evidence/profile/prompt/model; refresh/retry must not generate new bills
- Provider outage: coaching_unavailable; never pretend live call
- No paid inference, account change, tunnel, deployment, upload or secret

Verified facts: Vercel Hobby free within quotas; Functions 4.5 MB; Token Factory
  credits separate from AI Cloud, no published AI Cloud grant; no current cloud
  account entitlement; app uses guest sessions; catalogue verified Nemotron models;
  Docker compose (infra/compose.yaml) exists; Nebius provider is stub.

Rejected assumptions: Token Factory pays for AI Cloud; free frontend = free persistent backend.
Unverified: existing machine/tunnel has sufficient uptime/judge access; cloud
  account entitlement exists.

Cost: Zero recurring cost only if same-origin Docker host with persistent disk satisfies
  all requirements. If unsatisfied: concrete smallest-cost option, monthly duration,
  shutdown plan for owner decision (NOT activated).

Checks for review (NOT auto-executed):
1. Host: always-on, persistent disk, CPU/RAM, HTTPS domain
2. Upload: direct authenticated path outside 4.5 MB limit
3. Cookie/CSRF/CORS: across frontend/backend domains
4. Model catalog: access without paid activation
5. Restart/sleep: state preservation or workaround
6. Judge access: duration, persistent storage, no personal key dependency
7. Nebius provider: import and catalog discovery without credentials
8. Clip sizes vs 4.5 MB limit (lat: 6.70, press: 44.70, curls: 46.01, squat: 27.81 MB)
Integrator QC: corrected erroneous claim that6.70MB fits4.5MB. Model produced a usable checklist, not evidence of hosting or runtime coaching. Hosting selection remains deferred while local build proceeds.
