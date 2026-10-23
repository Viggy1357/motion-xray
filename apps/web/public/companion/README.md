# Illustrative companion assets

- `athlete.png`: original artwork generated for Motion X-Ray using the built-in
  image-generation tool on 23 October 2026. Generic adult athlete in blue sportswear;
  no uploaded person/photo or private analysis footage was used. Static transparent
  PNG, 1024 × 1536, approximately 1.4 MiB. Retain this provenance when replacing it.
- `athlete.js` and `index.html`: original procedural, sports-clad illustrative body
  map. This is a separate optional interactive object, not the model depicted in
  the PNG and not a reconstruction of the user.
- The map imports the existing local Three.js 0.170.0 module at
  `/ui-draft/vendor/three.module.min.js`. Its MIT notice remains in
  `../ui-draft/vendor/THREE-LICENSE.txt`; upstream details are in that folder's
  README. No new package or remote CDN is required.

Artwork budget for this iteration: one poster below 1.5 MiB and one optional map.
The map mounts only when opened, honours reduced motion, and disposes its renderer
when removed. These are asset/implementation bounds, not a measured mobile FPS or
Core Web Vitals certification. A high-quality rotatable athlete mesh is future art
work; do not add rotation controls to the poster or imply measured muscle growth.
