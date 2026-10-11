/**
 * Level-0 deterministic intent parser (no LLM). Pure & unit-tested.
 * The LLM never executes anything directly: model output is mapped onto the
 * same typed intents and then validated by the tool policy.
 */
import { addDaysWall, fromWall, toWall, type Recurrence } from "./time";

export type Intent =
  | { kind: "reminder"; title: string; dueAt: Date | null; recurrence: Recurrence; byWeekday?: number[]; trigger: "time" | "manual_arrival"; ambiguous: boolean; interpretation: string }
  | { kind: "timer"; minutes: number; label: string }
  | { kind: "today" }
  | { kind: "time" }
  | { kind: "date" }
  | { kind: "status" }
  | { kind: "help" }
  | { kind: "mode"; mode: "auto" | "online" | "offline" }
  | { kind: "confirm"; yes: boolean }
  | { kind: "tool"; tool: string; args: Record<string, unknown> };

const DAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];
const DAY_RE = "(sun|mon|tue|tues|wed|thu|thur|thurs|fri|sat)(?:day|nesday|rsday|urday)?";

function dayIndex(s: string): number {
  const k = s.slice(0, 3).toLowerCase();
  return DAYS.findIndex((d) => d.startsWith(k));
}

const APP_ALIASES: Record<string, string> = {
  chrome: "chrome", "google chrome": "chrome", edge: "edge", "microsoft edge": "edge", firefox: "firefox",
  notepad: "notepad", calculator: "calculator", calc: "calculator", explorer: "explorer", "file explorer": "explorer",
  "task manager": "taskmgr", settings: "settings", terminal: "terminal", powershell: "powershell", cmd: "cmd",
  "vs code": "vscode", vscode: "vscode", code: "vscode", spotify: "spotify", word: "word", excel: "excel",
  powerpoint: "powerpoint", paint: "paint", "snipping tool": "snippingtool", camera: "camera", whatsapp: "whatsapp",
  telegram: "telegram", discord: "discord", vlc: "vlc", outlook: "outlook", teams: "teams",
};

const FOLDERS = ["downloads", "documents", "desktop", "pictures", "music", "videos", "home"];

export interface ParseCtx {
  now: Date;
  tz: string;
}

/** Parse a time-of-day phrase. Returns hour/min and whether am/pm was explicit. */
function parseClock(s: string): { h: number; m: number; explicit: boolean } | null {
  const m = s.match(/\b(?:at\s+)?(\d{1,2})(?::|\.)?(\d{2})?\s*(a\.?m\.?|p\.?m\.?)?(?=\s|$|,)/i);
  if (!m) return null;
  let h = Number(m[1]);
  const min = m[2] ? Number(m[2]) : 0;
  if (h > 23 || min > 59) return null;
  const ap = m[3]?.toLowerCase().replace(/\./g, "");
  if (ap === "pm" && h < 12) h += 12;
  if (ap === "am" && h === 12) h = 0;
  const explicit = Boolean(ap) || h > 12 || h === 0 || Boolean(m[2] && m[1].length === 2 && h >= 13);
  return { h, m: min, explicit };
}

export function parseReminder(text: string, ctx: ParseCtx): Intent | null {
  const t = text.trim();
  const m = t.match(/^(?:hey\s+edith,?\s+)?(?:please\s+)?(?:remind\s+me|set\s+(?:a\s+)?reminder|create\s+(?:a\s+)?reminder|add\s+(?:a\s+)?reminder)\s*(?:to|about|that|for)?\s+(.+)$/i);
  if (!m) return null;
  let body = m[1].trim();
  const now = ctx.now;
  const tz = ctx.tz;
  const today = toWall(now, tz);

  // Arrival trigger (manual "Arrived" fallback; no background geofencing).
  if (/\bwhen\s+i\s+(reach|get|arrive|come)\s+(home|back|office|college|school)\b/i.test(body)) {
    const title = body.replace(/\bwhen\s+i\s+(reach|get|arrive|come)\s+(home|back|office|college|school)\b/i, "").trim() || body;
    return { kind: "reminder", title: cleanTitle(title), dueAt: null, recurrence: "none", trigger: "manual_arrival", ambiguous: false, interpretation: "when you tap “Arrived” in Today" };
  }

  // Relative: in N minutes/hours
  const rel = body.match(/\bin\s+(\d+|an?|one|half\s+an?)\s*(minutes?|mins?|hours?|hrs?)\b/i);
  if (rel) {
    const nRaw = rel[1].toLowerCase();
    let n = nRaw.startsWith("half") ? 0.5 : nRaw === "a" || nRaw === "an" || nRaw === "one" ? 1 : Number(nRaw);
    const unit = rel[2].toLowerCase();
    if (unit.startsWith("h")) n *= 60;
    const due = new Date(now.getTime() + Math.round(n) * 60_000);
    const title = body.replace(rel[0], "").trim();
    return { kind: "reminder", title: cleanTitle(title), dueAt: due, recurrence: "none", trigger: "time", ambiguous: false, interpretation: `in ${Math.round(n)} min` };
  }

  // Recurrence
  let recurrence: Recurrence = "none";
  let byWeekday: number[] | undefined;
  const everyDay = body.match(/\b(every\s*day|daily|each\s+day|every\s+morning|every\s+night|every\s+evening)\b/i);
  const everyWeekday = body.match(/\b(every\s+weekday|on\s+weekdays|weekdays)\b/i);
  const everyMonth = body.match(/\b(every\s+month|monthly)\b/i);
  const everyNamed = body.match(new RegExp(`\\bevery\\s+((?:${DAY_RE})(?:\\s*(?:,|and)\\s*(?:${DAY_RE}))*)\\b`, "i"));
  if (everyWeekday) {
    recurrence = "weekdays";
    body = body.replace(everyWeekday[0], " ");
  } else if (everyNamed) {
    recurrence = "weekly";
    byWeekday = everyNamed[1].split(/\s*(?:,|and)\s*/i).map(dayIndex).filter((x) => x >= 0);
    body = body.replace(everyNamed[0], " ");
  } else if (everyDay) {
    recurrence = "daily";
    body = body.replace(everyDay[0], " ");
  } else if (everyMonth) {
    recurrence = "monthly";
    body = body.replace(everyMonth[0], " ");
  }

  // Day words
  let dayOffset: number | null = null;
  let named: number | null = null;
  const tomorrow = body.match(/\b(tomorrow|tmrw|tmr)\b/i);
  const todayW = body.match(/\b(today|tonight|this\s+evening|this\s+morning)\b/i);
  const onDay = body.match(new RegExp(`\\b(?:on|next|this)\\s+(${DAY_RE})\\b`, "i"));
  if (tomorrow) {
    dayOffset = 1;
    body = body.replace(tomorrow[0], " ");
  } else if (todayW) {
    dayOffset = 0;
    body = body.replace(todayW[0], " ");
  } else if (onDay) {
    named = dayIndex(onDay[1]);
    body = body.replace(onDay[0], " ");
  }
  const tonight = Boolean(todayW && /tonight|evening/i.test(todayW[0]));

  // Clock
  const clockMatch = body.match(/\bat\s+\d{1,2}(?:[:.]\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?|\b\d{1,2}(?:[:.]\d{2})\s*(?:a\.?m\.?|p\.?m\.?)?|\b\d{1,2}\s*(?:a\.?m\.?|p\.?m\.?)/i);
  let clock = clockMatch ? parseClock(clockMatch[0]) : null;
  if (clockMatch) body = body.replace(clockMatch[0], " ");
  let ambiguous = false;
  if (!clock) {
    if (/\bmorning\b/i.test(t)) clock = { h: 8, m: 0, explicit: false };
    else if (/\b(evening|tonight)\b/i.test(t)) clock = { h: 19, m: 0, explicit: false };
    else if (/\bnight\b/i.test(t)) clock = { h: 21, m: 0, explicit: false };
    else if (/\bafternoon\b/i.test(t)) clock = { h: 14, m: 0, explicit: false };
    else return { kind: "reminder", title: cleanTitle(body), dueAt: null, recurrence, byWeekday, trigger: "time", ambiguous: true, interpretation: "no time given" };
    ambiguous = true;
  }
  if (!clock.explicit && clock.h >= 1 && clock.h <= 11) {
    // "at 7" — am or pm? Prefer pm for tonight/evening, otherwise flag ambiguity.
    if (tonight || /\b(evening|night)\b/i.test(t)) clock.h += 12;
    else ambiguous = true;
  }

  // Resolve date
  let target = { year: today.year, month: today.month, day: today.day };
  if (dayOffset !== null) target = addDaysWall(today, dayOffset);
  else if (named !== null) {
    let add = (named - today.weekday + 7) % 7;
    if (add === 0) add = 7;
    target = addDaysWall(today, add);
  } else if (recurrence === "weekly" && byWeekday?.length) {
    for (let i = 0; i < 8; i++) {
      const w = addDaysWall(today, i);
      if (byWeekday.includes(w.weekday) && fromWall(w.year, w.month, w.day, clock.h, clock.m, tz) > now) {
        target = w;
        break;
      }
    }
  }
  let due = fromWall(target.year, target.month, target.day, clock.h, clock.m, tz);
  if (due <= now && dayOffset === null && named === null) {
    // Time already passed today -> next valid day
    for (let i = 1; i <= 8; i++) {
      const w = addDaysWall(today, i);
      if (recurrence === "weekdays" && (w.weekday === 0 || w.weekday === 6)) continue;
      if (recurrence === "weekly" && byWeekday?.length && !byWeekday.includes(w.weekday)) continue;
      due = fromWall(w.year, w.month, w.day, clock.h, clock.m, tz);
      break;
    }
  }
  if (due <= now) ambiguous = true;

  return {
    kind: "reminder",
    title: cleanTitle(body),
    dueAt: due,
    recurrence,
    byWeekday,
    trigger: "time",
    ambiguous,
    interpretation: ambiguous ? "time needs confirmation" : "exact",
  };
}

function cleanTitle(s: string): string {
  const out = s
    .replace(/\s+/g, " ")
    .replace(/^(to|about|that)\s+/i, "")
    .replace(/\s+(at|on|by|for|every)$/i, "")
    .replace(/[\s,.]+$/, "")
    .trim();
  return out ? out.charAt(0).toUpperCase() + out.slice(1) : "Reminder";
}

export function parseIntent(input: string, ctx: ParseCtx): Intent | null {
  const raw = input.trim();
  const t = raw.toLowerCase().replace(/[?!.]+$/, "").trim();
  if (!t) return null;

  if (/^(yes|confirm|confirmed|do it|go ahead|ok(ay)?)$/.test(t)) return { kind: "confirm", yes: true };
  if (/^(no|cancel|abort|stop that|don'?t)$/.test(t)) return { kind: "confirm", yes: false };

  const rem = parseReminder(raw, ctx);
  if (rem) return rem;

  const timer = t.match(/^(?:set\s+(?:a\s+)?)?timer\s+(?:for\s+)?(\d+)\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?)?(?:\s+(?:for|called|named)\s+(.+))?$/);
  if (timer) {
    const n = Number(timer[1]);
    const u = (timer[2] || "min").toLowerCase();
    const minutes = u.startsWith("h") ? n * 60 : u.startsWith("s") ? Math.max(1, Math.round(n / 60)) : n;
    return { kind: "timer", minutes: Math.min(minutes, 24 * 60), label: timer[3] ? cleanTitle(timer[3]) : "Timer" };
  }

  if (/^(what('?s| is) (on )?(my )?(agenda|schedule)( for)? today|what('?s| is) on today|today'?s? (reminders|agenda|schedule|plan)|show (my )?(today|agenda|reminders)|my (reminders|agenda))$/.test(t)) return { kind: "today" };
  if (/^(what('?s| is) the time|what time is it|time now|current time)$/.test(t)) return { kind: "time" };
  if (/^(what('?s| is) (the |today'?s )?date|what day is (it|today)|today'?s date)$/.test(t)) return { kind: "date" };
  if (/^(status|system status|what is your status|how are you|show battery( level)?|battery( level| status)?|pc status|laptop status)$/.test(t)) return { kind: "status" };
  if (/^(help|what can you do|commands)$/.test(t)) return { kind: "help" };

  const mode = t.match(/^(?:switch to |go |set mode (?:to )?|use )?(auto|online|offline)(?: mode)?$/);
  if (mode) return { kind: "mode", mode: mode[1] as "auto" | "online" | "offline" };

  // Media & volume
  if (/^(pause|play|resume|play\/pause)( (the )?(music|media|song|video))?$/.test(t)) return { kind: "tool", tool: "media_control", args: { action: "play_pause" } };
  if (/^(next|skip)( (track|song))?$/.test(t)) return { kind: "tool", tool: "media_control", args: { action: "next" } };
  if (/^(previous|prev|back)( (track|song))?$/.test(t)) return { kind: "tool", tool: "media_control", args: { action: "prev" } };
  if (/^(mute|unmute)( (the )?(volume|sound|audio|pc))?$/.test(t)) return { kind: "tool", tool: "media_control", args: { action: "mute" } };
  if (/^(volume up|increase (the )?volume|louder)$/.test(t)) return { kind: "tool", tool: "media_control", args: { action: "vol_up" } };
  if (/^(volume down|decrease (the )?volume|quieter|lower (the )?volume)$/.test(t)) return { kind: "tool", tool: "media_control", args: { action: "vol_down" } };
  const vol = t.match(/^set (?:the )?volume (?:to )?(\d{1,3})\s*%?$/);
  if (vol) return { kind: "tool", tool: "set_volume", args: { level: Math.min(100, Number(vol[1])) } };

  if (/^lock (my |the )?(pc|computer|laptop|screen|workstation)$/.test(t)) return { kind: "tool", tool: "lock_pc", args: {} };
  if (/^(put (my |the )?(pc|computer|laptop) to sleep|sleep (my |the )?(pc|computer|laptop))$/.test(t)) return { kind: "tool", tool: "sleep_pc", args: {} };
  if (/^(shut ?down|turn off) (my |the )?(pc|computer|laptop)$/.test(t)) return { kind: "tool", tool: "shutdown_pc", args: {} };
  if (/^restart (my |the )?(pc|computer|laptop)$/.test(t)) return { kind: "tool", tool: "restart_pc", args: {} };
  if (/^(unlock( (my |the )?(pc|computer|laptop|screen))?)$/.test(t)) return { kind: "tool", tool: "unlock_pc", args: {} };

  const typ = raw.match(/^type\s+(?:out\s+)?["“]?(.+?)["”]?$/i);
  if (typ) return { kind: "tool", tool: "type_text", args: { text: typ[1].slice(0, 500) } };

  const open = raw.match(/^(?:open|launch|start|run|go to|visit)\s+(?:the\s+)?(.+?)$/i);
  if (open) {
    const target = open[1].trim().replace(/\s+(app|application|please)$/i, "");
    const lower = target.toLowerCase();
    const folder = lower.replace(/\s*folder$/, "");
    if (FOLDERS.includes(folder) && (lower.endsWith("folder") || folder !== "desktop" || lower === "desktop")) {
      return { kind: "tool", tool: "open_folder", args: { folder } };
    }
    if (/^https?:\/\//i.test(target) || /^[a-z0-9-]+(\.[a-z0-9-]+)+(\/\S*)?$/i.test(target)) {
      const url = /^https?:\/\//i.test(target) ? target : `https://${target}`;
      return { kind: "tool", tool: "open_url", args: { url } };
    }
    const SITES: Record<string, string> = {
      youtube: "https://www.youtube.com", gmail: "https://mail.google.com", google: "https://www.google.com",
      github: "https://github.com", "chat gpt": "https://chatgpt.com", chatgpt: "https://chatgpt.com",
      netflix: "https://www.netflix.com", instagram: "https://www.instagram.com", maps: "https://maps.google.com",
    };
    if (SITES[lower]) return { kind: "tool", tool: "open_url", args: { url: SITES[lower] } };
    if (APP_ALIASES[lower]) return { kind: "tool", tool: "open_app", args: { app: APP_ALIASES[lower] } };
    return { kind: "tool", tool: "open_app", args: { app: lower.replace(/[^a-z0-9 ._-]/g, "").slice(0, 40) } };
  }

  const search = raw.match(/^(?:search|google)\s+(?:for\s+)?(.+)$/i);
  if (search) return { kind: "tool", tool: "open_url", args: { url: `https://www.google.com/search?q=${encodeURIComponent(search[1])}` } };

  return null;
}
