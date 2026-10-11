# Security & privacy

**Threats considered:** stranger on the network/internet, stolen phone, replayed requests, prompt-injected model output, shoulder-surfing logs.

| Control | Implementation |
|---|---|
| Owner auth | scrypt passphrase; random session token, SHA-256 stored; HttpOnly SameSite=Strict cookie; login rate limit 8/5 min |
| First-run hijack | optional `EDITH_SETUP_KEY` required for setup |
| Device auth | 6-digit one-time code (5 min) → 256-bit token, hashed at rest; scopes; revocation kills sessions |
| Host auth | separate one-time code (10 min) → host token (stored in `%APPDATA%\EDITH\host_agent.json`, ACL to current user) |
| Remote control | requires `screen`/`control` scope and an active view; E-STOP blocks input/actions; local Disconnect on the PC; visible banner on HUD and topmost indicator on PC |
| Actions | typed tool registry, input validation, low/medium/high risk, auto/ask/deny; high-risk never auto; no arbitrary shell; no UAC bypass; Windows unlock unsupported by design |
| LLM | model may only *propose* a registered tool call; the registry validates and policy decides |
| Idempotency | request ids for commands, event ids for input, atomic job claims, job expiry (60 s) so a reconnecting host never runs stale commands |
| Secrets | API keys from `.env` or AES-256-GCM with `EDITH_SECRET_KEY`; never returned by the API; audit log redacts token/key patterns |
| Privacy | data in local PostgreSQL; screen frames & keystrokes never persisted; typed text not logged; diagnostics redacted; export at `/api/export` |
| CORS | `*` without credentials → cookies never sent cross-origin; phone uses tokens |

**Known risks**
- Cleartext HTTP is allowed for LAN/Tailscale use. Use HTTPS for anything internet-facing.
- The APK enables `allowUniversalAccessFromFileURLs` for its bundled UI only; external links open in the browser.
- The original `desktop/` Python server has unauthenticated stream/input endpoints and a public-tunnel feature — keep it bound to localhost or don't run its server.
- Medicine reminders are reminders only — no medical advice.
