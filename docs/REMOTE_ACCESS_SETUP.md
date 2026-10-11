# Remote access setup

## How it works
```
Phone (APK/PWA) --HTTPS/HTTP + device token--> Gateway <--outbound long-poll + frames-- Host agent (Windows)
```
* The host agent **dials out**; no inbound port is opened on the PC by the agent.
* Frames are relayed in memory only while an authorised viewer is watching. Input is accepted only from a principal that is currently viewing, only with the `control` scope, and is dropped if older than 5 s.
* Pairing: HUD → Devices & Remote → 6-digit code (5 min, single use, 6 attempts / 5 min / IP). The phone receives a random 256-bit token; only its SHA-256 is stored. Revoke any device from the same screen — it is disconnected immediately and cannot reconnect.

## Same Wi-Fi (LAN)
1. Run the gateway with `-H 0.0.0.0` and allow Node through Windows Firewall for **Private** networks only.
2. Phone app → Settings → `http://<PC-LAN-IP>:3000` + pairing code.

## Away from home (recommended: Tailscale, free for personal use)
1. Install Tailscale on the PC and phone, sign in with the same account.
2. Phone app URL: `http://<pc-name>.<tailnet>.ts.net:3000` or `http://100.x.y.z:3000` (traffic is WireGuard-encrypted).
3. Optional: `tailscale serve` to get HTTPS; then set `EDITH_SECURE_COOKIE=1`.
4. Save the URL in HUD → Devices & Remote → "Public / VPN URL" so it is shown to phones.

Alternatives: WireGuard on your router; or an HTTPS reverse proxy (Caddy/Cloudflare Tunnel) **plus** `EDITH_SETUP_KEY` set before first run. Never port-forward raw HTTP, VNC or RDP.

## What does NOT work
* PC shut down / asleep / offline → no stream, no actions (commands are refused, not queued for later).
* No relay is provided by this project; LAN works out of the box, global access needs the VPN/proxy above.

## Troubleshooting
* "PC host agent is offline" → check the agent console; it retries with back-off and prints the error.
* Black/stale view → screen locked (Windows secure desktop cannot be captured by user-mode apps) or UAC prompt visible.
* Slow stream → lower quality in phone app (resolution toggle); the agent also adapts automatically.
