# Development token budget through personal MVP

20 October 2026, Malaysia time. T21 planning estimate, not measured implementation usage.
Machine-readable allocations: [development-budget.json](development-budget.json).

## Scope and accounting

Forecast the remaining four-exercise MVP through T14: real pose, upload/jobs,
measurements, viewer, reviewed references, similarity, coaching, exercise expansion,
evaluation and personal release. Optional hackathon submission T15, incline press T17,
new model training and a commercial multi-user service are excluded.

The user authorizes up to 100,000 tokens per bounded task, with larger allocations for
heavy work where needed. Treat this as cumulative input plus completion across draft,
review and repair calls. Completion includes reasoning and final output: never count
reasoning twice. Tool-result/context resends consume input again. This is not a request
to spend 100,000 on every task, a 100,000-token prompt, or a model output/context limit.

## Baseline allocation

All token columns below are thousands. These are planning hypotheses derived from
remaining scope, not calibrated throughput measurements. Each row is split into the
listed bounded tasks; a row larger than 100k is not one oversized coding request.

| Work / owner | Tasks | Input k | Completion k | Total k |
| --- | ---: | ---: | ---: | ---: |
| Delegation/request handling (T21.1) | 1 | 30 | 20 | 50 |
| Canonical pose + real smoke (T01/T04) | 3 | 120 | 80 | 200 |
| Upload + durable jobs (T03/T08.1) | 3 | 150 | 100 | 250 |
| Lat-pulldown measurement engine (T05) | 3 | 160 | 110 | 270 |
| Measurements viewer (T11.1) | 3 | 140 | 90 | 230 |
| Reviewed reference builder (T06) | 2 | 110 | 70 | 180 |
| Alignment + similarity scoring (T07) | 2 | 100 | 70 | 170 |
| Evidence review controls (T10) | 2 | 90 | 60 | 150 |
| Coaching + complete results viewer (T09/T11.2) | 3 | 160 | 110 | 270 |
| Curl, raise and squat expansion (T12) | 3 | 180 | 120 | 300 |
| Held-out + browser evaluation (T13) | 3 | 140 | 90 | 230 |
| Personal release + recovery (T14) | 2 | 100 | 70 | 170 |
| **Total** | **30** | **1,480** | **990** | **2,470** |

Reserve a further 25% (617,500 tokens) for integration defects and unforeseen complexity:
the planning envelope is **3,087,500 development tokens**. Per-task 100k allowances
aggregate to 3M over 30 tasks; reserve expenditure above that requires explicit recorded
task allocation increases under the user's heavier-task authorization. This is not an
account spend limit or a guarantee that the MVP can be delivered within the estimate.
Reforecast if actual accepted-task usage suggests roughly double this forecast.

## Price scenarios

Published USD per million input/output tokens, checked 20 October:

| Model | Input | Output | Baseline | With 25% reserve |
| --- | ---: | ---: | ---: | ---: |
| Nemotron 3.5 Super VL | $0.30 | $0.90 | $1.34 | $1.67 |
| Nemotron 3.5 Lightning | $0.06 | $0.24 | $0.33 | $0.41 |
| Kimi-K2.7-Code | $0.95 | $4.00 | $5.37 | $6.71 |

These are alternative all-work-on-one-model arithmetic scenarios, not costs to add
together, evidence of equal quality or a recommendation to use the smallest model.
Formula: input_tokens/1M × input_rate + completion_tokens/1M × output_rate.
Sources: [Super VL pricing and reasoning-budget guidance](https://nebius.com/blog/posts/three-new-open-weight-models-from-us-companies-give-builders-more-choice),
[Lightning pricing](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference),
[Kimi pricing](https://nebius.com/services/token-factory/models/kimi-models-inference).

No cache discounts assumed. Taxes, provider minimums/rounding, GPU/CPU hosting, storage,
Tavily, data access and Codex account usage are excluded. Account credit balance was
not checked. Actual model mix and invoice rates determine real cost. A larger reliable
model may cost less per accepted change than repeated failing small-model calls.

## Allocation policy for agents

1. Keep Codex orchestration/review light. Use Nebius for substantive coding and targeted
   reviews. Check exact account model ID and run one successful scoped implementation
   before dispatching parallel drafts. Model availability is not a quality pass.
2. Start ordinary tasks with 60k–100k cumulative allowance. Use the row's average as an
   initial allocation, not as a mandatory consumption target. Reuse unchanged context
   intelligently and request patches/files rather than repeatedly reproducing the repo.
3. Give reasoning models sufficient completion space: an initial 16k–32k output ceiling
   can leave room for thought and code. Heavy requests may need 48k–64k where supported.
   Validate each provider's actual output cap and context constraint first; do not blindly
   send these values. These request maxima are ceilings, not desired output sizes.
4. Stream responses, record finish reason and usage even on parse failure, and distinguish
   reasoning-only exhaustion, truncation, transport failure and rejected code. Preserve
   partial drafts for inspection, never auto-apply them. Do not use reasoning text as code.
5. Treat 90 seconds as an idle/read bound, not a universal full-generation deadline.
   Start with a 10-minute total request bound and adjust deliberately to model/token
   throughput. Keep progress updates within 60 seconds using asynchronous orchestration.
6. Disable hidden SDK retries. A test-guided repair is an explicit call charged to the
   same task budget. Repeated failure triggers diagnosis/model change, not blind retries.
   Never mark code accepted because generation finished or JSON parsed.
7. Run at most three independent work tasks concurrently, with at most four per batch.
   Keep one writer integrating. Report accepted outputs, checks, tokens, cost and blockers
   before the next batch; dependent tasks wait for the necessary contracts/artifacts.
8. Notify/reforecast near 80% of a task allowance. Increase heavy-task budgets with a
   recorded reason and new ceiling; the user already permits justified increases.
   Large remaining scope may be split into separate tasks with separate acceptance.

The former 4,500/5,000-token draft caps and four-call batch A cap are historical, not
the new default. Do not interpret the 5k reasoning-only response as failed credentials.
The ledger must store task/model/request ID, input/output/reasoning tokens, finish
reason, elapsed time, price basis, review/test result and cumulative task usage.
Prior unaccounted usage stays unknown; do not erase it when computing a new forecast.

## Runtime validation is separate

Keep an optional reserve of 200k input + 300k completion tokens for bounded product
validation. At Super VL's published rates that is $0.33; this is not part of the coding
estimate and does not enable automatic paid calls. Actual application tests require their
own environment, per-run limits and usage records. Runtime Nemotron selection stays
under D004/T09 until a measured quality decision; coding-model choices do not change it.

No video is sent to the coaching model. The deterministic pose/metric/scoring pipeline
does not consume LLM tokens. Live Tavily and hosting require separate cost estimates.
Codex usage is on a separate billing system; no numerical Codex saving is claimed here.

## Calibration and next batch

Implement T21.1 request handling/ledger as a bounded supporting task, not a replacement
for T04. Use one real canonical-mapping implementation to calibrate settings and accepted
code quality, then expand to the other two pose tasks. Reforecast after the first three
accepted tasks. Keep the first usable lat-pulldown flow ahead of the remaining exercises;
the 2.47M estimate covers the full planned four-exercise MVP.

The last Kimi attempt recorded 987 input and 5,000 completion tokens, all completion
reported as reasoning, no final code, finish_reason=length. At the published rates,
that call is approximately $0.02094 before other charges. Four earlier draft calls lack
usable accounting records. No reliable tokens-per-accepted-task baseline exists yet.
