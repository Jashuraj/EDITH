/* EDITH Gateway: one-time pairing for the original phone app (PWA + APK).
 * If the "token" field contains a 6-digit pairing code, exchange it for a
 * long-lived, revocable device token. The code itself is single-use and expires in 5 minutes. */
(function () {
  "use strict";
  window.edithRid = function () {
    return window.crypto && crypto.randomUUID ? crypto.randomUUID() : "m" + Date.now() + Math.random().toString(16).slice(2);
  };
  window.edithResolveToken = async function (input, baseUrl, log) {
    const raw = String(input || "").trim();
    const code = raw.replace(/\s+/g, "");
    if (!/^\d{6}$/.test(code)) return raw;
    const base = String(baseUrl || window.location.origin || "").replace(/\/+$/, "");
    if (!/^https?:\/\//.test(base)) {
      if (log) log("PAIRING", "Enter the gateway URL first (e.g. http://192.168.1.20:3000 or your Tailscale address).");
      return "";
    }
    try {
      const name = (navigator.userAgentData && navigator.userAgentData.platform) || (/Android/i.test(navigator.userAgent) ? "Android phone" : "Phone");
      const r = await fetch(base + "/api/pair/claim", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Bypass-Tunnel-Reminder": "true" },
        body: JSON.stringify({ code: code, name: name }),
      });
      const d = await r.json().catch(function () { return {}; });
      if (r.ok && d.token) {
        if (log) log("PAIRED", "Paired with EDITH (" + (d.scopes || []).join(", ") + "). This phone can be revoked from the HUD.");
        return d.token;
      }
      if (log) log("PAIRING FAILED", d.error || "HTTP " + r.status);
      return "";
    } catch (e) {
      if (log) log("PAIRING FAILED", "Cannot reach " + base + ": " + e.message);
      return "";
    }
  };
})();
