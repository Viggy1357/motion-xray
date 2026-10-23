export type WeekMode = 'rolling7' | 'calendar';

export interface UxSettings {
  goalEnabled: boolean;
  goalTarget: number | null;
  weekMode: WeekMode;
}

export interface UxMetadata extends UxSettings {
  version: 1;
  viewed: Record<string, string>;
  [key: string]: unknown;
}

export const UX_METADATA_KEY = 'mxr.ux.v1';

export function defaultUxMetadata(): UxMetadata {
  return { version: 1, goalEnabled: false, goalTarget: null, weekMode: 'rolling7', viewed: {} };
}

function isWeekMode(v: unknown): v is WeekMode {
  return v === 'rolling7' || v === 'calendar';
}

function isValidTarget(v: unknown): v is number {
  return typeof v === 'number' && Number.isInteger(v) && v > 0;
}

/**
 * Parse raw stored value into UxMetadata. Unknown keys are preserved.
 * Unsupported version or corrupt shape returns null (caller keeps defaults
 * in memory but must NOT erase existing storage).
 */
export function parseUxMetadata(raw: string | null): UxMetadata | null {
  if (raw == null) return null;
  let obj: unknown;
  try {
    obj = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof obj !== 'object' || obj === null || Array.isArray(obj)) return null;
  const rec = obj as Record<string, unknown>;
  if (rec.version !== 1) return null;
  const out: Record<string, unknown> = { ...rec };
  out.version = 1;
  out.goalEnabled = rec.goalEnabled === true;
  out.goalTarget = isValidTarget(rec.goalTarget) ? (rec.goalTarget as number) : null;
  out.weekMode = isWeekMode(rec.weekMode) ? rec.weekMode : 'rolling7';
  const viewed: Record<string, string> = {};
  if (typeof rec.viewed === 'object' && rec.viewed !== null && !Array.isArray(rec.viewed)) {
    for (const [k, v] of Object.entries(rec.viewed as Record<string, unknown>)) {
      if (typeof k === 'string' && typeof v === 'string') viewed[k] = v;
    }
  }
  out.viewed = viewed;
  return out as unknown as UxMetadata;
}

export function validateUxSettings(settings: unknown): settings is UxSettings {
  if (typeof settings !== 'object' || settings === null) return false;
  const s = settings as Record<string, unknown>;
  if (typeof s.goalEnabled !== 'boolean') return false;
  if (s.goalTarget !== null && !isValidTarget(s.goalTarget)) return false;
  if (s.goalEnabled && !isValidTarget(s.goalTarget)) return false;
  if (!isWeekMode(s.weekMode)) return false;
  return true;
}

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

function getStorage(): StorageLike | null {
  try {
    if (typeof localStorage !== 'undefined') return localStorage;
  } catch {
    /* access denied */
  }
  return null;
}

/**
 * Atomic persist: serialize the full merged record and write once.
 * Returns true on success; on failure existing storage is untouched.
 */
export function persistUxMetadata(meta: UxMetadata, storage?: StorageLike | null): boolean {
  const store = storage === undefined ? getStorage() : storage;
  if (!store) return false;
  let serialized: string;
  try {
    serialized = JSON.stringify(meta);
  } catch {
    return false;
  }
  try {
    store.setItem(UX_METADATA_KEY, serialized);
    return true;
  } catch {
    return false;
  }
}

export function loadUxMetadata(storage?: StorageLike | null): { metadata: UxMetadata; error: string | null } {
  const store = storage === undefined ? getStorage() : storage;
  if (!store) return { metadata: defaultUxMetadata(), error: null };
  let raw: string | null = null;
  try {
    raw = store.getItem(UX_METADATA_KEY);
  } catch {
    return { metadata: defaultUxMetadata(), error: 'Local settings could not be read.' };
  }
  if (raw == null) return { metadata: defaultUxMetadata(), error: null };
  const parsed = parseUxMetadata(raw);
  if (!parsed) {
    // Corrupt or unsupported version: keep defaults in memory, do not erase.
    return { metadata: defaultUxMetadata(), error: 'Saved settings could not be read; defaults are in use.' };
  }
  return { metadata: parsed, error: null };
}

/** Merge settings into existing metadata, preserving unknown keys and viewed. */
export function applyUxSettings(meta: UxMetadata, settings: UxSettings): UxMetadata {
  return {
    ...meta,
    version: 1,
    goalEnabled: settings.goalEnabled,
    goalTarget: settings.goalEnabled ? settings.goalTarget : null,
    weekMode: settings.weekMode,
  };
}

/** Return a new metadata object with the viewed timestamp recorded. */
export function withViewed(meta: UxMetadata, analysisId: string, isoTimestamp: string): UxMetadata {
  return { ...meta, viewed: { ...meta.viewed, [analysisId]: isoTimestamp } };
}
