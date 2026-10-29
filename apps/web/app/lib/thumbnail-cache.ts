/**
 * Browser-safe in-memory thumbnail cache.
 *
 * Design contract (for integrator):
 *  - Module-scope LRU keyed by `${analysisId}|${cue}`. Different analyses and
 *    different cues for the same analysis get distinct keys; parallel
 *    instances never share or clobber each other's frame.
 *  - Entries are reference-counted. A URL is not revoked while refs > 0
 *    during normal release/drop paths; however sweepExpired() force-revokes
 *    expired entries even when refs > 0 so private pixels cannot outlive
 *    the 5-minute TTL, and subscribers are notified via the 'revoke' event.
 *  - 5-minute hard expiry. Expiry is checked on every acquire AND on a
 *    mounted timer so stale entries are cleared even when no new get() runs.
 *  - Scoped revocation: dropThumbnailsForAnalysis(id) clears every cue for
 *    that analysis synchronously, marks in-use entries stale, and prevents
 *    pending extractions from repopulating the cache (tombstone).
 *  - Cross-instance consistent fallback: clearThumbnailCache() is the only
 *    global wipe path; it is idempotent and safe to call repeatedly.
 *  - No persistent storage. No private media URLs are stored; only blob:
 *    object URLs created from canvas captures.
 *  - Generation tokens: every cache mutation bumps a global generation and a
 *    per-analysis generation. Subscribers receive notifications on revoke /
 *    clear so UI can drop stale URLs and abort pending work.
 *  - Events dispatched on the window for the integrator:
 *      mxr:media-revoked    detail: { analysisId: string }
 *      mxr:thumbnails-clear  detail: undefined
 *    Existing events are documented; no new endpoints are introduced.
 */

export interface CacheEntry {
  url: string;
  createdAt: number;
  refs: number;
  stale: boolean;
  tombstoned: boolean;
}

export type ThumbnailKey = string;

export type CacheEvent =
  | { kind: 'revoke'; analysisId: string; generation: number }
  | { kind: 'clear'; generation: number };

export type CacheSubscriber = (ev: CacheEvent) => void;

export const MAX_ENTRIES = 8;
export const MAX_AGE_MS = 5 * 60 * 1000;
export const SWEEP_INTERVAL_MS = 30 * 1000;

const cache = new Map<ThumbnailKey, CacheEntry>();
const tombstonedKeys = new Set<ThumbnailKey>();
const subscribers = new Set<CacheSubscriber>();

let globalGeneration = 0;
const analysisGenerations = new Map<string, number>();

let sweepTimer: ReturnType<typeof setInterval> | null = null;

function ensureSweeper(): void {
  if (sweepTimer !== null) return;
  if (typeof setInterval === 'undefined') return;
  sweepTimer = setInterval(() => {
    sweepExpired(Date.now());
  }, SWEEP_INTERVAL_MS);
  // Allow Node/test teardown to exit without keeping the loop alive.
  if (typeof (sweepTimer as { unref?: () => void }).unref === 'function') {
    (sweepTimer as { unref: () => void }).unref();
  }
}

function isUsable(entry: CacheEntry, now: number): boolean {
  if (entry.stale || entry.tombstoned) return false;
  return now - entry.createdAt <= MAX_AGE_MS;
}

function revokeIfIdle(key: ThumbnailKey, entry: CacheEntry): void {
  if (entry.refs <= 0) {
    try {
      URL.revokeObjectURL(entry.url);
    } catch {
      /* ignore: URL may already be revoked */
    }
    cache.delete(key);
  }
}

function evictOldestIdle(): boolean {
  for (const [k, e] of cache) {
    if (e.refs <= 0) {
      try {
        URL.revokeObjectURL(e.url);
      } catch {
        /* ignore */
      }
      cache.delete(k);
      return true;
    }
  }
  return false;
}

function notify(ev: CacheEvent): void {
  for (const sub of [...subscribers]) {
    try {
      sub(ev);
    } catch {
      /* subscriber errors must not break the cache */
    }
  }
}

function bumpGlobal(): number {
  globalGeneration += 1;
  return globalGeneration;
}

function bumpAnalysis(analysisId: string): number {
  const next = (analysisGenerations.get(analysisId) ?? 0) + 1;
  analysisGenerations.set(analysisId, next);
  return next;
}

/** Acquire a cached thumbnail; bumps refcount and returns the entry, or null. */
export function acquireThumbnail(
  key: ThumbnailKey,
  generation?: number,
): CacheEntry | null {
  if (typeof generation === 'number') {
    const analysisId = key.split('|', 1)[0];
    const current = analysisGenerations.get(analysisId) ?? 0;
    if (generation !== current) return null;
  }
  const entry = cache.get(key);
  if (!entry) return null;
  const now = Date.now();
  if (!isUsable(entry, now)) {
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

/** Release a previously acquired thumbnail; revokes when refs hit zero. */
export function releaseThumbnail(key: ThumbnailKey): void {
  const entry = cache.get(key);
  if (!entry) return;
  entry.refs = Math.max(0, entry.refs - 1);
  if (!isUsable(entry, Date.now())) entry.stale = true;
  revokeIfIdle(key, entry);
}

/**
 * Store a freshly captured thumbnail. If a tombstone exists for this key
 * (because the analysis was revoked while extraction was in flight), the
 * new URL is revoked immediately and the entry is NOT cached. This is the
 * "pending extraction cannot repopulate after revoke" guarantee.
 *
 * Same-key re-store policy:
 *  - If the incoming URL is identical to the existing entry's URL, the call
 *    is a no-op: the live URL is never revoked and ownership is preserved.
 *  - If the existing entry is still usable (not stale, not tombstoned) and
 *    has refs > 0, the existing entry is preserved and the incoming URL is
 *    revoked as a redundant duplicate. The acquisition fails (no overwrite).
 *  - If the existing entry is stale/tombstoned and idle (refs === 0), it is
 *    revoked and replaced by the incoming URL.
 *  - If the existing entry is stale/tombstoned but still held (refs > 0),
 *    ownership is preserved and the incoming URL is revoked; the held entry
 *    will be revoked when its last ref drops.
 */
export function storeThumbnail(key: ThumbnailKey, url: string): void {
  if (tombstonedKeys.has(key)) {
    try {
      URL.revokeObjectURL(url);
    } catch {
      /* ignore */
    }
    return;
  }
  const existing = cache.get(key);
  if (existing) {
    if (existing.url === url) {
      // Same URL re-acquired: never revoke the live URL.
      return;
    }
    const now = Date.now();
    const existingUsable = isUsable(existing, now);
    if (existingUsable && existing.refs > 0) {
      // Live entry still held: preserve ownership, drop the redundant URL.
      try {
        URL.revokeObjectURL(url);
      } catch {
        /* ignore */
      }
      return;
    }
    if (existing.refs > 0) {
      // Stale/tombstoned but still held: preserve ownership, drop incoming.
      try {
        URL.revokeObjectURL(url);
      } catch {
        /* ignore */
      }
      return;
    }
    // Idle (refs === 0): safe to revoke and replace.
    try {
      URL.revokeObjectURL(existing.url);
    } catch {
      /* ignore */
    }
    cache.delete(key);
  }
  cache.set(key, { url, createdAt: Date.now(), refs: 0, stale: false, tombstoned: false });
  while (cache.size > MAX_ENTRIES) {
    if (!evictOldestIdle()) break;
  }
  ensureSweeper();
}

/**
 * Scoped revocation: synchronously clear every cached thumbnail for one
 * analysis. Marks in-use entries stale so they are revoked the moment their
 * last ref drops, and tombstones every key so any pending extraction that
 * resolves later cannot repopulate the cache. Bumps the per-analysis
 * generation so any in-flight extraction that captured an older generation
 * will be rejected on its post-extraction acquire().
 */
export function dropThumbnailsForAnalysis(analysisId: string): void {
  const prefix = `${analysisId}|`;
  for (const [key, entry] of [...cache]) {
    if (!key.startsWith(prefix)) continue;
    entry.stale = true;
    entry.tombstoned = true;
    tombstonedKeys.add(key);
    revokeIfIdle(key, entry);
  }
  // Tombstone the common "auto" cue so callers without sourceS cannot
  // repopulate after revoke.
  tombstonedKeys.add(`${analysisId}|auto`);
  const gen = bumpAnalysis(analysisId);
  bumpGlobal();
  notify({ kind: 'revoke', analysisId, generation: gen });
}

/**
 * Explicit global clear: revokes all idle URLs, marks in-use ones stale,
 * and tombstones every key so any in-flight extraction cannot repopulate.
 * Bumps the global generation so any extraction that captured an older
 * generation is rejected on its post-extraction acquire(). Idempotent and
 * safe to call repeatedly.
 */
export function clearThumbnailCache(): void {
  for (const [key, entry] of [...cache]) {
    entry.stale = true;
    entry.tombstoned = true;
    tombstonedKeys.add(key);
    revokeIfIdle(key, entry);
  }
  bumpGlobal();
  notify({ kind: 'clear', generation: globalGeneration });
}

/**
 * Sweep expired entries. Called by the mounted interval AND by acquire()
 * so stale entries are cleared even when no new get() runs. Force-revokes
 * expired entries even when refs > 0 so private pixels cannot outlive the
 * 5-minute TTL.
 */
export function sweepExpired(now: number = Date.now()): number {
  let removed = 0;
  const revokedAnalysisIds = new Set<string>();
  for (const [key, entry] of [...cache]) {
    if (now - entry.createdAt > MAX_AGE_MS) {
      entry.stale = true;
      entry.tombstoned = true;
      tombstonedKeys.add(key);
      try {
        URL.revokeObjectURL(entry.url);
      } catch {
        /* ignore */
      }
      cache.delete(key);
      removed += 1;
      const analysisId = key.split('|', 1)[0];
      if (analysisId) revokedAnalysisIds.add(analysisId);
    }
  }
  for (const analysisId of revokedAnalysisIds) {
    const gen = bumpAnalysis(analysisId);
    notify({ kind: 'revoke', analysisId, generation: gen });
  }
  return removed;
}

/** Current global generation token. */
export function getGlobalGeneration(): number {
  return globalGeneration;
}

/** Current per-analysis generation token. */
export function getAnalysisGeneration(analysisId: string): number {
  return analysisGenerations.get(analysisId) ?? 0;
}

/** Subscribe to cache events. Returns an unsubscribe function. */
export function subscribeToCache(sub: CacheSubscriber): () => void {
  subscribers.add(sub);
  return () => {
    subscribers.delete(sub);
  };
}

/** Test/debug helpers. Not for production use. */
export function _cacheSize(): number {
  return cache.size;
}

export function _hasKey(key: ThumbnailKey): boolean {
  return cache.has(key);
}

export function _isTombstoned(key: ThumbnailKey): boolean {
  return tombstonedKeys.has(key);
}

export function _resetForTests(): void {
  for (const [, entry] of cache) {
    try {
      URL.revokeObjectURL(entry.url);
    } catch {
      /* ignore */
    }
  }
  cache.clear();
  tombstonedKeys.clear();
  subscribers.clear();
  analysisGenerations.clear();
  globalGeneration = 0;
  if (sweepTimer !== null) {
    clearInterval(sweepTimer);
    sweepTimer = null;
  }
}
