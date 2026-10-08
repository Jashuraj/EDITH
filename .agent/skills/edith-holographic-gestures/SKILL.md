---
name: edith-holographic-gestures
description: MediaPipe dual-hand holographic gesture engine and 3D Three.js HUD controls.
---

# EDITH Holographic Gestures

## Implementation
- 3D HUD & Gesture processor: `edith/ui/public/index.html`.
- MediaPipe Hands computer vision engine.

## Gesture Controls
- Simultaneous tracking of 21 3D landmarks on both hands.
- Two-hand pinch distance dynamically scales the holographic 3D orb.
- Open palm, fist, and pointing gestures trigger HUD mode transitions.
- Interactive camera look and 3D scene rotation based on hand movements.
