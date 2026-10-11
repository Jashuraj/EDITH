---
name: edith-screen-vision
description: Live desktop vision capture, active window localization, and contextual screen analysis.
---

# EDITH Screen Vision

## Implementation
- Screen inspection tool: `edith/tools/vision.py`.
- Windows API integration: `edith/tools/windows.py`.

## Capabilities
- Full desktop screenshot capture using PIL and Win32 DC.
- Active foreground window detection with title and bounding box.
- Dynamic visual prompting without canned responses.
- OCR and visual element detection for desktop automation.
