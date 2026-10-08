---
name: edith-voice-clap
description: Acoustic double-clap wake detection, voice synthesis, and cross-browser audio fallback.
---

# EDITH Voice and Acoustic Detection

## Implementation
- Acoustic clap detector: `edith/voice/clap_detector.py`.
- Voice synthesis: `edith/voice/speaker.py`.
- Speech recognition: `edith/voice/listener.py`.

## Capabilities
- Real-time double-clap detection with bandpass filtering and debounce.
- Automatic EDITH welcome voice greeting on verified clap event.
- Text-to-speech feedback with configurable pitch and rate.
- WebAudio chunk streaming fallback for Brave browser shield compatibility.
