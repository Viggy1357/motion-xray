'use client';

import React, { useEffect, useRef, useState } from 'react';
import styles from './ProgressWidgets.module.css';
import { parseTimestampMap, proxyTimeAt, type ProxyTimestampMap } from '../pose-overlay';

export interface SessionThumbnailProps {
  analysisId: string;
  sourceS?: number;
  label?: string;
}

interface CacheEntry {
  url: string;
  createdAt: number;
  refs: number;
  stale: boolean;
}

const MAX_ENTRIES = 8;
const MAX_AGE_MS = 5 * 60 * 1000;
const MAX_MAP_BYTES = 8 * 1024 * 1024;
const LOAD_TIMEOUT_MS = 15000;

// Module-scope in-memory LRU cache; never persisted to localStorage and never
// holds private URLs or image data outside blob: object URLs. Entries are
// reference-counted so a URL is never revoked while a mounted instance renders
// it; keys include BOTH analysisId and sourceS so parallel instances for the
// same analysis at different cues never share or clobber each other's frame.
const cache = new Map<string, CacheEntry>();

function keyFor(analysisId: string, sourceS?: number): string {
  const cue = typeof sourceS === 'number' && Number.isFinite(sourceS) ? sourceS.toFixed(3) : 'auto';
  return `${analysisId}|${cue}`;
}

function isUsable(entry: CacheEntry): boolean {
  return !entry.stale && Date.now() - entry.createdAt <= MAX_AGE_MS;
}

function revokeIfIdle(key: string, entry: CacheEntry): void {
  if (entry.refs <= 0) {
    URL.revokeObjectURL(entry.url);
    cache.delete(key);
  }
}

function acquire(key: string): CacheEntry | null {
  const entry = cache.get(key);
  if (!entry) return null;
  if (!isUsable(entry)) {
    entry.stale = true;
    revokeIfIdle(key, entry);
    return null;
  }
  entry.refs += 1;
  // LRU touch
  cache.delete(key);
  cache.set(key, entry);
  return entry;
}

function release(key: string): void {
  const entry = cache.get(key);
  if (!entry) return;
  entry.refs = Math.max(0, entry.refs - 1);
  if (!isUsable(entry)) entry.stale = true;
  revokeIfIdle(key, entry);
}

function store(key: string, url: string): void {
  const existing = cache.get(key);
  if (existing) {
    existing.stale = true;
    revokeIfIdle(key, existing);
  }
  cache.set(key, { url, createdAt: Date.now(), refs: 0, stale: false });
  // Evict oldest idle entries only; in-use entries are never revoked under a
  // rendering instance even if that temporarily exceeds MAX_ENTRIES.
  while (cache.size > MAX_ENTRIES) {
    let evicted = false;
    for (const [k, e] of cache) {
      if (e.refs <= 0) {
        URL.revokeObjectURL(e.url);
        cache.delete(k);
        evicted = true;
        break;
      }
    }
    if (!evicted) break;
  }
}

/** Drop every cached thumbnail for one analysis (scoped delete event). */
export function dropThumbnail(analysisId: string): void {
  const prefix = `${analysisId}|`;
  for (const [key, entry] of [...cache]) {
    if (!key.startsWith(prefix)) continue;
    entry.stale = true;
    revokeIfIdle(key, entry);
  }
}

/** Explicit global clear: revokes all idle URLs, marks in-use ones stale. */
export function clearThumbnailCache(): void {
  for (const [key, entry] of [...cache]) {
    entry.stale = true;
    revokeIfIdle(key, entry);
  }
}

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

/** Fetch and validate the canonical measured proxy timestamp map. */
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
      // Seek-to-zero: no 'seeked' fires when currentTime is already 0, so wait
      // for the first decodable frame instead.
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

export default function SessionThumbnail({ analysisId, sourceS, label }: SessionThumbnailProps) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const heldKeyRef = useRef<string | null>(null);

  useEffect(() => {
    const key = keyFor(analysisId, sourceS);
    const releaseHeld = () => {
      if (heldKeyRef.current !== null) {
        release(heldKeyRef.current);
        heldKeyRef.current = null;
      }
    };

    const cached = acquire(key);
    if (cached) {
      heldKeyRef.current = key;
      setUrl(cached.url);
      setFailed(false);
      return releaseHeld;
    }

    const controller = new AbortController();
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
        if (objectUrl) {
          store(key, objectUrl);
          const entry = acquire(key);
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
      releaseHeld();
    };
  }, [analysisId, sourceS]);

  // Scoped delete: only events naming THIS analysis invalidate this thumbnail.
  // A global wipe requires the explicit mxr:thumbnails-clear event.
  useEffect(() => {
    const onRevoked = (ev: Event) => {
      const detail = (ev as CustomEvent).detail as { analysisId?: string } | undefined;
      if (detail?.analysisId === analysisId) {
        dropThumbnail(analysisId);
        setUrl(null);
        setFailed(true);
      }
    };
    const onClear = () => {
      clearThumbnailCache();
      setUrl(null);
      setFailed(true);
    };
    window.addEventListener('mxr:media-revoked', onRevoked);
    window.addEventListener('mxr:thumbnails-clear', onClear);
    return () => {
      window.removeEventListener('mxr:media-revoked', onRevoked);
      window.removeEventListener('mxr:thumbnails-clear', onClear);
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
