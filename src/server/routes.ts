import { NextRequest } from "next/server";
import { and, desc, eq, gte, lte, or } from "drizzle-orm";
import { db } from "@/db";
import { auditLog, devices, events, hosts, reminders } from "@/db/schema";
import { CORS_HEADERS, clientIp, err, json, num, rateLimit, readJson, str } from "./http";
import {
  audit, consumePairingCode, createOwnerSession, createPairingCode, destroyOwnerSession, hasScope, hostFromRequest,
  newToken, ownerConfigured, principal, sessionCookie, setOwnerPassphrase, sha256, verifyPassphrase, type Principal,
} from "./auth";
import { getMode, getProfile, getSetting, setSetting, DEFAULT_PROFILE, type Profile } from "./settings";
import * as relay from "./relay";
import {
  claimJobs, finishJob, handleCommand, latestHost, onlineHost, pendingApprovals, recentTasks, resolveJob, isEmergencyStopped, HOST_ONLINE_MS,
} from "./assistant";
import {
  completeReminder, createReminder, deleteReminder, dismissReminder, fireArrival, listReminders, snoozeReminder, takeNotifications, tickReminders,
} from "./reminders";
import { activeLocalModel, callProvider, canStoreKeys, cloudConfigured, getPrefs, ollamaStatus, probeInternet, savePrefs, CLOUD, type ProviderId } from "./models";
import { holidaysBetween, parseIcs, toIcs, HOLIDAY_SOURCE, HOLIDAY_DATA_UPDATED, hasGazettedData } from "@/lib/holidays";
import { TOOLS, permissionFor, type Permission } from "@/lib/tools";
import { isValidTimeZone } from "@/lib/time";

type Ctx = { req: NextRequest; method: string; path: string; seg: string[] };

const DEVICE_SCOPES = ["chat", "screen", "control", "reminders"];
const NOT_IN_GATEWAY = (feature: string) =>
  err(501, `${feature} runs only in the full EDITH desktop runtime (python -m edith.main serve) and is not available through the secure gateway yet.`, { available: false });

async function requireAuth(ctx: Ctx, body?: Record<string, unknown>, scope?: string): Promise<Principal | Response> {
  const p = await principal(ctx.req, body);
  if (p.kind === "none") return err(401, "Authentication required. Sign in on the HUD or pair this device.", { auth_required: true });
  if (scope && !hasScope(p, scope)) return err(403, `This device lacks the “${scope}” permission.`);
  return p;
}
async function requireOwner(ctx: Ctx): Promise<Principal | Response> {
  const p = await principal(ctx.req);
  if (p.kind !== "owner") return err(401, "Owner sign-in required.", { auth_required: true });
  return p;
}
const isResp = (x: unknown): x is Response => x instanceof Response;

function hostOnline(h: { lastSeenAt: Date | null } | null) {
  return Boolean(h?.lastSeenAt && Date.now() - h.lastSeenAt.getTime() < HOST_ONLINE_MS);
}

async function metricsPayload() {
  const h = await latestHost();
  const online = hostOnline(h);
  const m = (online ? h?.metrics : null) ?? {};
  return {
    host_online: online,
    host_name: h?.name ?? null,
    host_last_seen: h?.lastSeenAt ?? null,
    cpu_percent: m.cpu_percent ?? null,
    ram_percent: m.ram_percent ?? null,
    ram_used_mb: m.ram_used_mb ?? null,
    used_ram_gb: m.ram_used_mb ? Math.round((Number(m.ram_used_mb) / 1024) * 10) / 10 : null,
    disk_percent: m.disk_percent ?? null,
    disk_free_gb: m.disk_free_gb ?? null,
    battery_percent: m.battery_percent ?? null,
    power_plugged: m.power_plugged ?? null,
  };
}

function frameResponse(f: relay.Frame) {
  return new Response(new Uint8Array(f.data), {
    headers: {
      "Content-Type": "image/jpeg",
      "Content-Length": String(f.data.length),
      "Cache-Control": "no-store",
      "X-Frame-Seq": String(f.seq),
      "X-Frame-Width": String(f.width),
      "X-Frame-Height": String(f.height),
      ...CORS_HEADERS,
    },
  });
}

async function weather(): Promise<Record<string, unknown>> {
  const profile = await getProfile();
  if ((await getMode()) === "offline") return { temp: null, desc: "offline mode", available: false };
  if (!profile.city) return { temp: null, desc: "set city", available: false };
  try {
    const geo = await fetch(`https://geocoding-api.open-meteo.com/v1/search?count=1&name=${encodeURIComponent(profile.city)}`, { signal: AbortSignal.timeout(3000) });
    const gj = (await geo.json()) as { results?: { latitude: number; longitude: number }[] };
    const loc = gj.results?.[0];
    if (!loc) return { temp: null, desc: "city not found", available: false };
    const w = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${loc.latitude}&longitude=${loc.longitude}&current=temperature_2m,weather_code`, { signal: AbortSignal.timeout(3000) });
    const wj = (await w.json()) as { current?: { temperature_2m: number; weather_code: number } };
    const code = wj.current?.weather_code ?? -1;
    const desc = code === 0 ? "clear" : code <= 3 ? "cloudy" : code <= 48 ? "fog" : code <= 67 ? "rain" : code <= 77 ? "snow" : code <= 82 ? "showers" : code >= 95 ? "storm" : "—";
    return { temp: Math.round(wj.current?.temperature_2m ?? NaN), desc, available: true, source: "open-meteo.com" };
  } catch {
    return { temp: null, desc: "weather unavailable", available: false };
  }
}

/* ======================================================================= */
export async function dispatch(req: NextRequest, rawPath: string[]): Promise<Response> {
  const method = req.method.toUpperCase();
  if (method === "OPTIONS") return new Response(null, { status: 204, headers: CORS_HEADERS });
  // /api/compat/<legacy path> is where root-level legacy EDITH endpoints are rewritten to.
  const seg = rawPath[0] === "compat" ? rawPath.slice(1) : rawPath;
  const path = seg.join("/");
  const ctx: Ctx = { req, method, path, seg };
  try {
    return await route(ctx);
  } catch (e) {
    console.error("[edith] route error", path, (e as Error).message);
    return err(500, "Internal error");
  }
}

async function route(ctx: Ctx): Promise<Response> {
  const { req, method, path, seg } = ctx;
  const M = (m: string, p: string) => method === m && path === p;

  /* ---------- public ---------- */
  if (path === "ping" || path === "health") return json({ status: "ok", system: "EDITH", gateway: true, time: new Date().toISOString() });

  if (M("GET", "auth/session")) {
    const p = await principal(req);
    return json({ configured: await ownerConfigured(), owner: p.kind === "owner", setup_key_required: Boolean(process.env.EDITH_SETUP_KEY) });
  }
  if (M("POST", "auth/setup")) {
    if (await ownerConfigured()) return err(409, "Owner passphrase already set. Sign in instead.");
    const b = await readJson(req);
    if (process.env.EDITH_SETUP_KEY && str(b.setup_key) !== process.env.EDITH_SETUP_KEY) return err(403, "Invalid setup key (see EDITH_SETUP_KEY in .env).");
    const pass = str(b.passphrase, 200);
    if (pass.length < 8) return err(400, "Passphrase must be at least 8 characters.");
    await setOwnerPassphrase(pass);
    const token = await createOwnerSession(req);
    await audit("owner", "auth.setup", clientIp(req));
    return json({ ok: true }, 200, { "Set-Cookie": sessionCookie(token) });
  }
  if (M("POST", "auth/login")) {
    if (!rateLimit(`login:${clientIp(req)}`, 8, 5 * 60_000)) return err(429, "Too many attempts. Wait 5 minutes.");
    const b = await readJson(req);
    const stored = await getSetting<string>("owner_pass_hash");
    if (!stored || !verifyPassphrase(str(b.passphrase, 200), stored)) {
      await audit("anonymous", "auth.login", `failed from ${clientIp(req)}`, false);
      return err(401, "Wrong passphrase.");
    }
    const token = await createOwnerSession(req);
    await audit("owner", "auth.login", clientIp(req));
    return json({ ok: true }, 200, { "Set-Cookie": sessionCookie(token) });
  }
  if (M("POST", "auth/logout")) {
    await destroyOwnerSession(req);
    return json({ ok: true }, 200, { "Set-Cookie": sessionCookie("", 0) });
  }
  if (M("POST", "pair/claim")) {
    if (!rateLimit(`pair:${clientIp(req)}`, 6, 5 * 60_000)) return err(429, "Too many pairing attempts. Wait 5 minutes.");
    const b = await readJson(req);
    const row = await consumePairingCode("device", str(b.code, 20));
    if (!row) {
      await audit("anonymous", "pair.claim", `bad/expired code from ${clientIp(req)}`, false);
      return err(401, "Invalid or expired pairing code. Generate a new one on the HUD (Devices & Remote).");
    }
    const token = newToken();
    const name = str(b.name, 60) || row.label || "Phone";
    const [d] = await db.insert(devices).values({ name, tokenHash: sha256(token), scopes: row.scopes, lastIp: clientIp(req), lastSeenAt: new Date() }).returning();
    await audit(`phone:${name}`, "pair.success", `scopes=${row.scopes.join(",")}`);
    return json({ ok: true, token, device_id: d.id, name, scopes: row.scopes });
  }
  if (M("POST", "host/link")) {
    if (!rateLimit(`hostlink:${clientIp(req)}`, 6, 5 * 60_000)) return err(429, "Too many attempts.");
    const b = await readJson(req);
    const row = await consumePairingCode("host", str(b.code, 20));
    if (!row) return err(401, "Invalid or expired host link code.");
    const token = newToken();
    const [h] = await db.insert(hosts).values({ name: str(b.name, 60) || "Windows PC", tokenHash: sha256(token), platform: str(b.platform, 80), agentVersion: str(b.agent_version, 20), lastSeenAt: new Date() }).returning();
    await audit("host", "host.linked", h.name);
    return json({ ok: true, host_token: token, host_id: h.id });
  }
  if (M("GET", "mobile/config")) {
    return json({
      system_name: "EDITH",
      gateway: true,
      cloud_url: (await getSetting<string>("public_url")) || null,
      tunnel_status: { online: false, note: "Use a private VPN (e.g. Tailscale/WireGuard) or HTTPS reverse proxy; see docs/REMOTE_ACCESS_SETUP.md" },
      pairing: "6-digit code from HUD → Devices & Remote",
    });
  }

  /* ---------- host agent channel ---------- */
  if (seg[0] === "host" && seg[1] !== "code") {
    const host = await hostFromRequest(req);
    if (!host) return err(401, "Invalid host token.");
    if (M("POST", "host/heartbeat")) {
      const b = await readJson(req);
      const metrics = (b.metrics && typeof b.metrics === "object" ? b.metrics : {}) as Record<string, unknown>;
      await db.update(hosts).set({ lastSeenAt: new Date(), metrics, capabilities: (b.capabilities as Record<string, unknown>) ?? host.capabilities, agentVersion: str(b.agent_version, 20) || host.agentVersion }).where(eq(hosts.id, host.id));
      await tickReminders();
      return json({ ok: true, emergency_stop: await isEmergencyStopped(), stream: { active: relay.streamWanted(), ...relay.hub.prefs } });
    }
    if (M("GET", "host/poll")) {
      const wait = num(req.nextUrl.searchParams.get("wait"), 20, 0, 25) * 1000;
      const since = num(req.nextUrl.searchParams.get("killed_since"), 0);
      await db.update(hosts).set({ lastSeenAt: new Date() }).where(eq(hosts.id, host.id));
      const collect = async () => {
        const stop = await isEmergencyStopped();
        const inputs = stop ? (relay.drainInputs(), []) : relay.drainInputs();
        const jobs = stop ? [] : await claimJobs();
        const notes = await takeNotifications("host");
        return { inputs, jobs, notifications: notes.map((n) => ({ title: n.title, body: n.body })) };
      };
      await tickReminders();
      let out = await collect();
      if (!out.inputs.length && !out.jobs.length && !out.notifications.length && wait > 0) {
        await relay.waitHost(wait);
        out = await collect();
      }
      return json({ ...out, stream: { active: relay.streamWanted(), ...relay.hub.prefs }, killed_at: relay.hub.killedAt > since ? relay.hub.killedAt : 0, emergency_stop: await isEmergencyStopped() });
    }
    if (M("POST", "host/frame")) {
      if (!relay.streamWanted()) return json({ ok: true, accepted: false, reason: "no active viewer" });
      const buf = Buffer.from(await req.arrayBuffer());
      if (buf.length < 100 || buf.length > 4_000_000 || buf[0] !== 0xff || buf[1] !== 0xd8) return err(400, "Expected a JPEG frame under 4 MB.");
      relay.putFrame(buf, host.id, num(req.headers.get("x-frame-width"), 0), num(req.headers.get("x-frame-height"), 0), num(req.headers.get("x-capture-ms"), 0));
      return json({ ok: true, accepted: true, stream: { active: true, ...relay.hub.prefs } });
    }
    if (M("POST", "host/result")) {
      const b = await readJson(req);
      const job = await finishJob(str(b.job_id, 60), { ok: Boolean(b.ok), message: str(b.message, 500), data: b.data ?? null, verified: Boolean(b.verified) });
      return json({ ok: Boolean(job) });
    }
    if (M("POST", "host/kill")) {
      // Local "Disconnect" button on the PC indicator.
      relay.killSessions();
      await audit(`host:${host.name}`, "remote.session.killed_locally");
      return json({ ok: true });
    }
    return err(404, "Unknown host endpoint");
  }

  /* ---------- assistant ---------- */
  if (M("POST", "cmd") || M("POST", "api/phone/send_command")) {
    const b = await readJson(req);
    const p = await requireAuth(ctx, b, undefined);
    if (isResp(p)) return p;
    if (p.kind === "device" && !hasScope(p, "chat")) return err(403, "Device lacks chat permission.");
    const command = str(b.command, 1000).trim();
    if (!command) return json({ matched: false, result: "Empty command provided", state: "READY" });
    const requestId = str(b.request_id, 80) || req.headers.get("x-request-id") || `${p.label}:${sha256(command + Math.floor(Date.now() / 1500)).slice(0, 24)}`;
    const out = await handleCommand(command, `${p.label}|${requestId}`, p);
    return json(out);
  }

  /* everything below requires auth */
  if (M("GET", "state") || M("GET", "telemetry") || M("GET", "status") || M("GET", "api/metrics") || M("GET", "api/mode")) {
    const p = await requireAuth(ctx);
    if (isResp(p)) return p;
    await tickReminders();
    const mode = await getMode();
    const m = await metricsPayload();
    const net = mode === "offline" ? null : await probeInternet();
    return json({
      ...m,
      state: (await isEmergencyStopped()) ? "emergency_stopped" : "ready",
      emergency_stopped: await isEmergencyStopped(),
      manual_mode: mode,
      mode,
      offline_mode: mode === "offline",
      is_online: net?.online ?? false,
      internet: net ? (net.online ? "reachable" : "unreachable") : "not checked (offline mode)",
      primary_model: await activeLocalModel(),
      runtime_status: mode === "offline" ? "OFFLINE (LOCAL ONLY)" : net?.online ? `ONLINE (${mode.toUpperCase()})` : "NO INTERNET (LOCAL FALLBACK)",
      remote: { viewers: relay.activeViewers().length, paused: relay.hub.paused },
    });
  }
  if (M("POST", "api/mode")) {
    const b = await readJson(req);
    const p = await requireAuth(ctx, b, "control");
    if (isResp(p)) return p;
    const mode = str(b.mode);
    if (!["auto", "online", "offline"].includes(mode)) return err(400, "mode must be auto|online|offline");
    await setSetting("mode", mode);
    await audit(p.label, "mode.set", mode);
    return json({ ok: true, mode, manual_mode: mode });
  }
  if (M("GET", "models")) {
    const p = await requireAuth(ctx);
    if (isResp(p)) return p;
    const st = await ollamaStatus(true);
    return json({ models: st.models.map((m) => m.name), details: st.models, active_model: await activeLocalModel(), ollama_up: st.up, error: st.error ?? null });
  }
  if (M("POST", "models") || M("POST", "models/switch")) {
    const b = await readJson(req);
    const p = await requireOwner(ctx);
    if (isResp(p)) return p;
    const model = str(b.model, 120);
    const prefs = await getPrefs();
    prefs.models.local = model;
    await setSetting("providers", prefs);
    return json({ ok: true, active_model: model });
  }
  if (M("GET", "weather")) {
    const p = await requireAuth(ctx);
    if (isResp(p)) return p;
    return json(await weather());
  }

  /* ---------- emergency stop ---------- */
  if (method === "POST" && ["emergency_stop", "api/emergency_stop", "emergency_resume", "api/emergency_resume"].includes(path)) {
    const b = await readJson(req);
    const p = await requireAuth(ctx, b);
    if (isResp(p)) return p;
    const cur = await isEmergencyStopped();
    let next = path.endsWith("resume") ? false : path === "api/emergency_stop" ? (typeof b.active === "boolean" ? b.active : !cur) : true;
    if (!next && p.kind !== "owner") return err(403, "Only the owner (HUD) can resume after an emergency stop.");
    if (next && p.kind === "device" && !hasScope(p, "control")) next = cur;
    await setSetting("emergency_stop", next);
    if (next) relay.killSessions();
    await audit(p.label, next ? "estop.engaged" : "estop.released");
    return json({ ok: true, emergency_stopped: next });
  }

  /* ---------- remote desktop relay ---------- */
  if (M("GET", "api/screen/capture")) {
    const p = await requireAuth(ctx, undefined, "screen");
    if (isResp(p)) return p;
    if (await isEmergencyStopped()) return err(423, "Emergency stop active.");
    const sp = req.nextUrl.searchParams;
    const isNew = relay.touchViewer(p.label, p.label, { scale: num(sp.get("scale"), 0), quality: num(sp.get("quality"), 0) });
    if (isNew) await audit(p.label, "remote.session.start", clientIp(req));
    if (!(await onlineHost())) return err(503, "PC host agent is offline — no live frames available.", { host_online: false });
    const after = num(sp.get("after"), 0);
    const f = await relay.waitFrame(after, relay.hub.frame ? 1500 : 4000);
    if (!f) return err(504, "Waiting for the host to send the first frame…", { host_online: true });
    relay.noteFrameServed(f);
    return frameResponse(f);
  }
  if (M("GET", "stream/screen") || M("GET", "stream/mjpeg")) {
    const p = await requireAuth(ctx, undefined, "screen");
    if (isResp(p)) return p;
    const sp = req.nextUrl.searchParams;
    relay.touchViewer(p.label, p.label, { scale: num(sp.get("scale"), 0), quality: num(sp.get("quality"), 0) });
    await audit(p.label, "remote.session.start", "mjpeg");
    const enc = new TextEncoder();
    let closed = false;
    req.signal.addEventListener("abort", () => (closed = true));
    const stream = new ReadableStream({
      async start(controller) {
        let seq = 0;
        const started = Date.now();
        while (!closed && Date.now() - started < 30 * 60_000) {
          relay.touchViewer(p.label, p.label);
          const f = await relay.waitFrame(seq, 2000);
          if (closed) break;
          if (!f) continue;
          seq = f.seq;
          relay.noteFrameServed(f);
          try {
            controller.enqueue(enc.encode(`--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ${f.data.length}\r\n\r\n`));
            controller.enqueue(new Uint8Array(f.data));
            controller.enqueue(enc.encode("\r\n"));
          } catch {
            break;
          }
        }
        try {
          controller.close();
        } catch {
          /* closed */
        }
      },
      cancel() {
        closed = true;
      },
    });
    return new Response(stream, { headers: { "Content-Type": "multipart/x-mixed-replace; boundary=frame", "Cache-Control": "no-store", ...CORS_HEADERS } });
  }
  if (method === "POST" && ["api/remote/input", "api/mouse", "api/remote/click", "api/remote/key_down", "api/remote/key_up"].includes(path)) {
    const b = await readJson(req);
    const p = await requireAuth(ctx, b, "control");
    if (isResp(p)) return p;
    if (await isEmergencyStopped()) return err(423, "Emergency stop active — input blocked.");
    if (!relay.activeViewers().some((v) => v.origin === p.label)) {
      // Input is only accepted while this principal is actively viewing the screen.
      return err(409, "Open the live remote view before sending input.");
    }
    let action = str(b.action, 40);
    let params = (b.params && typeof b.params === "object" ? b.params : {}) as Record<string, unknown>;
    if (path === "api/remote/click") {
      action = str(b.button) === "right" ? "right_click" : "click";
      params = { x: b.x, y: b.y };
    } else if (path === "api/remote/key_down" || path === "api/remote/key_up") {
      action = path.endsWith("down") ? "key_down" : "key_up";
      params = { key: str(b.key, 30) };
    }
    if (!action) return err(400, "Missing action");
    if (action === "type_text" && str(params.text).length > 500) return err(400, "Text too long");
    const r = relay.enqueueInput(action, params, p.label, str(b.event_id, 80) || undefined);
    return json({ ok: true, ...r });
  }
  if (M("GET", "api/remote/status")) {
    const p = await requireAuth(ctx);
    if (isResp(p)) return p;
    const h = await latestHost();
    return json({ host_online: hostOnline(h), host: h ? { name: h.name, last_seen: h.lastSeenAt, agent: h.agentVersion, capabilities: h.capabilities } : null, streamer: relay.relayStats(), input_active: hostOnline(h) });
  }
  if (M("POST", "api/remote/disconnect")) {
    const p = await requireAuth(ctx);
    if (isResp(p)) return p;
    relay.killSessions();
    await audit(p.label, "remote.session.killed");
    return json({ ok: true });
  }
  if (M("POST", "api/remote/pause")) {
    const b = await readJson(req);
    const p = await requireOwner(ctx);
    if (isResp(p)) return p;
    relay.hub.paused = Boolean(b.paused);
    relay.wakeHost();
    return json({ ok: true, paused: relay.hub.paused });
  }

  /* ---------- phone messages (heartbeat + reminder alerts) ---------- */
  if (M("GET", "api/phone/messages")) {
    const p = await requireAuth(ctx);
    if (isResp(p)) return p;
    const sp = req.nextUrl.searchParams;
    if (p.kind === "device") {
      const bat = sp.get("battery");
      await db.update(devices).set({ battery: bat && bat !== "null" ? Math.round(Number(bat)) || null : null, connType: str(sp.get("conn"), 20) || null, lastSeenAt: new Date() }).where(eq(devices.id, p.device.id));
    }
    await tickReminders();
    const notes = p.kind === "device" && hasScope(p, "reminders") ? await takeNotifications("phone") : [];
    const messages = notes.map((n) => ({ type: "alert", title: `⏰ ${n.title}`, text: `⏰ ${n.title}${n.body ? ` — ${n.body}` : ""}`, message: `⏰ ${n.title}${n.body ? ` — ${n.body}` : ""}`, at: n.createdAt }));
    return json({ messages, count: messages.length });
  }

  /* ---------- notifications for HUD ---------- */
  if (M("GET", "api/notifications")) {
    const p = await requireOwner(ctx);
    if (isResp(p)) return p;
    await tickReminders();
    return json({ notifications: await takeNotifications("hud") });
  }

  /* ---------- reminders ---------- */
  if (seg[0] === "api" && seg[1] === "reminders") {
    const b = method === "POST" ? await readJson(req) : {};
    const p = await requireAuth(ctx, b, "reminders");
    if (isResp(p)) return p;
    if (M("GET", "api/reminders")) {
      await tickReminders();
      return json({ reminders: await listReminders(req.nextUrl.searchParams.get("all") === "1"), timezone: (await getProfile()).timezone });
    }
    if (M("POST", "api/reminders")) {
      const title = str(b.title, 200).trim();
      const due = new Date(str(b.due_at, 40));
      if (!title) return err(400, "Title required");
      if (str(b.trigger) !== "manual_arrival" && isNaN(due.getTime())) return err(400, "Valid due_at (ISO date-time) required");
      const row = await createReminder({
        title, dueAt: isNaN(due.getTime()) ? new Date() : due, notes: str(b.notes, 1000) || null, recurrence: str(b.recurrence) || "none",
        byWeekday: Array.isArray(b.by_weekday) ? (b.by_weekday as unknown[]).map(Number) : null, priority: str(b.priority) || "normal",
        category: str(b.category) || "general", trigger: str(b.trigger) || "time", source: p.label,
      });
      await audit(p.label, "reminder.create", title);
      return json({ ok: true, reminder: row });
    }
    if (M("POST", "api/reminders/arrived")) return json({ ok: true, fired: await fireArrival() });
    if (M("GET", "api/reminders/export")) return json({ exported_at: new Date(), reminders: await listReminders(true) });
    if (M("POST", "api/reminders/import")) {
      const list = Array.isArray(b.reminders) ? (b.reminders as Record<string, unknown>[]) : [];
      let n = 0;
      const existing = new Set((await listReminders(true)).map((r) => `${r.title}|${r.dueAt.toISOString()}`));
      for (const r of list.slice(0, 1000)) {
        const due = new Date(String(r.dueAt ?? r.due_at ?? ""));
        const title = String(r.title ?? "").slice(0, 200);
        if (!title || isNaN(due.getTime()) || existing.has(`${title}|${due.toISOString()}`)) continue;
        await createReminder({ title, dueAt: due, recurrence: String(r.recurrence ?? "none"), byWeekday: (r.byWeekday as number[]) ?? null, category: String(r.category ?? "general"), priority: String(r.priority ?? "normal"), notes: (r.notes as string) ?? null, source: "import" });
        n++;
      }
      return json({ ok: true, imported: n });
    }
    const id = seg[2];
    if (id && method === "DELETE") {
      await deleteReminder(id);
      return json({ ok: true });
    }
    if (id && method === "POST") {
      const action = seg[3];
      const row = action === "snooze" ? await snoozeReminder(id, num(b.minutes, 10, 1, 1440)) : action === "complete" ? await completeReminder(id) : action === "dismiss" ? await dismissReminder(id) : null;
      if (!row) return err(404, "Reminder not found or unknown action");
      return json({ ok: true, reminder: row });
    }
  }

  /* ---------- calendar ---------- */
  if (seg[0] === "api" && seg[1] === "calendar") {
    const b = method === "POST" ? await readJson(req) : {};
    const p = await requireAuth(ctx, b, "reminders");
    if (isResp(p)) return p;
    if (M("GET", "api/calendar")) {
      const sp = req.nextUrl.searchParams;
      const from = str(sp.get("from"), 10) || new Date().toISOString().slice(0, 10);
      const to = str(sp.get("to"), 10) || from;
      const profile = await getProfile();
      const all = await db.select().from(events).where(or(and(gte(events.date, from), lte(events.date, to)), eq(events.recurrence, "yearly"))).limit(2000);
      const expanded: (typeof all[number] & { occurs: string })[] = [];
      const y0 = Number(from.slice(0, 4));
      const y1 = Number(to.slice(0, 4));
      for (const e of all) {
        if (e.recurrence === "yearly") {
          for (let y = y0; y <= y1; y++) {
            const d = `${y}${e.date.slice(4)}`;
            if (d >= from && d <= to && d >= e.date) expanded.push({ ...e, occurs: d });
          }
        } else expanded.push({ ...e, occurs: e.date });
      }
      const hol = profile.country === "IN" ? holidaysBetween(from, to, profile.holidayCategories) : [];
      return json({ events: expanded, holidays: hol, holiday_source: HOLIDAY_SOURCE, holiday_updated: HOLIDAY_DATA_UPDATED, gazetted_data_years: [y0, y1].filter((y, i, a) => a.indexOf(y) === i).map((y) => ({ year: y, available: hasGazettedData(y) })) });
    }
    if (M("POST", "api/calendar")) {
      const title = str(b.title, 200).trim();
      const date = str(b.date, 10);
      if (!title || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return err(400, "title and date (YYYY-MM-DD) required");
      const time = /^\d{2}:\d{2}$/.test(str(b.time)) ? str(b.time) : null;
      const category = str(b.category, 30) || "event";
      const dup = await db.select({ id: events.id }).from(events).where(and(eq(events.title, title), eq(events.date, date))).limit(1);
      if (dup.length) return err(409, "An event with the same title and date already exists.");
      const recurrence = str(b.recurrence) === "yearly" || ["birthday", "anniversary"].includes(category) ? "yearly" : "none";
      const [row] = await db.insert(events).values({ title, date, time, category, recurrence, notes: str(b.notes, 1000) || null, color: str(b.color, 20) || null }).returning();
      return json({ ok: true, event: row });
    }
    if (M("GET", "api/calendar/ics")) {
      const all = await db.select().from(events).limit(5000);
      return new Response(toIcs(all), { headers: { "Content-Type": "text/calendar; charset=utf-8", "Content-Disposition": 'attachment; filename="edith-calendar.ics"', ...CORS_HEADERS } });
    }
    if (M("POST", "api/calendar/import")) {
      const items = parseIcs(str(b.ics, 2_000_000));
      let n = 0;
      for (const it of items) {
        const dup = await db.select({ id: events.id }).from(events).where(and(eq(events.title, it.title), eq(events.date, it.date))).limit(1);
        if (dup.length) continue;
        await db.insert(events).values({ title: it.title, date: it.date, time: it.time, recurrence: it.yearly ? "yearly" : "none", source: "ics" });
        n++;
      }
      return json({ ok: true, imported: n, found: items.length });
    }
    if (seg[2] && method === "DELETE") {
      await db.delete(events).where(eq(events.id, seg[2]));
      return json({ ok: true });
    }
  }

  /* ---------- profile / permissions ---------- */
  if (M("GET", "api/profile")) {
    const p = await requireAuth(ctx);
    if (isResp(p)) return p;
    return json({ profile: await getProfile(), tutorial: (await getSetting<Record<string, boolean>>("tutorial")) ?? {} });
  }
  if (M("POST", "api/profile")) {
    const b = await readJson(req);
    const p = await requireOwner(ctx);
    if (isResp(p)) return p;
    const cur = await getProfile();
    const next: Profile = { ...cur };
    for (const k of Object.keys(DEFAULT_PROFILE) as (keyof Profile)[]) {
      if (b[k] === undefined) continue;
      if (k === "holidayCategories") next.holidayCategories = Array.isArray(b[k]) ? (b[k] as string[]).filter((c) => ["national", "gazetted"].includes(c)) : cur.holidayCategories;
      else if (k === "resourceProfile") next.resourceProfile = b[k] === "4gb" ? "4gb" : "8gb";
      else if (k === "timezone") next.timezone = isValidTimeZone(str(b[k])) ? str(b[k]) : cur.timezone;
      else if (k === "quietStart" || k === "quietEnd") next[k] = /^\d{2}:\d{2}$/.test(str(b[k])) ? str(b[k]) : null;
      else (next as unknown as Record<string, unknown>)[k] = str(b[k], 80);
    }
    await setSetting("profile", next);
    if (b.tutorial && typeof b.tutorial === "object") await setSetting("tutorial", b.tutorial);
    return json({ ok: true, profile: next });
  }
  if (M("GET", "api/permissions")) {
    const p = await requireOwner(ctx);
    if (isResp(p)) return p;
    const o = (await getSetting<Record<string, Permission>>("permissions")) ?? {};
    return json({ tools: Object.values(TOOLS).map((t) => ({ name: t.name, description: t.description, risk: t.risk, supported: t.supported, reason: t.unsupportedReason ?? null, permission: permissionFor(t, o) })) });
  }
  if (M("POST", "api/permissions")) {
    const b = await readJson(req);
    const p = await requireOwner(ctx);
    if (isResp(p)) return p;
    const o = (await getSetting<Record<string, Permission>>("permissions")) ?? {};
    const tool = TOOLS[str(b.tool)];
    const perm = str(b.permission) as Permission;
    if (!tool || !["auto", "ask", "deny"].includes(perm)) return err(400, "Invalid tool or permission");
    o[tool.name] = perm;
    await setSetting("permissions", o);
    await audit("owner", "permission.set", `${tool.name}=${permissionFor(tool, o)}`);
    return json({ ok: true, permission: permissionFor(tool, o) });
  }

  /* ---------- devices & hosts ---------- */
  if (M("GET", "api/devices") || M("GET", "api/phone/devices")) {
    const p = await requireOwner(ctx);
    if (isResp(p)) return p;
    const d = await db.select({ id: devices.id, name: devices.name, scopes: devices.scopes, createdAt: devices.createdAt, lastSeenAt: devices.lastSeenAt, lastIp: devices.lastIp, battery: devices.battery, connType: devices.connType, revokedAt: devices.revokedAt }).from(devices).orderBy(desc(devices.createdAt)).limit(50);
    const h = await db.select({ id: hosts.id, name: hosts.name, platform: hosts.platform, agentVersion: hosts.agentVersion, lastSeenAt: hosts.lastSeenAt, revokedAt: hosts.revokedAt, capabilities: hosts.capabilities }).from(hosts).orderBy(desc(hosts.createdAt)).limit(20);
    return json({ devices: d, hosts: h.map((x) => ({ ...x, online: !x.revokedAt && hostOnline(x) })) });
  }
  if (M("POST", "api/pair/code") || M("POST", "api/host/code") || M("POST", "host/code")) {
    const b = await readJson(req);
    const p = await requireOwner(ctx);
    if (isResp(p)) return p;
    const isHost = path !== "api/pair/code";
    const scopes = isHost ? ["host"] : (Array.isArray(b.scopes) ? (b.scopes as string[]) : DEVICE_SCOPES).filter((s) => DEVICE_SCOPES.includes(s));
    const { code, expiresAt } = await createPairingCode(isHost ? "host" : "device", scopes, str(b.name, 60) || (isHost ? "Windows PC" : "Phone"), isHost ? 10 : 5);
    await audit("owner", isHost ? "host.code" : "pair.code", `scopes=${scopes.join(",")}`);
    return json({ ok: true, code, expires_at: expiresAt, scopes });
  }
  if (seg[0] === "api" && (seg[1] === "devices" || seg[1] === "hosts") && seg[3] === "revoke" && method === "POST") {
    const p = await requireOwner(ctx);
    if (isResp(p)) return p;
    if (seg[1] === "devices") await db.update(devices).set({ revokedAt: new Date() }).where(eq(devices.id, seg[2]));
    else await db.update(hosts).set({ revokedAt: new Date() }).where(eq(hosts.id, seg[2]));
    relay.killSessions();
    await audit("owner", `${seg[1]}.revoke`, seg[2]);
    return json({ ok: true });
  }
  if (M("POST", "api/public_url")) {
    const b = await readJson(req);
    const p = await requireOwner(ctx);
    if (isResp(p)) return p;
    const u = str(b.url, 300).trim();
    if (u && !/^https?:\/\//.test(u)) return err(400, "URL must start with http(s)://");
    await setSetting("public_url", u || null);
    return json({ ok: true });
  }

  /* ---------- approvals & logs ---------- */
  if (M("GET", "api/confirm/pending")) {
    const p = await requireAuth(ctx);
    if (isResp(p)) return p;
    return json({ pending: await pendingApprovals() });
  }
  if (M("POST", "api/confirm/resolve")) {
    const b = await readJson(req);
    const p = await requireAuth(ctx, b, "control");
    if (isResp(p)) return p;
    const job = await resolveJob(str(b.id, 60), Boolean(b.approve), p.label);
    return job ? json({ ok: true, job }) : err(404, "No pending approval with that id (it may have expired).");
  }
  if (M("GET", "api/logs") || M("GET", "api/activity")) {
    const p = await requireOwner(ctx);
    if (isResp(p)) return p;
    const rows = await db.select().from(auditLog).orderBy(desc(auditLog.id)).limit(150);
    return json({ entries: rows, tasks: await recentTasks(), logs: rows.map((r) => `${r.at.toISOString()} [${r.actor}] ${r.action}${r.detail ? `: ${r.detail}` : ""}${r.ok ? "" : " (FAILED)"}`).join("\n") });
  }

  /* ---------- providers ---------- */
  if (M("GET", "api/providers")) {
    const p = await requireOwner(ctx);
    if (isResp(p)) return p;
    const prefs = await getPrefs();
    const configured: Record<string, boolean> = {};
    for (const c of CLOUD) configured[c] = await cloudConfigured(c, prefs);
    const st = await ollamaStatus();
    configured.local = st.up;
    return json({ active_provider: prefs.active_provider, models: prefs.models, gateway_url: prefs.gateway_url ?? null, configured, can_store_keys: canStoreKeys(), mode: await getMode() });
  }
  if (M("POST", "api/providers/save")) {
    const b = await readJson(req);
    const p = await requireOwner(ctx);
    if (isResp(p)) return p;
    try {
      const prefs = await savePrefs({ provider: str(b.provider), api_key: str(b.api_key, 300), model: str(b.model, 120), base_url: str(b.base_url, 300) });
      await audit("owner", "provider.save", prefs.active_provider);
      return json({ ok: true, active_provider: prefs.active_provider });
    } catch (e) {
      return err(400, (e as Error).message);
    }
  }
  if (M("POST", "api/providers/test") || M("POST", "api/providers")) {
    const b = await readJson(req);
    const p = await requireOwner(ctx);
    if (isResp(p)) return p;
    const prov = (str(b.provider) || "local") as ProviderId;
    if (prov !== "local" && (await getMode()) === "offline") return json({ ok: false, error: "Offline mode is on — cloud providers are not contacted." });
    const t0 = Date.now();
    try {
      const r = await callProvider(prov, "Reply with exactly: OK", { model: str(b.model, 120) || undefined, key: str(b.api_key, 300) || undefined, base: str(b.base_url, 300) || undefined, timeoutMs: prov === "local" ? 60_000 : 15_000 });
      return json({ ok: true, model: r.model, latency: Date.now() - t0, reply: r.text.slice(0, 60) });
    } catch (e) {
      return json({ ok: false, error: (e as Error).message.slice(0, 200), latency: Date.now() - t0 });
    }
  }

  /* ---------- diagnostics & data ---------- */
  if (M("GET", "api/diagnostics")) {
    const p = await requireOwner(ctx);
    if (isResp(p)) return p;
    const mode = await getMode();
    const h = await latestHost();
    const st = await ollamaStatus(true);
    const prefs = await getPrefs();
    const configured: Record<string, boolean> = {};
    for (const c of CLOUD) configured[c] = await cloudConfigured(c, prefs);
    return json({
      generated_at: new Date(),
      mode,
      internet: mode === "offline" ? "not probed (offline mode)" : await probeInternet(true),
      ollama: { up: st.up, url_is_local: /127\.0\.0\.1|localhost/.test(process.env.OLLAMA_URL || "127.0.0.1"), models: st.models.map((m) => `${m.name} (${Math.round(m.size / 1e6)} MB)`), error: st.error ?? null, active: await activeLocalModel() },
      providers: { active: prefs.active_provider, configured, keys_storable: canStoreKeys() },
      host: h ? { name: h.name, online: hostOnline(h), last_seen: h.lastSeenAt, agent: h.agentVersion, capabilities: h.capabilities } : null,
      remote: relay.relayStats(),
      emergency_stop: await isEmergencyStopped(),
      process: { node: process.version, rss_mb: Math.round(process.memoryUsage().rss / 1e6), uptime_s: Math.round(process.uptime()) },
      note: "Redacted: no tokens, keys, passphrases or screen content are included.",
    });
  }
  if (M("GET", "api/export")) {
    const p = await requireOwner(ctx);
    if (isResp(p)) return p;
    return json({ exported_at: new Date(), profile: await getProfile(), reminders: await db.select().from(reminders), events: await db.select().from(events) });
  }
  if (M("GET", "api/tunnel")) {
    const p = await requireAuth(ctx);
    if (isResp(p)) return p;
    return json({ online: false, provider: null, public_url: (await getSetting<string>("public_url")) || null, note: "The gateway does not open public tunnels. Use Tailscale/WireGuard or an HTTPS reverse proxy (docs/REMOTE_ACCESS_SETUP.md)." });
  }
  if (method === "POST" && (path === "voice/character" || path === "api/voice/character")) {
    const b = await readJson(req);
    const p = await requireAuth(ctx, b);
    if (isResp(p)) return p;
    await setSetting("voice_character", str(b.character, 30) || "edith");
    return json({ ok: true, character: str(b.character, 30) || "edith", note: "Speech is synthesized in your browser/phone (Web Speech API)." });
  }
  if (path.startsWith("voice/") || path.startsWith("api/voice/")) return NOT_IN_GATEWAY("Server-side voice (Whisper STT / clap wake / server TTS)");
  if (path.startsWith("api/sentinel")) return NOT_IN_GATEWAY("Face Sentinel");
  if (path.startsWith("api/airdrop")) return NOT_IN_GATEWAY("File transfer (AirDrop)");
  if (path.startsWith("api/audio") || path.startsWith("audio/")) return NOT_IN_GATEWAY("Per-app audio mixer (use “volume up/down”, “mute”, “set volume to 40”)");
  if (path.startsWith("api/clipboard")) return NOT_IN_GATEWAY("Clipboard sync (disabled by default for privacy)");
  if (path.startsWith("api/gamestream")) return NOT_IN_GATEWAY("GameStream");
  if (path.startsWith("vision/")) return NOT_IN_GATEWAY("Screen vision analysis");

  return err(404, `Unknown endpoint: /${path}`);
}


