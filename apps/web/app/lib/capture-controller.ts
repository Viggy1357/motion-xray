/**
 * Pure capture state controller for CameraRecorder.
 * No DOM, no network, no real timers: clock and media adapters are injected.
 * Implements camera state table C00-C07 and error rows C-E01..C-E11.
 *
 * Countdown uses a single monotonic deadline (clock.now() + COUNTDOWN_SECONDS*1000)
 * and a single setTimeout to that deadline; ticks are derived from the deadline,
 * not from chained timer decrements. This avoids drift and double-fire races.
 *
 * Recording schedules an early deadline (recordStartMs + CAPTURE_STOP_MS) tracked
 * by a single setTimeout, independent of the 250ms elapsed poll. The poll is
 * only used for UI updates. A stalled browser event loop can delay any timer;
 * strict final validation rejects a stop request beyond the 60s bound.
 */

export type CaptureState =
  | 'idle' // C00 entry / setup
  | 'education' // C01 permission education
  | 'permission' // C02 permission pending
  | 'ready' // C03 live preview ready
  | 'countdown' // C04 3s countdown
  | 'recording' // C05 recording
  | 'finishing' // C06 finalize
  | 'review' // C07 review
  | 'error';

export type CaptureErrorCode =
  | 'E01_PERMISSION_DENIED'
  | 'E02_NO_HARDWARE'
  | 'E03_UNSUPPORTED'
  | 'E04_CODEC'
  | 'E05_VALIDATION'
  | 'E15_INTERRUPTED';

export interface Clock {
  now(): number; // monotonic ms
  setTimeout(fn: () => void, ms: number): unknown;
  clearTimeout(id: unknown): void;
  setInterval(fn: () => void, ms: number): unknown;
  clearInterval(id: unknown): void;
}

export interface RecordedChunk {
  data: Uint8Array;
  mimeType: string;
}

export interface RecorderAdapter {
  readonly mimeType: string;
  start(): void;
  stop(): void; // requests stop; remaining chunks may be flushed asynchronously via onChunk before onStop fires
  onChunk: ((chunk: RecordedChunk) => void) | null;
  onStop: (() => void) | null;
  onError: ((err: unknown) => void) | null;
}

export interface FinalClip {
  chunks: RecordedChunk[];
  mimeType: string;
  extension: 'mp4' | 'webm' | 'mov';
  bytes: number;
  durationMs: number;
  interrupted: boolean;
}

export interface ControllerEvents {
  onState?: (state: CaptureState, prev: CaptureState) => void;
  onCountdownTick?: (remainingSeconds: number) => void;
  onElapsed?: (elapsedMs: number, bytes: number) => void;
  onFinalized?: (clip: FinalClip) => void;
  onError?: (code: CaptureErrorCode, message: string) => void;
}

export const MAX_DURATION_MS = 60_000;
// Schedule the deadline 1s before the strict 60s validation bound so the
// actual stop request and encoded media have headroom below the bound.
// Duration uses the actual stop-request time; a delayed stop beyond 60s
// is rejected. Encoder conversion latency does not extend that duration.
export const CAPTURE_STOP_MS = MAX_DURATION_MS - 1000;
export const MAX_BYTES = 100 * 1024 * 1024; // 100 MiB
export const COUNTDOWN_SECONDS = 3;

/** Blob allowlist: MP4 / WebM / MOV only. */
const MIME_EXT: Array<[RegExp, FinalClip['extension']]> = [
  [/^video\/mp4/i, 'mp4'],
  [/^video\/webm/i, 'webm'],
  [/^video\/quicktime/i, 'mov'],
  [/^video\/x-matroska/i, 'webm'],
];

export function extensionForMime(mime: string): FinalClip['extension'] | null {
  const base = mime.split(';')[0].trim();
  for (const [re, ext] of MIME_EXT) if (re.test(base)) return ext;
  return null;
}

export class CaptureController {
  private clock: Clock;
  private events: ControllerEvents;
  private _state: CaptureState = 'idle';
  private recorder: RecorderAdapter | null = null;

  private countdownTimer: unknown = null;
  private countdownDeadlineMs = 0;
  private countdownLastEmitted = -1;
  private countdownDisplayTimer: unknown = null;

  private elapsedTimer: unknown = null;
  private recordDeadlineTimer: unknown = null;
  private recordStartMs = 0;
  private recordDeadlineMs = 0;
  private recordDeadlineFired = false;
  private recordStopMs: number | null = null;
  private bytes = 0;
  private chunks: RecordedChunk[] = [];
  private mimeType = '';
  private interrupted = false;
  private stopping = false;
  private finalized = false;

  constructor(clock: Clock, events: ControllerEvents = {}) {
    this.clock = clock;
    this.events = events;
  }

  get state(): CaptureState {
    return this._state;
  }

  get recordedBytes(): number {
    return this.bytes;
  }

  private setState(next: CaptureState): void {
    if (next === this._state) return;
    const prev = this._state;
    this._state = next;
    this.events.onState?.(next, prev);
  }

  private fail(code: CaptureErrorCode, message: string): void {
    this.clearTimers();
    this.recorder = null;
    this.setState('error');
    this.events.onError?.(code, message);
  }

  /** C00 -> C01: user tapped Record; show permission education first. */
  requestRecord(): void {
    if (this._state === 'idle' || this._state === 'error' || this._state === 'review') {
      this.setState('education');
    }
  }

  /** C01 -> C02: user consented to camera prompt; caller performs getUserMedia. */
  beginPermission(): void {
    if (this._state === 'education') this.setState('permission');
  }

  /** Permission result. granted -> C03 ready; denied -> C-E01 back to education. */
  permissionResult(granted: boolean, reason?: 'denied' | 'no-hardware' | 'unsupported'): void {
    if (this._state !== 'permission' && this._state !== 'education') return;
    if (granted) {
      this.setState('ready');
      return;
    }
    if (reason === 'no-hardware') {
      this.fail('E02_NO_HARDWARE', 'No camera found on this device.');
    } else if (reason === 'unsupported') {
      this.fail('E03_UNSUPPORTED', 'Video capture is not supported here.');
    } else {
      this.setState('education');
      this.events.onError?.(
        'E01_PERMISSION_DENIED',
        'Camera access is not available. You can still choose a video file.',
      );
    }
  }

  /** Injected by host once a stream exists; returns a fresh recorder per take. */
  recorderFactory: (() => RecorderAdapter) | null = null;

  /**
   * C03 -> C04: explicit start; begins cancellable 3s monotonic countdown.
   * Uses a single deadline + single setTimeout; ticks are derived from the
   * deadline so chained timer decrements cannot drift or double-fire.
   */
  startCountdown(): boolean {
    if (this._state !== 'ready') return false;
    this.countdownDeadlineMs = this.clock.now() + COUNTDOWN_SECONDS * 1000;
    this.countdownLastEmitted = -1;
    this.setState('countdown');
    this.emitCountdownTick();
    this.countdownTimer = this.clock.setTimeout(() => this.fireCountdown(), COUNTDOWN_SECONDS * 1000);
    this.countdownDisplayTimer = this.clock.setInterval(() => this.emitCountdownTick(), 250);
    return true;
  }

  /**
   * Emit a countdown tick if the remaining seconds (ceil) have changed since
   * the last emission. Bounded updates: at most one tick per integer second.
   */
  private emitCountdownTick(): void {
    if (this._state !== 'countdown') return;
    const remainingMs = Math.max(0, this.countdownDeadlineMs - this.clock.now());
    const remaining = Math.ceil(remainingMs / 1000);
    if (remaining < 0) return;
    if (remaining !== this.countdownLastEmitted) {
      this.countdownLastEmitted = remaining;
      this.events.onCountdownTick?.(remaining);
    }
  }

  private fireCountdown(): void {
    this.countdownTimer = null;
    if (this.countdownDisplayTimer !== null) {
      this.clock.clearInterval(this.countdownDisplayTimer);
      this.countdownDisplayTimer = null;
    }
    if (this._state !== 'countdown') return;
    this.beginRecording();
  }

  /** Cancel countdown: releases timers, sends 0 bytes, returns to ready. */
  cancelCountdown(): void {
    if (this._state !== 'countdown') return;
    if (this.countdownTimer !== null) {
      this.clock.clearTimeout(this.countdownTimer);
      this.countdownTimer = null;
    }
    if (this.countdownDisplayTimer !== null) {
      this.clock.clearInterval(this.countdownDisplayTimer);
      this.countdownDisplayTimer = null;
    }
    this.countdownDeadlineMs = 0;
    this.countdownLastEmitted = -1;
    this.setState('ready');
  }

  private beginRecording(): void {
    if (!this.recorderFactory) {
      this.fail('E03_UNSUPPORTED', 'Video capture is not supported here.');
      return;
    }
    let rec: RecorderAdapter;
    try {
      rec = this.recorderFactory();
    } catch {
      this.fail('E04_CODEC', 'Could not encode the recording. Please try again.');
      return;
    }
    this.recorder = rec;
    this.chunks = [];
    this.bytes = 0;
    this.mimeType = rec.mimeType;
    this.interrupted = false;
    this.stopping = false;
    this.finalized = false;
    this.recordStartMs = this.clock.now();
    this.recordDeadlineMs = this.recordStartMs + CAPTURE_STOP_MS;
    this.recordDeadlineFired = false;
    this.recordStopMs = null;

    rec.onChunk = (chunk) => {
      // MediaRecorder delivers its final chunk AFTER stopRecording() has
      // transitioned the controller to 'finishing'. Accept chunks during
      // finishing so the final flush is preserved, but never after the
      // clip has been finalized. Oversize final chunks must reject safely
      // (no truncation, no silent drop) by routing through stopRecording.
      if (this.finalized) return;
      if (this._state !== 'recording' && this._state !== 'finishing') return;
      this.chunks.push(chunk);
      this.bytes += chunk.data.byteLength;
      if (this.bytes >= MAX_BYTES) this.stopRecording('limit');
    };
    rec.onStop = () => this.finalize();
    rec.onError = () => {
      this.destroy();
      this.fail('E04_CODEC', 'Could not encode the recording. Please try again.');
    };

    try {
      rec.start();
    } catch {
      this.recorder = null;
      this.fail('E04_CODEC', 'Could not encode the recording. Please try again.');
      return;
    }

    this.setState('recording');
    this.events.onElapsed?.(0, 0);
    // Absolute deadline timer: fires once at CAPTURE_STOP_MS (1s before the
    // strict 60s validation bound) so the native MediaRecorder final flush
    // and onStop callback have headroom to land inside MAX_DURATION_MS.
    // The 250ms poll below is purely for UI updates.
    this.recordDeadlineTimer = this.clock.setTimeout(
      () => this.handleRecordDeadline(),
      CAPTURE_STOP_MS,
    );
    this.elapsedTimer = this.clock.setInterval(() => {
      if (this._state !== 'recording') return;
      const elapsed = this.clock.now() - this.recordStartMs;
      this.events.onElapsed?.(elapsed, this.bytes);
      // Defensive: if the deadline timer was lost (e.g. clock skew), still
      // stop. The deadline timer is the primary trigger.
      if (elapsed >= CAPTURE_STOP_MS && !this.recordDeadlineFired) {
        this.handleRecordDeadline();
      }
    }, 250);
  }

  /**
   * Deadline callback: fires once when MAX_DURATION_MS has elapsed. Stops the
   * recording with reason 'limit'. Guarded against double-fire via
   * recordDeadlineFired.
   */
  private handleRecordDeadline(): void {
    if (this.recordDeadlineFired) return;
    if (this._state !== 'recording') return;
    this.recordDeadlineFired = true;
    this.stopRecording('limit');
  }

  /** C05 -> C06: explicit stop, hard limit, or interruption. */
  stopRecording(reason: 'user' | 'limit' | 'interrupted' = 'user'): void {
    if (this._state !== 'recording' || this.stopping) return;
    this.stopping = true;
    if (reason === 'interrupted') this.interrupted = true;
    // Capture the actual stop-request timestamp BEFORE rec.stop() so the
    // duration reflects when the user/limit/interrupt asked to stop, not
    // when the native encoder finished flushing. recordStopMs is nullable
    // and reset by destroy()/new-take so a stale value cannot leak across
    // takes.
    this.recordStopMs = this.clock.now();
    if (this.elapsedTimer !== null) {
      this.clock.clearInterval(this.elapsedTimer);
      this.elapsedTimer = null;
    }
    if (this.recordDeadlineTimer !== null) {
      this.clock.clearTimeout(this.recordDeadlineTimer);
      this.recordDeadlineTimer = null;
    }
    this.setState('finishing');
    const rec = this.recorder;
    if (rec) {
      try {
        rec.stop(); // triggers onStop -> finalize (async flush permitted)
      } catch {
        this.finalize();
      }
    } else {
      this.finalize();
    }
  }

  /** C06: finalize exactly once; validate nonempty blob and allowlisted type. */
  private finalize(): void {
    if (this.finalized) return;
    this.finalized = true;
    this.stopping = false;
    // Duration uses the stop-request timestamp captured in stopRecording(),
    // not the finalize instant. If recordStopMs is null (defensive: e.g.
    // finalize called without a prior stopRecording), fall back to
    // the current monotonic clock. Never invent a scheduled duration for
    // an unexpected native stop; an overlong take still fails validation.
    const stopMs = this.recordStopMs ?? this.clock.now();
    const durationMs = Math.max(0, stopMs - this.recordStartMs);
    this.recordStopMs = null;
    const chunks = this.chunks;
    const bytes = this.bytes;
    const mime = this.mimeType;
    this.recorder = null;
    this.chunks = [];

    if (bytes <= 0 || chunks.length === 0) {
      this.fail('E05_VALIDATION', 'Recording produced no usable data. Please retake or choose a video.');
      return;
    }
    const ext = extensionForMime(mime);
    if (!ext) {
      this.fail('E04_CODEC', 'Could not encode the recording. Please try again.');
      return;
    }
    // Hard limits: a clip must be strictly under 100MiB and within the 60s
    // bound. The byte guard in onChunk fires at >= MAX_BYTES, so any take that
    // tripped it always arrives here at or over the limit and must be rejected
    // rather than finalized. Duration is validated against the strict 60s
    // bound; delayed event-loop callbacks can still exceed it and fail.
    if (durationMs > MAX_DURATION_MS || bytes >= MAX_BYTES) {
      this.fail('E05_VALIDATION', 'Trim this clip to 60 seconds and 100MiB or less.');
      return;
    }
    const clip: FinalClip = {
      chunks,
      mimeType: mime,
      extension: ext,
      bytes,
      durationMs,
      interrupted: this.interrupted,
    };
    this.setState('review');
    this.events.onFinalized?.(clip);
    if (this.interrupted) {
      this.events.onError?.('E15_INTERRUPTED', 'Recording was interrupted. The clip may be incomplete.');
    }
  }

  /** C07 -> C00: retake/cancel after host discarded the clip. */
  discard(): void {
    if (this._state === 'review' || this._state === 'error') {
      this.clearTimers();
      this.recorder = null;
      this.setState('idle');
    }
  }

  /** Full teardown: tracks/timers/recorder races (C-E08/C-E10). */
  destroy(): void {
    if (this.countdownDisplayTimer !== null) {
      this.clock.clearInterval(this.countdownDisplayTimer);
      this.countdownDisplayTimer = null;
    }
    this.clearTimers();
    const rec = this.recorder;
    this.recorder = null;
    if (rec) {
      rec.onChunk = null;
      rec.onStop = null;
      rec.onError = null;
      try {
        rec.stop();
      } catch {
        /* ignore */
      }
    }
    this.chunks = [];
    this.bytes = 0;
    this.recordDeadlineFired = false;
    this.recordDeadlineMs = 0;
    this.recordStopMs = null;
    this.countdownDeadlineMs = 0;
    this.countdownLastEmitted = -1;
    this.setState('idle');
  }

  private clearTimers(): void {
    if (this.countdownTimer !== null) {
      this.clock.clearTimeout(this.countdownTimer);
      this.countdownTimer = null;
    }
    if (this.elapsedTimer !== null) {
      this.clock.clearInterval(this.elapsedTimer);
      this.elapsedTimer = null;
    }
    if (this.recordDeadlineTimer !== null) {
      this.clock.clearTimeout(this.recordDeadlineTimer);
      this.recordDeadlineTimer = null;
    }
  }
}
