// End-to-end test against a running gateway + the real Python host agent (--synthetic test pattern).
// Usage: BASE=http://127.0.0.1:3123 node tests/e2e.mjs
import { spawn } from "node:child_process";
import assert from "node:assert/strict";
const BASE = process.env.BASE || "http://127.0.0.1:3123";
let cookie = "";
const results = [];
const step = async (name, fn) => {
  try { const d = await fn(); results.push(["PASS", name, d ?? ""]); console.log("PASS", name, d ?? ""); }
  catch (e) { results.push(["FAIL", name, e.message]); console.log("FAIL", name, e.message); process.exitCode = 1; }
};
async function call(path, { method, body, token, owner = true, raw = false } = {}) {
  const h = { "Content-Type": "application/json" };
  if (owner && cookie) h.Cookie = cookie;
  if (token) h["X-Token"] = token;
  const r = await fetch(BASE + path, { method: method || (body ? "POST" : "GET"), headers: h, body: body ? JSON.stringify(body) : undefined });
  if (raw) return r;
  let j = {}; try { j = await r.json(); } catch {}
  return { s: r.status, j, h: r.headers };
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const pct = (a, p) => { const s = [...a].sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(p / 100 * s.length))]; };

let devToken, agent;
await step("legacy HUD served at / and phone app at /mobile", async () => {
  const r = await fetch(BASE + "/"); const t = await r.text();
  assert.equal(r.status, 200); assert.ok(t.includes("E.D.I.T.H.") && t.includes("edith-gateway.js"));
  const m = await fetch(BASE + "/mobile", { redirect: "follow" }); assert.equal(m.status, 200); assert.ok((await m.text()).includes("edith-pair.js"));
  return "ok";
});
await step("first-run owner setup", async () => {
  const s = await call("/api/auth/session", { owner: false });
  if (s.j.configured) { const l = await call("/api/auth/login", { body: { passphrase: "test-passphrase-123" }, owner: false }); assert.equal(l.s, 200); cookie = l.h.get("set-cookie").split(";")[0]; return "login"; }
  const r = await call("/api/auth/setup", { body: { passphrase: "test-passphrase-123" }, owner: false });
  assert.equal(r.s, 200); cookie = r.h.get("set-cookie").split(";")[0]; return "setup";
});
await step("unauthenticated access rejected (capture, input, cmd, devices)", async () => {
  assert.equal((await call("/api/screen/capture", { owner: false })).s, 401);
  assert.equal((await call("/api/remote/input", { body: { action: "click", params: {} }, owner: false })).s, 401);
  assert.equal((await call("/cmd", { body: { command: "status" }, owner: false })).s, 401);
  assert.equal((await call("/api/devices", { owner: false })).s, 401);
  assert.equal((await call("/api/screen/capture", { token: "x".repeat(43), owner: false })).s, 401);
  return "401 x5";
});
await step("bad pairing code rejected", async () => { assert.equal((await call("/api/pair/claim", { body: { code: "000000" }, owner: false })).s, 401); });
await step("pair phone with one-time code; code cannot be reused", async () => {
  const c = await call("/api/pair/code", { body: { name: "Test phone" } }); assert.equal(c.s, 200);
  const p = await call("/api/pair/claim", { body: { code: c.j.code, name: "Test phone" }, owner: false }); assert.equal(p.s, 200); devToken = p.j.token;
  const again = await call("/api/pair/claim", { body: { code: c.j.code }, owner: false }); assert.equal(again.s, 401);
  return `scopes=${p.j.scopes}`;
});
await step("link host agent (real Python agent, synthetic test pattern)", async () => {
  const c = await call("/api/host/code", { body: {} });
  agent = spawn("python3", ["host-agent/edith_host_agent.py", "--gateway", BASE, "--code", c.j.code, "--synthetic", "--no-indicator"], { env: { ...process.env, PYTHONPATH: "/tmp/pylib", APPDATA: "/tmp/edith-agent-test" }, stdio: ["ignore", "pipe", "pipe"] });
  agent.stdout.on("data", (d) => process.env.VERBOSE && process.stdout.write("  [agent] " + d));
  for (let i = 0; i < 30; i++) { await sleep(500); const m = await call("/api/metrics"); if (m.j.host_online) return `host online, ram ${m.j.ram_percent}%`; }
  throw new Error("host never came online");
});
await step("phone command: natural-language reminder", async () => {
  const r = await call("/cmd", { body: { command: "Remind me to wash my clothes at 7:30 PM", request_id: "e2e-rem-1" }, token: devToken, owner: false });
  assert.equal(r.s, 200); assert.match(r.j.result, /Reminder set|Please confirm/); return r.j.result;
});
await step("idempotency: same request_id does not execute twice", async () => {
  const r = await call("/cmd", { body: { command: "Remind me to wash my clothes at 7:30 PM", request_id: "e2e-rem-1" }, token: devToken, owner: false });
  assert.equal(r.j.duplicate, true);
  const list = await call("/api/reminders"); assert.equal(list.j.reminders.filter((x) => x.title === "Wash my clothes").length, 1);
  return "1 reminder";
});
await step("tool round trip via host agent (open chrome -> job -> agent result)", async () => {
  const r = await call("/cmd", { body: { command: "open chrome", request_id: "e2e-open-1" } });
  assert.ok(["done", "error"].includes(r.j.status), JSON.stringify(r.j)); return r.j.result;
});
await step("medium-risk action requires approval (lock pc)", async () => {
  const r = await call("/cmd", { body: { command: "lock my pc", request_id: "e2e-lock-1" } });
  assert.equal(r.j.status, "awaiting_approval");
  const p = await call("/api/confirm/pending"); const job = p.j.pending.find((x) => x.tool === "lock_pc"); assert.ok(job);
  const d = await call("/api/confirm/resolve", { body: { id: job.id, approve: false } }); assert.equal(d.s, 200); return "denied ok";
});
await step("input rejected before viewing (no blind control)", async () => {
  const r = await call("/api/remote/input", { body: { action: "click", params: { x: 0.5, y: 0.5 } }, token: devToken, owner: false }); assert.equal(r.s, 409);
});
const frameLat = [];
await step("live relay frames to phone (measured)", async () => {
  let got = 0, seq = 0, bytes = 0; const t0 = Date.now();
  for (let i = 0; i < 60; i++) {
    const s = Date.now(); const r = await call(`/api/screen/capture?scale=1280&quality=60&after=${seq}`, { token: devToken, owner: false, raw: true });
    if (r.status === 200) { const b = Buffer.from(await r.arrayBuffer()); assert.equal(b[0], 0xff); seq = Number(r.headers.get("x-frame-seq")); got++; bytes += b.length; frameLat.push(Date.now() - s); }
    else await r.text();
  }
  const secs = (Date.now() - t0) / 1000;
  assert.ok(got > 10, `only ${got} frames`);
  return `${got} distinct frames in ${secs.toFixed(1)}s = ${(got / secs).toFixed(1)} fps, avg ${Math.round(bytes / got / 1024)} KB/frame, fetch p50 ${pct(frameLat, 50)}ms p95 ${pct(frameLat, 95)}ms`;
});
await step("input relay while viewing (queued + delivered to agent)", async () => {
  for (let i = 0; i < 25; i++) { const r = await call("/api/remote/input", { body: { action: "click", params: { x: 0.5, y: 0.5 }, event_id: `e2e-${i}` }, token: devToken, owner: false }); assert.equal(r.s, 200); await sleep(80); call(`/api/screen/capture`, { token: devToken, owner: false, raw: true }).then((r) => r.arrayBuffer()).catch(() => {}); }
  const dup = await call("/api/remote/input", { body: { action: "click", params: {}, event_id: "e2e-3" }, token: devToken, owner: false }); assert.equal(dup.j.duplicate, true);
  await sleep(1500);
  const st = await call("/api/remote/status");
  const s = st.j.streamer; return `server-side input relay p50 ${s.input_relay_ms_p50}ms p95 ${s.input_relay_ms_p95}ms (n=${s.samples.input}); measured stream ${s.measured_fps} fps ${s.width}x${s.height}`;
});
await step("reminder fires and is delivered to HUD + phone", async () => {
  const r = await call("/api/reminders", { body: { title: "E2E due now", due_at: new Date(Date.now() - 1000).toISOString() } }); assert.equal(r.s, 200);
  await sleep(4500);
  const h = await call("/api/notifications"); assert.ok(h.j.notifications.some((n) => n.title === "E2E due now"), "hud");
  const p = await call("/api/phone/messages?battery=80&conn=wifi", { token: devToken, owner: false }); assert.ok(p.j.messages.some((m) => m.text.includes("E2E due now")), "phone");
  return "hud+phone delivered";
});
await step("offline mode makes no cloud calls", async () => {
  await call("/api/mode", { body: { mode: "offline" } });
  const r = await call("/cmd", { body: { command: "explain photosynthesis in one line", request_id: "e2e-off-1" } });
  const d = await call("/api/diagnostics");
  assert.match(String(d.j.internet), /not probed/);
  await call("/api/mode", { body: { mode: "auto" } });
  return `${r.j.model}: ${String(r.j.result).slice(0, 90)}`;
});
await step("calendar shows DoPT holidays + yearly birthday", async () => {
  await call("/api/calendar", { body: { title: "Amma birthday", date: "2025-11-08", category: "birthday" } });
  const c = await call("/api/calendar?from=2026-11-01&to=2026-11-30");
  assert.ok(c.j.holidays.some((h) => h.name.startsWith("Diwali"))); assert.ok(c.j.events.some((e) => e.title === "Amma birthday" && e.occurs === "2026-11-08"));
  return `${c.j.holidays.length} holidays, ${c.j.events.length} events`;
});
await step("revoked phone is rejected and cannot reconnect", async () => {
  const d = await call("/api/devices"); const dev = d.j.devices.find((x) => x.name === "Test phone" && !x.revokedAt);
  await call(`/api/devices/${dev.id}/revoke`, { body: {} });
  assert.equal((await call("/api/screen/capture", { token: devToken, owner: false })).s, 401);
  assert.equal((await call("/cmd", { body: { command: "status" }, token: devToken, owner: false })).s, 401);
  return "401 after revoke";
});
agent?.kill();
console.log(JSON.stringify({ summary: results.map((r) => `${r[0]} ${r[1]}`) }, null, 1));
