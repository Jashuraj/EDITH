# Project audit (baseline: github.com/Jashuraj/EDITH @ main, cloned during this session)

## Stack found
Python 3 runtime (`edith/`): `http.server` HUD on :8794 and phone gateway on :8795, Ollama/cloud/OmniRoute providers, reflex engine, task engine, SQLite memory, voice (Whisper, clap detector, TTS), screen streamer (MJPEG/JPEG), Win32 remote input, localtunnel-based tunnel manager. UI = static HTML/CSS/JS (`edith/ui/public`: HUD `index.html` 88 KB with inline JS, `orb.js` Three.js r128, `gestures.js`, `mobile/` PWA, `vnc/` portal). `dist/EDITH.apk` (1.48 MB, `com.edith.ai` 2.0.0, WebView wrapper of `mobile/`) and `dist/EDITH.exe` (78 MB PyInstaller). Upstream reports 48 unittest tests (not run here: Windows-only dependencies).

## Baseline UI inventory (preserved)
Left rail: Command Center, Intelligence & APIs, Face Sentinel, Command Guide, Audio Mixer, System Activity, Settings, avatar/About. Top bar: E.D.I.T.H. MARK II brand, theme pills (EDITH/JARVIS/FRIDAY/KAREN/SPIDEY/ULTRON), MODE button, status pill, clock, weather, E-STOP. Workspace: orb stage, telemetry cards, chat/composer, mobile link card. Dialogs: remote, gamepad, mixer, guide, settings (providers/voice/mobile/security tabs), sentinel, activity, about. Phone: header badge, orb, vitals, console, command capsule + mic, bottom nav (core/remote/gamepad/guide/settings), remote overlay, settings modal. Baseline copies: `baseline/index.original.html`, `baseline/mobile.app.original.js`, `baseline/vnc.original.html`, `baseline/EDITH.apk.original.sha256`. Screenshot capture was not possible (no browser in the sandbox); the HTML diff is the comparison artefact (HUD: 37 changed lines, all listed in CHANGELOG).

## Defects found (all fixed unless noted)
1. HUD MODE button → undefined `toggleSystemMode` (dead control).
2. Fake values: battery 100%, 24°C OPTIMAL, 12 ms latency/ping, fake model list, PINNED ONLINE, hard-coded loca.lt URL.
3. Provider save errors silently swallowed; text claimed keys saved in `.llm.env`.
4. Remote MJPEG kept streaming after dialog close.
5. **Phone app dead on load:** 96/122 element ids referenced by `app.js` missing from `mobile/index.html`; first `addEventListener` on null threw inside `init()`.
6. Phone remote view never rendered (`mobile-remote-img` id mismatch).
7. Phone app had no token/pairing input; `/pair` existed server-side only.
8. **Security:** `/stream/screen`, `/api/screen/capture`, `/api/remote/input` unauthenticated with `CORS *`; tunnel can publish them. (Mitigated by gateway path; upstream server left as-is in `desktop/`.)
9. Personal LAN IP + tunnel URL committed in `server_config.json`; personal `edith_memory.db` committed (excluded from this release).

## Command path (new)
Phone/HUD → `POST /cmd` (token/cookie, request_id) → idempotent task row → deterministic intent or model router → tool registry validation → permission (auto/ask/deny) → `host_jobs` → host agent long-poll claims → Win32 action + verification → `POST /api/host/result` → reply.

## Remote desktop path (new, verified end-to-end with synthetic frames)
Agent capture (ImageGrab/mss) → JPEG → `POST /api/host/frame` → in-memory relay → phone `GET /api/screen/capture?after=seq` (APK/PWA, unchanged client loop) or HUD MJPEG `/stream/screen` → touch → `POST /api/remote/input` → long-poll → `SendInput`.
