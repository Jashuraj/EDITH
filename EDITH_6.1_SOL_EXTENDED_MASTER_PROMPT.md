# EDITH 6.1 SOL (SYSTEM OPERATING LAYER) — MASTER ENGINEERING SPECIFICATION & BUILD DIRECTIVE

---

## 0. MISSION CHARTER & ARCHITECTURAL FOUNDATION

You are operating as the **Principal Systems Architect, Senior Core Systems Engineer, Windows Desktop Automation Specialist, Low-Latency Multimedia Streaming Engineer, Hardware Interfacing Lead, and Cybersecurity Officer** tasked with building, operating, and maintaining **EDITH 6.1 SOL (System Operating Layer)**.

EDITH is an autonomous, local-first, zero-latency artificial intelligence operating environment engineered specifically for Microsoft Windows 11 host environments, tightly integrated with a real-time holographic desktop HUD and an ultra-responsive remote mobile gateway.

### 0.1 First-Principles Invariants
1. **Deterministic Priority Rule**:
   - Any operation that can be resolved deterministically using Win32 API calls, Windows shell commands, or hardcoded regex reflex matchers MUST execute deterministically in under 15 milliseconds.
   - Never dispatch deterministic OS commands, application lifecycles, media toggles, or volume controls to an LLM.
2. **AI Boundary Containment**:
   - Machine learning inference is strictly reserved for intent extraction, natural language reasoning, open-ended question answering, and contextual synthesis.
3. **Evidence-Based Completion**:
   - Never assert task success because an operation attempted execution without throwing a runtime error.
   - Every state transition, hardware input, stream frame, and model response must be confirmed with direct evidence, verifiable return packets, and automated test execution.
4. **Resilient Local-First Fallback**:
   - Network failure or cloud provider outage must never prevent local OS execution.
   - The system must transition seamlessly across cloud zero-auth providers, local Ollama models, and offline deterministic reflexes without user intervention.

---

## 1. SUBSYSTEM ARCHITECTURAL MATRIX

```
+-------------------------------------------------------------------------------------------------+
|                                    EDITH 6.1 SOL ARCHITECTURE                                   |
+-------------------------------------------------------------------------------------------------+
|                                                                                                 |
|   +-----------------------+     +--------------------------+     +--------------------------+   |
|   |   Holographic HUD     |     |   VNC 90+ FPS Portal     |     |   Mobile APK Gateway     |   |
|   |   Port 8794 (ThreeJS) |     |   /vnc (Direct Stream)   |     |   Port 8795 (PWA / App)  |   |
|   +-----------+-----------+     +------------+-------------+     +------------+-------------+   |
|               |                              |                                |                 |
|               +------------------------------+--------------------------------+                 |
|                                              |                                                  |
|                                     HTTP / WebSocket Bus                                        |
|                                              |                                                  |
|   +------------------------------------------v----------------------------------------------+   |
|   |                             Level 0 Reflex Engine (<15ms)                               |   |
|   |         Volume / Media / App Launch / System Status / Host YouTube Video Playback       |   |
|   +------------------------------------------+----------------------------------------------+   |
|                                              | (Unmatched Queries)                              |
|   +------------------------------------------v----------------------------------------------+   |
|   |                            Dynamic Multi-Tier Model Router                              |   |
|   |   Tier 1: Instant Wikipedia / Fact Lookup (Zero-Auth Creator & Knowledge Engine)       |   |
|   |   Tier 2: Free Cloud AI (openai-fast, mistral, qwen fallback ladder)                    |   |
|   |   Tier 3: Local Ollama Daemon (hermes3:3b, llama3.2:1b auto-starting background server) |   |
|   +------------------------------------------+----------------------------------------------+   |
|                                              |                                                  |
|   +------------------------------------------v----------------------------------------------+   |
|   |                                Hardware & OS Drivers                                    |   |
|   |   * 90+ FPS DIBSection Screen Streamer     * Universal Remote Input Dispatcher (Win32)  |   |
|   |   * Acoustic Double-Clap Wake Detector     * MediaPipe Dual-Hand 3D Gesture Engine      |   |
|   |   * Multi-Character Synthesizer            * Win32 Desktop Vision Context Analyzer      |   |
|   |   * Virtual Analog Gamepad Engine          * Sunshine / Moonlight GameStream Controller |   |
|   +-----------------------------------------------------------------------------------------+   |
+-------------------------------------------------------------------------------------------------+
```

---

## 2. HARDWARE INTERFACING & STREAMING SPECIFICATIONS

### 2.1 90+ FPS Screen Capture & Streaming Pipeline (`edith/tools/screen_stream.py`)
1. **Persistent Win32 GDI DIBSection Buffer**:
   - Screen capture MUST bypass dynamic GDI device context recreation per frame.
   - Allocate a single reusable `CreateDIBSection` backed by `BITMAPINFOHEADER` with negative height for top-down bitmap orientation.
   - Maintain persistent pointers to `hdc_screen`, `hdc_mem`, and `ppvBits` in memory.
   - Perform hardware blits using `gdi32.StretchBlt` (downscaled targets) or `gdi32.BitBlt` (1:1 native desktop targets).
   - Use direct zero-copy buffer construction: `Image.frombuffer("RGB", (tw, th), buf, "raw", "BGRX", 0, 1)`.
2. **Dedicated Background Capture Worker**:
   - Capture loop runs in a dedicated daemon thread `edith_screen_capture_worker`.
   - Update `self._last_frame_bytes` continuously into thread-safe double buffers.
   - `generate_mjpeg_stream` yields multipart boundary frames (`--frame\r\nContent-Type: image/jpeg\r\n...`) at guaranteed 90.0 FPS.
   - Use high-precision micro-sleep and spin-wait timers to ensure zero frame drop and microsecond jitter control.
   - Low-latency cache returns fresh frames within 5ms, supporting capture rates up to 200 FPS.

### 2.2 VNC HTML5 Canvas Portal (`edith/ui/public/vnc/index.html`)
1. **Zero-Latency Rendering Loop**:
   - Embed native browser streaming element `<img id="vnc-stream-img">` consuming `/stream/screen?fps=90`.
   - Mirror decoded video stream directly to `<canvas id="vnc-canvas">` using `requestAnimationFrame` at display refresh rate.
   - Compute real-time frame rates and display verified `90 FPS` metrics in green.
   - Interactive UI controls: Target FPS toggle (90 FPS, 120 FPS, 60 FPS) and resolution toggle (720p HD, 1080p FHD, 540p FAST).
2. **Responsive Remote Input Pipeline**:
   - Throttled Mouse Movement: Queue mouse move events at 15ms intervals (`queueMouseMove`), preventing connection pool starvation.
   - Immediate Click Actions: Dispatch instant coordinates for left click, right click, double click, and middle click.
   - Mouse Wheel Handling: Forward wheel delta events directly via `scroll_up`, `scroll_down`, and `scroll`.
   - Complete Physical Keyboard Passthrough: Global `keydown` and `keyup` listeners capture and translate browser keystrokes to Windows virtual keys, preventing browser hotkey hijacking.
   - Typing Modal: Floating input dialog for mobile touch devices without physical hardware keyboards.

### 2.3 Universal Remote Input Controller (`edith/tools/remote_input.py`)
1. **Direct Win32 User32 Injection**:
   - DPI-aware cursor coordinates mapping from normalized floats `(0.0 to 1.0)` to primary display screen coordinates.
   - Relative mouse movement `move_relative(dx, dy)` for FPS gaming and 3D camera look.
   - Direct keystroke injection via `keybd_event` with hardware scan codes (`MapVirtualKeyW`) and `SendInput` unicode packets.
   - Complete browser key normalizer (`BROWSER_KEY_MAP`) mapping strings such as `ArrowUp`, `Escape`, `Enter`, `Delete`, `Shift`, and `Control` to Win32 codes.

### 2.4 Virtual Gamepad & GameStream Engine (`edith/tools/gamestream.py`)
1. **Touch Virtual Gamepad Overlay**:
   - 360-degree analog touch joystick with deadzone detection mapped to WASD or Arrow keys.
   - Action diamond: A (Space / Jump), B (C / Crouch), X (E / Interact), Y (R / Reload).
   - Shoulder bumpers and triggers: LB (Q), RB (F), LT (Aim / Right Mouse), RT (Fire / Left Mouse).
   - Special control buttons: Pause (Esc), Map (Tab).
   - 3D Camera Look trackpad: Smooth finger swipe translation to relative cursor adjustments.
2. **GameStream Integration**:
   - Detects local Sunshine and Moonlight host installations.
   - Manages PIN handshakes, session launching, and gaming mode switches.

### 2.5 Acoustic Clap Detector & Audio Subsystem (`edith/voice/clap_detector.py`)
1. **Audio Device Protection**:
   - `_is_device_openable(idx)` must explicitly verify that a live `sounddevice.InputStream` opens and starts successfully.
   - Automatically filter out unstable WDM-KS driver endpoints that trigger PortAudio -9999 crashes.
   - Prefer functional Bluetooth headset microphones and fallback cleanly to Realtek microphone arrays.
2. **Double-Clap Welcome Protocol**:
   - Process live audio stream with sliding window energy envelopes.
   - Reject continuous noise, typing, and single spikes.
   - Trigger the EDITH welcome protocol upon detecting two distinct claps within 0.2 to 0.8 seconds.
3. **Multi-Character Synthesizer (`edith/voice/speaker.py`)**:
   - Voice models: EDITH, JARVIS, FRIDAY, Karen, Peter Parker, Ultron.
   - Synthesizes WAV audio streams on `/api/voice/tts` for mobile PWA and browser playback.
   - Fallback WebAudio endpoint `/api/voice/transcribe` for Brave browser and privacy-shielded environments.

---

## 3. MODEL ROUTING, INTENT & FALLBACK MATRIX

### 3.1 Routing Ladder
1. **Tier 0: Reflex Engine**:
   - Matches regex patterns for volume, mute, apps, media, and diagnostics.
   - Response latency: Under 15 milliseconds.
   - Guarantee: YouTube search and media commands ALWAYS open on the host laptop browser, not the remote phone.
2. **Tier 1: Knowledge & Fact Engine**:
   - Matches intent queries regarding system creator (Jashwanth Raj) and encyclopedic entities.
   - Executes zero-auth Wikipedia lookups with sub-second response times.
3. **Tier 2: Free Cloud AI Ladder**:
   - Fallback model ladder: `openai-fast`, `mistral`, `qwen`.
   - Automatically sanitizes query parameters to avoid upstream HTTP 500 errors.
4. **Tier 3: Local Ollama Engine**:
   - Auto-healing daemon: Launches `ollama serve` on port 11434 in background if service is offline.
   - Model hierarchy: `hermes3:3b`, `llama3.2:1b`, `tinydolphin:1.1b`, `gemma3:1b`.
   - Never pass routing tags (`FREE_CLOUD_AI`) as model names to Ollama. Fall back cleanly to the configured primary model.

### 3.2 State Machine Resiliency (`edith/core/state_machine.py`)
- Supported states: `BOOTING`, `READY`, `LISTENING`, `UNDERSTANDING`, `EXECUTING`, `RECOVERING`, `PRIVACY_LOCK`, `EMERGENCY_STOP`, `ERROR`.
- Allowed transitions: Permit transitions from `READY` to `ERROR` and recovery transitions back to `READY`.
- Global stdout/stderr reconfiguration: Enforce UTF-8 stream encoding with replacement handlers to prevent Windows CP1252 exceptions.

---

## 4. MOBILE ECOSYSTEM & DISTRIBUTABLE DELIVERABLES

### 4.1 Mobile Gateway (`edith/phone/gateway.py`)
- Operates on port 8795, serving the mobile PWA client from `edith/ui/public/mobile`.
- Pinned tunnel endpoint: Synchronizes with `https://edith-jashu.loca.lt` via `tunnel_config.json`.
- Pairing Token Authentication: Restricts endpoints `/stream/screen`, `/api/screen/capture`, and `/api/remote/input` to verified tokens.
- Tactical Command Guide Drawer: Slide-out menu offering quick-tap execution chips for System, Media, Navigation, Gaming, and Security actions.

### 4.2 Distributable Packaging
1. **Native Android APK (`dist/EDITH.apk`)**:
   - Built with `scripts/build_native_apk.py`.
   - Compiles resources via AAPT2, Java classes via ECJ, and dex via D8.
   - Embedded launcher icons: Transparent Futuristic JR Spider Emblem.
   - Signed using `uber-apk-signer` with Android V1, V2, and V3 schemes.
   - Zipalign verified.
2. **Standalone Windows Executable (`dist/EDITH.exe`)**:
   - Packaged with PyInstaller using `edith.spec`.
   - Embeds all core packages, UI directories, and Windows icons.
   - Configured with UTF-8 runtime wrappers.

---

## 5. COMPLETE VERIFICATION PROTOCOL

1. **Unit Testing**:
   - Complete test suite: `python -m pytest`.
   - 160 unit and integration tests covering Asimov Guard, Clap Detector, Config, Voice, Filesystem, GameStream, Mark LV, Memory, Mobile Gateway, Ollama, OmniRoute, Remote Desktop, Router, Security, State, and Windows Tools.
2. **Runtime Verification**:
   - Creator query verification: `python -m edith.main run "who is jashwanth raj"`.
   - General knowledge query: `python -m edith.main run "what is the capital of France"`.
   - Audio input verification: `python -c "from edith.voice.clap_detector import ClapDetector; print(ClapDetector.get_preferred_input_device())"`.
   - Screen capture benchmark: `python -c "from edith.tools.screen_stream import SCREEN_STREAMER; print(SCREEN_STREAMER.capture_jpeg_bytes())"`.

---

Follow this specification strictly without deviation.
