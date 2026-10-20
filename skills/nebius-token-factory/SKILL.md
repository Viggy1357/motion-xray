---
name: nebius-token-factory
description: |
  How Motion X Ray calls NVIDIA Nemotron through Nebius Token Factory for grounded
  coaching, while conserving limited credits. Use when implementing or debugging the
  LLM coaching adapter, choosing a model, shaping prompts, validating structured
  output, or deciding whether a call should run at all. Token Factory is
  OpenAI-compatible. The deployed app MUST make a real Nemotron call at runtime —
  this is the hackathon's required NVIDIA-model path.
---

# Nebius Token Factory (coaching LLM)

## What this is for

The ONLY runtime LLM job in Motion X Ray is coaching: turning validated, deterministic
measurements into 2–3 grounded observations. The model never sees raw video, never
produces scores, and never invents numbers.

Endpoint (OpenAI-compatible): `https://api.tokenfactory.nebius.com/v1`
Key: `NEBIUS_API_KEY` (server-side only; never a public frontend prefix).

## Credit conservation (this project has limited credits)

Treat every call as costing money. Rules, strongest first:

1. **Never call per set blindly.** Cache coaching by a hash of the exact structured
   input (metrics + deviations + rep IDs + reference version + prompt version). Identical
   input returns the cached result with zero spend.
2. **Start with the smallest NVIDIA model.** Discover the exact model ID from the
   account catalog (`GET /v1/models` or the console). Begin with the smallest Nemotron
   (e.g. a Nano-class model); escalate only if measured coaching quality is inadequate,
   and record the change in DECISIONS.md (D004).
3. **Bound the budget.** Request timeout 30s, at most ONE transient retry with backoff,
   total coaching budget 60s. On exhaustion, return `coaching.status=unavailable` with an
   optional deterministic factual summary — do NOT keep retrying.
4. **CI never spends.** Offline tests use recorded fixtures. Live calls run only in
   authorized environments behind an explicit flag (see `scripts/smoke_nemotron.py`).
5. **Keep inputs small.** Send only what coaching needs: selected exercise/reference,
   validated metrics, deviations, rep intervals, visibility limits, deterministic
   scores, approved technique claims. No video, no face images, no full pose arrays.

## Minimal call shape (Python, OpenAI SDK)

```python
from openai import OpenAI
import os

client = OpenAI(
    base_url=os.environ["NEBIUS_BASE_URL"],      # .../v1
    api_key=os.environ["NEBIUS_API_KEY"],
)
resp = client.chat.completions.create(
    model=os.environ["NEBIUS_MODEL_ID"],         # discovered from catalog, not hardcoded
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT_V},   # versioned, neutral, JSON-only
        {"role": "user", "content": structured_evidence_json},
    ],
    temperature=0.2,
    max_tokens=400,
    # Prefer native structured output if the tested model supports it; otherwise
    # parse + validate JSON ourselves with one bounded repair attempt.
)
```

## Output grounding and validation (non-negotiable)

- Require 2–3 observations ONLY when that many distinct supported findings exist; allow
  fewer rather than fabricate issues.
- Every observation must cite valid `rep_ids` and `metric_ids` that exist in the input.
- Technique advice needs an approved claim/source ID; pure measurement descriptions may
  omit external sources if labelled as observations.
- Reject: medical diagnosis, invented numbers, unsupported causal claims (e.g. "fatigue
  caused this"), load/activation claims not observed.
- D010: torso-axis lean is not lumbar curvature; upper-arm motion is not muscle
  activation or measured scapular depression. Tracking predictions and filled gaps
  cannot justify observed-motion claims. Preserve unsupported/missing metric reasons.
- Validate types, allowed IDs, numeric values against inputs, bounded text lengths.
  Allow ONE bounded repair request. On failure → `status=unavailable`. Never regenerate
  scores.
- Record model ID, prompt version, latency, token usage, validation status. Do NOT
  retain sensitive prompts by default.

## Gate A checklist (prove it works once)

A model-list response proves catalog access only. A completion response with empty
final content proves transport, not usable coaching. Inspect finish reason/usage and
validate nonempty schema-correct output within the approved total token/time budget;
do not increase budgets repeatedly to chase a green smoke result.

- [ ] List models the key can access; pick the smallest NVIDIA Nemotron.
- [ ] One real chat completion returns parseable JSON matching the coaching schema.
- [ ] Record model ID, latency, token usage → DECISIONS.md D004.
- [ ] Confirm failure path returns `unavailable` cleanly (simulate a timeout).
