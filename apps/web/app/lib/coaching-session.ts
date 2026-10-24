// Memory-only cache of ACTUAL CoachingResult payloads for the current session.
// No localStorage, no network, no invented strings. SSR-safe pure helpers.

export interface SessionCoaching {
  analysisId: string;
  exercise: string;
  observation: string | null;
  nextSetCue: string | null;
  segmentOrdinal: number | null;
  sourceS: number | null;
}

export interface CoachingResultInput {
  status: string;
  summary?: string | null;
  observations: string[];
  next_set_cue?: string | null;
  limitations: string[];
}

export interface SessionRep {
  ordinal: number;
  start_s: number;
}

const MAX_ENTRIES = 8;
const TTL_MS = 30 * 60 * 1000;

interface CacheEntry {
  value: SessionCoaching;
  storedAt: number;
}

const cache = new Map<string, CacheEntry>();

// Strict validated prefix: 'Segment N (' where N must match an ACTUAL rep
// ordinal with a finite start_s. No match -> no replay association.
const SEGMENT_PREFIX = /^Segment (\d+) \(/;

function matchSegment(
  text: string,
  reps: ReadonlyArray<SessionRep>
): { ordinal: number; startS: number } | null {
  const m = SEGMENT_PREFIX.exec(text);
  if (!m) return null;
  const ordinal = Number(m[1]);
  if (!Number.isInteger(ordinal)) return null;
  const rep = reps.find(
    (r) =>
      r.ordinal === ordinal &&
      typeof r.start_s === "number" &&
      Number.isFinite(r.start_s)
  );
  if (!rep) return null;
  return { ordinal: rep.ordinal, startS: rep.start_s };
}

function asString(v: unknown): string | null {
  return typeof v === "string" && v.length > 0 ? v : null;
}

function isFresh(entry: CacheEntry, now: number): boolean {
  return now - entry.storedAt <= TTL_MS;
}

function evict(now: number): void {
  for (const [k, e] of [...cache]) {
    if (!isFresh(e, now)) cache.delete(k);
  }
  while (cache.size > MAX_ENTRIES) {
    const oldest = cache.keys().next();
    if (oldest.done) break;
    cache.delete(oldest.value);
  }
}

function notify(analysisId: string | null): void {
  if (typeof window === "undefined" || typeof window.dispatchEvent !== "function") return;
  try {
    window.dispatchEvent(
      new CustomEvent("mxr:coaching-session-changed", { detail: { analysisId } })
    );
  } catch {
    /* non-browser environment: no-op */
  }
}

export function storeSessionCoaching(
  analysisId: string,
  exercise: string,
  result: CoachingResultInput,
  reps: ReadonlyArray<SessionRep>
): void {
  if (typeof analysisId !== "string" || !analysisId) return;
  const now = Date.now();
  evict(now);
  // Only status "ok" with actual strings is cached; anything else clears the slot.
  if (!result || result.status !== "ok") {
    if (cache.delete(analysisId)) notify(analysisId);
    return;
  }
  const observations = Array.isArray(result.observations) ? result.observations : [];
  const first = observations.length > 0 ? asString(observations[0]) : null;
  const observation = first ?? asString(result.summary);
  const nextSetCue = asString(result.next_set_cue);
  const seg = observation !== null ? matchSegment(observation, reps) : null;
  cache.set(analysisId, {
    value: {
      analysisId,
      exercise: typeof exercise === "string" ? exercise : "",
      observation,
      nextSetCue,
      segmentOrdinal: seg ? seg.ordinal : null,
      sourceS: seg ? seg.startS : null,
    },
    storedAt: now,
  });
  evict(now);
  notify(analysisId);
}

export function readSessionCoaching(analysisId: string): SessionCoaching | null {
  if (typeof analysisId !== "string" || !analysisId) return null;
  const entry = cache.get(analysisId);
  if (!entry) return null;
  if (!isFresh(entry, Date.now())) {
    cache.delete(analysisId);
    return null;
  }
  // LRU touch
  cache.delete(analysisId);
  cache.set(analysisId, entry);
  return { ...entry.value };
}

export function clearSessionCoaching(analysisId?: string): void {
  if (typeof analysisId === "string") {
    if (cache.delete(analysisId)) notify(analysisId);
    return;
  }
  if (cache.size === 0) return;
  cache.clear();
  notify(null);
}

// React hook: re-reads on cache-change events and invalidates on TTL expiry.
// Imported lazily-safe: this module has no top-level React requirement beyond
// the hook itself, and pure helpers above remain SSR-safe.
import { useEffect, useState } from "react";

export function useSessionCoaching(analysisId: string): SessionCoaching | null {
  const [value, setValue] = useState<SessionCoaching | null>(() =>
    readSessionCoaching(analysisId)
  );

  useEffect(() => {
    setValue(readSessionCoaching(analysisId));
    let timer: ReturnType<typeof setTimeout> | null = null;
    const armExpiry = () => {
      if (timer !== null) clearTimeout(timer);
      timer = setTimeout(() => {
        setValue(readSessionCoaching(analysisId));
      }, TTL_MS + 50);
    };
    const onChanged = (ev: Event) => {
      const detail = (ev as CustomEvent).detail as { analysisId?: string } | undefined;
      if (detail && detail.analysisId !== null && detail.analysisId !== undefined && detail.analysisId !== analysisId) return;
      setValue(readSessionCoaching(analysisId));
      armExpiry();
    };
    armExpiry();
    window.addEventListener("mxr:coaching-session-changed", onChanged);
    return () => {
      if (timer !== null) clearTimeout(timer);
      window.removeEventListener("mxr:coaching-session-changed", onChanged);
    };
  }, [analysisId]);

  return value;
}
