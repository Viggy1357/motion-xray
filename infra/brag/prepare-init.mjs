#!/usr/bin/env node
// prepare-init.mjs — offline post-init fixup for Hyperframes scaffolds.
// The pinned image vendors gsap 3.15.0 from the locked npm package
// (node_modules/hyperframes/dist/vendor/npm/gsap@3.15.0/dist/gsap.min.js).
// We knowingly use that exact vendored build instead of the CDN gsap@3.14.2
// script that `hyperframes init` emits, so no network is ever needed.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const CDN = '<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>';
const LOCAL = '<script src="assets/vendor/gsap.min.js"></script>';
const GUARD = '<!-- brag: offline pinned image; do not run host npx/npm upgrade commands. -->\n';
const VENDOR = '/opt/brag/node_modules/hyperframes/dist/vendor/npm/gsap@3.15.0/dist/gsap.min.js';

const sha = (p) => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const noSymlink = (p) => { if (fs.lstatSync(p).isSymbolicLink()) throw new Error(`refusing symlink: ${p}`); };

export function prepareInit(projectDir, { vendorPath = VENDOR } = {}) {
  const root = path.resolve(projectDir);
  const index = path.join(root, 'index.html');
  if (!fs.existsSync(index)) throw new Error(`index.html missing in ${root}`);
  noSymlink(index);
  if (!fs.existsSync(vendorPath)) throw new Error(`vendor gsap missing: ${vendorPath}`);
  const vendorDir = path.join(root, 'assets', 'vendor');
  const dest = path.join(vendorDir, 'gsap.min.js');
  if (path.resolve(vendorPath) === dest) throw new Error('vendor source equals destination');
  for (const p of [path.join(root, 'assets'), vendorDir, dest]) {
    if (fs.existsSync(p)) noSymlink(p);
  }
  let html = fs.readFileSync(index, 'utf8');
  const hasCdn = html.includes(CDN);
  const hasLocal = html.includes(LOCAL);
  if (!hasCdn && !hasLocal) throw new Error('expected gsap script tag not found; unknown template');
  if (hasLocal && fs.existsSync(dest) && sha(dest) === sha(vendorPath)) return { changed: false };
  fs.mkdirSync(vendorDir, { recursive: true });
  fs.copyFileSync(vendorPath, dest);
  if (hasCdn) {
    html = html.split(CDN).join(LOCAL); // preserve all other markup
    fs.writeFileSync(index, html);
  }
  for (const name of ['AGENTS.md', 'CLAUDE.md']) {
    const p = path.join(root, name);
    if (!fs.existsSync(p)) continue;
    noSymlink(p);
    const t = fs.readFileSync(p, 'utf8');
    if (!t.startsWith(GUARD)) fs.writeFileSync(p, GUARD + t);
  }
  return { changed: true };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  try {
    prepareInit(process.cwd());
  } catch (e) {
    console.error(`prepare-init: ${e.message}`);
    process.exit(1);
  }
}
