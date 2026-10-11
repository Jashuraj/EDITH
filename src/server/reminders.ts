import { and, asc, eq, isNull, lte, sql, desc, inArray } from "drizzle-orm";
import { db } from "@/db";
import { notifications, reminders } from "@/db/schema";
import { formatInTz, nextOccurrence, toWall } from "@/lib/time";
import { getProfile } from "./settings";
import { wakeHost } from "./relay";

export type ReminderRow = typeof reminders.$inferSelect;
const CHANNELS = ["hud", "phone", "host"] as const;
const MISSED_MS = 30 * 60_000;

export interface NewReminder {
  title: string;
  dueAt: Date;
  notes?: string | null;
  recurrence?: string;
  byWeekday?: number[] | null;
  priority?: string;
  category?: string;
  trigger?: string;
  source?: string;
  timezone?: string;
}

const RECUR = ["none", "daily", "weekdays", "weekly", "monthly", "yearly"];

export async function createReminder(r: NewReminder): Promise<ReminderRow> {
  const profile = await getProfile();
  const [row] = await db
    .insert(reminders)
    .values({
      title: r.title.slice(0, 200),
      notes: r.notes?.slice(0, 1000) ?? null,
      dueAt: r.dueAt,
      timezone: r.timezone || profile.timezone,
      recurrence: RECUR.includes(r.recurrence ?? "") ? r.recurrence! : "none",
      byWeekday: r.byWeekday && r.byWeekday.length ? r.byWeekday.filter((d) => d >= 0 && d <= 6) : null,
      priority: ["low", "normal", "high"].includes(r.priority ?? "") ? r.priority! : "normal",
      category: (r.category || "general").slice(0, 30),
      trigger: r.trigger === "manual_arrival" ? "manual_arrival" : "time",
      source: r.source || "ui",
    })
    .returning();
  return row;
}

function inQuietHours(now: Date, tz: string, start: string | null, end: string | null): boolean {
  if (!start || !end) return false;
  const w = toWall(now, tz);
  const cur = w.hour * 60 + w.minute;
  const [sh, sm] = start.split(":").map(Number);
  const [eh, em] = end.split(":").map(Number);
  const s = sh * 60 + sm;
  const e = eh * 60 + em;
  return s <= e ? cur >= s && cur < e : cur >= s || cur < e;
}

let lastTick = 0;
/** Fire due reminders. Safe to call often and concurrently (atomic claim per reminder). */
export async function tickReminders(force = false): Promise<number> {
  const now = new Date();
  if (!force && now.getTime() - lastTick < 4000) return 0;
  lastTick = now.getTime();
  const profile = await getProfile();
  const due = await db
    .select()
    .from(reminders)
    .where(and(eq(reminders.status, "active"), eq(reminders.trigger, "time"), lte(reminders.dueAt, now)))
    .orderBy(asc(reminders.dueAt))
    .limit(50);

  let fired = 0;
  const quiet = inQuietHours(now, profile.timezone, profile.quietStart, profile.quietEnd);
  for (const r of due) {
    const missed = now.getTime() - r.dueAt.getTime() > MISSED_MS;
    const next = nextOccurrence(r.dueAt, r.recurrence, r.timezone, now, r.byWeekday);
    // Atomic claim: only the request that moves due_at/status wins.
    const claimed = await db
      .update(reminders)
      .set(
        next
          ? { dueAt: next, lastFiredAt: now, fireCount: sql`${reminders.fireCount} + 1`, updatedAt: now }
          : { status: "fired", lastFiredAt: now, fireCount: sql`${reminders.fireCount} + 1`, updatedAt: now },
      )
      .where(and(eq(reminders.id, r.id), eq(reminders.dueAt, r.dueAt), eq(reminders.status, "active")))
      .returning({ id: reminders.id });
    if (!claimed.length) continue;
    fired++;
    const body = missed
      ? `Missed while EDITH was offline/asleep — was due ${formatInTz(r.dueAt, r.timezone)}`
      : r.notes || (r.category === "medicine" ? "Medicine reminder (as scheduled by you)" : "Reminder");
    const channels = quiet && r.priority !== "high" ? ["hud"] : [...CHANNELS];
    await db.insert(notifications).values(channels.map((channel) => ({ reminderId: r.id, channel, title: r.title, body })));
  }
  if (fired) wakeHost();
  return fired;
}

/** Return & mark delivered all pending notifications for a channel. */
export async function takeNotifications(channel: string) {
  const rows = await db
    .update(notifications)
    .set({ deliveredAt: new Date() })
    .where(and(eq(notifications.channel, channel), isNull(notifications.deliveredAt)))
    .returning();
  return rows;
}

export async function listReminders(includeDone = false) {
  const q = db.select().from(reminders);
  const rows = includeDone
    ? await q.orderBy(desc(reminders.updatedAt)).limit(300)
    : await q.where(inArray(reminders.status, ["active", "fired"])).orderBy(asc(reminders.dueAt)).limit(300);
  return rows;
}

export async function snoozeReminder(id: string, minutes: number) {
  const due = new Date(Date.now() + Math.max(1, Math.min(24 * 60, minutes)) * 60_000);
  const [row] = await db
    .update(reminders)
    .set({ dueAt: due, status: "active", updatedAt: new Date() })
    .where(eq(reminders.id, id))
    .returning();
  return row ?? null;
}

/** Complete: one-time -> done; recurring -> skip to next occurrence after now. */
export async function completeReminder(id: string) {
  const [r] = await db.select().from(reminders).where(eq(reminders.id, id)).limit(1);
  if (!r) return null;
  const now = new Date();
  if (r.recurrence !== "none" && r.status !== "done") {
    // If the current occurrence is in the future (already advanced after firing), keep it.
    const next = r.dueAt > now && r.lastFiredAt ? r.dueAt : nextOccurrence(r.dueAt, r.recurrence, r.timezone, now, r.byWeekday);
    const [row] = await db
      .update(reminders)
      .set({ dueAt: next ?? r.dueAt, status: "active", updatedAt: now })
      .where(eq(reminders.id, id))
      .returning();
    return row;
  }
  const [row] = await db.update(reminders).set({ status: "done", updatedAt: now }).where(eq(reminders.id, id)).returning();
  return row;
}

export async function dismissReminder(id: string) {
  const [row] = await db.update(reminders).set({ status: "dismissed", updatedAt: new Date() }).where(eq(reminders.id, id)).returning();
  return row ?? null;
}

export async function deleteReminder(id: string) {
  await db.delete(reminders).where(eq(reminders.id, id));
}

/** Manual arrival trigger ("I'm home"): fire all arrival reminders now. */
export async function fireArrival() {
  const rows = await db
    .update(reminders)
    .set({ trigger: "time", dueAt: new Date(), updatedAt: new Date() })
    .where(and(eq(reminders.status, "active"), eq(reminders.trigger, "manual_arrival")))
    .returning();
  await tickReminders(true);
  return rows.length;
}

export function describeReminder(r: ReminderRow): string {
  if (r.trigger === "manual_arrival") return `“${r.title}” — when you tap Arrived`;
  const rec =
    r.recurrence === "none"
      ? ""
      : r.recurrence === "weekly" && r.byWeekday?.length
        ? `, every ${r.byWeekday.map((d) => ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][d]).join("/")}`
        : `, repeats ${r.recurrence}`;
  return `“${r.title}” at ${formatInTz(r.dueAt, r.timezone)}${rec}`;
}
