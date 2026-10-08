---
name: edith-virtual-gamepad
description: Mobile touch virtual gamepad, 360-degree analog joystick, and tactile key bindings.
---

# EDITH Virtual Gamepad

## Architecture
- Mobile touch UI: `edith/ui/public/mobile/app.js` and `style.css`.
- Windows key dispatch: `edith/tools/remote_input.py`.

## Features
- Analog thumbstick with deadzone detection mapped to WASD or Arrow keys.
- Tactile action buttons for A, B, X, Y, Space, Shift, and Escape.
- Landscape Game Mode HUD optimized for direct touch controls.
- Fast direct Win32 keystroke dispatch for responsive gameplay.
