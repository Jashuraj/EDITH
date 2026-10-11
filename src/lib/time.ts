/** Timezone-safe helpers using only Intl (no external deps). */

export interface WallClock {
  year: number;
  month: number; // 1-12
  day: number;
  hour: number;
  minute: number;
  weekday: number; // 0=Sun
}

const dtfCache = new Map<string, Intl.DateTimeFormat>();
function dtf(tz: string) {
  let f = dtfCache.get(tz);
  if (!f) {
    f = new Intl.DateTimeFormat("en-US", {
      timeZone: tz,
      hourCycle: "h23",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      weekday: "short",
    });
    dtfCache.set(tz, f);
  }
  return f;
}

const WD: Record<string, number> = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };

export function isValidTimeZone(tz: string): boolean {
  try {
    new Intl.DateTimeFormat("en-US", { timeZone: tz });
    return true;
  } catch {
    return false;
  }
}

export function toWall(date: Date, tz: string): WallClock {
  const parts = Object.fromEntries(dtf(tz).formatToParts(date).map((p) => [p.type, p.value]));
  return {
    year: Number(parts.year),
    month: Number(parts.month),
    day: Number(parts.day),
    hour: Number(parts.hour) % 24,
    minute: Number(parts.minute),
    weekday: WD[parts.weekday as string] ?? 0,
  };
}

/** Offset (ms) of tz from UTC at the given instant. */
function tzOffset(date: Date, tz: string): number {
  const w = toWall(date, tz);
  const asUtc = Date.UTC(w.year, w.month - 1, w.day, w.hour, w.minute, date.getUTCSeconds());
  return asUtc - Math.floor(date.getTime() / 1000) * 1000;
}

/** Convert a wall-clock time in tz to a UTC Date (handles DST by double pass). */
export function fromWall(year: number, month: number, day: number, hour: number, minute: number, tz: string): Date {
  const guess = Date.UTC(year, month - 1, day, hour, minute, 0);
  let off = tzOffset(new Date(guess), tz);
  let ts = guess - off;
  const off2 = tzOffset(new Date(ts), tz);
  if (off2 !== off) {
    off = off2;
    ts = guess - off;
  }
  return new Date(ts);
}

export function addDaysWall(w: { year: number; month: number; day: number }, n: number) {
  const d = new Date(Date.UTC(w.year, w.month - 1, w.day + n));
  return { year: d.getUTCFullYear(), month: d.getUTCMonth() + 1, day: d.getUTCDate(), weekday: d.getUTCDay() };
}

export function ymd(w: { year: number; month: number; day: number }): string {
  return `${w.year}-${String(w.month).padStart(2, "0")}-${String(w.day).padStart(2, "0")}`;
}

export type Recurrence = "none" | "daily" | "weekdays" | "weekly" | "monthly" | "yearly";

/**
 * Next occurrence strictly after `after`, keeping the wall-clock time of `due` in tz.
 * Returns null for non-recurring reminders.
 */
export function nextOccurrence(
  due: Date,
  recurrence: Recurrence | string,
  tz: string,
  after: Date,
  byWeekday?: number[] | null,
): Date | null {
  if (recurrence === "none") return null;
  const base = toWall(due, tz);
  const start = toWall(after, tz);
  const days = byWeekday && byWeekday.length ? byWeekday : [base.weekday];

  if (recurrence === "monthly" || recurrence === "yearly") {
    let y = base.year;
    let m = base.month;
    for (let i = 0; i < 600; i++) {
      if (recurrence === "monthly") {
        m += 1;
        if (m > 12) {
          m = 1;
          y += 1;
        }
      } else {
        y += 1;
      }
      const dim = new Date(Date.UTC(y, m, 0)).getUTCDate();
      const d = fromWall(y, m, Math.min(base.day, dim), base.hour, base.minute, tz);
      if (d.getTime() > after.getTime()) return d;
    }
    return null;
  }

  // daily / weekdays / weekly: scan from the later of due-date and after-date
  const from = due.getTime() > after.getTime() ? base : start;
  for (let i = 0; i <= 400; i++) {
    const w = addDaysWall(from, i);
    const ok =
      recurrence === "daily" ||
      (recurrence === "weekdays" && w.weekday >= 1 && w.weekday <= 5) ||
      (recurrence === "weekly" && days.includes(w.weekday));
    if (!ok) continue;
    const d = fromWall(w.year, w.month, w.day, base.hour, base.minute, tz);
    if (d.getTime() > after.getTime()) return d;
  }
  return null;
}

export function formatInTz(date: Date, tz: string): string {
  return new Intl.DateTimeFormat("en-IN", {
    timeZone: tz,
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(date);
}
