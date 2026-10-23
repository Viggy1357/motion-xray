#!/usr/bin/env node
/* Offline regression checks for the pure capture controller.
 * Transpiles apps/web/app/lib/capture-controller.ts with the existing
 * TypeScript install; no new dependencies, no network, no DOM. */
'use strict';

const fs = require('fs');
const path = require('path');
const ts = require('typescript');

const root = path.join(__dirname, '..');
const srcPath = path.join(root, 'app', 'lib', 'capture-controller.ts');
const source = fs.readFileSync(srcPath, 'utf8');
const js = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
    strict: true,
  },
  fileName: 'capture-controller.ts',
}).outputText;

const mod = { exports: {} };
new Function('module', 'exports', 'require', js)(mod, mod.exports, require);
const {
  CaptureController,
  extensionForMime,
  MAX_DURATION_MS,
  MAX_BYTES,
  COUNTDOWN_SECONDS,
} = mod.exports;

let failures = 0;
function check(name, cond) {
  if (cond) {
    console.log(`ok - ${name}`);
  } else {
    failures += 1;
    console.error(`FAIL - ${name}`);
  }
}

/** Fake monotonic clock with manual timer pump. */
function fakeClock() {
  let now = 0;
  let nextId = 1;
  const timers = new Map(); // id -> {fn, at, interval}
  const clock = {
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
        if (best.t.interval > 0) {
          best.t.at = now + best.t.interval;
        } else {
          timers.delete(best.id);
        }
        best.t.fn();
      }
      now = target;
    },
    pending: () => timers.size,
  };
  return clock;
}

function fakeRecorder(mime) {
  const rec = {
    mimeType: mime,
    onChunk: null,
    onStop: null,
    onError: null,
    started: false,
    stopped: false,
    start() {
      this.started = true;
    },
    stop() {
      this.stopped = true;
      if (this.onStop) this.onStop();
    },
    push(bytes) {
      if (this.onChunk) this.onChunk({ data: new Uint8Array(bytes), mimeType: mime });
    },
  };
  return rec;
}

function setup(mime = 'video/webm') {
  const clock = fakeClock();
  const events = { states: [], errors: [], finalized: [], ticks: [] };
  const c = new CaptureController(clock, {
    onState: (s) => events.states.push(s),
    onError: (code, msg) => events.errors.push([code, msg]),
    onFinalized: (clip) => events.finalized.push(clip),
    onCountdownTick: (n) => events.ticks.push(n),
  });
  let lastRecorder = null;
  c.recorderFactory = () => {
    lastRecorder = fakeRecorder(mime);
    return lastRecorder;
  };
  return { clock, c, events, rec: () => lastRecorder };
}

// --- MIME allowlist ---
check('mp4 -> mp4', extensionForMime('video/mp4;codecs=avc1') === 'mp4');
check('webm -> webm', extensionForMime('video/webm') === 'webm');
check('quicktime -> mov', extensionForMime('video/quicktime') === 'mov');
check('matroska -> webm', extensionForMime('video/x-matroska') === 'webm');
check('audio rejected', extensionForMime('audio/webm') === null);
check('unknown rejected', extensionForMime('video/avi') === null);

// --- Permission education flow (C00->C01->C02->C03) ---
{
  const { c, events } = setup();
  c.requestRecord();
  check('education state', c.state === 'education');
  c.beginPermission();
  check('permission pending', c.state === 'permission');
  c.permissionResult(false, 'denied');
  check('denied returns to education', c.state === 'education');
  check('denied error E01', events.errors.some(([code]) => code === 'E01_PERMISSION_DENIED'));
  c.beginPermission();
  c.permissionResult(true);
  check('granted -> ready', c.state === 'ready');
}

// --- No hardware / unsupported ---
{
  const { c, events } = setup();
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(false, 'no-hardware');
  check('no hardware error', events.errors.some(([code]) => code === 'E02_NO_HARDWARE'));
  check('no hardware state error', c.state === 'error');
}

// --- Countdown cancellable, 0 bytes (gate 3) ---
{
  const { clock, c, events } = setup();
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  check('startCountdown ok', c.startCountdown() === true);
  check('countdown state', c.state === 'countdown');
  check('first tick is 3', events.ticks[0] === COUNTDOWN_SECONDS);
  clock.advance(1500);
  c.cancelCountdown();
  check('cancel countdown -> ready', c.state === 'ready');
  clock.advance(5000);
  check('no recording after cancel', c.state === 'ready' && events.finalized.length === 0);
  check('no bytes after cancel', c.recordedBytes === 0);
}

// --- Full countdown -> recording -> stop -> review ---
{
  const { clock, c, events, rec } = setup('video/mp4');
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  clock.advance(3000);
  check('recording after 3s', c.state === 'recording');
  check('recorder started', rec().started === true);
  rec().push(1024);
  rec().push(2048);
  clock.advance(5000);
  c.stopRecording('user');
  check('review after stop', c.state === 'review');
  check('finalized once', events.finalized.length === 1);
  const clip = events.finalized[0];
  check('clip bytes', clip.bytes === 3072);
  check('clip ext mp4', clip.extension === 'mp4');
  check('clip chunks kept', clip.chunks.length === 2);
  check('not interrupted', clip.interrupted === false);
}

// --- 60s hard bound (gate 4) ---
{
  const { clock, c, events, rec } = setup();
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  clock.advance(3000);
  rec().push(100);
  clock.advance(MAX_DURATION_MS + 500);
  check('auto-stopped at 60s', c.state === 'review');
  check('finalized at limit', events.finalized.length === 1);
  check('duration <= bound+slack', events.finalized[0].durationMs <= MAX_DURATION_MS + 2000);
}

// --- 100MiB hard bound ---
{
  const { clock, c, events, rec } = setup();
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  clock.advance(3000);
  rec().push(MAX_BYTES); // single overshooting chunk triggers guard
  check('auto-stopped at 100MiB', c.state !== 'recording');
  check('overshoot chunk rejected at finalize', events.errors.some(([code]) => code === 'E05_VALIDATION'));
}

// --- Empty blob rejected (C-E06) ---
{
  const { clock, c, events } = setup();
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  clock.advance(3000);
  c.stopRecording('user');
  check('empty blob error', events.errors.some(([code]) => code === 'E05_VALIDATION'));
  check('empty blob not finalized', events.finalized.length === 0);
}

// --- Unsupported codec rejected (C-E05) ---
{
  const { clock, c, events, rec } = setup('video/avi');
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  clock.advance(3000);
  rec().push(512);
  c.stopRecording('user');
  check('codec error E04', events.errors.some(([code]) => code === 'E04_CODEC'));
  check('codec clip not finalized', events.finalized.length === 0);
}

// --- Interrupted partial review keeps valid chunks (E15) ---
{
  const { clock, c, events, rec } = setup();
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  clock.advance(3000);
  rec().push(4096);
  c.stopRecording('interrupted');
  check('interrupted still review', c.state === 'review');
  check('interrupted flag', events.finalized[0].interrupted === true);
  check('interrupted chunks retained', events.finalized[0].bytes === 4096);
  check('E15 surfaced', events.errors.some(([code]) => code === 'E15_INTERRUPTED'));
}

// --- Discard / retake (C07 -> C00) ---
{
  const { clock, c, rec } = setup();
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  clock.advance(3000);
  rec().push(100);
  c.stopRecording('user');
  c.discard();
  check('discard -> idle', c.state === 'idle');
}

// --- Destroy mid-recording releases timers and recorder (C-E10) ---
{
  const { clock, c, rec } = setup();
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  clock.advance(3000);
  c.destroy();
  check('destroy -> idle', c.state === 'idle');
  check('destroy stopped recorder', rec().stopped === true);
  check('destroy cleared timers', clock.pending() === 0);
}

// --- Double finalize race guarded ---
{
  const { clock, c, events, rec } = setup();
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  clock.advance(3000);
  rec().push(100);
  c.stopRecording('user');
  c.stopRecording('user'); // no-op, not recording
  rec().stop(); // stray second onStop
  check('finalize race guarded', events.finalized.length === 1);
}

if (failures > 0) {
  console.error(`${failures} check(s) failed`);
  process.exit(1);
}
console.log('All capture controller checks passed.');
