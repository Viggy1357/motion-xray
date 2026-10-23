# HM-PERF02 — resize-only and lost-cycle diagnosis

23 October2026 · FR04/05/07/08/12. User approved the next resize-only test.
Delivery/pose project skills and D009/D010 apply; previous sources/configs reused.
No production code, threshold, score or reference configuration changed.

| Recipe | Pose wall time | Complete cycles | Experimental resemblance |
| --- | --- | --- | --- |
| Original1080x1920/30Hz | 57.1115s | 2 | 81.6497 |
| 720x1280/30Hz | 33.6981s | 1 | 90.7500 |
| 720x1280/15Hz | 20.0565s | 1 | 87.4161 |

Original and15Hz timings/artifacts reused from HM-PERF01. New resize30 run uses the
same exact encoded720p file, full MediaPipe checkpoint, visibility0.6, and0..20.65s.
Resize30 is1.695x faster (41.0% less provider time);15Hz reduces provider time another
40.5% relative to resize30. Single sequential runs, not a statistically controlled
benchmark. Conversion, upload, queue and proxy time excluded. Resizing and reencoding
remain combined; cannot attribute the first speed difference to file size alone.

## Why the second cycle disappeared

Existing `find_cycles` resets state on **every missing angle**, separately from its
0.1s maximum timestamp-gap check. A short missing observation is not bridged.

Original second cycle has anchors16.435s (high),19.201667s (low),20.068333s (return).
Resize30 loses valid elbow observations at16.9s,17.0s and18.6s. It establishes a new
high plateau17.033333..18.5s, but the18.6s missing observation discards that anchor.
Then low19.166667..19.433333s and high20.033333..20.3s are observed for long enough,
but the earlier high is gone, so no complete HIGH-LOW-HIGH is accepted.

The15Hz recipe likewise loses the high anchor at18.6s. Original nearest18.601667s
has valid right shoulder/elbow/wrist; all three are invalid with null native quality
in both720p artifacts at18.6s. This establishes an observation dropout, not its
perception cause: it may be no detection or ambiguous/multiple detections; raw model
responses were not retained. It must not be described as a proven confidence dip or
as the user failing a rep. Earlier original cycle8.47..11.03s survives both recipes.

Additional local diagnostic: hold original angles fixed and select nearest samples
at the15Hz recipe timestamps (unique matches asserted). Existing detector yields3
cycles, including the previously lost second cycle. Removing samples alone therefore
does not explain this loss. It can even skip missing samples and change cycle counts;
this is not evidence that15Hz inference is equivalent or universally better.

## Interpretation

The strict segmentation logic is sensitive to a single perception dropout. The high
score after resizing describes a changed one-cycle subset against unchanged reference
bands, not improved technique/accuracy. Keep current production defaults. A future
bounded investigation can propose gap-aware segmentation using actual observed phase
anchors and explicit missing coverage; do not fabricate/interpolate missing anatomy
or silently weaken existing thresholds. Version policy and fixtures before adoption.

## Reproduction and verification

Use the existing720p file and original/optimized artifacts from HM-PERF01. Inside
`motion-xray-worker`, repo mounted `/workspace`, current contracts/providers on
PYTHONPATH:

```sh
python scripts/pose_smoke.py --video artifacts/perf01/curl-720.mp4 \
  --source-root /workspace --checkpoint /workspace/models/pose_landmarker_full.task \
  --output-dir /workspace/artifacts/perf01/resize30 --start-s 0 --duration-s 20.65
```

Unmodified CLI runs30Hz; new output620samples (original619 due actual timestamp
selection), same620 decoded source frames preserved from prior PTS check. Local
aggregate glue `artifacts/development/perf02_trace.py` invokes existing profile/report
and cycle functions, joins real timestamps, and reports contiguous high/low/middle/
missing runs. Hash-checked pose artifacts and generated reports stayed local.
Published `HM-PERF02-comparison.json` contains aggregate cycle anchors/threshold runs,
not joints or private media. Container inference and comparison exited0; document
whitespace check passes. No production build/test required for evidence-only changes.

No new paid calls: previous Nebius draft timeout remains in HM-PERF01 ledger; existing
tools suffice for this incremental diagnostic. No model sees private videos/pose.
