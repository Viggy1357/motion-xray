#!/usr/bin/env node
/* Offline regression checks for the recorder-adapter helper.
 * Transpiles apps/web/app/lib/recorder-adapter.ts and capture-controller.ts
 * with the existing TypeScript install; no new dependencies, no network, no DOM.
 *
 * The adapter is exercised through a fake MediaRecorder that simulates
 * deliberately delayed arrayBuffer() conversions, chunk ordering, and
 * stop-then-teardown-in-flight races. Tests await the actual adapter
 * onChunk/onStop signals via a bounded timeout — no microtask-counting
 * or setTimeout(0) hop guessing. */
'use strict';

const fs = require('fs');
const path = require('path');
const ts = require('typescript');

const root = path.join(__dirname, '..');
const libDir = path.join(root, 'app', 'lib');

function transpile(file) {
  const src = fs.readFileSync(path.join(libDir, file), 'utf8');
  return ts.transpileModule(src, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      strict: true,
    },
    fileName: file,
  }).outputText;
}

const ccJs = transpile('capture-controller.ts');
const raJs = transpile('recorder-adapter.ts');

const ccMod = { exports: {} };
new Function('module', 'exports', 'require', ccJs)(ccMod, ccMod.exports, require);
const { CaptureController, MAX_DURATION_MS, MAX_BYTES } = ccMod.exports;

let failures = 0;
function check(name, cond) {
  if (cond) {
    console.log(`ok - ${name}`);
  } else {
    failures += 1;
    console.error(`FAIL - ${name}`);
  }
}

/** Bounded wait for a predicate. Returns true if predicate became true,
 * false on timeout. Used to await real adapter signals without guessing
 * microtask counts. */
function waitFor(predicate, timeoutMs) {
  return new Promise((resolve) => {
    const start = Date.now();
    const tick = () => {
      let ok = false;
      try {
        ok = predicate();
      } catch {
        ok = false;
      }
      if (ok) {
        resolve(true);
        return;
      }
      if (Date.now() - start > timeoutMs) {
        resolve(false);
        return;
      }
      setTimeout(tick, 1);
    };
    tick();
  });
}

/** Fake MediaStream with a single video track. */
function fakeStream() {
  return { getTracks: () => [{ stop: () => undefined, kind: 'video' }] };
}

/**
 * Fake MediaRecorder that simulates delayed arrayBuffer() conversions.
 * Each dataavailable is queued; conversions resolve asynchronously.
 *
 * `awaitSettled()` resolves once every queued conversion has settled AND
 * the adapter's onChunk chain has drained, so tests can await the actual
 * adapter signals instead of guessing timer counts.
 */
function fakeMediaRecorder(opts) {
  const handlers = { data: null, stop: null, error: null };
  let state = 'inactive';
  let pending = 0;
  const rec = {
    get mimeType() {
      return opts.mimeType;
    },
    get state() {
      return state;
    },
    set ondataavailable(fn) {
      handlers.data = fn;
    },
    set onstop(fn) {
      handlers.stop = fn;
    },
    set onerror(fn) {
      handlers.error = fn;
    },
    start(timeslice) {
      state = 'recording';
      rec._timeslice = timeslice;
    },
    stop() {
      state = 'inactive';
      if (handlers.stop) handlers.stop();
    },
    // Test helper: emit a dataavailable with a blob whose arrayBuffer()
    // resolves after `delayMs`.
    _emit(bytes, delayMs) {
      const blob = {
        size: bytes.length,
        arrayBuffer: () =>
          new Promise((resolve) => {
            pending += 1;
            const done = () => {
              pending -= 1;
              resolve(bytes);
            };
            if (delayMs > 0) {
              setTimeout(done, delayMs);
            } else {
              setTimeout(done, 0);
            }
          }),
      };
      if (handlers.data) handlers.data({ data: blob });
    },
    _pendingCount() {
      return pending;
    },
  };
  return rec;
}

/**
 * Load recorder-adapter.ts with a stubbed MediaRecorder constructor.
 * The adapter calls `new MediaRecorder(...)` directly; we inject a fake
 * by evaluating the transpiled module with a MediaRecorder parameter.
 */
function loadAdapterWithFake(fakeInner) {
  const m = { exports: {} };
  const fn = new Function(
    'module',
    'exports',
    'require',
    'MediaRecorder',
    raJs,
  );
  fn(m, m.exports, require, function StubMediaRecorder() {
    return fakeInner;
  });
  return m.exports.createRecorderAdapter;
}

/** Fake monotonic clock with manual timer pump. */
function fakeClock() {
  let now = 0;
  let nextId = 1;
  const timers = new Map();
  return {
    now: () => now,
    setTimeout: (fn, ms) => {
      const id = nextId++;
      timers.set(id, { fn, at: now + ms, interval: 0 });
      return id;
    },
    clearTimeout: (id) => timers.delete(id),
    setInterval: (fn, ms) => {
      const id = nextId++;
      timers.set(id, { fn, at: now + ms, interval: ms });
      return id;
    },
    clearInterval: (id) => timers.delete(id),
    advance(ms) {
      const target = now + ms;
      for (;;) {
        let best = null;
        for (const [id, t] of timers) {
          if (t.at <= target && (!best || t.at < best.t.at)) best = { id, t };
        }
        if (!best) break;
        now = best.t.at;
        if (best.t.interval > 0) best.t.at = now + best.t.interval;
        else timers.delete(best.id);
        best.t.fn();
      }
      now = target;
    },
    pending: () => timers.size,
  };
}

async function runAll() {
  // --- Chunk ordering with delayed conversions ---
  {
    const inner = fakeMediaRecorder({ mimeType: 'video/webm' });
    const create = loadAdapterWithFake(inner);
    const adapter = create({
      stream: fakeStream(),
      mimeType: 'video/webm',
      timesliceMs: 1000,
      videoBitsPerSecond: 4_000_000,
    });
    const seen = [];
    adapter.onChunk = (c) => seen.push(c.data.length);
    adapter.start();
    inner._emit(new Uint8Array([1, 2, 3]), 5);
    inner._emit(new Uint8Array([4, 5, 6, 7, 8]), 15);
    inner._emit(new Uint8Array([9]), 1);
    const ok = await waitFor(() => seen.length === 3 && inner._pendingCount() === 0, 2000);
    check('chunk ordering preserved', ok && JSON.stringify(seen) === '[3,5,1]');
  }

  // --- Final chunk awaited before onStop ---
  {
    const inner = fakeMediaRecorder({ mimeType: 'video/webm' });
    const create = loadAdapterWithFake(inner);
    const adapter = create({
      stream: fakeStream(),
      mimeType: 'video/webm',
      timesliceMs: 1000,
      videoBitsPerSecond: 4_000_000,
    });
    const chunks = [];
    let stopped = false;
    adapter.onChunk = (c) => chunks.push(c.data.length);
    adapter.onStop = () => {
      stopped = true;
    };
    adapter.start();
    inner._emit(new Uint8Array([1, 2]), 10);
    inner._emit(new Uint8Array([3, 4, 5]), 20);
    adapter.stop();
    // Immediately after stop(), onStop must NOT have fired yet because the
    // final conversion is still pending.
    check('onStop waits for final conversion', stopped === false);
    const ok = await waitFor(() => stopped && chunks.length === 2, 2000);
    check('onStop fires after final conversion', ok && stopped === true);
    check('all chunks delivered before onStop', chunks.length === 2);
  }

  // --- Stop then teardown in flight: late callbacks discarded ---
  {
    const inner = fakeMediaRecorder({ mimeType: 'video/webm' });
    const create = loadAdapterWithFake(inner);
    const adapter = create({
      stream: fakeStream(),
      mimeType: 'video/webm',
      timesliceMs: 1000,
      videoBitsPerSecond: 4_000_000,
    });
    let chunks = 0;
    let stops = 0;
    adapter.onChunk = () => {
      chunks += 1;
    };
    adapter.onStop = () => {
      stops += 1;
    };
    adapter.start();
    inner._emit(new Uint8Array([1]), 30);
    adapter.stop();
    // Teardown before conversion lands.
    if (typeof adapter.__destroy === 'function') adapter.__destroy();
    // Wait long enough for the delayed conversion to have resolved.
    await new Promise((r) => setTimeout(r, 80));
    check('late chunk discarded after destroy', chunks === 0);
    check('late onStop discarded after destroy', stops === 0);
  }

  // --- Oversized final chunk is not truncated; controller rejects ---
  {
    const inner = fakeMediaRecorder({ mimeType: 'video/webm' });
    const create = loadAdapterWithFake(inner);
    const adapter = create({
      stream: fakeStream(),
      mimeType: 'video/webm',
      timesliceMs: 1000,
      videoBitsPerSecond: 4_000_000,
    });
    const chunks = [];
    adapter.onChunk = (c) => chunks.push(c);
    adapter.onStop = () => undefined;
    adapter.start();
    inner._emit(new Uint8Array(1024), 0);
    inner._emit(new Uint8Array(MAX_BYTES), 0);
    adapter.stop();
    const ok = await waitFor(() => chunks.length === 2, 2000);
    check('oversized chunk delivered', ok);
    // Adapter must deliver the full oversized chunk; it does not truncate.
    const total = chunks.reduce((s, c) => s + c.data.length, 0);
    check('oversized chunk not truncated', total === 1024 + MAX_BYTES);
    // Controller integration: oversized take is rejected at finalize.
    // Create a fresh adapter and fake inner so the controller receives
    // a chunk that exceeds MAX_BYTES and triggers E05.
    const inner2 = fakeMediaRecorder({ mimeType: 'video/webm' });
    const create2 = loadAdapterWithFake(inner2);
    const adapter2 = create2({
      stream: fakeStream(),
      mimeType: 'video/webm',
      timesliceMs: 1000,
      videoBitsPerSecond: 4_000_000,
    });
    const clock = fakeClock();
    const events = { errors: [], finalized: [] };
    const c = new CaptureController(clock, {
      onError: (code, msg) => events.errors.push([code, msg]),
      onFinalized: (clip) => events.finalized.push(clip),
    });
    c.recorderFactory = () => adapter2;
    c.requestRecord();
    c.beginPermission();
    c.permissionResult(true);
    c.startCountdown();
    clock.advance(3000);
    // Emit a chunk that exceeds MAX_BYTES so the controller rejects.
    inner2._emit(new Uint8Array(MAX_BYTES + 1024), 0);
    const ok2 = await waitFor(() => events.errors.length > 0, 2000);
    check('oversized take rejected', ok2 && events.errors.some(([code]) => code === 'E05_VALIDATION'));
    check('oversized take not finalized', events.finalized.length === 0);
  }

  // --- Delayed chunk conversions: controller sees chunks in order ---
  {
    const inner = fakeMediaRecorder({ mimeType: 'video/webm' });
    const create = loadAdapterWithFake(inner);
    const adapter = create({
      stream: fakeStream(),
      mimeType: 'video/webm',
      timesliceMs: 1000,
      videoBitsPerSecond: 4_000_000,
    });
    const clock = fakeClock();
    const events = { errors: [], finalized: [], chunks: [] };
    const c = new CaptureController(clock, {
      onError: (code, msg) => events.errors.push([code, msg]),
      onFinalized: (clip) => events.finalized.push(clip),
    });
    // Wrap onChunk to record sizes.
    let origOnChunk = null;
    Object.defineProperty(adapter, 'onChunk', {
      get() {
        return origOnChunk;
      },
      set(fn) {
        origOnChunk = (chunk) => {
          events.chunks.push(chunk.data.length);
          fn(chunk);
        };
      },
      configurable: true,
    });
    c.recorderFactory = () => adapter;
    c.requestRecord();
    c.beginPermission();
    c.permissionResult(true);
    c.startCountdown();
    clock.advance(3000);
    // Emit chunks with varying delays; adapter serializes them.
    inner._emit(new Uint8Array(100), 5);
    inner._emit(new Uint8Array(200), 20);
    inner._emit(new Uint8Array(300), 1);
    const ok = await waitFor(() => events.chunks.length === 3, 2000);
    check('delayed chunks delivered in order', ok && JSON.stringify(events.chunks) === '[100,200,300]');
  }

  // --- Stop called twice: onStop fires exactly once ---
  {
    const inner = fakeMediaRecorder({ mimeType: 'video/webm' });
    const create = loadAdapterWithFake(inner);
    const adapter = create({
      stream: fakeStream(),
      mimeType: 'video/webm',
      timesliceMs: 1000,
      videoBitsPerSecond: 4_000_000,
    });
    let stops = 0;
    adapter.onChunk = () => undefined;
    adapter.onStop = () => {
      stops += 1;
    };
    adapter.start();
    inner._emit(new Uint8Array(10), 0);
    adapter.stop();
    adapter.stop(); // second stop should not double-fire onStop
    const ok = await waitFor(() => stops >= 1, 2000);
    // Give any extra stop a chance to fire.
    await new Promise((r) => setTimeout(r, 20));
    check('double stop fires onStop once', ok && stops === 1);
  }

  // Behavioral test: arrayBuffer rejection must mark adapter destroyed,
  // clear handlers, notify onError exactly once, and stop best-effort,
  // suppressing further chunks/stops/errors.
  await (async () => {
    let errors = 0;
    let chunks = 0;
    let stops = 0;
    const inner = {
      mimeType: 'video/webm',
      state: 'inactive',
      start() { this.state = 'recording'; },
      stop() {
        this.state = 'inactive';
        if (typeof this.onstop === 'function') this.onstop();
      },
    };
    const createRecorderAdapter = loadAdapterWithFake(inner);
    const adapter = createRecorderAdapter({
      stream: fakeStream(), mimeType: 'video/webm',
      timesliceMs: 1000, videoBitsPerSecond: 4000000,
    });
    adapter.onChunk = () => { chunks += 1; };
    adapter.onStop = () => { stops += 1; };
    adapter.onError = () => { errors += 1; };
    adapter.start();
    inner.ondataavailable({ data: { size: 1, arrayBuffer: () => Promise.reject(new Error('decode')) } });
    const gotError = await waitFor(() => errors === 1, 1000);
    check('onError fired exactly once after arrayBuffer reject', gotError);
    check('conversion failure stops native recorder', inner.state === 'inactive');
    inner.ondataavailable({ data: { size: 1, arrayBuffer: () => Promise.reject(new Error('decode2')) } });
    adapter.stop();
    inner.ondataavailable({ data: { size: 1, arrayBuffer: () => Promise.reject(new Error('decode3')) } });
    inner.onstop();
    const settled = await waitFor(
      () => errors === 1 && chunks === 0 && stops === 0 && inner.state === 'inactive',
      1000,
    );
    check('no further errors after destroy', errors === 1);
    check('no chunks delivered after destroy', chunks === 0);
    check('no onStop delivered after destroy', stops === 0);
    check('inner state inactive after stop', inner.state === 'inactive');
    check('all post-destroy signals settled', settled);
  })();
  if (failures > 0) {
    console.error(`${failures} check(s) failed`);
    process.exit(1);
  }
  console.log('All recorder-adapter checks passed.');
}

runAll().catch((err) => {
  console.error('test runner crashed:', err);
  process.exit(1);
});
