/* EDITH Gateway integration for the original HUD (index.html).
 * Adds features INSIDE the existing design system (rail buttons + .dialog modals)
 * and replaces fake fallbacks with truthful state. No framework, no new theme. */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const log = (t, k) => { try { window.addLog && window.addLog(t, k); } catch (_) {} };
  const rid = () => (window.crypto && crypto.randomUUID ? crypto.randomUUID() : `r${Date.now()}${Math.random().toString(16).slice(2)}`);
  window.edithRequestId = rid;
  const TZ = () => (window.__edithProfile && window.__edithProfile.timezone) || "Asia/Kolkata";
  const fmt = (iso) => { try { return new Intl.DateTimeFormat("en-IN", { timeZone: TZ(), weekday: "short", day: "numeric", month: "short", hour: "numeric", minute: "2-digit", hour12: true }).format(new Date(iso)); } catch (_) { return iso; } };
  const ago = (iso) => { if (!iso) return "never"; const s = Math.round((Date.now() - new Date(iso).getTime()) / 1000); return s < 60 ? `${s}s ago` : s < 3600 ? `${Math.round(s / 60)}m ago` : s < 86400 ? `${Math.round(s / 3600)}h ago` : `${Math.round(s / 86400)}d ago`; };

  async function api(path, opts = {}) {
    const o = { method: opts.method || (opts.body ? "POST" : "GET"), headers: { "Content-Type": "application/json" }, credentials: "same-origin" };
    if (opts.body) o.body = JSON.stringify(opts.body);
    const r = await fetch(path, o);
    let data = {};
    try { data = await r.json(); } catch (_) {}
    if (r.status === 401 && data.auth_required && !opts.quiet) showAuth();
    return { ok: r.ok, status: r.status, data };
  }

  /* ------------------------------------------------------------ dialogs */
  function makeDialog(name, eyebrow, title, bodyHtml, wide = true) {
    if (document.getElementById(`modal-${name}`)) return;
    const el = document.createElement("div");
    el.className = "dialog-backdrop";
    el.id = `modal-${name}`;
    el.style.display = "none";
    el.setAttribute("role", "dialog");
    el.setAttribute("aria-modal", "true");
    el.setAttribute("aria-label", title);
    el.addEventListener("mousedown", (e) => { if (e.target === el && name !== "auth") window.closeDialog(name); });
    el.innerHTML = `<div class="dialog ${wide ? "dialog-wide" : ""}">
      <div class="dialog-head"><div><span class="eyebrow">${esc(eyebrow)}</span><h2>${esc(title)}</h2></div>
      ${name === "auth" ? "" : `<button class="icon-button" aria-label="Close" onclick="closeDialog('${name}')">✕</button>`}</div>
      <div class="dialog-body eg-body">${bodyHtml}</div></div>`;
    document.body.appendChild(el);
  }

  // Original openDialog/closeDialog are kept; we only hook data loading + stream teardown.
  const origOpen = window.openDialog;
  const origClose = window.closeDialog;
  window.openDialog = function (name) {
    origOpen(name);
    const loaders = { today: loadToday, calendar: loadCalendar, devices: loadDevices, tutorial: loadTutorial, activity: loadActivity, remote: loadRemoteStatus };
    if (loaders[name]) loaders[name]();
    const first = document.querySelector(`#modal-${name} input, #modal-${name} button`);
    if (first) setTimeout(() => first.focus(), 30);
  };
  window.closeDialog = function (name) {
    origClose(name);
    if (name === "remote") {
      // Fix: the MJPEG stream kept running after the dialog closed.
      const img = $("#remote-stream-img");
      if (img) img.removeAttribute("src");
    }
  };
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    const open = [...document.querySelectorAll(".dialog-backdrop")].find((d) => d.style.display === "flex" && d.id !== "modal-auth");
    if (open) window.closeDialog(open.id.replace("modal-", ""));
  });

  /* ------------------------------------------------------------ auth */
  function showAuth(configured) {
    makeDialog("auth", "SECURE ACCESS", "Sign in to EDITH", `<div id="eg-auth"></div>`, false);
    const box = $("#eg-auth");
    const setup = configured === false;
    box.innerHTML = `
      <p class="eg-p">${setup ? "First run: choose an owner passphrase. It protects the HUD, remote control and your data. Phones pair separately with one-time codes." : "Enter your owner passphrase."}</p>
      ${setup && window.__edithSetupKey ? `<div class="field"><label>SETUP KEY (from .env EDITH_SETUP_KEY)</label><input id="eg-setup-key" type="password" autocomplete="off"></div>` : ""}
      <div class="field"><label>OWNER PASSPHRASE</label><input id="eg-pass" type="password" autocomplete="${setup ? "new-password" : "current-password"}" minlength="8"></div>
      ${setup ? `<div class="field"><label>REPEAT PASSPHRASE</label><input id="eg-pass2" type="password" autocomplete="new-password"></div>` : ""}
      <div id="eg-auth-msg" class="connection-result" style="display:none;margin-top:10px"></div>
      <div class="settings-bottom"><button class="primary-button" id="eg-auth-go">${setup ? "Create passphrase" : "Sign in"}</button></div>`;
    const go = async () => {
      const pass = $("#eg-pass").value;
      const msg = $("#eg-auth-msg");
      if (setup && pass !== $("#eg-pass2").value) { msg.style.display = "flex"; msg.className = "connection-result error"; msg.textContent = "Passphrases do not match."; return; }
      const r = await api(setup ? "/api/auth/setup" : "/api/auth/login", { body: { passphrase: pass, setup_key: $("#eg-setup-key")?.value }, quiet: true });
      if (r.ok) { location.reload(); return; }
      msg.style.display = "flex"; msg.className = "connection-result error"; msg.textContent = r.data.error || "Failed";
    };
    $("#eg-auth-go").onclick = go;
    box.querySelectorAll("input").forEach((i) => i.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); }));
    $("#modal-auth").style.display = "flex";
    setTimeout(() => $("#eg-pass")?.focus(), 50);
  }

  /* ------------------------------------------------------------ truthful overrides */
  let lastState = null;
  window.fetchTelemetry = async function () {
    const r = await api("/api/metrics", { quiet: true });
    if (!r.ok) return;
    const d = r.data;
    lastState = d;
    const set = (id, txt, pct) => {
      const v = document.getElementById(`val-${id}`); const b = document.getElementById(`bar-${id}`);
      if (v) v.textContent = txt; if (b) b.style.width = `${pct == null ? 0 : Math.min(100, Math.max(0, Math.round(pct)))}%`;
    };
    const n = (x) => (x == null ? null : Math.round(x));
    set("cpu", d.cpu_percent == null ? "—" : `${n(d.cpu_percent)}%`, d.cpu_percent);
    set("ram", d.ram_percent == null ? "—" : `${n(d.ram_percent)}% (${d.ram_used_mb ?? "?"}MB)`, d.ram_percent);
    set("disk", d.disk_percent == null ? "—" : `${n(d.disk_percent)}%`, d.disk_percent);
    set("battery", d.battery_percent == null ? (d.host_online ? "AC / N/A" : "—") : `${n(d.battery_percent)}%${d.power_plugged ? " ⚡" : ""}`, d.battery_percent);
    const st = $("#lbl-system-state");
    const wrap = $("#hud-online-status");
    if (st) st.textContent = d.emergency_stopped ? "E-STOP ACTIVE" : d.host_online ? `PC LINKED · ${d.runtime_status}` : `PC HOST OFFLINE · ${d.runtime_status}`;
    if (wrap) wrap.classList.toggle("eg-warn", !d.host_online || d.emergency_stopped);
    const mb = $("#btn-mode-toggle");
    if (mb) mb.textContent = `MODE: ${(d.mode || "auto").toUpperCase()}`;
    const es = $("#btn-emergency");
    if (es) { es.textContent = d.emergency_stopped ? "▶ RESUME" : "🛑 E-STOP"; es.classList.toggle("eg-active", !!d.emergency_stopped); }
    const tun = $("#val-tunnel-status");
    if (tun) tun.textContent = d.host_online ? "HOST ONLINE" : "HOST OFFLINE";
  };
  window.fetchWeather = async function () {
    const r = await api("/weather", { quiet: true });
    const t = $("#w-temp"), ds = $("#w-desc");
    if (!t || !ds) return;
    if (r.ok && r.data.available && Number.isFinite(r.data.temp)) { t.textContent = `${r.data.temp}°C`; ds.textContent = String(r.data.desc).toUpperCase(); }
    else { t.textContent = "--°C"; ds.textContent = String((r.data && r.data.desc) || "NO DATA").toUpperCase(); t.title = "Set your city in Getting Started → Profile (needs internet; disabled in offline mode)."; }
  };
  window.loadMobileConfig = async function () {
    const r = await api("/mobile/config", { quiet: true });
    const url = (r.data && r.data.cloud_url) || location.origin;
    const el = $("#hud-cloud-url"); if (el) el.textContent = url;
    const setEl = $("#settings-cloud-url"); if (setEl) setEl.value = url;
  };
  window.copyCloudLink = function () {
    const url = ($("#hud-cloud-url")?.textContent || location.origin).trim();
    navigator.clipboard?.writeText(url).then(() => log(`Gateway link copied: ${url}`, "success"), () => log("Clipboard unavailable", "error"));
  };
  window.toggleEmergencyStop = async function () {
    const r = await api("/api/emergency_stop", { body: {} });
    if (r.ok) log(r.data.emergency_stopped ? "EMERGENCY STOP ENGAGED — PC actions & remote sessions blocked" : "Emergency stop released", r.data.emergency_stopped ? "error" : "success");
    else log(`E-STOP failed: ${r.data.error || r.status}`, "error");
    window.fetchTelemetry();
  };
  // Fix: MODE button called an undefined function.
  window.toggleSystemMode = async function () {
    const cur = ((lastState && lastState.mode) || "auto");
    const next = { auto: "online", online: "offline", offline: "auto" }[cur] || "auto";
    const r = await api("/api/mode", { body: { mode: next } });
    if (r.ok) log(`Mode → ${next.toUpperCase()}${next === "offline" ? " (no cloud/internet calls)" : ""}`, "success");
    window.fetchTelemetry();
  };
  const origLoadModels = window.loadActiveModels;
  window.loadActiveModels = async function () {
    const r = await api("/models", { quiet: true });
    const sel = $("#select-active-model");
    if (!sel || !r.ok) return origLoadModels && origLoadModels();
    sel.innerHTML = "";
    if (!r.data.ollama_up || !r.data.models.length) {
      const o = document.createElement("option");
      o.textContent = r.data.ollama_up ? "No Ollama models installed" : "Ollama offline"; o.disabled = true; o.selected = true;
      sel.appendChild(o); sel.title = r.data.error || "Install Ollama and run: ollama pull hermes3:3b";
      return;
    }
    r.data.models.forEach((m) => { const o = document.createElement("option"); o.value = m; o.textContent = m; if (m === r.data.active_model) o.selected = true; sel.appendChild(o); });
  };

  /* ------------------------------------------------------------ rail buttons */
  const ICONS = {
    today: '<path d="M12 8v4l3 2"/><circle cx="12" cy="12" r="9"/>',
    calendar: '<rect x="3" y="4" width="18" height="17" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    devices: '<rect x="2" y="4" width="14" height="10" rx="1"/><path d="M6 18h6M9 14v4"/><rect x="17" y="8" width="5" height="12" rx="1"/>',
    tutorial: '<circle cx="12" cy="12" r="9"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 2.5-3 4.5M12 17.5h.01"/>',
  };
  const LABELS = { today: "Today & Reminders", calendar: "Calendar & Festivals", devices: "Devices & Remote", tutorial: "Getting Started" };
  function addRail() {
    const anchor = $("#rail-btn-activity");
    if (!anchor || $("#rail-btn-today")) return;
    let after = anchor;
    for (const k of ["today", "calendar", "devices", "tutorial"]) {
      const b = document.createElement("button");
      b.className = "rail-button"; b.id = `rail-btn-${k}`; b.title = LABELS[k]; b.setAttribute("aria-label", LABELS[k]);
      b.onclick = () => window.openNav(k);
      b.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">${ICONS[k]}</svg><span class="rail-tooltip">${LABELS[k]}</span>${k === "today" ? '<span class="eg-badge" id="eg-today-badge" hidden></span>' : ""}`;
      after.after(b); after = b;
    }
  }

  /* ------------------------------------------------------------ TODAY / REMINDERS */
  const DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  function buildToday() {
    makeDialog("today", "REMINDERS · ROUTINES · ALARMS", "Today", `
      <div class="eg-row">
        <button class="secondary-button" onclick="edithG.arrived()">📍 I've arrived</button>
        <button class="secondary-button" id="eg-notif-btn" onclick="edithG.enableNotifs()">🔔 Enable desktop notifications</button>
        <button class="secondary-button" onclick="edithG.testNotif()">Test alert</button>
        <span class="eg-hint" id="eg-today-tz"></span>
      </div>
      <div id="eg-today-list" class="eg-list"><p class="eg-hint">Loading…</p></div>
      <h3 class="eg-h3">New reminder / routine</h3>
      <div class="eg-grid">
        <div class="field"><label>WHAT</label><input id="eg-r-title" placeholder="Wash clothes" maxlength="200"></div>
        <div class="field"><label>DATE & TIME</label><input id="eg-r-due" type="datetime-local"></div>
        <div class="field"><label>REPEAT</label><select id="eg-r-rec"><option value="none">Once</option><option value="daily">Daily</option><option value="weekdays">Weekdays</option><option value="weekly">Weekly (pick days)</option><option value="monthly">Monthly</option><option value="yearly">Yearly</option></select></div>
        <div class="field"><label>CATEGORY</label><select id="eg-r-cat"><option value="general">General</option><option value="routine">Routine</option><option value="chore">Chore</option><option value="study">Study / Work</option><option value="medicine">Medicine (reminder only)</option><option value="exercise">Exercise</option></select></div>
        <div class="field"><label>PRIORITY</label><select id="eg-r-pri"><option value="normal">Normal</option><option value="high">High (rings in quiet hours)</option><option value="low">Low</option></select></div>
        <div class="field"><label>TRIGGER</label><select id="eg-r-trig"><option value="time">At the time</option><option value="manual_arrival">When I tap “I've arrived”</option></select></div>
      </div>
      <div class="eg-row" id="eg-r-days">${DOW.map((d, i) => `<label class="eg-chip"><input type="checkbox" value="${i}"> ${d}</label>`).join("")}</div>
      <div class="field"><label>NOTES</label><input id="eg-r-notes" maxlength="300" placeholder="Optional"></div>
      <p class="eg-hint" id="eg-med-note" hidden>Medicine entries are reminders only — EDITH does not give dosage or medical advice. Please confirm your schedule with your doctor or pharmacist.</p>
      <div id="eg-r-msg" class="connection-result" style="display:none"></div>
      <div class="settings-bottom"><button class="secondary-button" onclick="edithG.exportReminders()">Export JSON</button><button class="primary-button" onclick="edithG.saveReminder()">Save reminder</button></div>
      <p class="eg-hint">Tip: you can also type “remind me to wash clothes at 7:30 pm” or “remind me to call mom every Sunday at 10 am” in the command bar.</p>`);
    $("#eg-r-cat").onchange = (e) => ($("#eg-med-note").hidden = e.target.value !== "medicine");
  }
  async function loadToday() {
    const r = await api("/api/reminders");
    const box = $("#eg-today-list");
    if (!r.ok) { box.innerHTML = `<p class="eg-hint">${esc(r.data.error || "Unable to load")}</p>`; return; }
    $("#eg-today-tz").textContent = `Timezone: ${r.data.timezone}`;
    const list = r.data.reminders;
    if (!list.length) { box.innerHTML = '<p class="eg-hint">No reminders yet. Create one below or type “remind me to … at …”.</p>'; return; }
    const now = Date.now();
    box.innerHTML = list.map((x) => {
      const fired = x.status === "fired"; const overdue = x.trigger === "time" && new Date(x.dueAt).getTime() < now;
      const when = x.trigger === "manual_arrival" ? "on arrival" : fmt(x.dueAt);
      const rec = x.recurrence === "none" ? "" : x.recurrence === "weekly" && x.byWeekday ? ` · ${x.byWeekday.map((d) => DOW[d]).join("/")}` : ` · ${x.recurrence}`;
      return `<div class="eg-item ${fired || overdue ? "eg-due" : ""}">
        <span class="status-dot ${fired ? "red" : x.priority === "high" ? "" : "green"}"></span>
        <div class="eg-item-main"><strong>${esc(x.title)}</strong><small>${esc(when)}${esc(rec)} · ${esc(x.category)}${fired ? " · RANG" : ""}${x.notes ? ` · ${esc(x.notes)}` : ""}</small></div>
        <div class="eg-item-actions">
          <button class="secondary-button" onclick="edithG.rem('${x.id}','complete')" title="Mark done">✓ Done</button>
          <button class="secondary-button" onclick="edithG.rem('${x.id}','snooze',10)">+10m</button>
          <button class="secondary-button" onclick="edithG.rem('${x.id}','snooze',60)">+1h</button>
          <button class="icon-button" aria-label="Delete" onclick="edithG.delRem('${x.id}')">🗑</button>
        </div></div>`;
    }).join("");
    const badge = $("#eg-today-badge");
    const n = list.filter((x) => x.status === "fired").length;
    if (badge) { badge.hidden = !n; badge.textContent = n; }
    const dt = $("#eg-r-due");
    if (dt && !dt.value) { const d = new Date(Date.now() + 3600_000); d.setMinutes(0, 0, 0); dt.value = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16); }
  }

  /* ------------------------------------------------------------ CALENDAR */
  let calCursor = new Date(); calCursor.setDate(1);
  function buildCalendar() {
    makeDialog("calendar", "INDIA CALENDAR · HOLIDAYS · BIRTHDAYS", "Calendar", `
      <div class="eg-row"><button class="secondary-button" onclick="edithG.calMove(-1)">◀</button><strong id="eg-cal-title" class="eg-cal-title"></strong><button class="secondary-button" onclick="edithG.calMove(1)">▶</button>
        <label class="eg-chip"><input type="checkbox" id="eg-f-hol" checked> Holidays</label><label class="eg-chip"><input type="checkbox" id="eg-f-ev" checked> My events</label>
        <a class="secondary-button eg-link" href="/api/calendar/ics">Export .ics</a><label class="secondary-button eg-link">Import .ics<input type="file" accept=".ics,text/calendar" id="eg-ics" hidden></label></div>
      <div id="eg-cal-grid" class="eg-cal"></div>
      <div id="eg-cal-agenda" class="eg-list"></div>
      <p class="eg-hint" id="eg-cal-src"></p>
      <h3 class="eg-h3">Add event / birthday / holiday</h3>
      <div class="eg-grid">
        <div class="field"><label>TITLE</label><input id="eg-e-title" maxlength="200" placeholder="Amma's birthday"></div>
        <div class="field"><label>DATE</label><input id="eg-e-date" type="date"></div>
        <div class="field"><label>TIME (optional)</label><input id="eg-e-time" type="time"></div>
        <div class="field"><label>TYPE</label><select id="eg-e-cat"><option value="event">Event</option><option value="birthday">Birthday (yearly)</option><option value="anniversary">Anniversary (yearly)</option><option value="exam">Exam / deadline</option><option value="holiday">Holiday (state/college/work)</option><option value="festival">Festival</option></select></div>
      </div>
      <div class="field"><label class="eg-chip"><input type="checkbox" id="eg-e-rem"> Also remind me at 9:00 AM that day</label></div>
      <div id="eg-e-msg" class="connection-result" style="display:none"></div>
      <div class="settings-bottom"><button class="primary-button" onclick="edithG.saveEvent()">Add to calendar</button></div>`);
    ["eg-f-hol", "eg-f-ev"].forEach((id) => ($("#" + id).onchange = loadCalendar));
    $("#eg-ics").onchange = async (e) => {
      const f = e.target.files[0]; if (!f) return;
      const r = await api("/api/calendar/import", { body: { ics: await f.text() } });
      log(r.ok ? `Imported ${r.data.imported} of ${r.data.found} events (duplicates skipped)` : `Import failed: ${r.data.error}`, r.ok ? "success" : "error");
      loadCalendar();
    };
  }
  async function loadCalendar() {
    const y = calCursor.getFullYear(), m = calCursor.getMonth();
    const pad = (n) => String(n).padStart(2, "0");
    const from = `${y}-${pad(m + 1)}-01`;
    const last = new Date(y, m + 1, 0).getDate();
    const to = `${y}-${pad(m + 1)}-${pad(last)}`;
    $("#eg-cal-title").textContent = calCursor.toLocaleDateString("en-IN", { month: "long", year: "numeric" });
    const r = await api(`/api/calendar?from=${from}&to=${to}`);
    if (!r.ok) return;
    const showH = $("#eg-f-hol").checked, showE = $("#eg-f-ev").checked;
    const byDay = {};
    if (showH) r.data.holidays.forEach((h) => (byDay[h.date] = byDay[h.date] || []).push({ t: h.name + (h.tentative ? " (tentative)" : ""), c: "hol", h }));
    if (showE) r.data.events.forEach((e) => (byDay[e.occurs] = byDay[e.occurs] || []).push({ t: e.title, c: e.category, e }));
    const startDow = new Date(y, m, 1).getDay();
    const todayStr = new Date().toISOString().slice(0, 10);
    let html = DOW.map((d) => `<div class="eg-cal-h">${d}</div>`).join("");
    for (let i = 0; i < startDow; i++) html += '<div class="eg-cal-c eg-empty"></div>';
    for (let d = 1; d <= last; d++) {
      const key = `${y}-${pad(m + 1)}-${pad(d)}`;
      const items = byDay[key] || [];
      html += `<div class="eg-cal-c ${key === todayStr ? "eg-today" : ""}"><span>${d}</span>${items.slice(0, 3).map((i) => `<em class="eg-tag eg-${esc(i.c)}" title="${esc(i.t)}">${esc(i.t)}</em>`).join("")}${items.length > 3 ? `<em class="eg-tag">+${items.length - 3}</em>` : ""}</div>`;
    }
    $("#eg-cal-grid").innerHTML = html;
    const agenda = Object.keys(byDay).sort().flatMap((k) => byDay[k].map((i) => ({ k, ...i })));
    $("#eg-cal-agenda").innerHTML = agenda.length ? agenda.map((a) => `<div class="eg-item"><span class="status-dot ${a.c === "hol" ? "" : "green"}"></span><div class="eg-item-main"><strong>${esc(a.t)}</strong><small>${esc(a.k)}${a.e && a.e.time ? " " + esc(a.e.time) : ""} · ${a.c === "hol" ? esc(a.h.category) : esc(a.c)}${a.e && a.e.recurrence === "yearly" ? " · yearly" : ""}</small></div>${a.e ? `<div class="eg-item-actions"><button class="icon-button" aria-label="Delete" onclick="edithG.delEvent('${a.e.id}')">🗑</button></div>` : ""}</div>`).join("") : '<p class="eg-hint">Nothing this month.</p>';
    const missing = (r.data.gazetted_data_years || []).filter((x) => !x.available).map((x) => x.year);
    $("#eg-cal-src").textContent = `Holidays: ${r.data.holiday_source}. Lunar/moon-sighting dates may shift; state holidays vary — add your own as “Holiday”.${missing.length ? ` Gazetted list not bundled for ${missing.join(", ")} (only fixed national holidays shown).` : ""}`;
  }

  /* ------------------------------------------------------------ DEVICES & REMOTE */
  function buildDevices() {
    makeDialog("devices", "PHONE PAIRING · PC HOST · REMOTE ACCESS", "Devices & Remote", `
      <div class="eg-grid2">
        <section class="eg-card"><h3 class="eg-h3">1 · This PC (host agent)</h3><div id="eg-host"></div>
          <button class="secondary-button" onclick="edithG.hostCode()">Link this PC (10-min code)</button><div id="eg-host-code" class="eg-code" hidden></div>
          <p class="eg-hint">On Windows run: <code>python host-agent\\edith_host_agent.py --gateway ${esc(location.origin)} --code &lt;CODE&gt;</code></p></section>
        <section class="eg-card"><h3 class="eg-h3">2 · Pair a phone</h3>
          <div class="field"><label>DEVICE NAME</label><input id="eg-p-name" value="My phone" maxlength="60"></div>
          <div class="eg-row">${["chat", "screen", "control", "reminders"].map((s) => `<label class="eg-chip"><input type="checkbox" class="eg-scope" value="${s}" checked> ${s}</label>`).join("")}</div>
          <button class="primary-button" onclick="edithG.pairCode()">Generate 5-min pairing code</button><div id="eg-pair-code" class="eg-code" hidden></div>
          <p class="eg-hint">In the EDITH phone app: Settings → enter this gateway URL as the Cloud/Local URL and the 6-digit code in the token field → Save.</p></section>
      </div>
      <section class="eg-card"><h3 class="eg-h3">Live remote session</h3><div id="eg-remote-stats" class="eg-mono">—</div>
        <div class="eg-row"><button class="secondary-button" onclick="openDialog('remote')">Open live view here</button><button class="secondary-button" onclick="edithG.pause()">Pause / resume stream</button><button class="primary-button eg-danger" onclick="edithG.kill()">Disconnect all sessions</button></div></section>
      <section class="eg-card"><h3 class="eg-h3">Paired devices</h3><div id="eg-dev-list" class="eg-list"></div></section>
      <section class="eg-card"><h3 class="eg-h3">Action permissions</h3><p class="eg-hint">Low-risk actions can run automatically; medium ask first; high-risk always need explicit “confirm”.</p><div id="eg-perms" class="eg-list"></div></section>
      <section class="eg-card"><h3 class="eg-h3">Away from home</h3><p class="eg-hint">The gateway never opens public ports or tunnels by itself. Recommended: install Tailscale (or WireGuard) on the PC and phone, then use the PC's private VPN address. Alternative: an HTTPS reverse proxy you control. Details: docs/REMOTE_ACCESS_SETUP.md.</p>
        <div class="field"><label>PUBLIC / VPN URL SHOWN TO PHONES (optional)</label><input id="eg-pub-url" placeholder="https://my-pc.tailnet-name.ts.net"></div><button class="secondary-button" onclick="edithG.savePub()">Save URL</button></section>`);
  }
  async function loadDevices() {
    const [d, perms, rs] = await Promise.all([api("/api/devices"), api("/api/permissions"), api("/api/remote/status")]);
    if (d.ok) {
      const h = d.data.hosts.filter((x) => !x.revokedAt);
      $("#eg-host").innerHTML = h.length ? h.map((x) => `<div class="eg-item"><span class="status-dot ${x.online ? "green" : "red"}"></span><div class="eg-item-main"><strong>${esc(x.name)}</strong><small>${x.online ? "ONLINE" : "OFFLINE"} · seen ${ago(x.lastSeenAt)} · agent ${esc(x.agentVersion || "?")} · ${esc(x.platform || "")}${x.capabilities ? ` · capture: ${esc(x.capabilities.capture || "?")}` : ""}</small></div><div class="eg-item-actions"><button class="icon-button" title="Revoke host" onclick="edithG.revoke('hosts','${x.id}')">⛔</button></div></div>`).join("") : '<p class="eg-hint">No PC linked yet.</p>';
      $("#eg-dev-list").innerHTML = d.data.devices.length ? d.data.devices.map((x) => `<div class="eg-item"><span class="status-dot ${x.revokedAt ? "dim" : x.lastSeenAt && Date.now() - new Date(x.lastSeenAt) < 60000 ? "green" : ""}"></span><div class="eg-item-main"><strong>${esc(x.name)}</strong><small>${x.revokedAt ? "REVOKED" : `seen ${ago(x.lastSeenAt)}`} · ${esc(x.scopes.join(", "))}${x.battery != null ? ` · 🔋${x.battery}%` : ""}${x.connType ? ` · ${esc(x.connType)}` : ""}</small></div>${x.revokedAt ? "" : `<div class="eg-item-actions"><button class="secondary-button eg-danger" onclick="edithG.revoke('devices','${x.id}')">Revoke</button></div>`}</div>`).join("") : '<p class="eg-hint">No phones paired.</p>';
    }
    if (perms.ok) $("#eg-perms").innerHTML = perms.data.tools.map((t) => `<div class="eg-item"><span class="eg-risk eg-risk-${t.risk}">${t.risk}</span><div class="eg-item-main"><strong>${esc(t.name)}</strong><small>${esc(t.supported ? t.description : t.reason)}</small></div>${t.supported ? `<select onchange="edithG.perm('${t.name}', this.value)" aria-label="Permission for ${esc(t.name)}">${["auto", "ask", "deny"].filter((p) => !(t.risk === "high" && p === "auto")).map((p) => `<option ${p === t.permission ? "selected" : ""}>${p}</option>`).join("")}</select>` : "<small>unsupported</small>"}</div>`).join("");
    if (rs.ok) renderRemoteStats(rs.data);
    const pub = await api("/mobile/config", { quiet: true });
    if (pub.data.cloud_url) $("#eg-pub-url").value = pub.data.cloud_url;
  }
  function renderRemoteStats(s) {
    const st = s.streamer || {};
    const txt = s.host_online
      ? `Host online · viewers ${st.viewers ? st.viewers.length : 0}${st.paused ? " · PAUSED" : ""} · ${st.width ? `${st.width}×${st.height}` : "no frame yet"} · ${st.measured_fps} fps measured · ${st.last_frame_bytes ? Math.round(st.last_frame_bytes / 1024) + " KB/frame" : ""}${st.est_kbps ? ` · ~${st.est_kbps} kbps` : ""} · input relay p50/p95 ${st.input_relay_ms_p50 ?? "—"}/${st.input_relay_ms_p95 ?? "—"} ms · frame age p50/p95 ${st.frame_age_ms_p50 ?? "—"}/${st.frame_age_ms_p95 ?? "—"} ms`
      : "PC host agent offline — no live stream possible until it connects.";
    const el = $("#eg-remote-stats"); if (el) el.textContent = txt;
    const lbl = $("#lbl-remote-fps"); if (lbl) lbl.textContent = s.host_online ? (st.has_frame ? `LIVE · ${st.measured_fps} FPS · ${st.width}×${st.height}` : "CONNECTING…") : "HOST OFFLINE";
    const sessions = (st.sessions || []).slice(0, 6).map((x) => `${new Date(x.startedAt).toLocaleTimeString()} ${x.origin} ${x.endedAt ? "ended" : "active"} (${x.inputs} inputs)`).join(" | ");
    if (el && sessions) el.textContent += `\nSessions: ${sessions}`;
  }
  async function loadRemoteStatus() { const r = await api("/api/remote/status", { quiet: true }); if (r.ok) renderRemoteStats(r.data); }

  /* ------------------------------------------------------------ ACTIVITY: approvals + history */
  async function loadActivity() {
    const body = $("#modal-activity .dialog-body");
    if (!body) return;
    let box = $("#eg-activity");
    if (!box) { box = document.createElement("div"); box.id = "eg-activity"; body.prepend(box); }
    const [p, l] = await Promise.all([api("/api/confirm/pending"), api("/api/logs")]);
    const pend = p.ok ? p.data.pending : [];
    box.innerHTML = `<h3 class="eg-h3">Waiting for your approval</h3>${pend.length ? pend.map((j) => `<div class="eg-item eg-due"><span class="eg-risk eg-risk-${j.risk}">${j.risk}</span><div class="eg-item-main"><strong>${esc(j.summary)}</strong><small>${esc(j.origin)} · ${ago(j.createdAt)}</small></div><div class="eg-item-actions"><button class="primary-button" onclick="edithG.approve('${j.id}',true)">Approve</button><button class="secondary-button" onclick="edithG.approve('${j.id}',false)">Deny</button></div></div>`).join("") : '<p class="eg-hint">Nothing pending.</p>'}
      <h3 class="eg-h3">Task history</h3><div class="eg-list eg-scroll">${l.ok ? l.data.tasks.map((t) => `<div class="eg-item"><span class="status-dot ${t.status === "done" ? "green" : t.status === "error" || t.status === "denied" ? "red" : ""}"></span><div class="eg-item-main"><strong>${esc(t.command)}</strong><small>${ago(t.createdAt)} · ${esc(t.origin)} · ${esc(t.engine || "")} · ${esc(t.status)} — ${esc((t.result || "").slice(0, 140))}</small></div></div>`).join("") : ""}</div>
      <h3 class="eg-h3">Audit log</h3><pre class="eg-pre">${l.ok ? esc(l.data.logs) : ""}</pre>
      <div class="eg-row"><button class="secondary-button" onclick="edithG.copyDiag()">Copy diagnostics (redacted)</button><a class="secondary-button eg-link" href="/api/export">Export my data</a></div>`;
  }

  /* ------------------------------------------------------------ TUTORIAL / FIRST RUN */
  const LESSONS = [
    ["welcome", "Welcome", "EDITH runs commands, reminders, a calendar and secure phone-to-PC remote control. It cannot act when your PC is off, asleep or offline, and it never runs high-risk actions without your explicit “confirm”.", null],
    ["privacy", "Privacy", "Data stays in your local PostgreSQL database. Screen frames and keystrokes are relayed in memory only and never stored. The mic and camera are only used when you press their buttons.", null],
    ["mode", "Choose a mode", "AUTO uses your online provider when reachable, otherwise local Ollama. OFFLINE makes no cloud or internet calls. Click the MODE button in the top bar to cycle modes.", "status"],
    ["ollama", "Local AI (Ollama)", "Install Ollama from ollama.com, then run “ollama pull hermes3:3b” (≈2 GB, your choice). Select the model in the Command Center. If you have 4 GB RAM, pick the 4 GB profile below.", null],
    ["host", "Link this PC", "Open Devices & Remote → “Link this PC”, then run the host agent on Windows with the code. Live screen, input and PC actions need the agent.", "open_devices"],
    ["phone", "Pair your phone", "Devices & Remote → Generate pairing code. In the phone app, enter the gateway URL and the 6-digit code. You can revoke the phone at any time.", "open_devices"],
    ["away", "Away from home", "Install Tailscale on both devices and use the PC's Tailscale address in the phone app. Never forward raw ports to the internet.", null],
    ["reminder", "Try a reminder", "Click “Try it” to create a test reminder for 2 minutes from now. It will ring in the HUD, on your phone and as a Windows notification.", "timer 2 minutes"],
    ["calendar", "Calendar & festivals", "Set your state and city below, then add birthdays and exams in Calendar. Lunar festival dates are marked tentative.", "open_calendar"],
    ["voice", "Voice & text", "Use the mic button for push-to-talk (browser speech recognition) or just type. Speech output uses your browser voice.", null],
    ["gestures", "Hand gestures", "The original HUD gesture tracking (camera) is optional and local. Turn it off when you don't need it — the camera light shows when it's active.", null],
    ["safety", "Safety controls", "E-STOP blocks all PC actions and ends remote sessions instantly. Approvals for medium/high-risk actions appear in System Activity.", null],
  ];
  function buildTutorial() {
    makeDialog("tutorial", "FIRST-RUN SETUP · LESSONS", "Getting Started", `
      <div id="eg-lessons" class="eg-list"></div>
      <h3 class="eg-h3">Profile (region, calendar, resources)</h3>
      <div class="eg-grid">
        <div class="field"><label>YOUR NAME</label><input id="eg-pf-name" maxlength="60"></div>
        <div class="field"><label>STATE / UT</label><input id="eg-pf-state" maxlength="60" placeholder="Telangana"></div>
        <div class="field"><label>CITY (weather)</label><input id="eg-pf-city" maxlength="60" placeholder="Hyderabad"></div>
        <div class="field"><label>TIMEZONE</label><input id="eg-pf-tz" maxlength="60" placeholder="Asia/Kolkata"></div>
        <div class="field"><label>RESOURCE PROFILE</label><select id="eg-pf-res"><option value="8gb">8 GB RAM (Latitude 5490)</option><option value="4gb">4 GB RAM (low memory)</option></select></div>
        <div class="field"><label>QUIET HOURS</label><div class="eg-row"><input id="eg-pf-qs" type="time"> – <input id="eg-pf-qe" type="time"></div></div>
      </div>
      <div class="eg-row"><label class="eg-chip"><input type="checkbox" id="eg-pf-nat"> National holidays</label><label class="eg-chip"><input type="checkbox" id="eg-pf-gaz"> Central gazetted holidays</label></div>
      <div id="eg-pf-msg" class="connection-result" style="display:none"></div>
      <div class="settings-bottom"><button class="secondary-button" onclick="edithG.resetTutorial()">Replay tutorial</button><button class="primary-button" onclick="edithG.saveProfile()">Save profile</button></div>`);
  }
  let tutorialState = {};
  async function loadTutorial() {
    const r = await api("/api/profile");
    if (!r.ok) return;
    const p = r.data.profile; tutorialState = r.data.tutorial || {};
    window.__edithProfile = p;
    $("#eg-pf-name").value = p.name || ""; $("#eg-pf-state").value = p.state || ""; $("#eg-pf-city").value = p.city || ""; $("#eg-pf-tz").value = p.timezone;
    $("#eg-pf-res").value = p.resourceProfile; $("#eg-pf-qs").value = p.quietStart || ""; $("#eg-pf-qe").value = p.quietEnd || "";
    $("#eg-pf-nat").checked = p.holidayCategories.includes("national"); $("#eg-pf-gaz").checked = p.holidayCategories.includes("gazetted");
    renderLessons();
  }
  function renderLessons() {
    const done = LESSONS.filter((l) => tutorialState[l[0]]).length;
    $("#eg-lessons").innerHTML = `<p class="eg-hint">${done}/${LESSONS.length} lessons completed — nothing here blocks normal use.</p>` + LESSONS.map((l, i) => `<div class="eg-item"><span class="status-dot ${tutorialState[l[0]] ? "green" : "dim"}"></span><div class="eg-item-main"><strong>${i + 1}. ${esc(l[1])}</strong><small>${esc(l[2])}</small></div><div class="eg-item-actions">${l[3] ? `<button class="secondary-button" onclick="edithG.tryLesson('${l[0]}')">Try it</button>` : ""}<button class="secondary-button" onclick="edithG.markLesson('${l[0]}')">${tutorialState[l[0]] ? "✓" : "Mark done"}</button></div></div>`).join("");
  }

  /* ------------------------------------------------------------ remote indicator + notifications */
  function buildIndicator() {
    const b = document.createElement("div");
    b.id = "eg-remote-banner"; b.hidden = true; b.setAttribute("role", "status");
    b.innerHTML = `<span class="status-dot red"></span><span id="eg-remote-who">REMOTE SESSION ACTIVE</span><button class="secondary-button" onclick="edithG.kill()">Disconnect</button>`;
    document.body.appendChild(b);
    const t = document.createElement("div"); t.id = "eg-toasts"; t.setAttribute("aria-live", "polite"); document.body.appendChild(t);
  }
  function toast(title, body) {
    const t = document.createElement("div"); t.className = "eg-toast";
    t.innerHTML = `<strong>${esc(title)}</strong>${body ? `<small>${esc(body)}</small>` : ""}<button class="icon-button" aria-label="Dismiss">✕</button>`;
    t.querySelector("button").onclick = () => t.remove();
    $("#eg-toasts").appendChild(t); setTimeout(() => t.remove(), 60000);
  }
  function beep() {
    try { const a = new (window.AudioContext || window.webkitAudioContext)(); [0, 0.35, 0.7].forEach((d) => { const o = a.createOscillator(), g = a.createGain(); o.frequency.value = 880; g.gain.value = 0.08; o.connect(g); g.connect(a.destination); o.start(a.currentTime + d); o.stop(a.currentTime + d + 0.2); }); } catch (_) {}
  }
  async function pollNotifications() {
    const r = await api("/api/notifications", { quiet: true });
    if (!r.ok) return;
    for (const n of r.data.notifications) {
      toast(`⏰ ${n.title}`, n.body); beep(); log(`Reminder: ${n.title}`, "success");
      if ("Notification" in window && Notification.permission === "granted") { try { new Notification(`⏰ ${n.title}`, { body: n.body || "", tag: `edith-${n.id}` }); } catch (_) {} }
    }
    if (r.data.notifications.length && $("#modal-today")?.style.display === "flex") loadToday();
  }
  async function pollRemote() {
    const r = await api("/api/remote/status", { quiet: true });
    if (!r.ok) return;
    const v = (r.data.streamer && r.data.streamer.viewers) || [];
    const remoteViewers = v.filter((x) => x.origin !== "owner");
    const b = $("#eg-remote-banner");
    b.hidden = !remoteViewers.length;
    if (remoteViewers.length) $("#eg-remote-who").textContent = `REMOTE SESSION ACTIVE · ${remoteViewers.map((x) => x.origin).join(", ")}`;
    if ($("#modal-devices")?.style.display === "flex" || $("#modal-remote")?.style.display === "flex") renderRemoteStats(r.data);
  }

  /* ------------------------------------------------------------ actions */
  const msg = (id, ok, text) => { const m = $("#" + id); if (!m) return; m.style.display = "flex"; m.className = `connection-result ${ok ? "success" : "error"}`; m.textContent = text; };
  window.edithG = {
    async saveReminder() {
      const title = $("#eg-r-title").value.trim(); const due = $("#eg-r-due").value; const rec = $("#eg-r-rec").value; const trig = $("#eg-r-trig").value;
      if (!title) return msg("eg-r-msg", false, "Enter what to remind you about.");
      if (trig === "time" && !due) return msg("eg-r-msg", false, "Pick a date and time.");
      const days = [...document.querySelectorAll("#eg-r-days input:checked")].map((i) => Number(i.value));
      if (rec === "weekly" && !days.length) return msg("eg-r-msg", false, "Pick at least one weekday for a weekly repeat.");
      const r = await api("/api/reminders", { body: { title, due_at: due ? new Date(due).toISOString() : null, recurrence: rec, by_weekday: days, category: $("#eg-r-cat").value, priority: $("#eg-r-pri").value, trigger: trig, notes: $("#eg-r-notes").value } });
      msg("eg-r-msg", r.ok, r.ok ? `Saved: ${title} — ${trig === "time" ? fmt(r.data.reminder.dueAt) : "on arrival"}` : r.data.error);
      if (r.ok) { $("#eg-r-title").value = ""; $("#eg-r-notes").value = ""; loadToday(); }
    },
    async rem(id, action, minutes) { const r = await api(`/api/reminders/${id}/${action}`, { body: { minutes } }); if (!r.ok) log(r.data.error, "error"); loadToday(); },
    async delRem(id) { if (!confirm("Delete this reminder?")) return; await api(`/api/reminders/${id}`, { method: "DELETE" }); loadToday(); },
    async arrived() { const r = await api("/api/reminders/arrived", { body: {} }); log(`Arrival: ${r.data.fired || 0} reminder(s) triggered`, "success"); setTimeout(pollNotifications, 500); loadToday(); },
    async enableNotifs() { if (!("Notification" in window)) return log("This browser has no notification support", "error"); const p = await Notification.requestPermission(); $("#eg-notif-btn").textContent = p === "granted" ? "🔔 Notifications on" : "🔕 Notifications blocked"; },
    async testNotif() { const r = await api("/cmd", { body: { command: "timer 1 minute", request_id: rid() } }); log(r.data.result || "Test timer created", "success"); loadToday(); },
    async exportReminders() { const r = await api("/api/reminders/export"); const blob = new Blob([JSON.stringify(r.data, null, 2)], { type: "application/json" }); const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "edith-reminders.json"; a.click(); },
    calMove(d) { calCursor.setMonth(calCursor.getMonth() + d); loadCalendar(); },
    async saveEvent() {
      const title = $("#eg-e-title").value.trim(), date = $("#eg-e-date").value, time = $("#eg-e-time").value, category = $("#eg-e-cat").value;
      if (!title || !date) return msg("eg-e-msg", false, "Title and date are required.");
      const r = await api("/api/calendar", { body: { title, date, time, category } });
      if (r.ok && $("#eg-e-rem").checked) {
        const [y, m, d] = date.split("-").map(Number);
        await api("/api/reminders", { body: { title: `📅 ${title}`, due_at: new Date(y, m - 1, d, 9, 0).toISOString(), recurrence: ["birthday", "anniversary"].includes(category) ? "yearly" : "none", category: "general" } });
      }
      msg("eg-e-msg", r.ok, r.ok ? `Added “${title}”` : r.data.error);
      if (r.ok) { $("#eg-e-title").value = ""; loadCalendar(); }
    },
    async delEvent(id) { if (!confirm("Delete this event?")) return; await api(`/api/calendar/${id}`, { method: "DELETE" }); loadCalendar(); },
    async pairCode() {
      const scopes = [...document.querySelectorAll(".eg-scope:checked")].map((i) => i.value);
      const r = await api("/api/pair/code", { body: { name: $("#eg-p-name").value, scopes } });
      const el = $("#eg-pair-code"); el.hidden = false;
      el.innerHTML = r.ok ? `<b>${r.data.code.slice(0, 3)} ${r.data.code.slice(3)}</b><small>Gateway: ${esc(($("#eg-pub-url").value || location.origin))} · expires ${new Date(r.data.expires_at).toLocaleTimeString()} · single use</small>` : esc(r.data.error);
    },
    async hostCode() {
      const r = await api("/api/host/code", { body: { name: "Windows PC" } });
      const el = $("#eg-host-code"); el.hidden = false;
      el.innerHTML = r.ok ? `<b>${r.data.code.slice(0, 3)} ${r.data.code.slice(3)}</b><small>expires ${new Date(r.data.expires_at).toLocaleTimeString()} · single use</small>` : esc(r.data.error);
    },
    async revoke(kind, id) { if (!confirm("Revoke access? The device will be disconnected and cannot reconnect without re-pairing.")) return; await api(`/api/${kind}/${id}/revoke`, { body: {} }); log(`Revoked ${kind.slice(0, -1)}`, "success"); loadDevices(); },
    async kill() { await api("/api/remote/disconnect", { body: {} }); log("All remote sessions disconnected", "success"); pollRemote(); },
    async pause() { const s = await api("/api/remote/status"); const paused = !(s.data.streamer && s.data.streamer.paused); await api("/api/remote/pause", { body: { paused } }); log(paused ? "Remote stream paused" : "Remote stream resumed", "success"); loadDevices(); },
    async perm(tool, permission) { const r = await api("/api/permissions", { body: { tool, permission } }); log(r.ok ? `${tool}: ${r.data.permission}` : r.data.error, r.ok ? "success" : "error"); },
    async savePub() { const r = await api("/api/public_url", { body: { url: $("#eg-pub-url").value } }); log(r.ok ? "Public/VPN URL saved" : r.data.error, r.ok ? "success" : "error"); window.loadMobileConfig(); },
    async approve(id, approve) { const r = await api("/api/confirm/resolve", { body: { id, approve } }); log(r.ok ? (approve ? "Approved" : "Denied") : r.data.error, r.ok ? "success" : "error"); setTimeout(loadActivity, 600); },
    async copyDiag() { const r = await api("/api/diagnostics"); const txt = JSON.stringify(r.data, null, 2); try { await navigator.clipboard.writeText(txt); log("Diagnostics copied (redacted)", "success"); } catch (_) { const w = window.open(); if (w) w.document.body.innerText = txt; } },
    async saveProfile() {
      const cats = []; if ($("#eg-pf-nat").checked) cats.push("national"); if ($("#eg-pf-gaz").checked) cats.push("gazetted");
      const r = await api("/api/profile", { body: { name: $("#eg-pf-name").value, state: $("#eg-pf-state").value, city: $("#eg-pf-city").value, timezone: $("#eg-pf-tz").value || "Asia/Kolkata", resourceProfile: $("#eg-pf-res").value, quietStart: $("#eg-pf-qs").value, quietEnd: $("#eg-pf-qe").value, holidayCategories: cats } });
      msg("eg-pf-msg", r.ok, r.ok ? "Profile saved." : r.data.error);
      if (r.ok) { window.__edithProfile = r.data.profile; window.fetchWeather(); }
    },
    async markLesson(k) { tutorialState[k] = !tutorialState[k]; await api("/api/profile", { body: { tutorial: tutorialState } }); renderLessons(); },
    async resetTutorial() { tutorialState = {}; await api("/api/profile", { body: { tutorial: {} } }); renderLessons(); },
    async tryLesson(k) {
      const l = LESSONS.find((x) => x[0] === k); if (!l) return;
      if (l[3] === "open_devices") { window.closeDialog("tutorial"); window.openNav("devices"); }
      else if (l[3] === "open_calendar") { window.closeDialog("tutorial"); window.openNav("calendar"); }
      else if (window.submitTextCommand) { window.closeDialog("tutorial"); window.submitTextCommand(l[3]); }
      tutorialState[k] = true; api("/api/profile", { body: { tutorial: tutorialState } });
    },
  };

  /* ------------------------------------------------------------ boot */
  async function boot() {
    const s = await api("/api/auth/session", { quiet: true });
    window.__edithSetupKey = s.data.setup_key_required;
    addRail(); buildToday(); buildCalendar(); buildDevices(); buildTutorial(); buildIndicator();
    const lat = $("#val-ping-latency"); if (lat) lat.textContent = "—"; // removed fake "12"
    if (!s.data.owner) { showAuth(s.data.configured); return; }
    const pr = await api("/api/profile", { quiet: true });
    if (pr.ok) { window.__edithProfile = pr.data.profile; if (!Object.keys(pr.data.tutorial || {}).length) setTimeout(() => window.openNav("tutorial"), 800); }
    window.fetchTelemetry(); window.fetchWeather(); window.loadMobileConfig(); window.loadActiveModels();
    pollNotifications(); setInterval(pollNotifications, 15000);
    pollRemote(); setInterval(pollRemote, 3000);
    setInterval(() => { if ($("#modal-today")?.style.display === "flex") loadToday(); }, 30000);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
