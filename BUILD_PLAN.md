# EDITH Master Build Plan: First 20 Implementation Tasks

**Target Machine:** Dell Latitude 5490 / Windows 11  
**Execution Strategy:** Incremental TDD, zero premature complexity, local-first.

---

### Task 1: System Configuration & Hardware Profile Detector
- **Why:** Provide runtime awareness of available RAM, CPU cores, battery status, and drive quotas so EDITH dynamically configures resource ceilings.
- **Files:** `edith/core/config.py`, `edith/tests/test_config.py`
- **Dependencies:** None
- **Test:** `python -m unittest edith/tests/test_config.py`
- **Done Condition:** Accurately detects 8GB RAM, i5-8350U, and sets low-memory ceilings.

---

### Task 2: Async Event Bus & State Machine
- **Why:** Decouple subsystems and establish deterministic states (`IDLE`, `LISTENING`, `THINKING`, `EXECUTING`, `VERIFYING`, `EMERGENCY_STOP`).
- **Files:** `edith/core/event_bus.py`, `edith/core/state_machine.py`, `edith/tests/test_state.py`
- **Dependencies:** Task 1
- **Test:** `python -m unittest edith/tests/test_state.py`
- **Done Condition:** Invalid state transitions raise typed exceptions; event emissions trigger registered listeners asynchronously.

---

### Task 3: Security & Policy Gate with Risk Levels
- **Why:** Prevent untrusted or destructive operations; classify commands into LOW, MEDIUM, HIGH, and CRITICAL risk; implement instant EMERGENCY STOP.
- **Files:** `edith/core/security.py`, `edith/tests/test_security.py`
- **Dependencies:** Task 2
- **Test:** `python -m unittest edith/tests/test_security.py`
- **Done Condition:** HIGH/CRITICAL commands block for user authorization; EMERGENCY STOP terminates active executions.

---

### Task 4: Level 0 Deterministic Reflex Engine
- **Why:** Guarantee near-instant (<15ms) responses for common system actions (launch apps, volume, battery, lock) without touching any LLM.
- **Files:** `edith/tools/reflex.py`, `edith/tests/test_reflex.py`
- **Dependencies:** Task 3
- **Test:** `python -m unittest edith/tests/test_reflex.py`
- **Done Condition:** 16 standard voice/text reflex commands match and execute deterministically in <15ms.

---

### Task 5: Windows Native Automation Toolpack
- **Why:** Execute core OS tasks safely on Windows 11 using PowerShell and Win32 APIs.
- **Files:** `edith/tools/windows.py`, `edith/tests/test_windows.py`
- **Dependencies:** Task 4
- **Test:** `python -m unittest edith/tests/test_windows.py`
- **Done Condition:** Can query system stats, launch/kill processes, toggle mute/volume, and lock workstation safely.

---

### Task 6: Tool Registry & Action Pack Architecture
- **Why:** Prevent model context saturation by bundling tools into modular action packs (`WINDOWS_PACK`, `FILES_PACK`, `CODING_PACK`).
- **Files:** `edith/tools/registry.py`, `edith/tests/test_tools.py`
- **Dependencies:** Task 5
- **Test:** `python -m unittest edith/tests/test_tools.py`
- **Done Condition:** Tools expose clean JSON schemas; action packs can be activated and deactivated dynamically.

---

### Task 7: Sandboxed Filesystem Toolpack
- **Why:** Enable safe workspace file reading, writing, diffing, and searching with strict directory jail and path traversal protection.
- **Files:** `edith/tools/filesystem.py`, `edith/tests/test_filesystem.py`
- **Dependencies:** Task 6
- **Test:** `python -m unittest edith/tests/test_filesystem.py`
- **Done Condition:** Path traversal attempts fail with security violations; valid file read/write operations succeed hermetically.

---

### Task 8: Model Provider Base Abstraction & Circuit Breaker
- **Why:** Decouple application logic from model vendors; support bounded retries and automatic circuit breaking.
- **Files:** `edith/providers/base.py`, `edith/tests/test_providers.py`
- **Dependencies:** Task 2
- **Test:** `python -m unittest edith/tests/test_providers.py`
- **Done Condition:** Abstract base classes defined; circuit breaker trips to open state upon consecutive timeouts/failures.

---

### Task 9: Ollama Local Provider (Hermes 3B & Llama 3.2 Integration)
- **Why:** Provide local, offline intelligence and function calling via the installed Ollama runtime.
- **Files:** `edith/providers/ollama_provider.py`, `edith/tests/test_ollama.py`
- **Dependencies:** Task 8
- **Test:** `python -m unittest edith/tests/test_ollama.py`
- **Done Condition:** Connects to localhost:11434, successfully streams responses and invokes Hermes 3B tool calling.

---

### Task 10: ModelRouter with Zero-Credit & Offline Fallback
- **Why:** Intelligently select models based on query complexity, internet connectivity, credit state, and hardware RAM headroom.
- **Files:** `edith/providers/router.py`, `edith/tests/test_router.py`
- **Dependencies:** Task 9
- **Test:** `python -m unittest edith/tests/test_router.py`
- **Done Condition:** Routes offline or zero-credit requests directly to local models; routes complex tasks to cloud only when available.

---

### Task 11: Structured Local Memory (SQLite)
- **Why:** Persist user preferences, conversation history, task logs, and system audit trails locally without cloud databases.
- **Files:** `edith/memory/local_store.py`, `edith/tests/test_memory.py`
- **Dependencies:** Task 2
- **Test:** `python -m unittest edith/tests/test_memory.py`
- **Done Condition:** SQLite schema created; sessions, logs, and user key-value entries store and retrieve reliably.

---

### Task 12: Persistent Task Engine with Checkpoints
- **Why:** Manage multi-step goals with state persistence, allowing pause, resume, and step recovery across restarts.
- **Files:** `edith/tasks/engine.py`, `edith/tests/test_task_engine.py`
- **Dependencies:** Task 11, Task 6
- **Test:** `python -m unittest edith/tests/test_task_engine.py`
- **Done Condition:** Tasks transition through state graph; checkpoints enable resumption after interrupted runs.

---

### Task 13: Self-Healing & Recovery Engine
- **Why:** Detect tool failures, parse error logs, and attempt localized repair strategies before giving up or prompting the user.
- **Files:** `edith/tasks/recovery.py`, `edith/tests/test_recovery.py`
- **Dependencies:** Task 12
- **Test:** `python -m unittest edith/tests/test_recovery.py`
- **Done Condition:** Emulated command errors trigger fallback actions and self-repair attempts cleanly.

---

### Task 14: Mission Control & Autonomous Goal Runner
- **Why:** Execute composite autonomous goals (inspect, plan, edit, verify, report) with explicit verification gates.
- **Files:** `edith/tasks/mission.py`, `edith/tests/test_mission.py`
- **Dependencies:** Task 12, Task 13
- **Test:** `python -m unittest edith/tests/test_mission.py`
- **Done Condition:** End-to-end multi-step plan executes to completion with verified evidence artifacts.

---

### Task 15: Local Voice & Speech Synthesizer (TTS / STT Interface)
- **Why:** Provide audible presence and natural voice interaction with offline speech synthesis and barge-in support.
- **Files:** `edith/voice/speaker.py`, `edith/voice/listener.py`, `edith/tests/test_voice.py`
- **Dependencies:** Task 2
- **Test:** `python -m unittest edith/tests/test_voice.py`
- **Done Condition:** Synthesizes speech locally; interrupts playback upon barge-in signal.

---

### Task 16: UI State Mirror & Airlock Server (barehands Protocol Adaptation)
- **Why:** Expose fast localhost HTTP endpoints for `state/state`, `state/mood.json`, `state/wave.json`, and safe media staging.
- **Files:** `edith/ui/server.py`, `edith/tests/test_ui_server.py`
- **Dependencies:** Task 2, Task 7
- **Test:** `python -m unittest edith/tests/test_ui_server.py`
- **Done Condition:** Server runs on localhost:8794; broadcasts state updates to frontend clients at low latency.

---

### Task 17: Holographic UI: Three.js Orb & Glass Control Stage (ULTRON + barehands Design)
- **Why:** Deliver the Iron Man Jarvis/Ultron aesthetic: 3D shader orb responding to audio/thinking state, floating glass panels, and mission control cards.
- **Files:** `edith/ui/public/index.html`, `edith/ui/public/orb.js`, `edith/ui/public/style.css`
- **Dependencies:** Task 16
- **Test:** Browser verification on localhost:8794
- **Done Condition:** WebGL orb renders smoothly on Intel UHD 620; shifts colors/pulsations with system state.

---

### Task 18: MediaPipe Hand Gesture & Vision Control Layer
- **Why:** Allow webcam hand-tracking gestures (pinch, drag, zoom, hold) to manipulate the UI and issue touchless commands.
- **Files:** `edith/ui/public/gestures.js`
- **Dependencies:** Task 17
- **Test:** Manual and mock gesture test harness
- **Done Condition:** Hand landmarks detect pinch and drag events without blocking the Three.js render loop.

---

### Task 19: Phone Gateway & Mobile Terminal Protocol
- **Why:** Enable a paired Android phone to send commands, receive progress notifications, and approve high-risk tasks over local Wi-Fi.
- **Files:** `edith/phone/gateway.py`, `edith/phone/protocol.py`, `edith/tests/test_phone.py`
- **Dependencies:** Task 3, Task 12
- **Test:** `python -m unittest edith/tests/test_phone.py`
- **Done Condition:** WebSocket handshake verifies pairing token; phone commands queue into task engine.

---

### Task 20: Master EDITH CLI, Doctor Health Check & Daemon Entrypoint
- **Why:** Tie all subsystems together into a single unified binary/entrypoint with `doctor`, `run`, `ui`, and `status` commands.
- **Files:** `edith/main.py`, `edith/core/doctor.py`, `edith/tests/test_integration.py`
- **Dependencies:** Tasks 1-19
- **Test:** `python -m edith.main doctor` and `python -m unittest edith/tests/test_integration.py`
- **Done Condition:** Full vertical slice verified: `edith doctor` reports all subsystems healthy; `edith run "open chrome"` executes Level 0 reflex and updates state orb.
