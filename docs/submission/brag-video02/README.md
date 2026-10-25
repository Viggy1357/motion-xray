# Meet Milo — launch film

Local deliverable: `brag-output-20261025-milo/milo-launch.mp4`.
Poster: `milo-poster.jpg` in the same directory. 30 seconds of video, 1080p, 30fps,
H.264 with AAC music and effects; no narration. The earlier teaser remains intact.

Story: training alone → Meet Milo → choose/upload/review → Motion X Ray.
Milo uses the existing layered 2D artwork with travel, hops and head tilts created
for the film. These movements do not add walking or cross-screen behaviour to the app.
The gym and replay are illustrations; no private workout video or measured result
appears. Processing is visibly condensed. Nothing was published.

The real walkthrough and future closing are drafted in
[MILO-WALKTHROUGH-DRAFT.md](../MILO-WALKTHROUGH-DRAFT.md):
30s teaser + 100s walkthrough + 20s future = **2:30 planned combined runtime**.
Only the teaser has been rendered. The walkthrough needs the owner's selected clip
for public capture; the roadmap must stay labelled Planned.

## Edit or reproduce

From the project root:

```sh
BRAG_OUTPUT_DIR=brag-output-20261025-milo ./scripts/brag.sh preview
```

Open `http://localhost:4173/#project/composition`. Milo has his own transparent
composition and paused timeline. Stop the preview with Ctrl+C. The optional
HyperFrames desktop app can also be used for further editing.

For a fresh checkout, follow `../../BRAG-QUICKSTART.md`, initialise a new
`brag-output-*` directory with the wrapper, copy `source/` into its `composition/`,
and copy the assets from the source paths in `assets-manifest.json`. Init supplies
the pinned local GSAP vendor file. Use the same output basename for all commands.
Run `check --json`, inspect snapshots, preview, then render through the wrapper:

```sh
BRAG_OUTPUT_DIR=brag-output-20261025-milo ./scripts/brag.sh render --fps 30 --workers 2 --quality delivery --output ../milo-launch.raw.mp4
```

The delivered file also replaces frame zero with the settled 6.5s poster, preserving
900 frames and soundtrack timing. MP4 and source assets stay in the ignored output
directory; editable composition files, hashes and evidence are versioned here.
No host runtime, new dependency, external media generator or product-runtime call
was used. Renderer isolation is unchanged.

## Credits

Music: Sascha Ende, [ende.app](https://ende.app), CC BY 4.0.
Happy Beats / Business Moves Vol. 11, 30s excerpt with fades and adjusted gain.
Kenney sound effects: CC0. App illustration provenance remains in the project.
Retain the music credit when sharing. The film contains its credit on the end card.

QC and export metadata: `../../audit/BRAG-VIDEO02-evidence.json`.
Usage: `../../development-usage-BRAG-VIDEO02-2026-10-25.json`.
