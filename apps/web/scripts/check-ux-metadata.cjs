#!/usr/bin/env node
'use strict';

/* Offline CJS unit tests for pure UX metadata + region logic.
 * Transpiles the TypeScript sources with the existing typescript package. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');

function loadTsModule(relPath) {
  const abs = path.join(__dirname, '..', relPath);
  const source = fs.readFileSync(abs, 'utf8');
  const js = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      jsx: ts.JsxEmit.ReactJSX,
      esModuleInterop: true,
    },
    fileName: abs,
  }).outputText;
  const mod = { exports: {} };
  const localRequire = (spec) => {
    if (spec === 'react') return require('react');
    // CSS module imports are inert in the Node harness: stub to an empty object.
    if (/\.css$/.test(spec)) return {};
    if (spec.startsWith('.')) {
      // Resolve relative TS imports (e.g. ../lib/ux-metadata).
      const resolved = path.join(path.dirname(relPath), spec).replace(/\\/g, '/');
      return loadTsModule(resolved.endsWith('.ts') || resolved.endsWith('.tsx') ? resolved : resolved + '.ts');
    }
    return require(spec);
  };
  const fn = new Function('require', 'module', 'exports', '__filename', '__dirname', js);
  fn(localRequire, mod, mod.exports, abs, path.dirname(abs));
  return mod.exports;
}

const ux = loadTsModule('app/lib/ux-metadata.ts');
const region = loadTsModule('app/components/RegionActivity.tsx');

function memStorage(initial) {
  const map = new Map(Object.entries(initial || {}));
  return {
    getItem: (k) => (map.has(k) ? map.get(k) : null),
    setItem: (k, v) => {
      map.set(k, String(v));
    },
    _map: map,
  };
}

function failingStorage(existing) {
  return {
    getItem: (k) => (k in existing ? existing[k] : null),
    setItem: () => {
      throw new Error('quota');
    },
  };
}

let passed = 0;
function test(name, fn) {
  try {
    fn();
    passed++;
    console.log('ok - ' + name);
  } catch (err) {
    console.error('FAIL - ' + name);
    console.error(err);
    process.exitCode = 1;
  }
}

// --- parse / defaults ---
test('defaults: goal off, null target, rolling7', () => {
  const d = ux.defaultUxMetadata();
  assert.equal(d.version, 1);
  assert.equal(d.goalEnabled, false);
  assert.equal(d.goalTarget, null);
  assert.equal(d.weekMode, 'rolling7');
  assert.deepEqual(d.viewed, {});
});

test('parse preserves unknown keys', () => {
  const raw = JSON.stringify({
    version: 1,
    goalEnabled: true,
    goalTarget: 4,
    weekMode: 'calendar',
    viewed: { a1: '2026-01-01T00:00:00.000Z' },
    futureField: { nested: [1, 2] },
  });
  const m = ux.parseUxMetadata(raw);
  assert.ok(m);
  assert.equal(m.goalEnabled, true);
  assert.equal(m.goalTarget, 4);
  assert.equal(m.weekMode, 'calendar');
  assert.deepEqual(m.futureField, { nested: [1, 2] });
  assert.equal(m.viewed.a1, '2026-01-01T00:00:00.000Z');
});

test('parse rejects corrupt JSON and unsupported version', () => {
  assert.equal(ux.parseUxMetadata('{not json'), null);
  assert.equal(ux.parseUxMetadata(JSON.stringify({ version: 2 })), null);
  assert.equal(ux.parseUxMetadata(JSON.stringify([1, 2])), null);
  assert.equal(ux.parseUxMetadata(null), null);
});

test('parse sanitizes invalid fields without dropping record', () => {
  const m = ux.parseUxMetadata(
    JSON.stringify({ version: 1, goalEnabled: 'yes', goalTarget: -3, weekMode: 'weekly', viewed: { a: 5, b: 'ok' } })
  );
  assert.ok(m);
  assert.equal(m.goalEnabled, false);
  assert.equal(m.goalTarget, null);
  assert.equal(m.weekMode, 'rolling7');
  assert.deepEqual(m.viewed, { b: 'ok' });
});

test('corrupt storage load keeps defaults and does not clear mxr.logs.v1', () => {
  const store = memStorage({ 'mxr.ux.v1': '{broken', 'mxr.logs.v1': '[{"id":1}]' });
  const { metadata, error } = ux.loadUxMetadata(store);
  assert.equal(metadata.goalEnabled, false);
  assert.ok(error);
  assert.equal(store.getItem('mxr.logs.v1'), '[{"id":1}]');
  assert.equal(store.getItem('mxr.ux.v1'), '{broken');
});

// --- validation ---
test('validateUxSettings', () => {
  assert.equal(ux.validateUxSettings({ goalEnabled: false, goalTarget: null, weekMode: 'rolling7' }), true);
  assert.equal(ux.validateUxSettings({ goalEnabled: true, goalTarget: 3, weekMode: 'calendar' }), true);
  assert.equal(ux.validateUxSettings({ goalEnabled: true, goalTarget: null, weekMode: 'rolling7' }), false);
  assert.equal(ux.validateUxSettings({ goalEnabled: true, goalTarget: 2.5, weekMode: 'rolling7' }), false);
  assert.equal(ux.validateUxSettings({ goalEnabled: false, goalTarget: null, weekMode: 'weekly' }), false);
});

// --- persistence ---
test('persist success writes merged record preserving unknown keys', () => {
  const store = memStorage();
  const meta = ux.applyUxSettings(
    { ...ux.defaultUxMetadata(), customKey: 'keep' },
    { goalEnabled: true, goalTarget: 5, weekMode: 'calendar' }
  );
  assert.equal(ux.persistUxMetadata(meta, store), true);
  const back = ux.parseUxMetadata(store.getItem('mxr.ux.v1'));
  assert.equal(back.goalEnabled, true);
  assert.equal(back.goalTarget, 5);
  assert.equal(back.customKey, 'keep');
});

test('persist failure returns false and preserves existing record', () => {
  const existing = { 'mxr.ux.v1': JSON.stringify(ux.defaultUxMetadata()) };
  const store = failingStorage(existing);
  const meta = ux.applyUxSettings(ux.defaultUxMetadata(), {
    goalEnabled: true,
    goalTarget: 9,
    weekMode: 'calendar',
  });
  assert.equal(ux.persistUxMetadata(meta, store), false);
});

test('disabling goal clears target', () => {
  const meta = ux.applyUxSettings(ux.defaultUxMetadata(), {
    goalEnabled: false,
    goalTarget: 7,
    weekMode: 'rolling7',
  });
  assert.equal(meta.goalTarget, null);
});

test('withViewed records timestamp immutably', () => {
  const base = ux.defaultUxMetadata();
  const next = ux.withViewed(base, 'abc', '2026-02-01T00:00:00.000Z');
  assert.equal(next.viewed.abc, '2026-02-01T00:00:00.000Z');
  assert.deepEqual(base.viewed, {});
});

// --- region activity ---
test('primary region mapping', () => {
  assert.equal(region.primaryRegionForExercise('lat_pulldown'), 'back');
  assert.equal(region.primaryRegionForExercise('dumbbell_curl'), 'arms');
  assert.equal(region.primaryRegionForExercise('squat'), 'legs');
  assert.equal(region.primaryRegionForExercise('incline_chest_press'), 'chest');
  assert.equal(region.primaryRegionForExercise('other'), null);
});

test('eligibility requires exact matching proof', () => {
  const good = {
    analysisId: 'a1',
    exercise: 'squat',
    recognition: { analysisId: 'a1', exercise: 'squat' },
  };
  assert.equal(region.isEligibleSet(good), true);
  assert.equal(region.isEligibleSet({ ...good, recognition: { analysisId: 'a2', exercise: 'squat' } }), false);
  assert.equal(region.isEligibleSet({ ...good, recognition: { analysisId: 'a1', exercise: 'lat_pulldown' } }), false);
  assert.equal(region.isEligibleSet({ analysisId: null, exercise: 'squat' }), false);
  // Legacy record with recognitionVersion but no proof: no retrospective credit.
  assert.equal(region.isEligibleSet({ analysisId: 'a9', exercise: 'squat', recognitionVersion: '1' }), false);
});

test('region counts dedupe by analysisId and skip ineligible', () => {
  const sets = [
    { analysisId: 'a1', exercise: 'squat', recognition: { analysisId: 'a1', exercise: 'squat' } },
    { analysisId: 'a1', exercise: 'squat', recognition: { analysisId: 'a1', exercise: 'squat' } }, // dup
    { analysisId: 'a2', exercise: 'lat_pulldown', recognition: { analysisId: 'a2', exercise: 'lat_pulldown' } },
    { analysisId: 'a3', exercise: 'dumbbell_curl' }, // no proof
    { analysisId: 'a4', exercise: 'unknown', recognition: { analysisId: 'a4', exercise: 'unknown' } },
  ];
  const counts = region.countByRegion(sets);
  assert.deepEqual(counts, { back: 1, arms: 0, legs: 1, chest: 0 });
});

console.log(passed + ' tests passed');
if (process.exitCode) process.exit(process.exitCode);
