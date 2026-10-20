# T20 — Project guidance synchronization

20 October 2026, Malaysia time. Documentation completion, not pipeline completion.

## Changes

- Recorded D009 selective upstream reuse and D010 measurement/alignment semantics.
- Routed active product/architecture/agent guidance to the source review and adoption
  gates; retained MediaPipe primary and lat pulldown first.
- Assigned T19 follow-ups to T04/T05/T06/T07/T13 in TASKS and DELIVERY, including
  artifact/signal interfaces, phase calibration, typed alignment, reference provenance
  and deployment-realistic evaluation.
- Documented planned contract/API changes without editing schemas or generated clients.
- Corrected stale three-exercise/curl-first statements and unsupported activation
  interpretations. Lat-pulldown YAML changes are comments only.
- Updated operations and pose runtime guidance with conditional experiment boundaries,
  dependency/terms checks and observed-versus-predicted joint handling.
- Updated all four project skills. No Addy Osmani pack skills loaded or modified.

## Verification

1. `./scripts/test.sh python` through the repository container entrypoint: exit 0.
   Ruff clean; mypy clean over 36 source files; 61 tests pass. One existing Starlette/
   AnyIO deprecation warning. Provider smoke scripts remain dry-run with no credentials
   or network calls; their output is not model validation.
2. Read-only check in the same offline Python Compose service: 18 modified Markdown
   files pass local-link and fenced-block checks; core guidance contains integration
   routing; PyYAML-parsed lat-pulldown config equals the pre-change HEAD version.
3. `git diff --check`: clean. Application/generated/archived paths are not modified.

Docker required access to its builder metadata outside the workspace sandbox; the
check succeeded with the permitted container execution. No host project runtime was
installed. No frontend rebuild was needed for documentation and config comments.

## Remaining work

T01/T04 real pose artifact is still next. D009 candidates are not installed or
runtime-validated. T05–T07 interfaces, algorithms, references and scored outputs remain
implementation work. No metric accuracy or performance gain is claimed here.
