import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { prepareInit } from './prepare-init.mjs';

const CDN = '<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>';
const LOCAL = '<script src="assets/vendor/gsap.min.js"></script>';

function setup(html) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pi-'));
  const vendor = path.join(dir, 'vendor-src.js');
  fs.writeFileSync(vendor, '/* gsap 3.15.0 vendored */');
  const proj = path.join(dir, 'proj');
  fs.mkdirSync(proj);
  fs.writeFileSync(path.join(proj, 'index.html'), html);
  return { dir, proj, vendor };
}
const page = (extra = '') => `<!doctype html><html><head>${CDN}</head><body>${extra}</body></html>`;

test('replaces CDN script and copies vendor', () => {
  const { proj, vendor } = setup(page('<div id="app">keep me</div>'));
  const r = prepareInit(proj, { vendorPath: vendor });
  assert.equal(r.changed, true);
  const html = fs.readFileSync(path.join(proj, 'index.html'), 'utf8');
  assert.ok(html.includes(LOCAL));
  assert.ok(!html.includes(CDN));
  assert.ok(html.includes('<div id="app">keep me</div>'));
  assert.equal(fs.readFileSync(path.join(proj, 'assets/vendor/gsap.min.js'), 'utf8'),
    fs.readFileSync(vendor, 'utf8'));
});

test('idempotent second run', () => {
  const { proj, vendor } = setup(page());
  prepareInit(proj, { vendorPath: vendor });
  const r = prepareInit(proj, { vendorPath: vendor });
  assert.equal(r.changed, false);
});

test('rejects missing vendor', () => {
  const { proj } = setup(page());
  assert.throws(() => prepareInit(proj, { vendorPath: path.join(proj, 'nope.js') }), /vendor gsap missing/);
});

test('fails closed on unknown template', () => {
  const { proj, vendor } = setup('<html><head><script src="https://other.cdn/x.js"></script></head></html>');
  assert.throws(() => prepareInit(proj, { vendorPath: vendor }), /unknown template/);
});

test('rejects missing index.html', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pi-'));
  const vendor = path.join(dir, 'v.js');
  fs.writeFileSync(vendor, 'x');
  assert.throws(() => prepareInit(dir, { vendorPath: vendor }), /index.html missing/);
});

test('rejects symlinked index.html', () => {
  const { dir, proj, vendor } = setup(page());
  const outside = path.join(dir, 'outside.html');
  fs.writeFileSync(outside, page());
  fs.rmSync(path.join(proj, 'index.html'));
  fs.symlinkSync(outside, path.join(proj, 'index.html'));
  assert.throws(() => prepareInit(proj, { vendorPath: vendor }), /symlink/);
});

test('rejects symlinked assets dir escape', () => {
  const { dir, proj, vendor } = setup(page());
  const outside = path.join(dir, 'escape');
  fs.mkdirSync(outside);
  fs.symlinkSync(outside, path.join(proj, 'assets'));
  assert.throws(() => prepareInit(proj, { vendorPath: vendor }), /symlink/);
  assert.ok(!fs.existsSync(path.join(outside, 'vendor/gsap.min.js')));
});

test('guard prefix added once to AGENTS.md/CLAUDE.md, content kept', () => {
  const { proj, vendor } = setup(page());
  fs.writeFileSync(path.join(proj, 'AGENTS.md'), 'upstream instructions\n');
  fs.writeFileSync(path.join(proj, 'CLAUDE.md'), 'claude upstream\n');
  prepareInit(proj, { vendorPath: vendor });
  prepareInit(proj, { vendorPath: vendor });
  const a = fs.readFileSync(path.join(proj, 'AGENTS.md'), 'utf8');
  assert.ok(a.startsWith('<!-- brag: offline pinned image'));
  assert.ok(a.includes('upstream instructions'));
  assert.equal(a.match(/brag: offline/g).length, 1);
  assert.ok(fs.readFileSync(path.join(proj, 'CLAUDE.md'), 'utf8').includes('claude upstream'));
});

test('rejects vendor source equal to destination', () => {
  const { proj, vendor } = setup(page());
  fs.mkdirSync(path.join(proj, 'assets/vendor'), { recursive: true });
  const dest = path.join(proj, 'assets/vendor/gsap.min.js');
  fs.copyFileSync(vendor, dest);
  assert.throws(() => prepareInit(proj, { vendorPath: dest }), /equals destination/);
});
