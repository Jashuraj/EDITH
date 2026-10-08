---
name: edith-vnc-portal
description: Zero-dependency HTML5 canvas VNC web portal and browser desktop streaming.
---

# EDITH VNC Web Portal

## Architecture
- Frontend endpoint: `edith/ui/public/vnc/index.html`.
- Stream server: `edith/ui/server.py`.

## Features
- Direct browser access via `/vnc`.
- HTML5 canvas rendering of desktop frames with adaptive JPEG compression.
- Complete mouse movement, click, scroll, and keyboard input passthrough.
- Real-time stream telemetry and FPS display.
