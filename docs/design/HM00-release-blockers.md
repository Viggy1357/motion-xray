HM00 Release Blockers
Blockers preventing release readiness:

1. DEPLOYMENT ROUTE UNRESOLVED
   - No confirmed path: zero cost Docker host availability unverified;
     Vercel+Docker persistent backend/storage unvalidated

2. RUNTIME NEMOTRON NOT VALIDATED
   - Provider is stub (NotImplementedError); no real Nebius call completed
   - Model catalogue availability is not runtime proof
   - No paid inference, account change, or credential activation in this proposal

3. PAYLOAD LIMIT VIOLATION
   - All four clips exceed 4.5 MB Functions limit; must validate direct authenticated
     upload path outside Functions boundary
   - API config, ingestion, proxy/provider, PoseJobInput, model recipe and
     fixtures must change together; env var increase cannot fix hard-coded 30s

4. COST ASSUMPTIONS UNCHECKED
   - No cloud account entitlement verified. Official FAQ confirms Token Factory
     promotional credit does not establish AI Cloud hosting credit. A free frontend
     does not establish a free persistent backend.
   - All cost decisions final owner choice after feasibility work

5. JUDGE ACCESS PATH UNCLEAR
   - Persistent storage, HTTPS domain, judge access duration not confirmed
   - Submission path cannot depend on personal API key in public code
   - Judges must not need to buy credits or supply their own provider key

Go/No-Go/Dependent:
GO when: Docker host confirmed; direct upload validated; Nemotron coaching
  implemented and tested; all four exercise clips processed through UI; persistent
  storage and owner isolation verified.
NO-GO until: deployment route confirmed; Nemotron call functional; payload limits
  resolved; cost assumptions checked and owner decision made.
DEPENDENT blocked by: HM01 schema migration; HM03 full-set media lifecycle;
  HM04 lat runtime report; owner cost decision before deployment activation.

Commands for review (NOT auto-executed):
1. Verify Docker host: always-on, persistent disk, CPU/RAM, HTTPS domain
2. Test direct upload: actual clip sizes vs 4.5 MB limit
3. Implement Nemotron coach: structured evidence, bounded tokens, timeout
4. Validate cookie/CSRF/CORS across domains
5. Check judge access: persistent storage, duration, no personal key dependency
