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
import styles from './CameraRecorder.module.css';

export interface CameraRecorderProps {
  onUse: (file: File) => void;
  onClose: () => void;
  exerciseLabel: string;
  guidance: string;
  disabled?: boolean;
}

type Facing = 'environment' | 'user';

interface RecorderAdapterImpl extends RecorderAdapter {
  inner: MediaRecorder;
}

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

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const reviewRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const controllerRef = useRef<CaptureController | null>(null);
  const clipUrlRef = useRef<string | null>(null);
  const destroyedRef = useRef(false);

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
        const blob = new Blob(
          clip.chunks.map((c) => c.data.slice().buffer as ArrayBuffer),
          { type: clip.mimeType },
        );
        const file = new File([blob], `recorded-set.${clip.extension}`, { type: clip.mimeType });
        const url = URL.createObjectURL(blob);
        clipUrlRef.current = url;
        setClipUrl(url);
        setClipFile(file);
        setClipInterrupted(clip.interrupted);
      },
      onError: (_code, message) => {
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
      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: mode } },
          audio: false, // no microphone, ever
        });
      } catch (err) {
        const name = err instanceof DOMException ? err.name : '';
        if (name === 'NotFoundError' || name === 'OverconstrainedError') {
          controller.permissionResult(false, 'no-hardware');
        } else {
          controller.permissionResult(false, 'denied');
        }
        return false;
      }
      if (destroyedRef.current) {
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
        setCanSwitch(devices.filter((d) => d.kind === 'videoinput').length > 1);
      } catch {
        setCanSwitch(false);
      }
      controller.recorderFactory = (): RecorderAdapter => {
        const inner = new MediaRecorder(stream, { mimeType: mime });
        const adapter: RecorderAdapterImpl = {
          inner,
          mimeType: inner.mimeType || mime,
          onChunk: null,
          onStop: null,
          onError: null,
          start() {
            inner.ondataavailable = (e: BlobEvent): void => {
              if (e.data.size > 0 && adapter.onChunk) {
                void e.data.arrayBuffer().then((buf) => {
                  adapter.onChunk?.({ data: new Uint8Array(buf), mimeType: adapter.mimeType });
                });
              }
            };
            inner.onstop = (): void => {
              // Allow the final dataavailable arrayBuffer to land before finalize.
              setTimeout(() => adapter.onStop?.(), 0);
            };
            inner.onerror = (): void => adapter.onError?.(new Error('recorder error'));
            inner.start(1000);
          },
          stop() {
            if (inner.state !== 'inactive') inner.stop();
            else adapter.onStop?.();
          },
        };
        return adapter;
      };
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
          // Switch failure retains working camera attempt on previous facing.
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
    releaseClip();
    controllerRef.current?.destroy();
    releaseStream();
    onClose();
  }, [onClose, releaseClip, releaseStream]);

  const seconds = Math.floor(elapsedMs / 1000);
  const maxSeconds = Math.floor(MAX_DURATION_MS / 1000);
  const mirrored = facing === 'user';

  return (
    <div className={styles.root} role="dialog" aria-label={`Record a set: ${exerciseLabel}`}>
      <div className={styles.header}>
        <h2 className={styles.title}>Record a set — {exerciseLabel}</h2>
        <button type="button" className={styles.closeBtn} onClick={handleCancel} aria-label="Cancel and close">
          ✕
        </button>
      </div>

      <p className={styles.guidance}>{guidance}</p>
      <p className={styles.hint}>
        Framing corners are guidance only; good framing cannot be verified automatically. No audio is
        recorded and the microphone is never requested.
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
            <button type="button" className={styles.primary} onClick={handleConsentContinue} disabled={disabled}>
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
            <button type="button" className={styles.primary} onClick={handleStartCountdown} disabled={disabled}>
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
            onClick={() => controllerRef.current?.cancelCountdown()}
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
            <button type="button" className={styles.primary} onClick={handleUse} disabled={disabled || !clipFile}>
              Use this video
            </button>
            <button type="button" className={styles.secondary} onClick={handleRetake}>
              {confirmDiscard ? 'Confirm discard & retake' : 'Retake'}
            </button>
            {confirmDiscard ? (
              <button type="button" className={styles.secondary} onClick={() => setConfirmDiscard(false)}>
                Keep clip
              </button>
            ) : null}
            <button type="button" className={styles.secondary} onClick={handleCancel}>
              Cancel
            </button>
          </>
        ) : null}
      </div>
    </div>
  );
}
