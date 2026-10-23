# HM-PERF01 — one-video speed experiment

23 October2026 · FR04/05/07/08/12. User authorizes one-video test using Nebius.
No production configuration, reference bands or thresholds changed.

## Result

| Measure | Original | Smaller analysis copy |
| --- | --- | --- |
| Display resolution | 1080x1920 | 720x1280 |
| Actual sampling | 29.95Hz | 15Hz |
| Pose provider wall time | 57.1115s | 20.0565s |
| Input bytes | 46,008,563 | 8,889,760 |
| Analysed frames | 619 | 310 |
| Right elbow observed coverage | 98.71% | 96.77% |
| Usable complete cycles | 2 | 1 |
| Experimental resemblance | 81.6497 | 87.4161 |

Inference speedup2.8475x;65% less pose-processing time. This excludes preparation,
playback proxy, queue, upload and report timing. Conversion timing was not captured.
The comparison used the same existing unreviewed reference bands: scores here are
sensitivity diagnostics, not recalibrated technique scores. A higher score does not
mean the faster recipe is more accurate; fewer cycles are contributing.

Timestamp-nearest paired right-arm observations (<=40ms) give mean/p95/max absolute
estimated3D elbow differences2.53/7.13/20.96degrees over296 valid pairs. Projected2D
elbow2.19/4.94/43.23degrees. Torso-axis mean0.665/p951.85degrees. Right arm is the
visible assessment side; left arm is mostly occluded and was not used to conclude
agreement. Confidence masks do not establish true anatomical accuracy.

Decision: **keep current defaults**. Next useful experiment is resize-only at30Hz,
isolating the spatial change before reducing temporal sampling. A future adopted
recipe needs all exercises/references recalibrated and regression checked.

## Method and checks

Existing `scripts/pose_smoke.py` and MediaPipe full checkpoint, one sequential run per
recipe in `motion-xray-worker`, no concurrent benchmark workers. Existing adapter,
visibility0.6 and measurement thresholds unchanged. This tests0..20.65s of the
20.653333s curl input. Original620 decoded frame timestamps versus converted620,
max difference0.001667s; no FPS conversion/interpolation. Original portrait rotation
-90 converted to upright720x1280, aspect preserved. Same checkpoint SHA recorded in
comparison JSON. Candidate libx264 CRF18/veryfast; audio omitted in analysis copy.

Both container inference commands and aggregate comparison exited0. Hash-checked
pose frames were passed through existing `build_exercise_report` and
`apply_reference_assessment`. Measurements used displayed dimensions after rotation.
Pairs joined by nearest actual timestamp; missing observations excluded, not imputed.
Coverage denominators are each recipe's actual samples, not identical frame counts.

This single unreplicated comparison combines resizing, encoding and sampling changes;
it does not isolate their effects or provide a ground-truth accuracy claim. Baseline
perception itself is provisional. No production tests/build needed: only task/audit
and usage documents changed. Local media, pose arrays, HTML and reports remain ignored.

## Reproduction

Inside the existing worker image, repository mounted at `/workspace`, current source
packages on PYTHONPATH:

```sh
ffmpeg -v error -i 'data/demo/Bicep Curls.MOV' -map 0:v:0 -an -sn \
  -vf 'scale=720:1280:force_original_aspect_ratio=decrease:force_divisible_by=2' \
  -c:v libx264 -crf 18 -preset veryfast -fps_mode passthrough \
  artifacts/perf01/curl-720.mp4
python scripts/pose_smoke.py --video 'data/demo/Bicep Curls.MOV' \
  --source-root /workspace --checkpoint /workspace/models/pose_landmarker_full.task \
  --output-dir /workspace/artifacts/perf01/original --start-s 0 --duration-s 20.65
sed 's/sample_rate_hz=30,/sample_rate_hz=15,/' scripts/pose_smoke.py > /tmp/perf01-smoke15.py
python /tmp/perf01-smoke15.py --video artifacts/perf01/curl-720.mp4 \
  --source-root /workspace --checkpoint /workspace/models/pose_landmarker_full.task \
  --output-dir /workspace/artifacts/perf01/optimized --start-s 0 --duration-s 20.65
```

Directory must exist and output file must not already exist for fresh conversion.
Original diagnostic remains unchanged; rate edit applies only to temporary copy.
Local comparison glue is `artifacts/development/perf01_compare.py`; published aggregate
is `HM-PERF01-comparison.json`, containing timings, masks, actual rates and angle deltas.

## Delegation/accounting

One bounded source-only Nebius Kimi-K2.7-Code call timed out at600s before returning
any code. No retry or accepted draft. Last streamed22,336tokens, conservative guard
$0.204624 (not final invoice); maximum$0.459417 reservation retained for uncertain
final usage. Existing tools reused rather than a large replacement implementation.
Private footage/pose and credentials never sent to coding model. No runtime model,
Tavily or hosting spend. Separate usage ledger preserves failure and maximum exposure.
