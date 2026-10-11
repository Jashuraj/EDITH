import { and, desc, eq, gt, isNull, lt, sql } from "drizzle-orm";
import { db } from "@/db";
import { hostJobs, hosts, tasks } from "@/db/schema";
import { parseIntent, type Intent } from "@/lib/intent";
import { TOOLS, extractToolCall, permissionFor, type Permission } from "@/lib/tools";
import { formatInTz } from "@/lib/time";
import { audit, hasScope, type Principal } from "./auth";
import { routeChat, probeInternet, ollamaStatus, activeLocalModel } from "./models";
import { createReminder, describeReminder, listReminders } from "./reminders";
import { getMode, getProfile, getSetting, setSetting } from "./settings";
import { wakeHost } from "./relay";

export const HOST_ONLINE_MS = 20_000;

export interface CmdResponse {
  matched: boolean;
  result: string;
  model: string;
  state: string;
  status: string;
  task_id?: string;
  job_id?: string;
  needs_approval?: boolean;
  url?: string | null;
  opened_on_host?: boolean;
  duplicate?: boolean;
  server_spoken: boolean;
}

type Pending = { kind: "reminder"; intent: Extract<Intent, { kind: "reminder" }>; at: number };
const g = globalThis as typeof globalThis & { __edithPending?: Map<string, Pending>; __edithJobWaiters?: Map<string, (r: Record<string, unknown>) => void> };
const pending: Map<string, Pending> = g.__edithPending ?? (g.__edithPending = new Map<string, Pending>());
export const jobWaiters: Map<string, (r: Record<string, unknown>) => void> =
  g.__edithJobWaiters ?? (g.__edithJobWaiters = new Map<string, (r: Record<string, unknown>) => void>());

export async function onlineHost() {
  const rows = await db
    .select()
    .from(hosts)
    .where(and(isNull(hosts.revokedAt), gt(hosts.lastSeenAt, new Date(Date.now() - HOST_ONLINE_MS))))
    .orderBy(desc(hosts.lastSeenAt))
    .limit(1);
  return rows[0] ?? null;
}

export async function latestHost() {
  const rows = await db.select().from(hosts).where(isNull(hosts.revokedAt)).orderBy(desc(hosts.lastSeenAt)).limit(1);
  return rows[0] ?? null;
}

export async function isEmergencyStopped() {
  return Boolean(await getSetting<boolean>("emergency_stop"));
}

function resp(partial: Partial<CmdResponse> & { result: string }): CmdResponse {
  return { matched: true, model: "REFLEX_ENGINE", state: "READY", status: "done", server_spoken: false, ...partial };
}

async function waitJob(jobId: string, ms: number): Promise<Record<string, unknown> | null> {
  return new Promise((resolve) => {
    const t = setTimeout(() => {
      jobWaiters.delete(jobId);
      resolve(null);
    }, ms);
    jobWaiters.set(jobId, (r) => {
      clearTimeout(t);
      jobWaiters.delete(jobId);
      resolve(r);
    });
  });
}

export async function runTool(name: string, args: Record<string, unknown>, p: Principal, taskId: string | undefined, via: string): Promise<CmdResponse> {
  const def = TOOLS[name];
  if (!def) return resp({ result: `Unknown tool “${name}”.`, status: "error" });
  if (!def.supported) return resp({ result: def.unsupportedReason || "Not supported.", status: "error" });
  const v = def.validate(args);
  if (!v.ok) return resp({ result: v.error, status: "error" });
  if (def.runsOn === "host" && !hasScope(p, "control")) {
    return resp({ result: "This paired device does not have the “control” permission for PC actions.", status: "denied" });
  }
  if (await isEmergencyStopped()) return resp({ result: "🛑 Emergency stop is active. PC actions are blocked until you resume from the HUD.", status: "denied" });

  const overrides = await getSetting<Record<string, Permission>>("permissions");
  const perm = permissionFor(def, overrides);
  if (perm === "deny") return resp({ result: `“${v.summary}” is disabled in your permission settings.`, status: "denied" });

  const host = await onlineHost();
  if (!host) {
    const last = await latestHost();
    await audit(p.label, `tool.${name}`, "host offline", false);
    return resp({
      result: last?.lastSeenAt
        ? `Your PC host is offline (last seen ${formatInTz(last.lastSeenAt, (await getProfile()).timezone)}). The command was NOT sent — it will not run later by surprise.`
        : "No PC host agent is linked yet. Open Devices & Remote → “Link this PC” and run the EDITH host agent on Windows.",
      status: "error",
    });
  }

  const status = perm === "ask" ? "awaiting_approval" : "pending";
  const [job] = await db
    .insert(hostJobs)
    .values({ taskId: taskId ?? null, tool: name, args: v.args, risk: def.risk, summary: v.summary, status, origin: p.label })
    .returning();
  await audit(p.label, `tool.${name}`, `${status} via ${via}: ${v.summary}`);

  if (status === "awaiting_approval") {
    return resp({
      result:
        def.risk === "high"
          ? `⚠ High-risk action: ${v.summary}. Reply “confirm” to proceed or “cancel”. You can also approve it in System Activity.`
          : `Approval needed: ${v.summary}. Reply “yes” to run it, or approve it in System Activity.`,
      status: "awaiting_approval",
      needs_approval: true,
      job_id: job.id,
    });
  }
  wakeHost();
  const r = await waitJob(job.id, 8000);
  if (!r) return resp({ result: `Sent to PC: ${v.summary}. Waiting for the host to confirm…`, status: "queued", job_id: job.id });
  return resp({ result: String(r.message || (r.ok ? "Done." : "Failed.")), status: r.ok ? "done" : "error", job_id: job.id, opened_on_host: Boolean(r.ok) });
}

export async function resolveJob(jobId: string, approve: boolean, actor: string) {
  const [job] = await db
    .update(hostJobs)
    .set({ status: approve ? "pending" : "denied", finishedAt: approve ? null : new Date() })
    .where(and(eq(hostJobs.id, jobId), eq(hostJobs.status, "awaiting_approval")))
    .returning();
  if (!job) return null;
  await audit(actor, approve ? "approval.granted" : "approval.denied", job.summary);
  if (approve) wakeHost();
  return job;
}

async function latestAwaiting(origin: string) {
  const rows = await db
    .select()
    .from(hostJobs)
    .where(and(eq(hostJobs.status, "awaiting_approval"), eq(hostJobs.origin, origin), gt(hostJobs.createdAt, new Date(Date.now() - 10 * 60_000))))
    .orderBy(desc(hostJobs.createdAt))
    .limit(1);
  return rows[0] ?? null;
}

async function todaySummary(): Promise<string> {
  const profile = await getProfile();
  const rows = await listReminders(false);
  const end = new Date(Date.now() + 24 * 3600_000);
  const upcoming = rows.filter((r) => r.trigger === "time" && r.status === "active" && r.dueAt <= end);
  const fired = rows.filter((r) => r.status === "fired");
  const arrival = rows.filter((r) => r.trigger === "manual_arrival" && r.status === "active");
  if (!upcoming.length && !fired.length && !arrival.length) return "Nothing scheduled in the next 24 hours.";
  const parts: string[] = [];
  if (fired.length) parts.push(`Needs attention: ${fired.map((r) => r.title).join(", ")}.`);
  if (upcoming.length) parts.push(`Next 24h: ${upcoming.slice(0, 8).map((r) => `${r.title} (${formatInTz(r.dueAt, profile.timezone)})`).join("; ")}.`);
  if (arrival.length) parts.push(`On arrival: ${arrival.map((r) => r.title).join(", ")}.`);
  return parts.join(" ");
}

async function saveReminderIntent(intent: Extract<Intent, { kind: "reminder" }>, source: string) {
  const row = await createReminder({
    title: intent.title,
    dueAt: intent.dueAt ?? new Date(),
    recurrence: intent.recurrence,
    byWeekday: intent.byWeekday,
    trigger: intent.trigger,
    category: /medicine|tablet|pill/i.test(intent.title) ? "medicine" : /laundry|clothes|wash|clean/i.test(intent.title) ? "chore" : "general",
    source,
  });
  return `Reminder set: ${describeReminder(row)}.`;
}

async function handleIntent(intent: Intent, p: Principal, taskId: string, raw: string): Promise<CmdResponse | null> {
  const profile = await getProfile();
  const tz = profile.timezone;
  switch (intent.kind) {
    case "confirm": {
      const pend = pending.get(p.label);
      if (pend && Date.now() - pend.at < 5 * 60_000) {
        pending.delete(p.label);
        if (!intent.yes) return resp({ result: "Okay, reminder not saved." });
        return resp({ result: await saveReminderIntent(pend.intent, p.label) });
      }
      const job = await latestAwaiting(p.label);
      if (!job) return resp({ result: "There is nothing waiting for confirmation." });
      if (intent.yes && job.risk === "high" && !/^confirm/i.test(raw.trim())) {
        return resp({ result: `This is high-risk (${job.summary}). Type “confirm” exactly to proceed.`, status: "awaiting_approval" });
      }
      if (intent.yes && !hasScope(p, "control")) return resp({ result: "This device cannot approve PC actions.", status: "denied" });
      await resolveJob(job.id, intent.yes, p.label);
      if (!intent.yes) return resp({ result: `Cancelled: ${job.summary}.` });
      const r = await waitJob(job.id, 8000);
      return resp({ result: r ? String(r.message || "Done.") : `Approved: ${job.summary}. Waiting for the host…`, status: r ? (r.ok ? "done" : "error") : "queued", job_id: job.id });
    }
    case "reminder": {
      if (intent.trigger === "time" && !intent.dueAt) {
        return resp({ result: `When should I remind you to “${intent.title}”? Try: “remind me to ${intent.title.toLowerCase()} at 7:30 pm”.` });
      }
      if (intent.ambiguous) {
        pending.set(p.label, { kind: "reminder", intent, at: Date.now() });
        return resp({
          result: `Please confirm: “${intent.title}” at ${formatInTz(intent.dueAt!, tz)}${intent.recurrence !== "none" ? ` (repeats ${intent.recurrence})` : ""}. Reply “yes” to save, or rephrase with AM/PM.`,
          status: "awaiting_confirmation",
        });
      }
      return resp({ result: await saveReminderIntent(intent, p.label) });
    }
    case "timer": {
      const row = await createReminder({ title: `⏱ ${intent.label}`, dueAt: new Date(Date.now() + intent.minutes * 60_000), category: "timer", priority: "high", source: p.label });
      return resp({ result: `Timer set for ${intent.minutes} min (rings at ${formatInTz(row.dueAt, tz)}).` });
    }
    case "today":
      return resp({ result: await todaySummary() });
    case "time":
      return resp({ result: `It's ${new Intl.DateTimeFormat("en-IN", { timeZone: tz, hour: "numeric", minute: "2-digit", hour12: true }).format(new Date())} (${tz}).` });
    case "date":
      return resp({ result: new Intl.DateTimeFormat("en-IN", { timeZone: tz, weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(new Date()) });
    case "status": {
      const host = await onlineHost();
      const mode = await getMode();
      const m = (host?.metrics ?? {}) as Record<string, number | boolean | null>;
      const hostTxt = host
        ? `PC online: CPU ${m.cpu_percent ?? "?"}%, RAM ${m.ram_percent ?? "?"}%, battery ${m.battery_percent ?? "n/a"}%${m.power_plugged ? " (charging)" : ""}.`
        : "PC host agent offline.";
      const ol = mode === "offline" ? null : await probeInternet();
      const oll = await ollamaStatus();
      return resp({
        result: `${hostTxt} Mode ${mode.toUpperCase()}. Internet: ${ol ? (ol.online ? "reachable" : "unreachable") : "not checked (offline mode)"}. Ollama: ${oll.up ? `running (${oll.models.length} models, active ${await activeLocalModel()})` : "not reachable"}.`,
      });
    }
    case "help":
      return resp({
        result:
          "Try: “remind me to wash clothes at 7:30 pm”, “remind me to call mom every Sunday at 10 am”, “timer 10 minutes”, “what's on today”, “open chrome”, “open youtube.com”, “volume up”, “lock pc”, “status”, “go offline”. Anything else goes to the AI model (local Ollama or your online provider).",
      });
    case "mode":
      await setSetting("mode", intent.mode);
      await audit(p.label, "mode.set", intent.mode);
      return resp({ result: `Mode set to ${intent.mode.toUpperCase()}.${intent.mode === "offline" ? " No cloud AI or internet calls will be made." : ""}` });
    case "tool":
      return runTool(intent.tool, intent.args, p, taskId, "reflex");
  }
  return null;
}

/** Main entry for /cmd (HUD, phone PWA, APK). Idempotent by request_id. */
export async function handleCommand(command: string, requestId: string, p: Principal): Promise<CmdResponse> {
  const inserted = await db
    .insert(tasks)
    .values({ requestId, origin: p.label, command: command.slice(0, 1000), status: "running" })
    .onConflictDoNothing()
    .returning();
  if (!inserted.length) {
    const [prev] = await db.select().from(tasks).where(eq(tasks.requestId, requestId)).limit(1);
    if (prev?.result) return { ...(prev.result as unknown as CmdResponse), duplicate: true };
    return resp({ result: "This request is already being processed.", status: "running", duplicate: true });
  }
  const task = inserted[0];
  let out: CmdResponse;
  try {
    const profile = await getProfile();
    const intent = parseIntent(command, { now: new Date(), tz: profile.timezone });
    out = (intent && (await handleIntent(intent, p, task.id, command))) || (await llmPath(command, p, task.id));
  } catch (e) {
    out = resp({ result: `Internal error: ${(e as Error).message}`, status: "error", matched: false });
  }
  out.task_id = task.id;
  await db
    .update(tasks)
    .set({ status: out.status, engine: out.model, result: out as unknown as Record<string, unknown>, finishedAt: new Date() })
    .where(eq(tasks.id, task.id));
  return out;
}

async function llmPath(command: string, p: Principal, taskId: string): Promise<CmdResponse> {
  const r = await routeChat(command);
  if (!r.ok) return resp({ matched: false, result: r.text, model: "NONE", status: "error" });
  const call = extractToolCall(r.text);
  if (call) {
    const out = await runTool(call.tool, call.args, p, taskId, `model ${r.engine}`);
    return { ...out, model: r.engine.toUpperCase() };
  }
  return resp({ matched: false, result: r.text, model: r.engine.toUpperCase(), status: "done" });
}

/** Expire stale jobs so a reconnecting host never runs old commands. */
export async function expireStaleJobs() {
  await db
    .update(hostJobs)
    .set({ status: "expired", finishedAt: new Date() })
    .where(and(eq(hostJobs.status, "pending"), lt(hostJobs.createdAt, new Date(Date.now() - 60_000))));
  await db
    .update(hostJobs)
    .set({ status: "expired", finishedAt: new Date() })
    .where(and(eq(hostJobs.status, "awaiting_approval"), lt(hostJobs.createdAt, new Date(Date.now() - 15 * 60_000))));
}

export async function claimJobs() {
  await expireStaleJobs();
  return db
    .update(hostJobs)
    .set({ status: "claimed", claimedAt: new Date() })
    .where(eq(hostJobs.status, "pending"))
    .returning({ id: hostJobs.id, tool: hostJobs.tool, args: hostJobs.args, summary: hostJobs.summary });
}

export async function finishJob(id: string, result: Record<string, unknown>) {
  const [job] = await db
    .update(hostJobs)
    .set({ status: result.ok ? "done" : "error", result, finishedAt: new Date() })
    .where(and(eq(hostJobs.id, id), eq(hostJobs.status, "claimed")))
    .returning();
  if (job) jobWaiters.get(id)?.(result);
  return job ?? null;
}

export async function pendingApprovals() {
  await expireStaleJobs();
  return db.select().from(hostJobs).where(eq(hostJobs.status, "awaiting_approval")).orderBy(desc(hostJobs.createdAt)).limit(20);
}

export async function recentTasks(limit = 40) {
  return db
    .select({ id: tasks.id, origin: tasks.origin, command: tasks.command, engine: tasks.engine, status: tasks.status, createdAt: tasks.createdAt, result: sql<string>`${tasks.result}->>'result'` })
    .from(tasks)
    .orderBy(desc(tasks.createdAt))
    .limit(limit);
}
