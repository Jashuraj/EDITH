---
name: edith-remote-desktop
description: Low-latency remote desktop streaming, RAT input dispatch, and touch coordinate translation.
---

# EDITH Remote Desktop

## Architecture
- Screen streaming module: `edith/tools/screen_stream.py`.
- Remote input controller: `edith/tools/remote_input.py`.
- WebSocket streaming endpoint: `/stream/screen`.

## Capabilities
- Real-time desktop capture streaming at 20 to 30 FPS.
- Sub-pixel touch coordinate mapping with aspect ratio compensation.
- Mouse movement, left click, right click, double click, drag, and scroll.
- Remote keyboard keystrokes and system shortcuts.
- Laptop target execution: media and URLs open on host PC.
