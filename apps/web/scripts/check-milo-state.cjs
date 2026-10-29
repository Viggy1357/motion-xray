#!/usr/bin/env node
'use strict';

/* Offline CJS unit tests for the pure Milo state controller.
 * Transpiles the TypeScript source with the existing typescript package.
 * No ts-node, no network, no DOM. */

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
    if (spec.startsWith('.')) {
      const resolved = path.join(path.dirname(relPath), spec).replace(/\\/g, '/');
      const withExt = resolved.endsWith('.ts') || resolved.endsWith('.tsx') ? resolved : resolved + '.ts';
      return loadTsModule(withExt);
    }
    return require(spec);
  };
  const fn = new Function('require', 'module', 'exports', '__filename', '__dirname', js);
  fn(localRequire, mod, mod.exports, abs, path.dirname(abs));
  return mod.exports;
}

const milo = loadTsModule('app/lib/milo-state.ts');

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

const baseInput = {
  recording: false,
  hidden: false,
  reducedMotion: false,
  activeJobId: null,
  latestResult: null,
  pendingSaveJobId: null,
  saveConfirmedJobId: null,
};

function input(overrides) {
  return Object.assign({}, baseInput, overrides || {});
}

// --- makeEventKey ---
test('makeEventKey joins jobId and kind', () => {
  assert.equal(milo.makeEventKey('job-1', 'result:ready'), 'job-1:result:ready');
  assert.equal(milo.makeEventKey(null, 'save'), 'none:save');
  assert.equal(milo.makeEventKey(undefined, 'save'), 'none:save');
  assert.equal(milo.makeEventKey('', 'save'), 'none:save');
});

// --- shouldSuppressStale ---
test('shouldSuppressStale: no result -> false', () => {
  const prev = milo.DEFAULT_MILO_DECISION;
  assert.equal(milo.shouldSuppressStale(prev, input()), false);
});

test('shouldSuppressStale: same job as active -> false', () => {
  const prev = milo.DEFAULT_MILO_DECISION;
  const i = input({
    activeJobId: 'j1',
    latestResult: { jobId: 'j1', status: 'ready', usable: true },
  });
  assert.equal(milo.shouldSuppressStale(prev, i), false);
});

test('shouldSuppressStale: stale result already seen -> true', () => {
  const key = milo.makeEventKey('j1', 'result:ready');
  const prev = {
    visual: 'idle',
    size: 'compact',
    eventKey: null,
    seenEventKeys: [key],
    lastReactionAt: 100,
  };
  const i = input({
    activeJobId: 'j2',
    latestResult: { jobId: 'j1', status: 'ready', usable: true },
  });
  assert.equal(milo.shouldSuppressStale(prev, i), true);
});

test('shouldSuppressStale: stale result unseen but mismatched active -> true', () => {
  const prev = milo.DEFAULT_MILO_DECISION;
  const i = input({
    activeJobId: 'j2',
    latestResult: { jobId: 'j1', status: 'ready', usable: true },
  });
  assert.equal(milo.shouldSuppressStale(prev, i), true);
});

// --- defaults ---
test('default decision is idle compact with empty history', () => {
  const d = milo.DEFAULT_MILO_DECISION;
  assert.equal(d.visual, 'idle');
  assert.equal(d.size, 'compact');
  assert.equal(d.eventKey, null);
  assert.deepEqual(d.seenEventKeys, []);
  assert.equal(d.lastReactionAt, null);
});

// --- recording / reducedMotion / hidden ---
test('recording forces static', () => {
  const d = milo.decideMilo(milo.DEFAULT_MILO_DECISION, input({ recording: true }), 1000);
  assert.equal(d.visual, 'static');
  assert.equal(d.eventKey, null);
});

test('reducedMotion forces static', () => {
  const d = milo.decideMilo(milo.DEFAULT_MILO_DECISION, input({ reducedMotion: true }), 1000);
  assert.equal(d.visual, 'static');
});

test('hidden forces static and preserves history', () => {
  const prev = {
    visual: 'cheer',
    size: 'compact',
    eventKey: 'j1:result:ready',
    seenEventKeys: ['j1:result:ready'],
    lastReactionAt: 500,
  };
  const d = milo.decideMilo(prev, input({ hidden: true }), 2000);
  assert.equal(d.visual, 'static');
  assert.deepEqual(d.seenEventKeys, ['j1:result:ready']);
  assert.equal(d.lastReactionAt, 500);
});

// --- active job ---
test('active job without result -> attentive', () => {
  const d = milo.decideMilo(milo.DEFAULT_MILO_DECISION, input({ activeJobId: 'j1' }), 1000);
  assert.equal(d.visual, 'attentive');
});

test('active job with partial result -> attentive (no cheer)', () => {
  const d = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({ activeJobId: 'j1', latestResult: { jobId: 'j1', status: 'partial', usable: false } }),
    1000
  );
  assert.equal(d.visual, 'attentive');
  assert.equal(d.eventKey, null);
});

// --- failure / cancelled / expired ---
test('failed same job as active -> static', () => {
  const d = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({ activeJobId: 'j1', latestResult: { jobId: 'j1', status: 'failed', usable: false } }),
    1000
  );
  assert.equal(d.visual, 'static');
});

test('cancelled same job as active -> static', () => {
  const d = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({ activeJobId: 'j1', latestResult: { jobId: 'j1', status: 'cancelled', usable: false } }),
    1000
  );
  assert.equal(d.visual, 'static');
});

test('expired same job as active -> static', () => {
  const d = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({ activeJobId: 'j1', latestResult: { jobId: 'j1', status: 'expired', usable: false } }),
    1000
  );
  assert.equal(d.visual, 'static');
});

test('failed different newer active job wins over stale failure', () => {
  const d = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({
      activeJobId: 'j2',
      latestResult: { jobId: 'j1', status: 'failed', usable: false },
    }),
    1000
  );
  assert.equal(d.visual, 'attentive');
});

// --- ready result ---
test('ready usable result cheers once', () => {
  const d = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({ latestResult: { jobId: 'j1', status: 'ready', usable: true } }),
    1000
  );
  assert.equal(d.visual, 'cheer');
  assert.equal(d.eventKey, 'j1:result:ready');
  assert.deepEqual(d.seenEventKeys, ['j1:result:ready']);
  assert.equal(d.lastReactionAt, 1000);
});

test('ready usable result does not replay on re-read', () => {
  const prev = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({ latestResult: { jobId: 'j1', status: 'ready', usable: true } }),
    1000
  );
  const d2 = milo.decideMilo(
    prev,
    input({ latestResult: { jobId: 'j1', status: 'ready', usable: true } }),
    2000
  );
  assert.equal(d2.visual, 'idle');
  assert.equal(d2.eventKey, null);
  assert.deepEqual(d2.seenEventKeys, ['j1:result:ready']);
});

test('ready not usable -> idle, no cheer', () => {
  const d = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({ latestResult: { jobId: 'j1', status: 'ready', usable: false } }),
    1000
  );
  assert.equal(d.visual, 'idle');
  assert.equal(d.eventKey, null);
});

test('partial result -> attentive, no cheer', () => {
  const d = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({ latestResult: { jobId: 'j1', status: 'partial', usable: false } }),
    1000
  );
  assert.equal(d.visual, 'attentive');
  assert.equal(d.eventKey, null);
});

// --- stale result suppression ---
test('stale ready result does not cheer when newer active job exists', () => {
  const prev = {
    visual: 'idle',
    size: 'compact',
    eventKey: null,
    seenEventKeys: [milo.makeEventKey('j1', 'result:ready')],
    lastReactionAt: 500,
  };
  const d = milo.decideMilo(
    prev,
    input({
      activeJobId: 'j2',
      latestResult: { jobId: 'j1', status: 'ready', usable: true },
    }),
    2000
  );
  // Spec: activeJobId means currently PROCESSING ONLY and always attentive.
  assert.equal(d.visual, 'attentive');
  assert.equal(d.eventKey, null);
});

test('newer active job supersedes old job completion', () => {
  // First job completes ready.
  const a = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({ latestResult: { jobId: 'j1', status: 'ready', usable: true } }),
    1000
  );
  assert.equal(a.visual, 'cheer');
  // New job starts; old result still present but stale.
  const b = milo.decideMilo(
    a,
    input({
      activeJobId: 'j2',
      latestResult: { jobId: 'j1', status: 'ready', usable: true },
    }),
    2000
  );
  assert.equal(b.visual, 'attentive');
  assert.equal(b.eventKey, null);
});

// --- save handling ---
test('pending save does not cheer', () => {
  const d = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({
      latestResult: { jobId: 'j1', status: 'ready', usable: true },
      pendingSaveJobId: 'j1',
    }),
    1000
  );
  assert.equal(d.visual, 'idle');
  assert.equal(d.eventKey, null);
});

test('save confirmed matching latestResult cheers once', () => {
  const d = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({
      latestResult: { jobId: 'j1', status: 'ready', usable: true },
      saveConfirmedJobId: 'j1',
    }),
    1000
  );
  assert.equal(d.visual, 'cheer');
  assert.equal(d.eventKey, 'j1:save');
});

test('processing wins save', () => {
  const d = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({
      activeJobId: 'j1',
      saveConfirmedJobId: 'j1',
    }),
    1000
  );
  // Spec: activeJobId means currently PROCESSING ONLY and always attentive.
  assert.equal(d.visual, 'attentive');
  assert.equal(d.eventKey, null);
});

test('save confirmed for distinct stale job does not cheer', () => {
  const d = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({
      activeJobId: 'j2',
      latestResult: { jobId: 'j2', status: 'ready', usable: true },
      saveConfirmedJobId: 'j1',
    }),
    1000
  );
  // Spec: activeJobId means currently PROCESSING ONLY and always attentive.
  assert.equal(d.visual, 'attentive');
  assert.equal(d.eventKey, null);
});

test('save confirmed collapse: ready then save within 3000ms collapses to idle', () => {
  const a = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({ latestResult: { jobId: 'j1', status: 'ready', usable: true } }),
    1000
  );
  assert.equal(a.visual, 'cheer');
  const b = milo.decideMilo(
    a,
    input({
      latestResult: { jobId: 'j1', status: 'ready', usable: true },
      saveConfirmedJobId: 'j1',
    }),
    2000
  );
  // Within collapse window: no second cheer; collapsed event must NEVER reappear.
  assert.equal(b.visual, 'idle');
  assert.equal(b.eventKey, null);
  // Re-read after collapse window: still no replay of the collapsed save.
  const c = milo.decideMilo(
    b,
    input({
      latestResult: { jobId: 'j1', status: 'ready', usable: true },
      saveConfirmedJobId: 'j1',
    }),
    1000 + milo.MILO_COLLAPSE_WINDOW_MS + 500
  );
  assert.equal(c.visual, 'idle');
  assert.equal(c.eventKey, null);
});

test('save confirmed after collapse window cheers', () => {
  const a = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({ latestResult: { jobId: 'j1', status: 'ready', usable: true } }),
    1000
  );
  const b = milo.decideMilo(
    a,
    input({
      latestResult: { jobId: 'j1', status: 'ready', usable: true },
      saveConfirmedJobId: 'j1',
    }),
    1000 + milo.MILO_COLLAPSE_WINDOW_MS + 1
  );
  assert.equal(b.visual, 'cheer');
  assert.equal(b.eventKey, 'j1:save');
});

test('save confirmed replay does not re-cheer', () => {
  const a = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({
      latestResult: { jobId: 'j1', status: 'ready', usable: true },
      saveConfirmedJobId: 'j1',
    }),
    1000
  );
  assert.equal(a.visual, 'cheer');
  const b = milo.decideMilo(
    a,
    input({
      latestResult: { jobId: 'j1', status: 'ready', usable: true },
      saveConfirmedJobId: 'j1',
    }),
    5000
  );
  assert.equal(b.visual, 'idle');
  assert.equal(b.eventKey, null);
});

// --- independent jobs ---
test('independent jobs each get their own cheer', () => {
  const a = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({ latestResult: { jobId: 'j1', status: 'ready', usable: true } }),
    1000
  );
  assert.equal(a.visual, 'cheer');
  const b = milo.decideMilo(
    a,
    input({ latestResult: { jobId: 'j2', status: 'ready', usable: true } }),
    5000
  );
  assert.equal(b.visual, 'cheer');
  assert.equal(b.eventKey, 'j2:result:ready');
  assert.deepEqual(b.seenEventKeys, ['j1:result:ready', 'j2:result:ready']);
});

// --- history bounded ---
test('history bounded to 128 keys', () => {
  let prev = milo.DEFAULT_MILO_DECISION;
  for (let i = 0; i < 200; i++) {
    prev = milo.decideMilo(
      prev,
      input({ latestResult: { jobId: 'j' + i, status: 'ready', usable: true } }),
      1000 + i * 5000
    );
  }
  assert.ok(prev.seenEventKeys.length <= milo.MILO_HISTORY_LIMIT);
  assert.equal(prev.seenEventKeys.length, milo.MILO_HISTORY_LIMIT);
  // Oldest entries dropped.
  assert.equal(prev.seenEventKeys[0], milo.makeEventKey('j' + (200 - milo.MILO_HISTORY_LIMIT), 'result:ready'));
});

// --- negative / non-finite time ---
test('negative time is treated as 0 and does not crash', () => {
  const d = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({ latestResult: { jobId: 'j1', status: 'ready', usable: true } }),
    -100
  );
  assert.equal(d.visual, 'cheer');
  assert.equal(d.lastReactionAt, 0);
});

test('non-finite time is treated as 0', () => {
  const d = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({ latestResult: { jobId: 'j1', status: 'ready', usable: true } }),
    NaN
  );
  assert.equal(d.visual, 'cheer');
  assert.equal(d.lastReactionAt, 0);
});

test('undefined time is treated as 0', () => {
  const d = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({ latestResult: { jobId: 'j1', status: 'ready', usable: true } }),
    undefined
  );
  assert.equal(d.visual, 'cheer');
  assert.equal(d.lastReactionAt, 0);
});

// --- history survives idle/hidden transitions ---
test('history survives idle transition', () => {
  const a = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({ latestResult: { jobId: 'j1', status: 'ready', usable: true } }),
    1000
  );
  const b = milo.decideMilo(a, input(), 2000);
  assert.equal(b.visual, 'idle');
  assert.deepEqual(b.seenEventKeys, ['j1:result:ready']);
  // Re-read same result: still no replay.
  const c = milo.decideMilo(
    b,
    input({ latestResult: { jobId: 'j1', status: 'ready', usable: true } }),
    3000
  );
  assert.equal(c.visual, 'idle');
  assert.equal(c.eventKey, null);
});

test('history survives hidden then visible transition', () => {
  const a = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({ latestResult: { jobId: 'j1', status: 'ready', usable: true } }),
    1000
  );
  const b = milo.decideMilo(a, input({ hidden: true }), 2000);
  assert.equal(b.visual, 'static');
  assert.deepEqual(b.seenEventKeys, ['j1:result:ready']);
  const c = milo.decideMilo(
    b,
    input({ latestResult: { jobId: 'j1', status: 'ready', usable: true } }),
    3000
  );
  assert.equal(c.visual, 'idle');
  assert.equal(c.eventKey, null);
});

// --- size default compact ---
test('default size is compact', () => {
  const d = milo.decideMilo(milo.DEFAULT_MILO_DECISION, input(), 1000);
  assert.equal(d.size, 'compact');
});

test('size hero preserved across decisions', () => {
  const prev = {
    visual: 'idle',
    size: 'hero',
    eventKey: null,
    seenEventKeys: [],
    lastReactionAt: null,
  };
  const d = milo.decideMilo(prev, input({ activeJobId: 'j1' }), 1000);
  assert.equal(d.size, 'hero');
});

// --- once suppressed returns idle ---
test('once suppressed (hidden) returns idle when revealed with no new event', () => {
  const a = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({ latestResult: { jobId: 'j1', status: 'ready', usable: true } }),
    1000
  );
  const b = milo.decideMilo(a, input({ hidden: true }), 2000);
  assert.equal(b.visual, 'static');
  const c = milo.decideMilo(b, input(), 3000);
  assert.equal(c.visual, 'idle');
  assert.equal(c.eventKey, null);
});

// --- recording overrides everything ---
test('recording overrides active job and ready result', () => {
  const d = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({
      recording: true,
      activeJobId: 'j1',
      latestResult: { jobId: 'j1', status: 'ready', usable: true },
    }),
    1000
  );
  assert.equal(d.visual, 'static');
});

// --- dedup: same eventKey never replays ---
test('same eventKey never replays across many decisions', () => {
  let prev = milo.DEFAULT_MILO_DECISION;
  for (let i = 0; i < 10; i++) {
    prev = milo.decideMilo(
      prev,
      input({ latestResult: { jobId: 'j1', status: 'ready', usable: true } }),
      1000 + i * 100
    );
  }
  assert.equal(prev.visual, 'idle');
  assert.equal(prev.eventKey, null);
  assert.deepEqual(prev.seenEventKeys, ['j1:result:ready']);
});

// --- partial save must not imply validated result ---
test('partial result with pending save stays idle (no cheer)', () => {
  const d = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({
      latestResult: { jobId: 'j1', status: 'partial', usable: false },
      pendingSaveJobId: 'j1',
    }),
    1000
  );
  assert.equal(d.visual, 'idle');
  assert.equal(d.eventKey, null);
});

test('partial result with save confirmed for same job stays attentive (no cheer)', () => {
  const d = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({
      latestResult: { jobId: 'j1', status: 'partial', usable: false },
      saveConfirmedJobId: 'j1',
    }),
    1000
  );
  assert.equal(d.visual, 'attentive');
  assert.equal(d.eventKey, null);
});

// --- corrected: activeJobId + stale result -> attentive, not idle/cheer ---
test('activeJobId with stale ready result returns attentive (not idle/cheer)', () => {
  const prev = milo.DEFAULT_MILO_DECISION;
  const d = milo.decideMilo(
    prev,
    input({
      activeJobId: 'j2',
      latestResult: { jobId: 'j1', status: 'ready', usable: true },
    }),
    1000
  );
  // Spec: activeJobId means currently PROCESSING ONLY and always attentive.
  assert.equal(d.visual, 'attentive');
  assert.equal(d.eventKey, null);
});

// --- corrected: activeJobId with stale partial result -> attentive ---
test('activeJobId with stale partial result returns attentive', () => {
  const prev = milo.DEFAULT_MILO_DECISION;
  const d = milo.decideMilo(
    prev,
    input({
      activeJobId: 'j2',
      latestResult: { jobId: 'j1', status: 'partial', usable: false },
    }),
    1000
  );
  assert.equal(d.visual, 'attentive');
  assert.equal(d.eventKey, null);
});

// --- corrected: save only latestResult ready+usable, no partial/failure ---
test('save confirmed with partial result does not cheer', () => {
  const d = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({
      latestResult: { jobId: 'j1', status: 'partial', usable: false },
      saveConfirmedJobId: 'j1',
    }),
    1000
  );
  // Partial result: save should not cheer.
  assert.equal(d.visual, 'attentive');
  assert.equal(d.eventKey, null);
});

test('save confirmed with failed result does not cheer', () => {
  const d = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({
      latestResult: { jobId: 'j1', status: 'failed', usable: false },
      saveConfirmedJobId: 'j1',
    }),
    1000
  );
  assert.equal(d.visual, 'static');
  assert.equal(d.eventKey, null);
});

// --- corrected: dedup consumption collapsed BOTH ready/save same job ---
test('collapsed ready+save consumed forever, never re-cheer', () => {
  // Ready cheer at t=1000
  const a = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({ latestResult: { jobId: 'j1', status: 'ready', usable: true } }),
    1000
  );
  assert.equal(a.visual, 'cheer');
  assert.equal(a.eventKey, 'j1:result:ready');
  // Save within collapse window: consumed silently
  const b = milo.decideMilo(
    a,
    input({
      latestResult: { jobId: 'j1', status: 'ready', usable: true },
      saveConfirmedJobId: 'j1',
    }),
    2000
  );
  assert.equal(b.visual, 'idle');
  assert.equal(b.eventKey, null);
  // Both keys in history
  assert.deepEqual(b.seenEventKeys, ['j1:result:ready', 'j1:save']);
  // Much later: neither key replays
  const c = milo.decideMilo(
    b,
    input({
      latestResult: { jobId: 'j1', status: 'ready', usable: true },
      saveConfirmedJobId: 'j1',
    }),
    100000
  );
  assert.equal(c.visual, 'idle');
  assert.equal(c.eventKey, null);
  assert.deepEqual(c.seenEventKeys, ['j1:result:ready', 'j1:save']);
});

// --- corrected: distinct job gets own celebration regardless collapse ---
test('distinct job cheers even if previous job collapsed', () => {
  const a = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({ latestResult: { jobId: 'j1', status: 'ready', usable: true } }),
    1000
  );
  assert.equal(a.visual, 'cheer');
  // Collapse save for j1
  const b = milo.decideMilo(
    a,
    input({
      latestResult: { jobId: 'j1', status: 'ready', usable: true },
      saveConfirmedJobId: 'j1',
    }),
    2000
  );
  assert.equal(b.visual, 'idle');
  // New job j2 ready
  const c = milo.decideMilo(
    b,
    input({ latestResult: { jobId: 'j2', status: 'ready', usable: true } }),
    3000
  );
  assert.equal(c.visual, 'cheer');
  assert.equal(c.eventKey, 'j2:result:ready');
});

// --- corrected: history first key must be j72:result:ready using makeEventKey ---
test('history first key uses makeEventKey format', () => {
  const d = milo.decideMilo(
    milo.DEFAULT_MILO_DECISION,
    input({ latestResult: { jobId: 'j72', status: 'ready', usable: true } }),
    1000
  );
  assert.equal(d.visual, 'cheer');
  assert.equal(d.eventKey, milo.makeEventKey('j72', 'result:ready'));
  assert.equal(d.seenEventKeys[0], milo.makeEventKey('j72', 'result:ready'));
});

console.log(passed + ' tests passed');
if (process.exitCode) process.exit(process.exitCode);
