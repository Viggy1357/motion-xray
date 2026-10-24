#!/usr/bin/env node
'use strict';

/* Offline CJS unit tests for the pure coaching-session cache logic.
 * Transpiles TypeScript with the existing typescript package; stubs react. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');

const reactStub = {
  useState: (init) => [typeof init === 'function' ? init() : init, () => {}],
  useEffect: () => {},
  useRef: (v) => ({ current: v }),
};

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
    if (spec === 'react') return reactStub;
    if (/\.css$/.test(spec)) return {};
    if (spec.startsWith('.')) {
      const resolved = path.join(path.dirname(relPath), spec).replace(/\\/g, '/');
      return loadTsModule(resolved.endsWith('.ts') || resolved.endsWith('.tsx') ? resolved : resolved + '.ts');
    }
    return require(spec);
  };
  const fn = new Function('require', 'module', 'exports', '__filename', '__dirname', js);
  fn(localRequire, mod, mod.exports, abs, path.dirname(abs));
  return mod.exports;
}

const cs = loadTsModule('app/lib/coaching-session.ts');

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

const REPS = [
  { ordinal: 1, start_s: 2.5 },
  { ordinal: 3, start_s: 12.75 },
];

function okResult(over) {
  return Object.assign(
    {
      status: 'ok',
      summary: 'Actual summary string.',
      observations: ['Segment 3 (12.75s): actual observation text.'],
      next_set_cue: 'Actual next set cue.',
      limitations: [],
    },
    over || {}
  );
}

test('stores and reads actual strings with validated segment mapping', () => {
  cs.clearSessionCoaching();
  cs.storeSessionCoaching('a1', 'squat', okResult(), REPS);
  const v = cs.readSessionCoaching('a1');
  assert.ok(v);
  assert.equal(v.analysisId, 'a1');
  assert.equal(v.exercise, 'squat');
  assert.equal(v.observation, 'Segment 3 (12.75s): actual observation text.');
  assert.equal(v.nextSetCue, 'Actual next set cue.');
  assert.equal(v.segmentOrdinal, 3);
  assert.equal(v.sourceS, 12.75);
});

test('invalid status is not cached and clears existing slot', () => {
  cs.clearSessionCoaching();
  cs.storeSessionCoaching('a2', 'squat', okResult(), REPS);
  assert.ok(cs.readSessionCoaching('a2'));
  cs.storeSessionCoaching('a2', 'squat', okResult({ status: 'unavailable' }), REPS);
  assert.equal(cs.readSessionCoaching('a2'), null);
});

test('null cue stays null; never invented', () => {
  cs.clearSessionCoaching();
  cs.storeSessionCoaching('a3', 'squat', okResult({ next_set_cue: null }), REPS);
  const v = cs.readSessionCoaching('a3');
  assert.ok(v);
  assert.equal(v.nextSetCue, null);
  assert.equal(v.observation, 'Segment 3 (12.75s): actual observation text.');
});

test('strict prefix: missing prefix yields no replay association', () => {
  cs.clearSessionCoaching();
  cs.storeSessionCoaching('a4', 'squat', okResult({ observations: ['No prefix observation.'] }), REPS);
  const v = cs.readSessionCoaching('a4');
  assert.ok(v);
  assert.equal(v.observation, 'No prefix observation.');
  assert.equal(v.segmentOrdinal, null);
  assert.equal(v.sourceS, null);
});

test('mismatched ordinal yields no replay association', () => {
  cs.clearSessionCoaching();
  cs.storeSessionCoaching('a5', 'squat', okResult({ observations: ['Segment 9 (1.0s): not a real rep.'] }), REPS);
  const v = cs.readSessionCoaching('a5');
  assert.ok(v);
  assert.equal(v.segmentOrdinal, null);
  assert.equal(v.sourceS, null);
});

test('non-finite rep start_s is not matched', () => {
  cs.clearSessionCoaching();
  cs.storeSessionCoaching('a5b', 'squat', okResult({ observations: ['Segment 1 (x): text.'] }), [
    { ordinal: 1, start_s: NaN },
  ]);
  const v = cs.readSessionCoaching('a5b');
  assert.ok(v);
  assert.equal(v.segmentOrdinal, null);
  assert.equal(v.sourceS, null);
});

test('empty observations falls back to actual summary', () => {
  cs.clearSessionCoaching();
  cs.storeSessionCoaching('a5c', 'squat', okResult({ observations: [] }), REPS);
  const v = cs.readSessionCoaching('a5c');
  assert.ok(v);
  assert.equal(v.observation, 'Actual summary string.');
});

test('replacement overwrites with new actual strings', () => {
  cs.clearSessionCoaching();
  cs.storeSessionCoaching('a6', 'squat', okResult(), REPS);
  cs.storeSessionCoaching('a6', 'squat', okResult({
    observations: ['Segment 1 (2.50s): replacement observation.'],
    next_set_cue: 'Replacement cue.',
  }), REPS);
  const v = cs.readSessionCoaching('a6');
  assert.ok(v);
  assert.equal(v.observation, 'Segment 1 (2.50s): replacement observation.');
  assert.equal(v.nextSetCue, 'Replacement cue.');
  assert.equal(v.segmentOrdinal, 1);
  assert.equal(v.sourceS, 2.5);
});

test('clear scoped and global', () => {
  cs.clearSessionCoaching();
  cs.storeSessionCoaching('a7', 'squat', okResult(), REPS);
  cs.storeSessionCoaching('a8', 'squat', okResult(), REPS);
  cs.clearSessionCoaching('a7');
  assert.equal(cs.readSessionCoaching('a7'), null);
  assert.ok(cs.readSessionCoaching('a8'));
  cs.clearSessionCoaching();
  assert.equal(cs.readSessionCoaching('a8'), null);
});

test('expiry: entries older than TTL read as null', () => {
  cs.clearSessionCoaching();
  const realNow = Date.now;
  try {
    Date.now = () => 1_000_000;
    cs.storeSessionCoaching('a9', 'squat', okResult(), REPS);
    Date.now = () => 1_000_000 + 31 * 60 * 1000;
    assert.equal(cs.readSessionCoaching('a9'), null);
  } finally {
    Date.now = realNow;
  }
});

test('bounded cache: 9th insert evicts oldest', () => {
  cs.clearSessionCoaching();
  for (let i = 0; i < 9; i++) {
    cs.storeSessionCoaching('b' + i, 'squat', okResult(), REPS);
  }
  assert.equal(cs.readSessionCoaching('b0'), null);
  assert.ok(cs.readSessionCoaching('b8'));
});

test('bad result shape coerced safely without crash or cue', () => {
  cs.clearSessionCoaching();
  cs.storeSessionCoaching('c1', 'squat', {
    status: 'ok',
    summary: 42,
    observations: 'not-an-array',
    next_set_cue: 7,
    limitations: null,
  }, REPS);
  const v = cs.readSessionCoaching('c1');
  assert.ok(v);
  assert.equal(v.observation, null);
  assert.equal(v.nextSetCue, null);
  assert.equal(v.segmentOrdinal, null);
  assert.equal(v.sourceS, null);
});

test('read of unknown id returns null', () => {
  cs.clearSessionCoaching();
  assert.equal(cs.readSessionCoaching('nope'), null);
});

console.log(passed + ' tests passed');
if (process.exitCode) process.exit(process.exitCode);
