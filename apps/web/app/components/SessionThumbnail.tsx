'use client';

import React, { useEffect, useRef, useState } from 'react';
import styles from './ProgressWidgets.module.css';
import {
  acquireThumbnail,
  releaseThumbnail,
  storeThumbnail,
  dropThumbnailsForAnalysis,
  clearThumbnailCache,
  getAnalysisGeneration,
  getGlobalGeneration,
  subscribeToCache,
  type ThumbnailKey,
} from '../lib/thumbnail-cache';

export interface SessionThumbnailProps {
  analysisId: string;
  sourceS?: number;
  label?: string;
}

const LOAD_TIMEOUT_MS = 15000;

function keyFor(analysisId: string, sourceS?: number): ThumbnailKey {
  const cue = typeof sourceS === 'number' && Number.isFinite(sourceS) ? sourceS.toFixed(3) : 'auto';
  return `${analysisId}|${cue}`;
}

export default function SessionThumbnail({ analysisId, sourceS, label }: SessionThumbnailProps) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const heldKeyRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const unsubscribeRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    const key = keyFor(analysisId, sourceS);
    // Capture the generation BEFORE any extraction so a revoke/clear that
    // happens mid-flight causes the post-extraction acquire() to be rejected.
    const capturedAnalysisGen = getAnalysisGeneration(analysisId);
    const capturedGlobalGen = getGlobalGeneration();

    const releaseHeld = () => {
      if (heldKeyRef.current !== null) {
        releaseThumbnail(heldKeyRef.current);
        heldKeyRef.current = null;
      }
    };

    const cached = acquireThumbnail(key, capturedAnalysisGen);
    if (cached) {
      heldKeyRef.current = key;
      setUrl(cached.url);
      setFailed(false);
      return releaseHeld;
    }

    const controller = new AbortController();
    abortRef.current = controller;
    const timeout = setTimeout(() => controller.abort(), LOAD_TIMEOUT_MS);
    let active = true;
    setUrl(null);
    setFailed(false);

    (async () => {
      try {
        let proxyTime = 0;
        if (typeof sourceS === 'number' && Number.isFinite(sourceS)) {
          // A requested source cue REQUIRES the actual measured timestamp map;
          // without it we never assume source==proxy and show the fallback.
          const map = await fetchTimestampMap(analysisId, controller.signal);
          if (!active) return;
          const mapped = map ? proxyTimeAt(map, sourceS) : null;
          if (mapped === null) {
            setFailed(true);
            return;
          }
          proxyTime = mapped;
        }
        const objectUrl = await captureFrame(analysisId, proxyTime, controller.signal);
        if (!active) {
          if (objectUrl) URL.revokeObjectURL(objectUrl);
          return;
        }
        // Generation guard: if the cache was revoked or cleared while we
        // were extracting, do NOT repopulate. The storeThumbnail tombstone
        // check is the second line of defence.
        if (
          getAnalysisGeneration(analysisId) !== capturedAnalysisGen ||
          getGlobalGeneration() !== capturedGlobalGen
        ) {
          if (objectUrl) URL.revokeObjectURL(objectUrl);
          setFailed(true);
          return;
        }
        if (objectUrl) {
          storeThumbnail(key, objectUrl);
          const entry = acquireThumbnail(key, capturedAnalysisGen);
          if (entry) {
            heldKeyRef.current = key;
            setUrl(entry.url);
          } else {
            setFailed(true);
          }
        } else {
          setFailed(true);
        }
      } catch {
        // AbortError (unmount, prop change, bounded-load timeout) and any
        // fetch/decode failure land here: no unhandled rejection, just fallback.
        if (active && !controller.signal.aborted) setFailed(true);
      }
    })();

    return () => {
      active = false;
      clearTimeout(timeout);
      controller.abort();
      abortRef.current = null;
      releaseHeld();
    };
  }, [analysisId, sourceS]);

  // Subscribe to cache events so a revoke/clear that happens after mount
  // immediately drops the displayed URL and aborts any pending extraction.
  useEffect(() => {
    const onRevoked = (ev: Event) => {
      const detail = (ev as CustomEvent).detail as { analysisId?: string } | undefined;
      if (detail?.analysisId === analysisId) {
        dropThumbnailsForAnalysis(analysisId);
        abortRef.current?.abort();
        if (heldKeyRef.current !== null) {
          releaseThumbnail(heldKeyRef.current);
          heldKeyRef.current = null;
        }
        setUrl(null);
        setFailed(true);
      }
    };
    const onClear = () => {
      clearThumbnailCache();
      abortRef.current?.abort();
      if (heldKeyRef.current !== null) {
        releaseThumbnail(heldKeyRef.current);
        heldKeyRef.current = null;
      }
      setUrl(null);
      setFailed(true);
    };
    window.addEventListener('mxr:media-revoked', onRevoked);
    window.addEventListener('mxr:thumbnails-clear', onClear);
    const unsubscribe = subscribeToCache((ev) => {
      if (ev.kind === 'revoke' && ev.analysisId === analysisId) {
        abortRef.current?.abort();
        if (heldKeyRef.current !== null) {
          releaseThumbnail(heldKeyRef.current);
          heldKeyRef.current = null;
        }
        setUrl(null);
        setFailed(true);
      } else if (ev.kind === 'clear') {
        abortRef.current?.abort();
        if (heldKeyRef.current !== null) {
          releaseThumbnail(heldKeyRef.current);
          heldKeyRef.current = null;
        }
        setUrl(null);
        setFailed(true);
      }
    });
    unsubscribeRef.current = unsubscribe;
    return () => {
      window.removeEventListener('mxr:media-revoked', onRevoked);
      window.removeEventListener('mxr:thumbnails-clear', onClear);
      unsubscribe();
      unsubscribeRef.current = null;
    };
  }, [analysisId]);

  if (!url || failed) {
    return (
      <span className={styles.thumbFallback} role="img" aria-label={label ?? 'Session preview unavailable'}>
        <svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <rect x="3" y="5" width="18" height="14" rx="2" fill="none" stroke="currentColor" strokeWidth="1.5" />
          <path d="M10 9.5v5l4-2.5z" fill="currentColor" />
        </svg>
      </span>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img className={styles.thumb} src={url} alt={label ?? 'Session video frame'} />
  );
}

// --- Local helpers (kept private to this module; no private media routes) ---

const MAX_MAP_BYTES = 8 * 1024 * 1024;

async function readBoundedText(res: Response, maxBytes: number, signal: AbortSignal): Promise<string> {
  const reader = res.body?.getReader();
  if (!reader) throw new Error('artifact body unreadable');
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    for (;;) {
      if (signal.aborted) throw new DOMException('aborted', 'AbortError');
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > maxBytes) {
        await reader.cancel();
        throw new Error('timestamp map exceeds size limit');
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const buf = new Uint8Array(total);
  let off = 0;
  for (const c of chunks) {
    buf.set(c, off);
    off += c.byteLength;
  }
  return new TextDecoder().decode(buf);
}

async function fetchTimestampMap(analysisId: string, signal: AbortSignal): Promise<ProxyTimestampMap | null> {
  const res = await fetch(
    `/api/analyses/${encodeURIComponent(analysisId)}/artifacts/timestamps`,
    { signal, credentials: 'include', headers: { Accept: 'application/json' } }
  );
  if (!res.ok) return null;
  try {
    const text = await readBoundedText(res, MAX_MAP_BYTES, signal);
    return parseTimestampMap(text);
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err;
    return null;
  }
}

function waitFor(video: HTMLVideoElement, event: string, signal: AbortSignal): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    const onOk = () => {
      cleanup();
      resolve();
    };
    const onErr = () => {
      cleanup();
      reject(new Error('video load failed'));
    };
    const onAbort = () => {
      cleanup();
      reject(new DOMException('aborted', 'AbortError'));
    };
    const cleanup = () => {
      video.removeEventListener(event, onOk);
      video.removeEventListener('error', onErr);
      signal.removeEventListener('abort', onAbort);
    };
    video.addEventListener(event, onOk, { once: true });
    video.addEventListener('error', onErr, { once: true });
    signal.addEventListener('abort', onAbort, { once: true });
  });
}

async function captureFrame(analysisId: string, proxyTimeS: number, signal: AbortSignal): Promise<string | null> {
  const video = document.createElement('video');
  video.muted = true;
  video.autoplay = false;
  video.preload = 'auto';
  video.src = `/api/analyses/${encodeURIComponent(analysisId)}/artifacts/proxy`;
  try {
    await waitFor(video, 'loadedmetadata', signal);
    const duration = Number.isFinite(video.duration) ? video.duration : proxyTimeS;
    const t = Math.max(0, Math.min(proxyTimeS, Math.max(0, duration - 0.05)));
    if (t > 0) {
      const seeked = waitFor(video, 'seeked', signal);
      video.currentTime = t;
      await seeked;
    } else if (video.readyState < 2) {
      await waitFor(video, 'loadeddata', signal);
    }
    const w = video.videoWidth;
    const h = video.videoHeight;
    if (!w || !h) return null;
    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    ctx.drawImage(video, 0, 0, w, h);
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob((b) => resolve(b), 'image/jpeg', 0.7)
    );
    if (!blob) return null;
    return URL.createObjectURL(blob);
  } finally {
    video.removeAttribute('src');
    video.load();
  }
}

// Re-exported types from pose-overlay (kept local to avoid leaking imports).
export type { ProxyTimestampMap } from '../pose-overlay';
import { parseTimestampMap, proxyTimeAt, type ProxyTimestampMap } from '../pose-overlay';
