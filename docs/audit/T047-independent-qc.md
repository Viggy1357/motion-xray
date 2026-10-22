# T047 Independent Targeted QC — Retention, Artifact Streams, Scoring

Scope: targeted edge-regression review of `services/api/app/retention.py`,
`services/api/app/artifact_streams.py`, `packages/scoring/scoring/components.py`.
Source read-only; no gates weakened. New tests drafted in
`tests/unit/test_t047_qc.py` (8 cases, reusing `_committed` from
`tests/unit/test_retention.py`).

**Tests were drafted, not executed. Author acceptance pending test execution.**

**Final author outcome22 October:** the retry defect below was fixed with a durable
private cleanup receipt. The final10 independent edge tests run within the767 passing
full-suite cases. The generated reproduction's FD path, overflowing-band fixture and
database lookup/write-failure setup needed bounded corrections before they exercised
their intended cases. Original findings below remain a dated review, not open defects.

## Findings

### F1 (HIGH, real bug): partial `rmtree` failure after manifest deletion leaves an unretryable residual
In `cleanup_once` step 2 (expired job path), `_rmtree_dir` deletes the attempt
directory contents including `manifest.json`. If `shutil.rmtree` raises
`OSError` partway (after the manifest is gone), the `UPDATE jobs SET deleted=1`
never runs. On retry, `_validate_manifest` raises `FileNotFoundError`, and the
skip-silently branch requires `job["deleted"] and expired` — false because the
job was never marked deleted — so the job is counted `deferred` forever and the
remaining payload files (proxy, frames) are never reclaimed. Reproduced by
`test_partial_rmtree_failure_leaves_unretryable_residual` (monkeypatched rmtree
deletes manifest then raises; second run with healthy rmtree still defers and
`proxy/proxy.mp4` remains). Suggested direction (no fix applied): treat
"manifest missing + expired" as retryable attempt-dir removal, or mark the job
deleted before/atomically with the rmtree attempt.

### F2 (informational, not a bug): cancelled/deleted jobs with unknown process reaping
Step 3 defers `deleted=1 AND state='cancelled' AND result_key IS NULL` jobs.
This is intentional conservative scope (documented in module docstring), not a
defect. No test added.

### F3 (informational): LIVE writer / FAILED stale lease
Supervisor code marking jobs failed vs. process reaping is not in the provided
context; per instructions, no speculation and no test.

## Verified-correct behaviors covered by new tests
- Malformed `frames_artifact_key` in an otherwise valid manifest -> validation
  returns None, deferred, `request.json` and payloads preserved
  (`test_malformed_frames_key_preserves_request_json`).
- Symlink ancestor in raw `storage_key` (`link/secret.mp4` through a symlinked
  dir) -> `O_NOFOLLOW` open fails, error counted, outside file untouched
  (`test_symlink_ancestor_raw_key_outside_untouched`).
- Symlinked subdir inside an attempt dir during report-TTL rmtree -> symlink
  target outside the attempt is not followed/destroyed
  (`test_symlink_ancestor_attempt_path_untouched`).
- Malformed manifest parsed repeatedly -> no FD leak (`/proc/self/fd` stable
  across 10 runs; `_validate_manifest` closes dir fd in `finally` and uses
  `os.fdopen` context for the manifest fd)
  (`test_malformed_manifest_no_fd_leak_repeated`).
- Scoring: `unknown` comparability with overflowing deviation ->
  `non_finite_deviation`, no Inf in any field
  (`test_unknown_comparability_overflow_no_inf`).
- Scoring: band/context view mismatch -> flagged `incompatible`, descriptive
  deltas only, `score=None`, `valid_technique_score=None`
  (`test_view_mismatch_descriptive_not_scored`).
- Scoring: owner-prototype band scores as
  `owner_reviewed_reference_similarity`, never a technique claim
  (`test_owner_prototype_score_kind_and_no_technique_claim`).

## Streaming (`artifact_streams.py`) notes
- Ownership/auth, hash binding (proxy sha256, pose key-embedded hash,
  timestamp-map equality), manifest provenance binding, mid-stream recheck,
  and close-before-iteration all read as correct.
- Root TOCTOU: `_open_secure` rejects symlinked root ancestors and uses
  `O_NOFOLLOW` per segment; residual risk is local-trusted-filesystem only,
  not a remote threat. Binding assessed safe; recorded per instructions.
- No new streaming tests drafted: the integration fixture helpers
  (`tests/integration/test_artifact_streams`) were not included in the
  read-only context, so rather than guess their signatures, streaming coverage
  is deferred to the author. Refusal preferred over a guessed test.

## Acceptance
Pending: author executes `pytest tests/unit/test_t047_qc.py` (plus existing
130-test suite) and confirms F1 reproduction before any source change.
