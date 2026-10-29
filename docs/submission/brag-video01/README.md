# Motion X Ray teaser

25-second, 1920×1080, 30fps Brag film based on app commit `4f7adb2`.
An animated UI recreation with the actual athlete and Pip artwork, music and SFX.
It contains no workout footage, measured result, voiceover or real-time speed claim.
This teaser complements the permissioned runtime walkthrough in `../DEMO-SCRIPT.md`;
it does not replace that demonstration. Nothing was published.

Local output: `brag-output-20261025-film/brag.mp4`, poster `brag.jpg`.
The output directory is gitignored; editable source and asset hashes are retained here.
Checks and export metadata: `../../audit/BRAG-VIDEO01-evidence.json`.

To edit, run from the repository root:

```sh
BRAG_OUTPUT_DIR=brag-output-20261025-film ./scripts/brag.sh preview
```

Open `http://localhost:4173/#project/composition`. The preview stays local.
Stop with Ctrl+C. The HyperFrames desktop app is optional for further editing.

To reconstruct after a fresh checkout, install the pinned local skills and renderer
according to `../../BRAG-QUICKSTART.md`. Initialise a fresh `brag-output-*` folder
with the wrapper, copy `source/` into its `composition/`, then copy only the assets
listed in `assets-manifest.json` to the indicated names. Scaffold init already copies
the pinned GSAP vendor file. Run `check --json`, inspect snapshots and preview, then
`render --fps 30 --workers 2 --quality delivery --output ../brag.mp4` through the same
wrapper with the chosen `BRAG_OUTPUT_DIR`. Never use host npm, Node or FFmpeg.

The wrapper now sets `TMPDIR=/work` so scratch files use the output-only mount rather
than the small RAM-backed `/tmp`. Rendering remains offline with a read-only root.

Music: Sascha Ende, [ende.app](https://ende.app), CC BY 4.0;
Happy Beats / Business Moves Vol. 12, excerpt with fades and lowered gain.
SFX: Kenney, CC0. App illustration assets retain their existing project provenance.
Keep the music attribution in captions when sharing. Review the final film before
publication; public upload and submission remain owner actions.
