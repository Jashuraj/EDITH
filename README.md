# EDITH — upgraded (Gateway + Host Agent + Phone APK)

Same EDITH HUD, phone app and VNC portal you already have — now backed by a secure gateway with real pairing, real remote desktop relay, durable reminders, an India calendar and Auto/Online/Offline AI routing.

| Part | Path | Runs on |
|---|---|---|
| Gateway (HUD `/`, phone `/mobile`, VNC `/vnc`, API) | `src/`, `public/` | Your PC (or any server you control) — Node 20+ & PostgreSQL |
| Host agent (screen, input, PC actions) | `host-agent/` | The Windows PC to control — Python 3.9+ & Pillow |
| Phone app (APK) | `dist/EDITH.apk`, source `android/` | Android 5.0+ |
| Original desktop runtime (reference) | `desktop/` | unchanged upstream Python project |

## Quick start (Windows 11)
1. Install **Node.js 20+**, **PostgreSQL 16** (create DB `app_db`), **Python 3.11** and optionally **Ollama**.
2. `copy .env.example .env` and set `DATABASE_URL` (+ optional keys).
3. `npm install` → `npx drizzle-kit push` → `npm run build` → `npm run start -- -p 3000 -H 0.0.0.0`
4. Open `http://localhost:3000`, create your owner passphrase, follow **Getting Started**.
5. HUD → **Devices & Remote → Link this PC**, then `host-agent\start_host_agent.bat --gateway http://127.0.0.1:3000 --code <CODE>`.
6. HUD → **Generate pairing code**; install `dist/EDITH.apk` on the phone → Settings → gateway URL (e.g. `http://192.168.1.20:3000`) + code → **Connect to Host**.
7. Optional local AI: `ollama pull hermes3:3b` (≈2 GB, your choice; not bundled).

Away from home: install **Tailscale** on PC and phone and use the PC's Tailscale address — see `docs/REMOTE_ACCESS_SETUP.md`.

## Commands that work without any AI model
`remind me to wash clothes at 7:30 pm` · `remind me to call mom every Sunday at 10 am` · `timer 10 minutes` · `what's on today` · `open chrome` · `open youtube.com` · `open downloads folder` · `volume up` · `set volume to 40` · `lock pc` (asks first) · `status` · `go offline`

## Tests
`node --import tsx --test tests/core.test.ts` (17 unit tests) · `BASE=http://127.0.0.1:3000 node tests/e2e.mjs` (17 end-to-end steps, needs Pillow for the agent's `--synthetic` mode) · `bash android/build_apk.sh` (rebuild APK).

## Honest limitations
- The PC must be **on, awake and online** with the host agent running; nothing can reach a shut-down or sleeping PC.
- Stream is JPEG-over-HTTPS (not H.264/WebRTC): fine for desktop work on LAN/Tailscale, not for gaming. Latency is never zero — see measured numbers in `docs/RELEASE_REPORT.md`.
- Windows cannot be unlocked programmatically; virtual gamepad, clipboard sync, file transfer, Face Sentinel and server-side Whisper/clap are only in the original desktop runtime and return a clear 501 through the gateway.
- The APK is **debug-signed** (original signing key unavailable): uninstall the old EDITH app before installing.

Docs: `docs/BEGINNER_GUIDE.md`, `docs/REMOTE_ACCESS_SETUP.md`, `docs/OFFLINE_ONLINE_MODES.md`, `docs/SECURITY_AND_PRIVACY.md`, `docs/TROUBLESHOOTING.md`, `docs/PROJECT_AUDIT.md`, `docs/REFERENCE_AUDIT.md`, `docs/RELEASE_REPORT.md`.
