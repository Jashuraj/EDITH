# Release report — EDITH 2.1.0

Environment: Linux sandbox (no Windows, no Android device/emulator, no browser for screenshots, Ollama not installed). Everything below was actually executed here unless marked NOT RUN.

## Commands & results
| Check | Command | Result |
|---|---|---|
| Unit tests | `node --import tsx --test tests/core.test.ts` | **17/17 pass** (time zones/DST, NL reminders, ambiguity, recurrence, catch-up, intents, tool validation, risk policy, LLM tool-call filtering, holidays, ICS) |
| End-to-end | `BASE=… node tests/e2e.mjs` with real Python agent `--synthetic` | **17/17 pass** (see list below) |
| Restart persistence | stop/start gateway, list reminders | pass (reminders intact) |
| Typecheck / build | `npx next typegen`, `tsc --noEmit`, `npm run build` | pass |
| Python agent | `py_compile` of 3 modules; ran on Linux in synthetic mode | pass (Windows SendInput/ImageGrab paths NOT RUN on Windows) |
| APK build | `bash android/build_apk.sh` | pass — see APK section |
| APK on device/emulator | — | **NOT RUN** (no device available) |
| Windows end-to-end | — | **NOT RUN** (no Windows host) |
| Global (mobile data → home) | — | **NOT RUN** (no Tailscale/relay available) |

E2E steps: HUD & phone served · owner setup · unauthenticated capture/input/cmd/devices rejected (401) · bad pairing code rejected · one-time pairing + reuse rejected · agent linked & online · NL reminder from phone · duplicate request_id not re-executed · tool job round-trip through agent · medium-risk approval flow · blind input rejected before viewing · live relayed frames · input relay + duplicate event ignored · reminder fired & delivered to HUD and phone · offline mode makes no internet probe/cloud call · calendar holidays + yearly birthday · revoked phone rejected.

## Measured relay performance (loopback, synthetic 1280×720 test pattern — NOT a Windows desktop over Wi-Fi)
* Delivered stream: **15.1 fps** (agent cap 15), ~17 KB/frame (~2 Mbit/s at 15 fps)
* Phone-side frame fetch (waits for next frame): p50 67 ms, p95 70 ms
* Server-side input relay (enqueue → agent pickup): p50 0 ms, p95 1 ms (n=25)
These exclude real capture/encode time on an i5-8350U and Wi-Fi/VPN RTT. Expect end-to-end input-to-visible-change latency of roughly one network RTT + capture/encode (~30–80 ms est.) + one frame interval; **not measured on target hardware.** The HUD (Devices & Remote) shows live p50/p95 once the real agent runs.

## APK
* Path: `dist/EDITH.apk` (also in the ZIP) — built from `android/` + `public/mobile/`
* Package `com.edith.ai`, versionCode 3, versionName 2.1.0, minSdk 21, targetSdk 33
* Signature: v1+v2+v3 verified, zipalign verified, **debug key** (CN=Android Debug, cert SHA-256 1e08a903…5953). Not a production-signed upgrade: original key unavailable → uninstall old app first.
* SHA-256: see `dist/EDITH.apk.sha256`
* Original APK (`com.edith.ai` 2.0.0, SHA-256 in `baseline/`) was a WebView wrapper of the broken phone page; not reused.

## Resource notes
Gateway process RSS observed ~100–150 MB on Linux (Node 22). Host agent: Python + Pillow, idle ≈ a long-poll every 20 s and a heartbeat every 5 s; capture runs only while viewed. Ollama memory is separate (hermes3:3b ≈ 2–3 GB RAM). 4 GB profile reduces context to 1024 and threads to 2. Not measured on the Latitude 5490.

## Remaining manual steps
1. Run on Windows 11: gateway + agent; verify capture, SendInput, toast, app launch verification.
2. Install APK on a phone; pair; verify live view & touch control on LAN; then via Tailscale on mobile data; record p50/p95 from the HUD.
3. Optional: sign APK with your own release keystore (`apksigner sign --ks …`).
4. Reference repository license review (docs/REFERENCE_AUDIT.md).
