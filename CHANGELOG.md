# Changelog

## 2.1.0 — EDITH Gateway upgrade (this release)

### Added
- **EDITH Gateway** (Next.js + PostgreSQL) serving the original HUD (`/`), phone app (`/mobile`) and VNC portal (`/vnc`) unchanged in layout, with the original `/api/*`, `/cmd`, `/state`, `/stream/screen` contract implemented securely.
- Owner passphrase sign-in (scrypt, HttpOnly SameSite=Strict session), one-time 6-digit phone pairing codes (5 min, single use, rate-limited), per-device scopes (`chat`, `screen`, `control`, `reminders`), revocation.
- **Windows host agent** (`host-agent/`): outbound-only link, real screen capture → JPEG relay, SendInput mouse/keyboard/text, allowlisted tools with outcome verification, Windows toasts, metrics, on-screen “REMOTE SESSION ACTIVE” indicator with local Disconnect.
- Remote relay with adaptive FPS/quality, unchanged-frame skipping, pointer-move coalescing, stale-input dropping, idempotent input event ids, measured FPS / frame age / input relay p50–p95, session log, kill switch, pause.
- Assistant core: idempotent `/cmd` (request_id), deterministic intents (reminders, timers, apps, URLs, folders, media, lock, status, mode), typed tool registry with low/medium/high risk, auto/ask/deny permissions, approvals (System Activity, or reply “yes” / “confirm”), E-STOP enforcement.
- Auto / Online / Offline model routing: Ollama discovery (`/api/tags`), Gemini, OpenAI, Groq, OpenRouter, OmniRoute/OpenAI-compatible; failover chain; offline mode never contacts the internet; LLM tool proposals validated by the registry.
- Durable reminders: recurrence (daily/weekdays/weekly days/monthly/yearly), snooze, done, arrival (manual “I've arrived”), quiet hours, missed-reminder catch-up, delivery to HUD (toast + sound + desktop notification), phone (existing alert channel) and Windows toast.
- India calendar: fixed national holidays + DoPT 2026 gazetted list (moon-sighting dates flagged tentative), birthdays/anniversaries (yearly), exams, custom holidays, ICS import/export, duplicate detection.
- Getting Started tutorial (12 lessons, “Try it”, progress, replay) and profile (state, city, timezone, 4 GB / 8 GB profile, quiet hours).
- Rebuilt Android APK from source (`android/`), same package `com.edith.ai`, version 2.1.0 (3).

### Fixed (existing UI defects)
- HUD `MODE: AUTO` button called an undefined function — now cycles Auto → Online → Offline.
- Fake fallbacks removed: battery “100%”, weather “24°C OPTIMAL”, provider latency “12 ms”, ping “12 ms”, hard-coded `edith-jashu.loca.lt` link, fake model list when Ollama is down, “PINNED ONLINE” tunnel label.
- Provider save failures were silently ignored — now shown.
- Remote MJPEG stream kept running after closing the dialog — now stopped.
- **Phone app was non-functional**: `app.js` referenced 96 elements missing from `mobile/index.html`; `initEvents()` threw and aborted `init()`, so no buttons worked. Event wiring is now null-safe.
- Phone remote view never displayed frames (`mobile-remote-img` vs `remote-screen-img` mismatch) — fixed.
- Phone app had no way to enter a token — added “Pairing code” field to the existing settings modal.
- Personal IP and dead tunnel URL removed from `mobile/server_config.json`.
- Escape closes dialogs; visible focus ring; reduced-motion support; dialogs fit small screens.

### Security
- Upstream desktop server exposes `/stream/screen`, `/api/screen/capture` and `/api/remote/input` with `CORS *` and no auth; with `tunnel.py` this can expose the desktop publicly. The gateway path requires owner/device auth for all of these. See docs/SECURITY_AND_PRIVACY.md. The upstream Python server in `desktop/` is kept for reference but should not be exposed beyond localhost.

### Intentional visible UI changes
- Four rail buttons added after “System Activity”: Today & Reminders, Calendar & Festivals, Devices & Remote, Getting Started (same rail style/tooltips).
- Sign-in dialog on first load (existing dialog style).
- Status pill text is truthful (e.g. “PC HOST OFFLINE · ONLINE (AUTO)”); E-STOP button shows “▶ RESUME” while engaged.
- Red “REMOTE SESSION ACTIVE · Disconnect” banner while a phone views the screen; reminder toasts bottom-right.
- Phone settings modal gains one “Pairing code” input.
- APK: same UI; signed with a debug key (uninstall the old app first — signatures differ).
