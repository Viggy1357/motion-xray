#!/usr/bin/env node
'use strict';

/* Offline CJS unit tests for pure UX metadata + region logic + thumbnail cache
 * + week-window helpers. Transpiles the TypeScript sources with the existing
 * typescript package. No ReactDOM test dependency. */

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
    if (/\.css$/.test(spec)) return {};
    if (spec.startsWith('.')) {
      const resolved = path.join(path.dirname(relPath), spec).replace(/\\/g, '/');
      return loadTsModule(
        resolved.endsWith('.ts') || resolved.endsWith('.tsx') ? resolved : resolved + '.ts'
      );
    }
    return require(spec);
  };
  const fn = new Function('require', 'module', 'exports', '__filename', '__dirname', js);
  fn(localRequire, mod, mod.exports, abs, path.dirname(abs));
  return mod.exports;
}

const ux = loadTsModule('app/lib/ux-metadata.ts');
const region = loadTsModule('app/components/RegionActivity.tsx');
const week = loadTsModule('app/lib/week-window.ts');
const cache = loadTsModule('app/lib/thumbnail-cache.ts');

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
  assert.equal(region.isEligibleSet({ analysisId: 'a9', exercise: 'squat', recognitionVersion: '1' }), false);
});

test('region counts dedupe by analysisId and skip ineligible', () => {
  const sets = [
    { analysisId: 'a1', exercise: 'squat', recognition: { analysisId: 'a1', exercise: 'squat' } },
    { analysisId: 'a1', exercise: 'squat', recognition: { analysisId: 'a1', exercise: 'squat' } },
    { analysisId: 'a2', exercise: 'lat_pulldown', recognition: { analysisId: 'a2', exercise: 'lat_pulldown' } },
    { analysisId: 'a3', exercise: 'dumbbell_curl' },
    { analysisId: 'a4', exercise: 'unknown', recognition: { analysisId: 'a4', exercise: 'unknown' } },
  ];
  const counts = region.countByRegion(sets);
  assert.deepEqual(counts, { back: 1, arms: 0, legs: 1, chest: 0 });
});

// --- week-window ---
function isoLocal(d) {
  const off = d.getTimezoneOffset() * 60000;
  return new Date(d.getTime() - off).toISOString().slice(0, 10);
}

test('rolling7: 7 local dates ending today, start midnight today-6, end tomorrow exclusive', () => {
  const now = new Date(2026, 2, 10, 14, 30, 0, 0); // Tue Mar 10 2026 14:30 local
  const { start, end } = week.weekBounds('rolling7', now);
  assert.equal(isoLocal(start), '2026-03-04');
  assert.equal(isoLocal(end), '2026-03-11');
  assert.equal(start.getHours(), 0);
  assert.equal(end.getHours(), 0);
  const days = week.weekDays('rolling7', now);
  assert.equal(days.length, 7);
  assert.equal(isoLocal(days[0]), '2026-03-04');
  assert.equal(isoLocal(days[6]), '2026-03-10');
});

test('calendar: Monday 00:00 to following Monday 00:00 exclusive', () => {
  const wed = new Date(2026, 2, 11, 9, 0, 0, 0); // Wed Mar 11 2026
  const { start, end } = week.weekBounds('calendar', wed);
  assert.equal(isoLocal(start), '2026-03-09'); // Monday
  assert.equal(isoLocal(end), '2026-03-16'); // following Monday, exclusive
  const days = week.weekDays('calendar', wed);
  assert.equal(days.length, 7);
  assert.equal(isoLocal(days[0]), '2026-03-09');
  assert.equal(isoLocal(days[6]), '2026-03-15');
});

test('calendar: Sunday rolls back to the preceding Monday', () => {
  const sun = new Date(2026, 2, 15, 12, 0, 0, 0); // Sun Mar 15 2026
  const { start } = week.weekBounds('calendar', sun);
  assert.equal(isoLocal(start), '2026-03-09');
});

test('inWeek: rolling7 includes today, excludes tomorrow, rejects invalid and future', () => {
  const now = new Date(2026, 2, 10, 14, 30, 0, 0);
  assert.equal(week.inWeek('2026-03-10T14:00:00', 'rolling7', now), true);
  assert.equal(week.inWeek('2026-03-04T00:00:00', 'rolling7', now), true);
  assert.equal(week.inWeek('2026-03-11T00:00:00', 'rolling7', now), false); // end exclusive
  assert.equal(week.inWeek('2026-03-03T23:59:59', 'rolling7', now), false); // before start
  assert.equal(week.inWeek('not-a-date', 'rolling7', now), false);
  assert.equal(week.inWeek('', 'rolling7', now), false);
  // Future timestamp rejected even if inside the window.
  assert.equal(week.inWeek('2026-03-10T23:59:59', 'rolling7', now), false); // future beyond now
  assert.equal(week.inWeek('2026-03-10T15:00:00', 'rolling7', now), false); // > now
  // Past timestamps inside the window are accepted.
  assert.equal(week.inWeek('2026-03-10T13:00:00', 'rolling7', now), true); // earlier today
  assert.equal(week.inWeek('2026-03-04T12:00:00', 'rolling7', now), true); // earlier this week
});

test('inWeek: calendar rejects future timestamps beyond now', () => {
  const now = new Date(2026, 2, 11, 9, 0, 0, 0); // Wed
  assert.equal(week.inWeek('2026-03-15T23:59:59', 'calendar', now), false); // Sun is future relative to Wed
  assert.equal(week.inWeek('2026-03-16T00:00:00', 'calendar', now), false); // following Mon, exclusive
  assert.equal(week.inWeek('2026-03-11T10:00:00', 'calendar', now), false); // future
  // Past timestamps within the current calendar week are accepted.
  assert.equal(week.inWeek('2026-03-09T08:00:00', 'calendar', now), true); // earlier this week
  assert.equal(week.inWeek('2026-03-08T23:59:59', 'calendar', now), false); // previous Sunday precedes Monday start
});

test('DST spring-forward: rolling7 window stays 7 local days', () => {
  // US "spring forward" 2026-03-08 02:00 -> 03:00 local. Pick a fixed offset
  // timezone to make the assertion deterministic regardless of host TZ.
  const realTz = process.env.TZ;
  process.env.TZ = 'America/New_York';
  try {
    const now = new Date('2026-03-10T14:30:00'); // interpreted in host TZ
    const { start, end } = week.weekBounds('rolling7', now);
    const days = week.weekDays('rolling7', now);
    assert.equal(days.length, 7);
    assert.equal(isoLocal(start), '2026-03-04');
    assert.equal(isoLocal(end), '2026-03-11');
  } finally {
    if (realTz === undefined) delete process.env.TZ;
    else process.env.TZ = realTz;
  }
});

test('DST fall-back: calendar week still Mon->Mon exclusive', () => {
  const realTz = process.env.TZ;
  process.env.TZ = 'America/New_York';
  try {
    const now = new Date('2026-11-04T10:00:00'); // during fall-back week
    const { start, end } = week.weekBounds('calendar', now);
    assert.equal(isoLocal(start), '2026-11-02'); // Mon
    assert.equal(isoLocal(end), '2026-11-09'); // following Mon, exclusive
  } finally {
    if (realTz === undefined) delete process.env.TZ;
    else process.env.TZ = realTz;
  }
});

test('midnight earlier than oldest day is excluded', () => {
  const now = new Date(2026, 2, 10, 14, 30, 0, 0);
  // 23:59:59 the day before the window starts -> excluded.
  assert.equal(week.inWeek('2026-03-03T23:59:59', 'rolling7', now), false);
  // 00:00:00 of the start day -> included.
  assert.equal(week.inWeek('2026-03-04T00:00:00', 'rolling7', now), true);
});

// --- thumbnail cache ---
test('thumbnail cache: different analysis or cue keys do not collide', () => {
  cache._resetForTests();
  cache.storeThumbnail('a1|1.000', 'blob:one');
  cache.storeThumbnail('a1|2.000', 'blob:two');
  cache.storeThumbnail('a2|1.000', 'blob:three');
  assert.equal(cache._cacheSize(), 3);
  assert.ok(cache._hasKey('a1|1.000'));
  assert.ok(cache._hasKey('a1|2.000'));
  assert.ok(cache._hasKey('a2|1.000'));
  cache._resetForTests();
});

test('thumbnail cache: refcount prevents revoke while refs > 0', () => {
  cache._resetForTests();
  cache.storeThumbnail('a1|1.000', 'blob:one');
  const e1 = cache.acquireThumbnail('a1|1.000');
  assert.ok(e1);
  assert.equal(e1.refs, 1);
  cache.dropThumbnailsForAnalysis('a1');
  // Entry is stale/tombstoned but still present because refs > 0.
  assert.ok(cache._hasKey('a1|1.000'));
  cache.releaseThumbnail('a1|1.000');
  // Now refs == 0 and stale -> revoked and removed.
  assert.equal(cache._hasKey('a1|1.000'), false);
  cache._resetForTests();
});

test('thumbnail cache: pending extraction cannot repopulate after revoke', () => {
  cache._resetForTests();
  cache.dropThumbnailsForAnalysis('a1');
  // Simulate a pending extraction that resolves after revocation.
  cache.storeThumbnail('a1|auto', 'blob:late');
  assert.equal(cache._hasKey('a1|auto'), false);
  assert.equal(cache._isTombstoned('a1|auto'), true);
  cache._resetForTests();
});

test('thumbnail cache: sweepExpired clears stale entries by actual 5-minute expiry', () => {
  cache._resetForTests();
  cache.storeThumbnail('a1|1.000', 'blob:one');
  // Advance virtual clock past MAX_AGE_MS.
  const future = Date.now() + cache.MAX_AGE_MS + 1000;
  const removed = cache.sweepExpired(future);
  assert.equal(removed, 1);
  assert.equal(cache._hasKey('a1|1.000'), false);
  cache._resetForTests();
});

test('thumbnail cache: held key preserves original blob across two refs and rejects redundant incoming', () => {
  cache._resetForTests();
  const revoked = [];
  const origRevoke = URL.revokeObjectURL;
  URL.revokeObjectURL = (u) => { revoked.push(u); };
  try {
    cache.storeThumbnail('a1|1.000', 'blob:orig');
    const e1 = cache.acquireThumbnail('a1|1.000');
    const e2 = cache.acquireThumbnail('a1|1.000');
    assert.ok(e1 && e2);
    assert.equal(e1.url, 'blob:orig');
    assert.equal(e2.url, 'blob:orig');
    assert.equal(e1.refs, 2);
    // Distinct redundant incoming URL while held: must be revoked exactly once.
    cache.storeThumbnail('a1|1.000', 'blob:dup');
    assert.equal(revoked.filter((u) => u === 'blob:dup').length, 1);
    assert.equal(revoked.filter((u) => u === 'blob:orig').length, 0);
    // Original entry still usable; both refs intact.
    assert.ok(cache._hasKey('a1|1.000'));
    assert.equal(e1.refs, 2);
    // Last release revokes the original per existing policy.
    cache.releaseThumbnail('a1|1.000');
    cache.releaseThumbnail('a1|1.000');
    assert.equal(cache._hasKey('a1|1.000'), false);
    assert.equal(revoked.filter((u) => u === 'blob:orig').length, 1);
  } finally {
    URL.revokeObjectURL = origRevoke;
    cache._resetForTests();
  }
});

test('thumbnail cache: same live URL re-store is a no-op until release', () => {
  cache._resetForTests();
  const revoked = [];
  const origRevoke = URL.revokeObjectURL;
  URL.revokeObjectURL = (u) => { revoked.push(u); };
  try {
    cache.storeThumbnail('a1|1.000', 'blob:live');
    const e = cache.acquireThumbnail('a1|1.000');
    assert.ok(e);
    assert.equal(e.refs, 1);
    // Re-store with identical URL while held: no revoke, no overwrite.
    cache.storeThumbnail('a1|1.000', 'blob:live');
    assert.equal(revoked.length, 0);
    assert.ok(cache._hasKey('a1|1.000'));
    const e2 = cache.acquireThumbnail('a1|1.000');
    assert.equal(e2.url, 'blob:live');
    assert.equal(e2.refs, 2);
    // Release both refs: now the live URL is revoked exactly once.
    cache.releaseThumbnail('a1|1.000');
    cache.releaseThumbnail('a1|1.000');
    assert.equal(cache._hasKey('a1|1.000'), false);
    assert.equal(revoked.filter((u) => u === 'blob:live').length, 1);
  } finally {
    URL.revokeObjectURL = origRevoke;
    cache._resetForTests();
  }
});

test('thumbnail cache: scoped revoke tombstones held key; new store rejected; last release cleans old', () => {
  cache._resetForTests();
  const revoked = [];
  const origRevoke = URL.revokeObjectURL;
  URL.revokeObjectURL = (u) => { revoked.push(u); };
  try {
    cache.storeThumbnail('a1|1.000', 'blob:orig');
    const e = cache.acquireThumbnail('a1|1.000');
    assert.ok(e);
    assert.equal(e.refs, 1);
    cache.dropThumbnailsForAnalysis('a1');
    // Held entry remains present until last release; tombstone set.
    assert.ok(cache._hasKey('a1|1.000'));
    assert.equal(cache._isTombstoned('a1|1.000'), true);
    // Distinct new URL after revoke: rejected, revoked immediately, not cached.
    cache.storeThumbnail('a1|1.000', 'blob:new');
    assert.equal(revoked.filter((u) => u === 'blob:new').length, 1);
    assert.equal(cache._hasKey('a1|1.000'), true);
    // acquireThumbnail after revoke returns null (tombstoned/stale).
    assert.equal(cache.acquireThumbnail('a1|1.000'), null);
    // Last release revokes the original and removes the entry.
    cache.releaseThumbnail('a1|1.000');
    assert.equal(cache._hasKey('a1|1.000'), false);
    assert.equal(revoked.filter((u) => u === 'blob:orig').length, 1);
  } finally {
    URL.revokeObjectURL = origRevoke;
    cache._resetForTests();
  }
});

test('thumbnail cache: clearThumbnailCache is idempotent and tombstones all', () => {
  cache._resetForTests();
  cache.storeThumbnail('a1|1.000', 'blob:one');
  cache.storeThumbnail('a2|1.000', 'blob:two');
  cache.clearThumbnailCache();
  cache.clearThumbnailCache();
  assert.equal(cache._cacheSize(), 0);
  assert.equal(cache._isTombstoned('a1|1.000'), true);
  assert.equal(cache._isTombstoned('a2|1.000'), true);
  cache._resetForTests();
});

console.log(passed + ' tests passed');
if (process.exitCode) process.exit(process.exitCode);
