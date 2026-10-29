/**
 * Browser-safe week-window helpers.
 *
 * Exports (for integrator):
 *   weekBounds(mode: 'rolling7' | 'calendar', now: Date): { start: Date; end: Date }
 *   inWeek(iso: string, mode: 'rolling7' | 'calendar', now: Date): boolean
 *   weekDays(mode: 'rolling7' | 'calendar', now: Date): Date[]
 *
 * Semantics:
 *   rolling7  -> seven LOCAL calendar dates ending today.
 *                start = local midnight of (today - 6 days)
 *                end   = local midnight of (tomorrow)  EXCLUSIVE
 *                Label: "Last 7 days".
 *   calendar  -> Mon 00:00 local to following Mon 00:00 local, EXCLUSIVE end.
 *                Future entries (date/time > now) are excluded by inWeek().
 *
 * DST safety: all arithmetic uses Date.setDate() / setHours() / setMinutes()
 * / setSeconds() / setMilliseconds() on a fresh local-midnight Date. No
 * 86400000 subtraction, so DST transitions do not shift the window.
 *
 * No source dates or user data are referenced; all inputs are explicit.
 */

export type WeekMode = 'rolling7' | 'calendar';

export interface WeekBounds {
  start: Date;
  end: Date; // exclusive
}

function localMidnight(d: Date): Date {
  const out = new Date(d.getTime());
  out.setHours(0, 0, 0, 0);
  return out;
}

function startOfWeekMonday(d: Date): Date {
  const out = localMidnight(d);
  // getDay(): 0 = Sunday, 1 = Monday, ... 6 = Saturday
  const dow = out.getDay();
  const delta = dow === 0 ? 6 : dow - 1; // Monday = 0
  out.setDate(out.getDate() - delta);
  return out;
}

function addDays(d: Date, n: number): Date {
  const out = new Date(d.getTime());
  out.setDate(out.getDate() + n);
  return out;
}

function isValidIso(iso: string): boolean {
  if (typeof iso !== 'string' || iso.length === 0) return false;
  const t = Date.parse(iso);
  return Number.isFinite(t);
}

/** Compute the [start, end) bounds for the requested week mode. */
export function weekBounds(mode: WeekMode, now: Date): WeekBounds {
  if (mode === 'rolling7') {
    const today = localMidnight(now);
    const start = addDays(today, -6);
    const end = addDays(today, 1); // tomorrow midnight, exclusive
    return { start, end };
  }
  // calendar: Mon 00:00 -> following Mon 00:00 (exclusive)
  const start = startOfWeekMonday(now);
  const end = addDays(start, 7);
  return { start, end };
}

/**
 * True iff the ISO timestamp falls inside the week window.
 * - Invalid ISO strings return false.
 * - Future timestamps (strictly greater than `now`) are rejected so a
 *   calendar week that extends past "today" does not include future logs.
 */
export function inWeek(iso: string, mode: WeekMode, now: Date): boolean {
  if (!isValidIso(iso)) return false;
  const t = Date.parse(iso);
  if (t > now.getTime()) return false;
  const { start, end } = weekBounds(mode, now);
  return t >= start.getTime() && t < end.getTime();
}

/**
 * Return the LOCAL calendar dates that make up the week window.
 * rolling7 -> 7 dates (today and the 6 preceding local midnights).
 * calendar -> 7 dates starting at Monday.
 */
export function weekDays(mode: WeekMode, now: Date): Date[] {
  const { start } = weekBounds(mode, now);
  const out: Date[] = [];
  for (let i = 0; i < 7; i++) {
    out.push(addDays(start, i));
  }
  return out;
}
