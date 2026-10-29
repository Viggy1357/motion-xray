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

function fakeRecorder(mime, opts = {}) {
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
    // Default: synchronous flush (legacy behavior). When opts.deferredStop is
    // true, stop() only marks the flag; the test must call emitFinalFlush()
    // to deliver the late final chunk + onStop, mirroring real MediaRecorder
    // behavior where the final chunk arrives after stop() returns.
    stop() {
      this.stopped = true;
      if (!opts.deferredStop && this.onStop) this.onStop();
    },
    push(bytes) {
      if (this.onChunk) this.onChunk({ data: new Uint8Array(bytes), mimeType: mime });
    },
    emitFinalFlush(bytes) {
      if (this.onChunk) this.onChunk({ data: new Uint8Array(bytes), mimeType: mime });
      if (this.onStop) this.onStop();
    },
  };
  return rec;
}

function setup(mime = 'video/webm', opts = {}) {
  const clock = fakeClock();
  const events = { states: [], errors: [], finalized: [], ticks: [], elapsed: [] };
  const c = new CaptureController(clock, {
    onState: (s) => events.states.push(s),
    onError: (code, msg) => events.errors.push([code, msg]),
    onFinalized: (clip) => events.finalized.push(clip),
    onCountdownTick: (n) => events.ticks.push(n),
    onElapsed: (ms, b) => events.elapsed.push([ms, b]),
  });
  let lastRecorder = null;
  c.recorderFactory = () => {
    lastRecorder = fakeRecorder(mime, opts);
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

// --- Countdown uses single deadline, not chained decrement ---
{
  const { clock, c, events } = setup();
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  // Countdown schedules the deadline timer plus the display interval.
  check('countdown schedules deadline + display timers', clock.pending() === 2);
  clock.advance(COUNTDOWN_SECONDS * 1000);
  check('countdown fires once', c.state === 'recording');
  check('no extra countdown ticks', events.ticks.length === 3);
}

// --- Countdown emits 3/2/1 based on ceil((deadline-now)/1000) ---
{
  const { clock, c, events } = setup();
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  // Initial tick is 3.
  check('countdown tick 3 at start', events.ticks[0] === 3);
  // Advance 500ms: ceil((3000-500)/1000) = 3, no new tick.
  clock.advance(500);
  check('countdown no tick at 500ms', events.ticks.length === 1);
  // Advance to 1001ms total: ceil((3000-1001)/1000) = 2.
  clock.advance(501);
  check('countdown tick 2 at ~1s', events.ticks[events.ticks.length - 1] === 2);
  // Advance to 2001ms total: ceil((3000-2001)/1000) = 1.
  clock.advance(1000);
  check('countdown tick 1 at ~2s', events.ticks[events.ticks.length - 1] === 1);
  // Advance to deadline: recording begins.
  clock.advance(999);
  check('countdown fires at deadline', c.state === 'recording');
  // Total ticks: 3, 2, 1 (no duplicates, no zero at deadline).
  check('countdown ticks bounded', JSON.stringify(events.ticks) === '[3,2,1]');
  check('countdown never emits zero', !events.ticks.includes(0));
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

// --- 60s hard bound via deadline timer (gate 4) ---
{
  const { clock, c, events, rec } = setup();
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  clock.advance(3000);
  rec().push(100);
  // Advance exactly to MAX_DURATION_MS: deadline timer fires.
  clock.advance(MAX_DURATION_MS);
  check('auto-stopped at 60s', c.state === 'review');
  check('finalized at limit', events.finalized.length === 1);
  // Duration is measured at finalize (stop request time), which is the
  // deadline instant. Must be <= MAX_DURATION_MS + 2000 flush slack.
  check('duration <= bound+slack', events.finalized[0].durationMs <= MAX_DURATION_MS + 2000);
  // Exact bound: duration must not exceed 60s + 2s slack.
  check('duration not 62s slack', events.finalized[0].durationMs <= MAX_DURATION_MS + 2000);
}

// --- 60s bound: deadline timer fires exactly once, no double-stop ---
{
  const { clock, c, events, rec } = setup();
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  clock.advance(3000);
  rec().push(100);
  // Advance well past the deadline.
  clock.advance(MAX_DURATION_MS + 5000);
  check('finalized exactly once at deadline', events.finalized.length === 1);
  check('state review after deadline', c.state === 'review');
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

// --- Duration uses stop request time, not conversion delay ---
{
  const { clock, c, events, rec } = setup();
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  clock.advance(3000);
  rec().push(100);
  clock.advance(2000);
  c.stopRecording('user');
  // Duration is measured at finalize (stop request time), not at conversion.
  check('duration reflects stop time', events.finalized[0].durationMs === 2000);
}

// --- Late flush: duration uses stop-requested time even if finalize is late ---
{
  const { clock, c, events, rec } = setup();
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  clock.advance(3000);
  rec().push(100);
  clock.advance(2000);
  c.stopRecording('user');
  // Simulate a late flush: advance the clock further before checking.
  clock.advance(10000);
  // Duration must still reflect the stop-requested time, not the late flush.
  check('late flush duration uses stop time', events.finalized[0].durationMs === 2000);
}

// --- Repeated stopRecording calls are idempotent ---
{
  const { clock, c, events, rec } = setup();
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  clock.advance(3000);
  rec().push(100);
  c.stopRecording('user');
  c.stopRecording('user');
  c.stopRecording('limit');
  c.stopRecording('interrupted');
  check('repeated stopRecording idempotent', events.finalized.length === 1);
  check('repeated stopRecording state review', c.state === 'review');
}

// --- Teardown after stop clears all timers ---
{
  const { clock, c, rec } = setup();
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  clock.advance(3000);
  rec().push(100);
  c.stopRecording('user');
  c.destroy();
  check('teardown after stop clears timers', clock.pending() === 0);
  check('teardown after stop -> idle', c.state === 'idle');
}

// --- Shortened tick does not drift countdown ---
{
  const { clock, c, events } = setup();
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  // Advance in small irregular steps; ticks must still be 3, 2, 1.
  clock.advance(100);
  clock.advance(400);
  clock.advance(500);
  clock.advance(1);
  clock.advance(999);
  clock.advance(500);
  clock.advance(500);
  check('shortened tick no drift', JSON.stringify(events.ticks) === '[3,2,1]');
  check('shortened tick fires at deadline', c.state === 'recording');
}

// --- Deadline timer is independent of 250ms poll ---
{
  const { clock, c, events, rec } = setup();
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  clock.advance(3000);
  rec().push(100);
  // Advance in steps that skip the 250ms poll entirely.
  clock.advance(MAX_DURATION_MS);
  check('deadline fires without poll', c.state === 'review');
  check('deadline fires without poll finalized', events.finalized.length === 1);
}

// --- Deadline is scheduled at CAPTURE_STOP_MS (59000), not MAX_DURATION_MS ---
{
  const { clock, c, events, rec } = setup();
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  clock.advance(3000);
  rec().push(100);
  // At exactly CAPTURE_STOP_MS the deadline timer fires; the controller is
  // in 'finishing' (not yet 'review') because the synchronous fake recorder
  // calls onStop immediately, which finalizes.
  clock.advance(MAX_DURATION_MS - 1000);
  check('deadline scheduled at CAPTURE_STOP_MS', c.state === 'review');
  check('deadline scheduled at CAPTURE_STOP_MS finalized', events.finalized.length === 1);
  // Duration must reflect the stop-request time (CAPTURE_STOP_MS), not a
  // fabricated 60s.
  check('deadline duration uses stop time', events.finalized[0].durationMs === MAX_DURATION_MS - 1000);
}

// --- Late flush: final chunk arrives AFTER finishing; must be preserved ---
{
  // Use a deferred-stop fake recorder so stop() does NOT call onStop. The
  // test manually advances the clock past the stop-request instant, then
  // emits the late final chunk + onStop. This mirrors real MediaRecorder
  // behavior where the final chunk arrives after stop() returns.
  const { clock, c, events, rec } = setup('video/webm', { deferredStop: true });
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  clock.advance(3000);
  rec().push(2048);
  rec().push(1024);
  clock.advance(2000);
  c.stopRecording('user');
  // Controller is now in 'finishing'; recorder.stop() ran but did NOT call
  // onStop. Advance the clock well past the stop-request instant to
  // simulate encoder/mux flush latency.
  check('finishing after stop', c.state === 'finishing');
  check('not finalized before flush', events.finalized.length === 0);
  clock.advance(10000);
  // Late final chunk + onStop arrive now.
  rec().emitFinalFlush(4096);
  check('finalized after late flush', events.finalized.length === 1);
  const clip = events.finalized[0];
  // All three chunks must be retained (no truncation, no silent drop).
  check('late flush retains all chunks', clip.chunks.length === 3);
  check('late flush retains all bytes', clip.bytes === 2048 + 1024 + 4096);
  // Duration must reflect the original stop-request time (2000ms), NOT the
  // late flush instant.
  check('late flush duration uses stop time', clip.durationMs === 2000);
  check('late flush state review', c.state === 'review');
}

// --- Late flush: finalize runs exactly once even with late onStop ---
{
  const { clock, c, events, rec } = setup('video/webm', { deferredStop: true });
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  clock.advance(3000);
  rec().push(100);
  clock.advance(2000);
  c.stopRecording('user');
  clock.advance(10000);
  rec().emitFinalFlush(100);
  // A stray second onStop must not double-finalize.
  rec().emitFinalFlush(100);
  check('late flush finalize exactly once', events.finalized.length === 1);
}

// --- Oversize final chunk during finishing rejects safely (no truncation) ---
{
  const { clock, c, events, rec } = setup('video/webm', { deferredStop: true });
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  clock.advance(3000);
  rec().push(50 * 1024 * 1024);
  clock.advance(2000);
  c.stopRecording('user');
  // Late final chunk pushes total over MAX_BYTES; must reject, not truncate.
  rec().emitFinalFlush(60 * 1024 * 1024);
  check('oversize final chunk rejected', events.errors.some(([code]) => code === 'E05_VALIDATION'));
  check('oversize final chunk not finalized', events.finalized.length === 0);
}

// --- Conversion delay past 60s does not extend an earlier stop request ---
{
  const { clock, c, events, rec } = setup('video/webm', { deferredStop: true });
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  clock.advance(3000);
  rec().push(100);
  // Stop requested at 2000ms (well under 60s).
  clock.advance(2000);
  c.stopRecording('user');
  // But the late flush arrives after the clock has advanced past 60s.
  clock.advance(MAX_DURATION_MS);
  rec().emitFinalFlush(100);
  // Duration is still 2000ms (stop-request time), so this should finalize.
  check('late flush within bound finalizes', events.finalized.length === 1);
  check('late flush within bound duration', events.finalized[0].durationMs === 2000);
}

// --- Deadline timer fires at CAPTURE_STOP_MS, not MAX_DURATION_MS ---
{
  const { clock, c, events, rec } = setup();
  c.requestRecord();
  c.beginPermission();
  c.permissionResult(true);
  c.startCountdown();
  clock.advance(3000);
  rec().push(100);
  // At CAPTURE_STOP_MS - 1ms the deadline has not fired.
  clock.advance(MAX_DURATION_MS - 1001);
  check('before CAPTURE_STOP_MS still recording', c.state === 'recording');
  // Advance the last 1ms to hit CAPTURE_STOP_MS exactly.
  clock.advance(1);
  check('at CAPTURE_STOP_MS deadline fires', c.state === 'review');
  check('at CAPTURE_STOP_MS finalized', events.finalized.length === 1);
}

if (failures > 0) {
  console.error(`${failures} check(s) failed`);
  process.exit(1);
}
console.log('All capture controller checks passed.');
