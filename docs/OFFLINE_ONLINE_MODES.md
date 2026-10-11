# Auto / Online / Offline

| Feature | Auto | Online | Offline |
|---|---|---|---|
| Deterministic commands (reminders, timers, apps, media, status) | ✓ | ✓ | ✓ |
| Reminders & notifications (HUD/phone/Windows) | ✓ | ✓ | ✓ (on LAN) |
| Local AI (Ollama) | used if preferred or when cloud fails/absent | last-resort fallback | only engine |
| Cloud AI (Gemini/OpenAI/Groq/OpenRouter/OmniRoute) | if internet reachable & key configured | preferred | **never contacted** |
| Internet probe (gstatic generate_204, 2.5 s) | ✓ (cached 20 s) | ✓ | **not performed** |
| Weather (open-meteo) | ✓ if city set | ✓ | disabled |
| Remote desktop on LAN | ✓ | ✓ | ✓ |
| Remote desktop away from home | needs VPN/proxy + internet | same | ✗ |

Auto order: preferred online provider → other configured providers → Ollama. If the preferred provider is "Local", Ollama goes first. Every reply shows which engine answered (`model` field / chat label). Failures list each attempt in diagnostics.

Ollama: detected via `OLLAMA_URL/api/tags`; models listed in the Command Center selector; `num_ctx` 2048 (8 GB profile) or 1024 + 2 threads (4 GB profile); `keep_alive` 5 m so models unload when idle. Benchmarks for `hermes3:3b` on the Latitude 5490 were **not** run in this environment.
