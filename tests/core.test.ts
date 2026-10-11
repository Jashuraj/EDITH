import { test } from "node:test";
import assert from "node:assert/strict";
import { parseIntent, parseReminder } from "../src/lib/intent";
import { fromWall, nextOccurrence, toWall } from "../src/lib/time";
import { TOOLS, permissionFor, extractToolCall } from "../src/lib/tools";
import { holidaysBetween, parseIcs, toIcs } from "../src/lib/holidays";

const tz = "Asia/Kolkata";
// Fixed "now": Wed 2026-03-04 10:00 IST
const now = fromWall(2026, 3, 4, 10, 0, tz);
const ctx = { now, tz };

test("timezone round trip (IST is UTC+5:30)", () => {
  const d = fromWall(2026, 3, 4, 19, 30, tz);
  assert.equal(d.toISOString(), "2026-03-04T14:00:00.000Z");
  const w = toWall(d, tz);
  assert.deepEqual([w.hour, w.minute, w.weekday], [19, 30, 3]);
});

test("DST zone conversion stays on wall clock", () => {
  const d = fromWall(2026, 7, 1, 9, 0, "America/New_York");
  assert.equal(d.toISOString(), "2026-07-01T13:00:00.000Z");
});

test("remind me to wash my clothes at 7:30 PM -> today 19:30, exact", () => {
  const r = parseReminder("Remind me to wash my clothes at 7:30 PM", ctx);
  assert.ok(r && r.kind === "reminder");
  assert.equal(r.title, "Wash my clothes");
  assert.equal(r.dueAt!.toISOString(), fromWall(2026, 3, 4, 19, 30, tz).toISOString());
  assert.equal(r.ambiguous, false);
  assert.equal(r.recurrence, "none");
});

test("time already passed today rolls to tomorrow", () => {
  const r = parseReminder("remind me to stretch at 9 am", ctx);
  assert.ok(r && r.kind === "reminder");
  assert.equal(r.dueAt!.toISOString(), fromWall(2026, 3, 5, 9, 0, tz).toISOString());
});

test("ambiguous 'at 7' requires confirmation", () => {
  const r = parseReminder("remind me to call dad at 7", ctx);
  assert.ok(r && r.kind === "reminder");
  assert.equal(r.ambiguous, true);
});

test("tonight at 8 resolves to 20:00 without ambiguity", () => {
  const r = parseReminder("remind me to take out trash tonight at 8", ctx);
  assert.ok(r && r.kind === "reminder");
  assert.equal(toWall(r.dueAt!, tz).hour, 20);
  assert.equal(r.ambiguous, false);
});

test("every Sunday at 10 am -> weekly on Sunday", () => {
  const r = parseReminder("remind me to call mom every Sunday at 10 am", ctx);
  assert.ok(r && r.kind === "reminder");
  assert.equal(r.recurrence, "weekly");
  assert.deepEqual(r.byWeekday, [0]);
  assert.equal(r.dueAt!.toISOString(), fromWall(2026, 3, 8, 10, 0, tz).toISOString());
  assert.equal(r.title, "Call mom");
});

test("relative: in 10 minutes", () => {
  const r = parseReminder("remind me to check the oven in 10 minutes", ctx);
  assert.ok(r && r.kind === "reminder");
  assert.equal(r.dueAt!.getTime() - now.getTime(), 600_000);
});

test("arrival trigger is manual (no fake geofencing)", () => {
  const r = parseReminder("remind me to water plants when I reach home", ctx);
  assert.ok(r && r.kind === "reminder");
  assert.equal(r.trigger, "manual_arrival");
  assert.equal(r.dueAt, null);
});

test("no time given asks for one", () => {
  const r = parseReminder("remind me to buy milk", ctx);
  assert.ok(r && r.kind === "reminder");
  assert.equal(r.dueAt, null);
});

test("recurrence: weekly next occurrence and monthly clamp", () => {
  const due = fromWall(2026, 3, 8, 10, 0, tz); // Sun
  const next = nextOccurrence(due, "weekly", tz, fromWall(2026, 3, 8, 10, 1, tz), [0]);
  assert.equal(next!.toISOString(), fromWall(2026, 3, 15, 10, 0, tz).toISOString());
  const jan31 = fromWall(2026, 1, 31, 9, 0, tz);
  const feb = nextOccurrence(jan31, "monthly", tz, fromWall(2026, 1, 31, 9, 1, tz));
  assert.equal(toWall(feb!, tz).day, 28);
  const wk = nextOccurrence(fromWall(2026, 3, 6, 8, 0, tz), "weekdays", tz, fromWall(2026, 3, 6, 8, 1, tz)); // Fri -> Mon
  assert.equal(toWall(wk!, tz).weekday, 1);
  assert.equal(nextOccurrence(due, "none", tz, now), null);
});

test("catch-up: missed daily reminder advances to next future slot only", () => {
  const due = fromWall(2026, 3, 1, 7, 0, tz);
  const next = nextOccurrence(due, "daily", tz, now); // now = Mar 4 10:00
  assert.equal(next!.toISOString(), fromWall(2026, 3, 5, 7, 0, tz).toISOString());
});

test("intents: apps, urls, folders, media, timer, mode, confirm", () => {
  assert.deepEqual(parseIntent("open chrome", ctx), { kind: "tool", tool: "open_app", args: { app: "chrome" } });
  assert.deepEqual(parseIntent("open youtube.com", ctx), { kind: "tool", tool: "open_url", args: { url: "https://youtube.com" } });
  assert.deepEqual(parseIntent("open downloads folder", ctx), { kind: "tool", tool: "open_folder", args: { folder: "downloads" } });
  assert.deepEqual(parseIntent("volume up", ctx), { kind: "tool", tool: "media_control", args: { action: "vol_up" } });
  assert.deepEqual(parseIntent("set volume to 40%", ctx), { kind: "tool", tool: "set_volume", args: { level: 40 } });
  assert.deepEqual(parseIntent("timer 10 minutes", ctx), { kind: "timer", minutes: 10, label: "Timer" });
  assert.deepEqual(parseIntent("go offline", ctx), { kind: "mode", mode: "offline" });
  assert.deepEqual(parseIntent("yes", ctx), { kind: "confirm", yes: true });
  assert.equal(parseIntent("lock my pc", ctx)?.kind, "tool");
  assert.equal(parseIntent("explain quantum entanglement simply", ctx), null);
});

test("tool validation & risk policy", () => {
  assert.equal(TOOLS.open_app.validate({ app: "rm -rf" }).ok, false);
  assert.equal(TOOLS.open_url.validate({ url: "file:///C:/Windows" }).ok, false);
  assert.equal(TOOLS.open_url.validate({ url: "javascript:alert(1)" }).ok, false);
  assert.equal(TOOLS.open_url.validate({ url: "https://example.com" }).ok, true);
  assert.equal(permissionFor(TOOLS.open_app, undefined), "auto");
  assert.equal(permissionFor(TOOLS.lock_pc, undefined), "ask");
  assert.equal(permissionFor(TOOLS.shutdown_pc, { shutdown_pc: "auto" }), "ask", "high risk can never auto-run");
  assert.equal(permissionFor(TOOLS.open_app, { open_app: "deny" }), "deny");
  assert.equal(TOOLS.unlock_pc.supported, false);
});

test("model tool-call extraction only accepts registered tools", () => {
  assert.deepEqual(extractToolCall('Sure! {"tool":"open_app","args":{"app":"notepad"}}'), { tool: "open_app", args: { app: "notepad" } });
  assert.equal(extractToolCall('{"tool":"format_drive","args":{}}'), null);
  assert.equal(extractToolCall("plain answer"), null);
});

test("holidays: fixed national + DoPT 2026 gazetted with tentative flags", () => {
  const h = holidaysBetween("2026-01-01", "2026-12-31");
  assert.ok(h.find((x) => x.date === "2026-01-26" && x.name === "Republic Day"));
  assert.ok(h.find((x) => x.date === "2026-11-08" && x.name.startsWith("Diwali")));
  assert.equal(h.find((x) => x.name === "Id-ul-Fitr")?.tentative, true);
  const h27 = holidaysBetween("2027-01-01", "2027-12-31");
  assert.equal(h27.length, 3, "only fixed national holidays for years without an official list");
});

test("ICS round trip", () => {
  const ics = toIcs([{ id: "1", title: "Amma, birthday", date: "2026-05-02", time: null, recurrence: "yearly", category: "birthday" }]);
  const back = parseIcs(ics);
  assert.deepEqual(back, [{ title: "Amma, birthday", date: "2026-05-02", time: null, yearly: true }]);
});
