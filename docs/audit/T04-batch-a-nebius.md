# T04 batch A — External coding dispatch outcome

20 October 2026, Malaysia time. Codex orchestration only; three planned coding tasks.

## Authorized scope and bounds

User authorized implementation through Nebius Token Factory using existing credentials,
with Codex coordinating and no more than 3–4 tasks per batch. Planned tasks:

1. Immutable validated PoseFrame JSONL artifacts and failure-mode tests.
2. Canonical named MP33 joints, coordinate/quality mapping and tests.
3. Timestamped MediaPipe video adapter and offline tests.

Used `Qwen/Qwen3-30B-A3B-Instruct-2507`, available in the account catalog. Kept the
configured runtime Nemotron model unchanged. Credentials remained inside Docker env;
only selected source/contracts/instructions were sent, never private clips or keys.
Generation cap: four calls, including one reserved smaller streamed attempt; no SDK
retries. Requested output caps: 4,500; 4,500; 7,000; 3,500 tokens respectively.

## Observed results

| Call | Result |
| --- | --- |
| Artifact implementation | APITimeoutError after 90.39 seconds; no response artifact received. |
| Canonical mapping | APITimeoutError after 90.45 seconds; no response artifact received. |
| Adapter implementation | APITimeoutError after 90.39 seconds; no response artifact received. |
| Smaller streamed mapping attempt | 11,971 characters received over 81.34 seconds; JSONDecodeError on incomplete output. |

Static review of the recoverable fourth draft found edits outside the permitted files,
an invalid dataclass decorator on a function, type-only checks presented as finite-value
validation, and missing-observation behaviour that did not meet the task requirements.
No generated source, contract edit or test was applied or executed.

The account catalog is reachable. The cause of the generation timeouts is unconfirmed;
do not infer a provider outage, missing funds or invalid credentials. Usage/billing is
unknown because no usable accounting record was retained from these failed responses.
Requested token caps are not measured usage. Do not claim zero spend.

## Checkpoint and continuation

All three implementation tasks remain unfinished. No pose artifact, real model inference,
runtime coaching proof or new dependency was produced. Four-call cap reached; no further
paid generation was attempted in this batch. No fallback coding subagents were spawned.

Orchestration prompts, raw drafts and helpers remain under ignored `.agents/batch-a/`;
they are scratch evidence, not trusted executable project scripts. Existing private
diagnostic scripts were preserved. Only task/execution guidance and this report changed.
Documentation diff whitespace checks pass; no application tests were rerun because no
application/config/generated files changed in this batch.

For the next bounded batch, select a different account-visible coding route/model and
start with one compact task. Require valid scoped output before parallel dispatch. Use
streaming, preserve finish reason/usage even on parse failure, and distinguish truncated
drafts from complete output. Do not raise budgets automatically or retry the same large
prompts. Resume T04 only after a reviewed implementation and container checks succeed.
