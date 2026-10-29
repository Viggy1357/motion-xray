// apps/web/app/lib/milo-state.ts
// Pure Milo state controller. No DOM, no network, no globals.
// Deterministic mapping from authoritative app state to a bounded
// visual decision. History survives idle/hidden transitions so a
// re-render or re-read of the latest report never replays a cheer.

export type MiloVisual = 'idle' | 'attentive' | 'cheer' | 'static';
export type MiloSize = 'hero' | 'compact';
export type MiloResultStatus = 'ready' | 'partial' | 'failed' | 'cancelled' | 'expired';

export interface MiloLayerManifest {
  version: number;
  layers: ReadonlyArray<{
    id: string;
    src: string;
    pivot?: { x: number; y: number };
    z?: number;
  }>;
}

export interface MiloLatestResult {
  jobId: string;
  status: MiloResultStatus;
  usable: boolean;
}

export interface MiloInput {
  recording: boolean;
  hidden: boolean;
  reducedMotion: boolean;
  activeJobId: string | null;
  latestResult: MiloLatestResult | null;
  pendingSaveJobId: string | null;
  saveConfirmedJobId: string | null;
}

export interface MiloDecision {
  visual: MiloVisual;
  size: MiloSize;
  eventKey: string | null;
  seenEventKeys: string[];
  lastReactionAt: number | null;
}

export const MILO_HISTORY_LIMIT = 128;
export const MILO_COLLAPSE_WINDOW_MS = 3000;

export const DEFAULT_MILO_DECISION: MiloDecision = Object.freeze({
  visual: 'idle',
  size: 'compact',
  eventKey: null,
  seenEventKeys: [],
  lastReactionAt: null,
});

function safeNow(now: number | undefined): number {
  if (typeof now !== 'number' || !Number.isFinite(now)) return 0;
  return now < 0 ? 0 : now;
}

function clampHistory(keys: readonly string[]): string[] {
  if (keys.length <= MILO_HISTORY_LIMIT) return keys.slice();
  return keys.slice(keys.length - MILO_HISTORY_LIMIT);
}

function hasSeen(prev: MiloDecision, key: string): boolean {
  for (let i = 0; i < prev.seenEventKeys.length; i++) {
    if (prev.seenEventKeys[i] === key) return true;
  }
  return false;
}

function recordSeen(prev: MiloDecision, key: string, now: number): MiloDecision {
  const next = clampHistory([...prev.seenEventKeys, key]);
  return {
    visual: prev.visual,
    size: prev.size,
    eventKey: prev.eventKey,
    seenEventKeys: next,
    lastReactionAt: now,
  };
}

export function makeEventKey(jobId: string | null | undefined, kind: string): string {
  const safeJob = jobId == null || jobId === '' ? 'none' : String(jobId);
  return safeJob + ':' + kind;
}

export function shouldSuppressStale(prev: MiloDecision, input: MiloInput): boolean {
  const result = input.latestResult;
  if (!result) return false;
  // Stale: latestResult refers to a job that is no longer the active job.
  // The active job, if any, wins. Suppress regardless of whether we have
  // already reacted to it, so a stale result never re-emerges.
  if (input.activeJobId && result.jobId !== input.activeJobId) {
    return true;
  }
  return false;
}

function isTerminalFailure(status: MiloResultStatus): boolean {
  return status === 'failed' || status === 'cancelled' || status === 'expired';
}

export function decideMilo(prev: MiloDecision, input: MiloInput, now: number): MiloDecision {
  const t = safeNow(now);
  const size: MiloSize = prev.size === 'hero' ? 'hero' : 'compact';

  // 1. Hard suppressions: recording, reduced motion, hidden.
  if (input.recording || input.reducedMotion || input.hidden) {
    return {
      visual: 'static',
      size,
      eventKey: null,
      seenEventKeys: prev.seenEventKeys,
      lastReactionAt: prev.lastReactionAt,
    };
  }

  const result = input.latestResult;

  // 2. Terminal failure handling.
  // Same-job terminal failure wins over an active job that is older or equal.
  // A newer active job (different id) wins over a stale failure.
  if (result && isTerminalFailure(result.status)) {
    if (!input.activeJobId || result.jobId === input.activeJobId) {
      return {
        visual: 'static',
        size,
        eventKey: null,
        seenEventKeys: prev.seenEventKeys,
        lastReactionAt: prev.lastReactionAt,
      };
    }
    // Different, newer active job: fall through to attentive handling below.
  }

  // 3. Latest active job (not yet terminal) -> attentive.
  if (input.activeJobId) {
    return {
      visual: 'attentive',
      size,
      eventKey: null,
      seenEventKeys: prev.seenEventKeys,
      lastReactionAt: prev.lastReactionAt,
    };
  }

  // 4. Save confirmation: only when matching latestResult or active job.
  if (input.saveConfirmedJobId) {
    const matchesResult = result != null && result.jobId === input.saveConfirmedJobId
      && result.status === 'ready' && result.usable;
    const matchesActive = input.activeJobId != null && input.activeJobId === input.saveConfirmedJobId;
    if (matchesResult || matchesActive) {
      // Invalid save: result is partial (not a validated completion).
      // Do not cheer; do not fall through to attentive.
      if (matchesResult && result != null && result.status === 'partial') {
        return {
          visual: 'idle',
          size,
          eventKey: null,
          seenEventKeys: prev.seenEventKeys,
          lastReactionAt: prev.lastReactionAt,
        };
      }
      const key = makeEventKey(input.saveConfirmedJobId, 'save');
      if (!hasSeen(prev, key)) {
        // Collapse closely spaced ready/save reactions: if a reaction just
        // happened for the same job, consume the save event silently.
        const lastKey = prev.seenEventKeys.length > 0
          ? prev.seenEventKeys[prev.seenEventKeys.length - 1]
          : null;
        const sameJobRecent = lastKey != null && lastKey.startsWith(input.saveConfirmedJobId + ':');
        const recent =
          sameJobRecent &&
          prev.lastReactionAt != null && t - prev.lastReactionAt < MILO_COLLAPSE_WINDOW_MS;
        if (recent) {
          const history = clampHistory([...prev.seenEventKeys, key]);
          return {
            visual: 'idle',
            size,
            eventKey: null,
            seenEventKeys: history,
            lastReactionAt: prev.lastReactionAt,
          };
        }
        const history = recordSeen(prev, key, t);
        return {
          visual: 'cheer',
          size,
          eventKey: key,
          seenEventKeys: history.seenEventKeys,
          lastReactionAt: history.lastReactionAt,
        };
      }
      // Already celebrated this save; collapse to idle without replay.
      return {
        visual: 'idle',
        size,
        eventKey: null,
        seenEventKeys: prev.seenEventKeys,
        lastReactionAt: prev.lastReactionAt,
      };
    }
    // Save for a stale job: no celebration.
  }

  // 5. Pending save: no success acknowledgement until confirmed.
  if (input.pendingSaveJobId) {
    return {
      visual: 'idle',
      size,
      eventKey: null,
      seenEventKeys: prev.seenEventKeys,
      lastReactionAt: prev.lastReactionAt,
    };
  }

  // 6. Latest result handling.
  if (result) {
    // Stale result suppression: an older job's result must not cheer once
    // a newer active job exists.
    if (shouldSuppressStale(prev, input)) {
      return {
        visual: 'idle',
        size,
        eventKey: null,
        seenEventKeys: prev.seenEventKeys,
        lastReactionAt: prev.lastReactionAt,
      };
    }

    if (result.status === 'partial') {
      // Partial: attentive, never cheer.
      return {
        visual: 'attentive',
        size,
        eventKey: null,
        seenEventKeys: prev.seenEventKeys,
        lastReactionAt: prev.lastReactionAt,
      };
    }

    if (result.status === 'ready' && result.usable) {
      const key = makeEventKey(result.jobId, 'result:ready');
      if (!hasSeen(prev, key)) {
        const history = recordSeen(prev, key, t);
        return {
          visual: 'cheer',
          size,
          eventKey: key,
          seenEventKeys: history.seenEventKeys,
          lastReactionAt: history.lastReactionAt,
        };
      }
      // Already celebrated this ready result.
      return {
        visual: 'idle',
        size,
        eventKey: null,
        seenEventKeys: prev.seenEventKeys,
        lastReactionAt: prev.lastReactionAt,
      };
    }

    // ready but not usable, or other non-celebrated states.
    return {
      visual: 'idle',
      size,
      eventKey: null,
      seenEventKeys: prev.seenEventKeys,
      lastReactionAt: prev.lastReactionAt,
    };
  }

  // 7. Default: idle.
  return {
    visual: 'idle',
    size,
    eventKey: null,
    seenEventKeys: prev.seenEventKeys,
    lastReactionAt: prev.lastReactionAt,
  };
}
