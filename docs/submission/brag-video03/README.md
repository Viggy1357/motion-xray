# Motion X Ray — local submission film

Finished local draft: `brag-output-20261027-submission/motion-xray-submission.mp4`.
Exactly **2:30**: 30s Milo teaser + 100s recorded walkthrough + 20s planned future.
1920×1080, 30fps, H.264/AAC. Captioned with music; no voice narration.
Standalone `walkthrough.mp4` and `future.mp4` are in the same output directory.
Nothing has been published or submitted. Owner-approved workout media stays local and outside Git.

## What is real

The walkthrough continuously records the app uploading the approved lat-pulldown clip,
processing it, displaying its measured report, replaying a segment and requesting coaching.
No mocked API, seeded result or fabricated coaching response was used.
The processing wait was about 88 seconds; the edit condenses that section to 15 seconds,
explicitly labelled on screen. The raw successful recording lasts about 178 seconds.
Reference estimates remain provisional, missing measurements unavailable, and signal
visibility is not claimed to be measurement accuracy.

The single owner-authorized paid coaching call returned `unavailable`: the runtime model
response failed local validation (`unvalidated`). That outcome is shown and labelled honestly.
No additional call was made. A separate coaching-validation repair is still needed before
claiming a successful coaching demonstration. The future section is explicitly PLANNED;
the compact camera is a concept illustration.

## Edit and reproduce

The existing 30s teaser is preserved unchanged; see `../brag-video02/` for its source.
This folder contains walkthrough/future HTML, the Playwright recorder and trim filter.
Use the pinned Docker wrapper only; see `../../BRAG-QUICKSTART.md` for setup.

```sh
BRAG_OUTPUT_DIR=brag-output-20261027-submission ./scripts/brag.sh preview
BRAG_OUTPUT_DIR=brag-output-20261027-submission ./scripts/brag.sh check --json
BRAG_OUTPUT_DIR=brag-output-20261027-submission ./scripts/brag.sh render --fps 30 --workers 2 --quality delivery --output ../walkthrough.mp4
```

For a new checkout, initialise separate Brag output directories and copy each `source/`
subdirectory into its corresponding `composition/`. Restore the local assets listed in
`assets-manifest.json`; init supplies local GSAP. Private recording files are deliberately
excluded, so the HTML alone does not reproduce the real walkthrough without the approved
local media. The recorder expects the existing browser-QC image, mounted input/output,
backend Docker network and explicit `ALLOW_ONE_COACHING_CALL=1` for any future paid call.
Do not rerun that paid call under the already-consumed authorization.

## Credits and QC

Music: Sascha Ende, https://ende.app, CC BY 4.0, Happy Beats / Business Moves
Vol. 1 (walkthrough) and Vol. 11 (teaser/future), excerpts with gain/fades.
Kenney effects: CC0. Retain music attribution when sharing; final card includes it.
Milo uses the existing app artwork. Teaser motions illustrate the product vision.

Visual samples from the final encoded MP4 were inspected. Final video has 4,500 frames,
150.000s duration and 48kHz AAC; peak audio −5.0dBFS. Walkthrough check passed with
zero errors and 16 editability/timing-density warnings; future check passed without
lint/runtime/layout/contrast issues. Those checks do not prove clinical or coaching accuracy.
Evidence: `../../audit/BRAG-VIDEO03-evidence.json`.
Development usage: `../../development-usage-BRAG-VIDEO03-2026-10-27.json`.
