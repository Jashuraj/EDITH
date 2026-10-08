---
name: edith-mobile-gateway
description: Mobile LAN gateway, pinned static cloud tunnel, pairing token auth, and responsive UI.
---

# EDITH Mobile Gateway

## Architecture
- Gateway server: `edith/phone/gateway.py` on port 8795.
- Tunnel manager: `edith/phone/tunnel.py`.
- Static pinned URL: `https://edith-jashu.loca.lt`.
- Mobile client: `edith/ui/public/mobile/`.

## Capabilities
- Static WAN cloud tunnel without randomized hostnames.
- Cryptographic pairing token authentication.
- Local LAN discovery and encrypted WebSocket duplex channel.
- Responsive mobile layout fitting all phone viewports without clipping.
