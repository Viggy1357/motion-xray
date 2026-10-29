'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { ReactElement } from 'react';
import {
  CaptureController,
  COUNTDOWN_SECONDS,
  MAX_DURATION_MS,
  extensionForMime,
} from '../lib/capture-controller';
import type { CaptureState, Clock, FinalClip, RecorderAdapter } from '../lib/capture-controller';
import { createRecorderAdapter } from '../lib/recorder-adapter';
import styles from './CameraRecorder.module.css';

export interface CameraRecorderProps {
  onUse: (file: File) => void;
  onClose: () => void;
  exerciseLabel: string;
  guidance: string;
  disabled?: boolean;
}

type Facing = 'environment' | 'user';

/** Browser-safe clock adapter: monotonic now + bound timer functions. */
function createBrowserClock(): Clock {
  const perf: Pick<Performance, 'now'> | null =
    typeof performance !== 'undefined' && typeof performance.now === 'function'
      ? performance
      : null;
  return {
    now: perf ? () => perf.now() : () => Date.now(),
    setTimeout: (fn, ms) => window.setTimeout(fn, ms),
    clearTimeout: (id) => window.clearTimeout(id as number),
    setInterval: (fn, ms) => window.setInterval(fn, ms),
    clearInterval: (id) => window.clearInterval(id as number),
  };
}

function pickMime(): string | null {
  if (typeof MediaRecorder === 'undefined') return null;
  const candidates = [
    'video/mp4;codecs=avc1',
    'video/mp4',
    'video/webm;codecs=vp9',
    'video/webm;codecs=vp8',
    'video/webm',
    'video/quicktime',
  ];
  for (const m of candidates) {
    try {
      if (MediaRecorder.isTypeSupported(m) && extensionForMime(m)) return m;
    } catch {
      /* ignore */
    }
  }
  return null;
}

/** Conservative bitrate/timeslice headroom: 4 Mbps target, 1s timeslice. */
const RECORDER_BITRATE = 4_000_000;
const RECORDER_TIMESLICE_MS = 1000;

export default function CameraRecorder({
  onUse,
  onClose,
  exerciseLabel,
  guidance,
  disabled = false,
}: CameraRecorderProps): ReactElement {
  const [state, setState] = useState<CaptureState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [countdown, setCountdown] = useState<number>(COUNTDOWN_SECONDS);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [facing, setFacing] = useState<Facing>('environment');
  const [canSwitch, setCanSwitch] = useState(false);
  const [clipUrl, setClipUrl] = useState<string | null>(null);
  const [clipFile, setClipFile] = useState<File | null>(null);
  const [clipInterrupted, setClipInterrupted] = useState(false);
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const reviewRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const controllerRef = useRef<CaptureController | null>(null);
  const clipUrlRef = useRef<string | null>(null);
  const destroyedRef = useRef(false);
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const lastFocusRef = useRef<HTMLElement | null>(null);
  // Refs mirror the latest state so the focus-trap effect can read them
  // without re-running on every state change.
  const stateRef = useRef<CaptureState>('idle');
  const confirmDiscardRef = useRef(false);
  const confirmCancelRef = useRef(false);
  const clipFileRef = useRef<File | null>(null);
  // Generation counter for getUserMedia: each acquireStream call increments
  // it; any in-flight request whose generation is stale must stop its tracks
  // so we never end up with two live streams at once.
  const acquireGenRef = useRef(0);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);
  useEffect(() => {
    confirmDiscardRef.current = confirmDiscard;
  }, [confirmDiscard]);
  useEffect(() => {
    confirmCancelRef.current = confirmCancel;
  }, [confirmCancel]);
  useEffect(() => {
    clipFileRef.current = clipFile;
  }, [clipFile]);

  const releaseStream = useCallback((): void => {
    const s = streamRef.current;
    streamRef.current = null;
    if (s) for (const t of s.getTracks()) t.stop();
    if (videoRef.current) videoRef.current.srcObject = null;
  }, []);

  const releaseClip = useCallback((): void => {
    if (clipUrlRef.current) {
      URL.revokeObjectURL(clipUrlRef.current);
      clipUrlRef.current = null;
    }
    setClipUrl(null);
    setClipFile(null);
    setClipInterrupted(false);
  }, []);

  // Create controller once.
  useEffect(() => {
    destroyedRef.current = false;
    const controller = new CaptureController(createBrowserClock(), {
      onState: (s) => {
        if (!destroyedRef.current) setState(s);
      },
      onCountdownTick: (n) => {
        if (!destroyedRef.current) setCountdown(n);
      },
      onElapsed: (ms) => {
        if (!destroyedRef.current) setElapsedMs(ms);
      },
      onFinalized: (clip: FinalClip) => {
        if (destroyedRef.current) return;
        releaseStream();
        // Async Blob conversion is serialized and awaited before exposing the
        // File to the parent. The controller has already validated duration
        // and bytes; we still re-check here so a delayed conversion cannot
        // smuggle an oversized or empty blob into Review.
        const mime = clip.mimeType;
        const ext = clip.extension;
        const parts = clip.chunks.map((c) => c.data.slice().buffer as ArrayBuffer);
        const blob = new Blob(parts, { type: mime });
        if (blob.size <= 0) {
          setError('Recording produced no usable data. Please retake or choose a video.');
          setState('error');
          return;
        }
        if (blob.size >= 100 * 1024 * 1024) {
          setError('Trim this clip to 60 seconds and 100MiB or less.');
          setState('error');
          return;
        }
        const file = new File([blob], `recorded-set.${ext}`, { type: mime });
        const url = URL.createObjectURL(blob);
        clipUrlRef.current = url;
        setClipUrl(url);
        setClipFile(file);
        setClipInterrupted(clip.interrupted);
      },
      onError: (_code, message) => {
        releaseStream();
        if (!destroyedRef.current) setError(message);
      },
    });
    controllerRef.current = controller;
    return () => {
      destroyedRef.current = true;
      controller.destroy();
      releaseStream();
      if (clipUrlRef.current) {
        URL.revokeObjectURL(clipUrlRef.current);
        clipUrlRef.current = null;
      }
    };
  }, [releaseStream]);

  // Warn on unload mid-recording (C-E10).
  useEffect(() => {
    if (state !== 'recording' && state !== 'countdown') return;
    const handler = (e: BeforeUnloadEvent): void => {
      e.preventDefault();
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [state]);

  // Track-ended / visibility / pagehide interruptions (C-E08/C-E10).
  // pagehide and visibilitychange must flush capture and release resources
  // promptly so the browser can reclaim hardware safely.
  useEffect(() => {
    const stream = streamRef.current;
    if (!stream) return;
    const onEnded = (): void => {
      const c = controllerRef.current;
      if (c && c.state === 'recording') c.stopRecording('interrupted');
    };
    for (const t of stream.getTracks()) t.addEventListener('ended', onEnded);
    const onVisibility = (): void => {
      if (document.visibilityState === 'hidden') {
        const c = controllerRef.current;
        if (c && c.state === 'recording') c.stopRecording('interrupted');
      }
    };
    const onPageHide = (): void => {
      const c = controllerRef.current;
      // pagehide is a hard teardown signal: stop capture, flush final chunks,
      // and release the stream so the browser can reclaim hardware.
      if (c && (c.state === 'recording' || c.state === 'countdown')) {
        c.stopRecording('interrupted');
      }
      releaseStream();
    };
    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener('pagehide', onPageHide);
    return () => {
      for (const t of stream.getTracks()) t.removeEventListener('ended', onEnded);
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('pagehide', onPageHide);
    };
  }, [state, releaseStream]);

  // Focus trap + restore focus for the modal dialog.
  // Capture the originally-focused element ONCE on mount, then trap focus
  // using the latest state via refs so the effect does not re-run on every
  // state change. Restore focus only on unmount.
  useEffect(() => {
    const root = dialogRef.current;
    if (!root) return;
    lastFocusRef.current = document.activeElement as HTMLElement | null;
    const focusables = (): HTMLElement[] =>
      Array.from(
        root.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      );
    const initial = focusables()[0];
    if (initial) initial.focus();
    const onKey = (e: KeyboardEvent): void => {
      if (e.key === 'Escape') {
        e.preventDefault();
        const curState = stateRef.current;
        const curConfirmDiscard = confirmDiscardRef.current;
        const curConfirmCancel = confirmCancelRef.current;
        const curClipFile = clipFileRef.current;
        if (curConfirmDiscard) {
          setConfirmDiscard(false);
        } else if (curConfirmCancel) {
          setConfirmCancel(false);
        } else if (curState === 'review' && curClipFile) {
          // Unsaved clip: require explicit confirmation rather than silently
          // discarding on Escape.
          setConfirmCancel(true);
        } else if (curState === 'countdown') {
          handleCancelCountdown();
        } else if (curState === 'recording') {
          controllerRef.current?.stopRecording('user');
        } else {
          handleCancel();
        }
        return;
      }
      if (e.key !== 'Tab') return;
      const list = focusables();
      if (list.length === 0) return;
      const first = list[0];
      const last = list[list.length - 1];
      const active = document.activeElement as HTMLElement | null;
      if (e.shiftKey && active === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    };
    root.addEventListener('keydown', onKey);
    return () => {
      root.removeEventListener('keydown', onKey);
      // Restore focus only on real unmount, not on every state change.
      const prev = lastFocusRef.current;
      if (prev && typeof prev.focus === 'function') prev.focus();
    };
  }, []);

  const acquireStream = useCallback(
    async (mode: Facing): Promise<boolean> => {
      const controller = controllerRef.current;
      if (!controller) return false;
      if (!navigator.mediaDevices?.getUserMedia) {
        controller.permissionResult(false, 'unsupported');
        return false;
      }
      const mime = pickMime();
      if (!mime) {
        controller.permissionResult(false, 'unsupported');
        return false;
      }
      // Generation counter: any in-flight acquireStream with a stale
      // generation must stop its tracks so we never hold two streams at once.
      const gen = ++acquireGenRef.current;
      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: mode } },
          audio: false, // no microphone, ever
        });
      } catch (err) {
        if (gen !== acquireGenRef.current) return false;
        const name = err instanceof DOMException ? err.name : '';
        if (name === 'NotFoundError' || name === 'OverconstrainedError') {
          controller.permissionResult(false, 'no-hardware');
        } else {
          controller.permissionResult(false, 'denied');
        }
        return false;
      }
      if (destroyedRef.current || gen !== acquireGenRef.current) {
        for (const t of stream.getTracks()) t.stop();
        return false;
      }
      releaseStream();
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play().catch(() => undefined);
      }
      // Front switch only when another video device plausibly exists.
      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        if (gen === acquireGenRef.current) {
          setCanSwitch(devices.filter((d) => d.kind === 'videoinput').length > 1);
        }
      } catch {
        if (gen === acquireGenRef.current) setCanSwitch(false);
      }
      controller.recorderFactory = (): RecorderAdapter =>
        createRecorderAdapter({
          stream,
          mimeType: mime,
          timesliceMs: RECORDER_TIMESLICE_MS,
          videoBitsPerSecond: RECORDER_BITRATE,
        });
      controller.permissionResult(true);
      return true;
    },
    [releaseStream],
  );

  const handleRecordIntent = useCallback((): void => {
    setError(null);
    controllerRef.current?.requestRecord();
  }, []);

  const handleConsentContinue = useCallback((): void => {
    const controller = controllerRef.current;
    if (!controller) return;
    controller.beginPermission();
    void acquireStream(facing);
  }, [acquireStream, facing]);

  const handleSwitchFacing = useCallback((): void => {
    const next: Facing = facing === 'environment' ? 'user' : 'environment';
    setFacing(next);
    const controller = controllerRef.current;
    if (controller && state === 'ready') {
      controller.beginPermission();
      void acquireStream(next).then((ok) => {
        if (!ok) {
          setFacing(facing);
          controller.beginPermission();
          void acquireStream(facing);
        }
      });
    }
  }, [acquireStream, facing, state]);

  const handleStartCountdown = useCallback((): void => {
    setError(null);
    setElapsedMs(0);
    controllerRef.current?.startCountdown();
  }, []);

  // Explicit countdown cancel: stops the stream, cancels timers, and resets
  // the controller so the camera is released even though the UI claimed it
  // would be. Reacquisition only happens on a new explicit user intent.
  const handleCancelCountdown = useCallback((): void => {
    const controller = controllerRef.current;
    if (!controller) return;
    controller.cancelCountdown();
    releaseStream();
    // Reset the controller so any pending recorder state is cleared and the
    // next user intent must explicitly request a new stream.
    controller.destroy();
  }, [releaseStream]);

  const handleStop = useCallback((): void => {
    controllerRef.current?.stopRecording('user');
  }, []);

  const handleRetake = useCallback((): void => {
    if (!confirmDiscard) {
      setConfirmDiscard(true);
      return;
    }
    setConfirmDiscard(false);
    releaseClip();
    controllerRef.current?.discard();
  }, [confirmDiscard, releaseClip]);

  const handleUse = useCallback((): void => {
    if (clipFile) onUse(clipFile); // File only; parent owns upload + consent.
  }, [clipFile, onUse]);

  const handleCancel = useCallback((): void => {
    if (clipFile && !confirmCancel) {
      setConfirmCancel(true);
      return;
    }
    setConfirmCancel(false);
    releaseClip();
    controllerRef.current?.destroy();
    releaseStream();
    onClose();
  }, [clipFile, confirmCancel, onClose, releaseClip, releaseStream]);

  const seconds = Math.floor(elapsedMs / 1000);
  const maxSeconds = Math.floor(MAX_DURATION_MS / 1000);
  const mirrored = facing === 'user';

  return (
    <div
      className={styles.root}
      role="dialog"
      aria-modal="true"
      aria-label={`Record a set: ${exerciseLabel}`}
      ref={dialogRef}
    >
      <div className={styles.header}>
        <h2 className={styles.title}>Record a set — {exerciseLabel}</h2>
        <button
          type="button"
          className={styles.closeBtn}
          onClick={handleCancel}
          aria-label="Cancel and close"
        >
          ✕
        </button>
      </div>

      <p className={styles.guidance}>{guidance}</p>
      <p className={styles.hint}>
        Framing corners are guidance only; good framing cannot be verified automatically. No audio is
        recorded and the microphone is never requested. Recording stops automatically at 60 seconds or
        100MiB; the camera is released if you cancel the countdown.
      </p>

      {error ? (
        <p className={styles.error} role="alert">
          {error}
        </p>
      ) : null}

      <div className={styles.stage}>
        {state === 'review' && clipUrl ? (
          <video
            ref={reviewRef}
            className={styles.video}
            src={clipUrl}
            controls
            playsInline
            aria-label="Recorded clip preview"
          />
        ) : (
          <>
            <video
              ref={videoRef}
              className={`${styles.video} ${mirrored ? styles.mirrored : ''}`}
              muted
              playsInline
              autoPlay
              aria-label="Live camera preview"
            />
            <div className={styles.corners} aria-hidden="true">
              <span className={styles.cornerTL} />
              <span className={styles.cornerTR} />
              <span className={styles.cornerBL} />
              <span className={styles.cornerBR} />
            </div>
            {state === 'countdown' ? (
              <div className={styles.countdown} role="status" aria-live="assertive">
                {countdown}
              </div>
            ) : null}
            {state === 'recording' ? (
              <div className={styles.recBadge} role="status" aria-live="polite">
                ● REC {seconds}s / {maxSeconds}s
              </div>
            ) : null}
          </>
        )}
      </div>

      <div className={styles.controls}>
        {state === 'idle' || state === 'error' ? (
          <>
            <button
              type="button"
              className={styles.primary}
              onClick={handleRecordIntent}
              disabled={disabled}
            >
              Record a set
            </button>
            <button type="button" className={styles.secondary} onClick={handleCancel}>
              Choose a video file instead
            </button>
          </>
        ) : null}

        {state === 'education' ? (
          <div className={styles.education}>
            <p>
              To record, this browser needs camera access. Video stays on this device until you
              explicitly choose Upload &amp; analyse. If you prefer not to grant access, you can
              choose an existing video file instead.
            </p>
            <button
              type="button"
              className={styles.primary}
              onClick={handleConsentContinue}
              disabled={disabled}
            >
              Continue to camera
            </button>
            <button type="button" className={styles.secondary} onClick={handleCancel}>
              Choose a video file instead
            </button>
          </div>
        ) : null}

        {state === 'permission' ? <p role="status">Waiting for camera permission…</p> : null}

        {state === 'ready' ? (
          <>
            {canSwitch ? (
              <button type="button" className={styles.secondary} onClick={handleSwitchFacing}>
                Switch to {facing === 'environment' ? 'front' : 'rear'} camera
              </button>
            ) : null}
            <button
              type="button"
              className={styles.primary}
              onClick={handleStartCountdown}
              disabled={disabled}
            >
              Start recording
            </button>
            <button type="button" className={styles.secondary} onClick={handleCancel}>
              Cancel
            </button>
          </>
        ) : null}

        {state === 'countdown' ? (
          <button
            type="button"
            className={styles.secondary}
            onClick={handleCancelCountdown}
          >
            Cancel countdown
          </button>
        ) : null}

        {state === 'recording' ? (
          <button type="button" className={styles.danger} onClick={handleStop}>
            Stop
          </button>
        ) : null}

        {state === 'finishing' ? <p role="status">Finishing recording…</p> : null}

        {state === 'review' ? (
          <>
            {clipInterrupted ? (
              <p className={styles.error} role="alert">
                Recording was interrupted. The clip may be incomplete.
              </p>
            ) : null}
            {confirmDiscard ? (
              <p role="alert">Discard this unsaved recording? This cannot be undone.</p>
            ) : null}
            {confirmCancel ? (
              <p role="alert">
                Close without saving? The recorded clip will be discarded.
              </p>
            ) : null}
            <button
              type="button"
              className={styles.primary}
              onClick={handleUse}
              disabled={disabled || !clipFile}
            >
              Use this video
            </button>
            <button type="button" className={styles.secondary} onClick={handleRetake}>
              {confirmDiscard ? 'Confirm discard & retake' : 'Retake'}
            </button>
            {confirmDiscard ? (
              <button
                type="button"
                className={styles.secondary}
                onClick={() => setConfirmDiscard(false)}
              >
                Keep clip
              </button>
            ) : null}
            <button type="button" className={styles.secondary} onClick={handleCancel}>
              {confirmCancel ? 'Confirm close & discard' : 'Cancel'}
            </button>
            {confirmCancel ? (
              <button
                type="button"
                className={styles.secondary}
                onClick={() => setConfirmCancel(false)}
              >
                Keep clip
              </button>
            ) : null}
          </>
        ) : null}
      </div>
    </div>
  );
}
