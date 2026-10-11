# Troubleshooting
| Symptom | Fix |
|---|---|
| HUD asks for sign-in every time | Cookies blocked, or `EDITH_SECURE_COOKIE=1` on plain HTTP — set it to 0 |
| "Ollama offline" | Start Ollama (`ollama serve`), check `OLLAMA_URL`, then `ollama pull hermes3:3b` |
| "No AI engine is reachable" | Offline mode with no Ollama, or no provider key. Deterministic commands still work |
| Phone: "Invalid or expired pairing code" | Codes last 5 min and work once — generate a new one |
| Phone can't connect | Same Wi-Fi? Firewall allows Node on Private networks? Using `http://` + correct port? On mobile data use the Tailscale address |
| "PC host agent is offline" | Run `host-agent\start_host_agent.bat`; if it says token rejected, re-link with a new code |
| `open X` says not on approved list | Add it to `src/lib/tools.ts` APPS and `host-agent/allowlist.json` |
| Remote view black when PC locked | Expected: Windows secure desktop can't be captured. Sign in on the PC |
| Reminders didn't ring while PC was off | Gateway must be running; missed reminders are delivered once ("Missed while EDITH was offline") |
| Copy diagnostics | System Activity → "Copy diagnostics (redacted)" |
