# EDITH — ANTIGRAVITY MASTER BUILD / REPAIR PROMPT
## Mission: turn EDITH into a genuinely elite, offline-first Windows personal AI operating layer

You are not being asked to produce another superficial AI-assistant demo.

You are acting as the **principal architect, senior systems engineer, performance engineer, desktop-automation engineer, voice/vision engineer, security engineer, and UI/UX lead** responsible for taking the existing EDITH codebase to a production-quality state.

Think like an exceptional engineer operating at the highest practical level:
- diagnose root causes instead of patching symptoms;
- preserve working functionality;
- make architecture simpler where possible, not more complicated;
- use deterministic software for deterministic jobs;
- use AI only where intelligence is actually needed;
- design for failure, interruption, latency, CPU/RAM pressure, device loss, and model failure;
- verify behavior with real tests instead of claiming success because code compiles;
- do not waste context on repetitive explanations, obvious commentary, or unnecessary rewrites.

The output must be a **working EDITH**, not a beautiful prototype.

---

# 0. ABSOLUTE PRIORITY ORDER

Follow this priority order exactly:

1. **The existing EDITH codebase and its real runtime behavior**
2. **The uploaded EDITH goal/specification and user requirements**
3. **The concrete runtime logs and reproducible failures**
4. **Security, reliability, offline-first, performance, and user experience requirements in this prompt**
5. **Lessons/patterns from the reference repositories below**
6. General engineering knowledge

Do not let a reference repository override an EDITH-specific requirement.

Do not blindly copy another project's architecture.

Do not rewrite EDITH merely because another repository uses a different stack.

First understand what already exists, what is working, and what is broken.

---

# 1. OPERATING MODE: ELITE CODER, TOKEN-EFFICIENT EXECUTION

Work as an autonomous senior engineer.

## Do this

- Inspect the workspace before changing architecture.
- Map the actual runtime/data flow.
- Search the codebase surgically.
- Batch independent inspections.
- Trace bugs from UI/input -> backend -> state machine -> model/router -> tool -> OS -> response.
- Fix the smallest architectural layer that genuinely solves the problem.
- Prefer reusable abstractions over duplicated special cases.
- Add targeted diagnostics where the system currently lies, hangs, duplicates, or silently fails.
- Build or update tests around every repaired subsystem.
- Run the application and exercise real workflows.
- Re-test after every major subsystem change.
- Remove temporary debug code before finalizing.

## Do NOT do this

- Do not narrate every tiny action.
- Do not repeat the same diagnosis five times.
- Do not produce long explanations instead of code.
- Do not create fake "success" states.
- Do not hide exceptions.
- Do not add random dependencies just to look sophisticated.
- Do not add a cloud requirement to an offline feature.
- Do not make Ollama responsible for deterministic OS operations.
- Do not let an LLM directly invent arbitrary shell commands when a deterministic tool exists.
- Do not replace the entire application without evidence that the current architecture cannot be repaired.
- Do not stop after fixing only the first visible bug.

## Decision rule

Whenever you discover multiple ways to solve something, prefer:

**most reliable + lowest latency + lowest resource cost + easiest to test + easiest to recover**

over:

**most complicated + most futuristic + most dependent on an LLM**

---

# 2. FIRST: READ AND UNDERSTAND THE WHOLE PROJECT

Before making substantive code changes:

### 2.1 Inventory the project

Identify:

- entry points
- process topology
- Python/Node/Rust/etc. components
- UI layer
- API/server layer
- state machine
- voice input
- VAD
- speech-to-text
- text-to-speech
- model router
- Ollama integration
- tool registry
- Windows tools
- application launcher
- keyboard/mouse control
- camera/gesture subsystem
- image/background rendering
- emergency stop
- configuration
- logging
- persistence/memory
- startup/shutdown
- threading/process/async architecture

### 2.2 Build an internal architecture map

Do not merely inspect filenames.

Trace the real data path:

`microphone/camera/UI`
-> `input capture`
-> `preprocessing`
-> `intent/command`
-> `state machine`
-> `model/router`
-> `tool selection`
-> `OS/tool execution`
-> `result`
-> `response`
-> `TTS/UI`

Also map:

`camera frame`
-> `gesture detection`
-> `gesture normalization`
-> `action dispatch`
-> `OS action`
-> `UI feedback`

### 2.3 Establish a baseline

Before changing major code, reproduce and document:

- voice command flow
- double-clap flow
- microphone device selection
- opening Chrome
- opening another application
- mouse movement
- keyboard control
- one-hand gesture
- other-hand gesture
- two-hand gesture
- camera ON/OFF
- gesture ON/OFF
- background visibility
- Ollama request
- offline model fallback
- emergency stop
- startup/shutdown
- repeated/duplicate response behavior

Do not assume a failure is caused by the component whose name appears in the UI.

---

# 3. AUTHORITATIVE CURRENT FAILURE EVIDENCE

The runtime evidence shows several root-cause signals.

### 3.1 Clap detector is repeatedly self-triggering / over-triggering

The log repeatedly reports:

`DOUBLE CLAP DETECTED!`

followed by:

`EDITH Welcome Protocol activated by double-clap`

and immediately:

`EDITH Speaking: 'Welcome home...'`

Then another clap event interrupts speech and starts it again.

This is not acceptable behavior.

Treat this as an **audio feedback / detector state-management bug**, not merely a UI annoyance.

### 3.2 The gesture action path has a concrete exception

The runtime crashes here:

`edith.tools.mouse_controller.handle_gesture_action`

because:

`WindowsTools` has no attribute `perform_window_action`

Do not paper over this with `hasattr()` and silently do nothing.

Fix the contract between the gesture subsystem and Windows tool layer.

### 3.3 Volume/command events are being produced repeatedly

The logs show many repeated volume-control actions within short periods.

Treat this as a possible combination of:

- duplicate command submission;
- gesture event flooding;
- state-machine re-entry;
- retry without idempotency;
- continuous gesture mapped to discrete action;
- missing debounce/rate limit.

Trace which one actually occurs.

### 3.4 Online provider failure is falling back to local/deterministic tiers

The routing architecture already shows a layered fallback model.

Do not destroy that model.

Improve it.

When a cloud provider fails:

- local model should remain usable;
- deterministic tools should remain usable;
- OS commands must not fail merely because the LLM provider failed.

### Acceptance principle

A broken AI provider must never make deterministic features such as:

- opening Chrome,
- changing volume,
- moving the mouse,
- typing,
- opening Notepad,
- reading system state

unavailable.

---

# 4. NON-NEGOTIABLE PRODUCT GOAL

EDITH must become:

> **A fast, reliable, offline-first Windows personal AI assistant with voice, text, desktop control, gestures, visual feedback, local intelligence, optional online intelligence, and strong safety boundaries.**

The assistant should feel:

- immediate;
- calm;
- intelligent;
- visually polished;
- predictable;
- recoverable;
- beginner-friendly;
- powerful for advanced users;
- private by default.

EDITH should not behave like:

- a chat box wearing a sci-fi skin;
- an LLM that sometimes happens to press keys;
- an overloaded camera demo;
- a UI that lies about what is happening.

---

# 5. OFFLINE-FIRST ARCHITECTURE

This is a major requirement.

## Core principle

**EDITH must function without internet for all locally possible capabilities.**

Internet may enhance EDITH but must never be a mandatory dependency for:

- local UI;
- microphone;
- speech recognition using installed local engine/model;
- TTS using installed local engine/model;
- Ollama/local model inference;
- application launching;
- keyboard/mouse control;
- window management;
- volume/brightness where locally supported;
- camera;
- gestures;
- local files;
- local memory;
- local deterministic utilities.

## Runtime modes

Create an explicit capability model:

### OFFLINE
Everything available locally only.

### ONLINE-ENHANCED
Local features continue working; internet augments research, web tasks, remote providers, etc.

### DEGRADED
A dependency is unavailable, but EDITH keeps every unaffected subsystem functional.

Never make the entire state "broken" because one provider is unavailable.

---

# 6. MODEL ARCHITECTURE

Separate:

## Intelligence

Used for:

- natural-language understanding;
- ambiguous requests;
- planning;
- multi-step task reasoning;
- contextual conversation;
- summarization;
- selecting tools.

## Deterministic tools

Used for:

- launch application;
- close application;
- activate window;
- minimize/maximize;
- mute/unmute;
- volume;
- keyboard shortcuts;
- mouse movement/click;
- file operations;
- clipboard;
- screenshots;
- system information;
- timers;
- camera state;
- gesture configuration.

Do NOT ask the LLM to generate arbitrary system operations when a deterministic EDITH tool already exists.

---

# 7. OLLAMA / LOCAL MODEL DESIGN

Make the Ollama layer a **provider**, not the operating system controller.

Required behavior:

`Natural Language`
-> `intent/tool planning`
-> `validated tool call`
-> `deterministic execution`
-> `structured result`
-> `natural-language response`

If Ollama is unavailable:

- deterministic tools still work;
- fallback model/provider may be used;
- user gets an honest capability message only when intelligence is truly required.

If a model returns malformed tool arguments:

1. validate;
2. reject safely;
3. optionally repair once;
4. retry only when bounded;
5. never loop indefinitely.

Use explicit timeouts and cancellation.

A tool call must have:

- request ID;
- tool name;
- validated arguments;
- start time;
- completion/failure;
- result;
- cancellation support;
- user-visible status.

---

# 8. HERMES INTEGRATION / INSPIRATION

I use a local Hermes/Ollama setup.

Treat Hermes as an optional **agent/runtime inspiration or provider**, not as a hard dependency.

Study Hermes' current architecture for:

- skills;
- memory;
- tools;
- multi-surface agent design;
- local/remote model abstraction;
- interrupt-and-redirect behavior;
- provider switching;
- reusable skills.

Repository:

https://github.com/NousResearch/hermes-agent

Official documentation:

https://hermes-agent.nousresearch.com/docs/

Important:
- Do not replace EDITH with Hermes.
- Do not require WSL/Linux just to make EDITH work on Windows.
- If Hermes is integrated, isolate it behind an adapter.
- EDITH must remain functional if Hermes is not installed.

---

# 9. VOICE SYSTEM — FIX IT PROPERLY

The voice pipeline needs an explicit lifecycle.

Use states similar to:

`IDLE`
`ARMING`
`LISTENING`
`CAPTURING`
`TRANSCRIBING`
`UNDERSTANDING`
`EXECUTING`
`SPEAKING`
`CANCELLED`
`ERROR`

Never allow multiple active command sessions unless explicitly supported.

## 9.1 Microphone

Create a microphone manager that:

- enumerates devices;
- remembers the selected device;
- validates device availability;
- handles device disconnect/reconnect;
- exposes input level;
- reports sample rate;
- logs the chosen device;
- can switch devices without restarting the entire assistant.

## 9.2 VAD

Use proper voice activity detection rather than naive amplitude alone.

Reference:

https://github.com/snakers4/silero-vad

Optional transcription references:

https://github.com/SYSTRAN/faster-whisper

https://github.com/ggml-org/whisper.cpp

Whisper reference:

https://github.com/openai/whisper

Prefer a CPU-efficient local configuration on modest Windows hardware.

Do not continuously run an expensive transcription model when nobody is speaking.

## 9.3 Turn detection

EDITH must know:

- when the user started talking;
- when the user stopped;
- when the utterance is complete;
- when speech is only EDITH's own TTS;
- when speech is noise;
- when the user interrupts EDITH intentionally.

## 9.4 Prevent speaker-to-microphone feedback

This is critical.

When EDITH speaks:

- either suppress/dampen wake/clap/VAD detection appropriately;
- or use robust echo-aware gating;
- or suspend only the relevant trigger detector while TTS is active;
- preserve user barge-in using a separate controlled path.

Do NOT let EDITH's own voice repeatedly trigger its wake/clap mechanism.

## 9.5 Double-clap

Double-clap must have:

- minimum inter-clap interval;
- maximum inter-clap interval;
- amplitude validation;
- duration validation;
- noise floor adaptation;
- cooldown;
- one activation per event;
- no re-trigger while the protocol is already active;
- protection while TTS is emitting;
- reset after timeout;
- explicit disable switch.

Add a visible beginner control:

`Double Clap: ON`
`Double Clap: OFF`

and status:

`Listening for clap`

or:

`Paused while EDITH speaks`

---

# 10. RESPONSE DEDUPLICATION — ZERO DUPLICATE REFLEX

EDITH must never produce two responses for one user action.

Implement a single command lifecycle:

`INPUT_ID`
-> `COMMAND_ID`
-> `PLAN_ID`
-> `EXECUTION_ID`
-> `RESPONSE_ID`

Every event should be traceable.

Add idempotency.

For example, the same command arriving twice within an extremely short window should not execute twice unless the user deliberately repeated it.

Protect against:

- UI click + microphone trigger;
- clap + wake word;
- browser event duplicate;
- WebSocket retry;
- HTTP retry;
- gesture flooding;
- asynchronous race;
- provider retry creating duplicate execution;
- TTS callback causing command re-entry.

Use:

- command locks;
- event sequence numbers;
- debounce;
- deduplication windows;
- cancellation tokens;
- single-flight execution where appropriate.

Do NOT simply ignore all repeated commands.

A repeated user command after a legitimate interval must still work.

---

# 11. WINDOWS DESKTOP CONTROL — MAKE THIS ROBUST

EDITH must reliably control real Windows applications.

## 11.1 Application launching hierarchy

Create a deterministic launch strategy:

1. explicit executable/path if known;
2. registered Windows application / Start menu resolution;
3. shell launch;
4. known aliases;
5. browser URL handling;
6. controlled fallback.

Do not depend on an LLM inventing executable names.

Support examples:

- Chrome
- Edge
- Notepad
- Calculator
- File Explorer
- Settings
- Terminal
- common installed applications discovered from Windows.

## 11.2 Window management

Implement a real window service.

Capabilities:

- list visible windows;
- activate/focus;
- minimize;
- maximize;
- restore;
- move;
- resize;
- close;
- switch;
- identify foreground window.

Make this service available to:

- voice;
- text;
- gestures;
- UI buttons.

Fix the concrete `WindowsTools.perform_window_action` contract problem at the proper abstraction layer.

No fake compatibility wrapper that hides failure.

## 11.3 Preferred Windows UI automation

Study:

https://github.com/pywinauto/pywinauto

Use it where semantic UI automation is superior to raw coordinates.

Use accessibility/UI Automation when possible.

## 11.4 Raw mouse/keyboard fallback

Study:

https://github.com/asweigart/pyautogui

Use for:

- mouse movement;
- clicks;
- drag;
- keyboard shortcuts;
- typing;
- simple screen interactions.

But do not make raw coordinates the only automation strategy.

---

# 12. COMPUTER-USE / GUI AGENT REFERENCES

Study these for architecture and failure handling.

## UI-TARS

https://github.com/bytedance/UI-TARS

Focus on:

- desktop computer-use action vocabulary;
- grounding;
- coordinate handling;
- separation of perception and action;
- task-specific action templates.

Do not blindly add a huge vision model if the hardware cannot support it.

## OpenAI CUA sample app

https://github.com/openai/openai-cua-sample-app

Focus on:

- persistent worker model;
- request/event contracts;
- agent loop;
- desktop action verification;
- interruption/recovery;
- explicit caution that generated actions do not prove success.

Use the architectural ideas, not a cloud dependency.

## Browser Use

https://github.com/browser-use/browser-use

Use as reference for future browser-specific automation.

Keep browser automation separated from OS automation.

## Microsoft MagenticLite

https://github.com/microsoft/magentic-ui

Study:

- human-in-the-loop;
- approval boundaries;
- small-model-friendly agent architecture;
- browser/local-file workflows;
- safe execution boundaries.

Do not make it a mandatory runtime dependency.

---

# 13. OPENJARVIS — PRIMARY ARCHITECTURE REFERENCE

Study deeply:

https://github.com/open-jarvis/OpenJarvis

Documentation:

https://open-jarvis.github.io/OpenJarvis/

Use it as a major reference for:

- local-first architecture;
- provider abstraction;
- agents;
- skills;
- local model operation;
- desktop GUI;
- structured tools;
- research;
- persistent state;
- efficient local execution.

OpenJarvis is currently positioned as local-first personal AI and exposes Windows + desktop GUI paths, so it is highly relevant.

Do NOT fork it wholesale.

Do NOT turn EDITH into OpenJarvis.

Borrow architectural principles only where they clearly improve EDITH.

---

# 14. LEON — MEMORY / SKILLS / TOOLS REFERENCE

Study:

https://github.com/leon-ai/leon

Focus on:

- skills -> actions -> tools -> functions;
- memory separation;
- practical assistant architecture;
- local/remote provider separation;
- deterministic execution;
- modular extensibility.

Do not import unnecessary complexity.

---

# 15. ULTRON — UX / VOICE / ASSISTANT EXPERIENCE REFERENCE

Study:

https://github.com/SAGAR-TAMANG/ultron-by-sagar-builds

Use it for:

- assistant presentation;
- voice-first interaction;
- visual command center ideas;
- startup experience;
- user feedback patterns.

But review current issues/PRs as well.

Do not assume every pattern is correct merely because it exists.

---

# 16. BAREHANDS — GESTURE / HOLOGRAPHIC UI REFERENCE

Study:

https://github.com/jaredrhod/barehands

It is especially useful for:

- hand-tracked UI concepts;
- gesture vocabulary;
- two-hand interaction;
- visual state feedback;
- camera + UI composition;
- beginner gesture teaching;
- interaction models.

Read:

- README
- `barehands.md`
- `TROUBLESHOOTING.md`
- server/action architecture

Important licensing constraint:

barehands is AGPL-3.0-or-later.

Therefore:

**Do not copy its source into EDITH blindly.**

You may study architectural ideas. If any code is reused, comply with its license and preserve required notices/source obligations.

If EDITH is intended to remain closed-source, prefer implementing an independent equivalent or using permissively licensed components.

---

# 17. JARVIS VOICE ASSISTANT — HIGH-VALUE UX REFERENCE

Study:

https://github.com/sunkarakrwutarth9-ai/jarvis-voice-assistant

Specifically inspect its Windows voice interaction, command examples, command-center presentation, browser launching, system controls, gestures, and visual interaction.

The repository demonstrates user-facing patterns such as:

- opening Chrome by voice;
- system controls;
- live visual output;
- gestures;
- voice-driven desktop workflows.

Treat it as a reference, not as an authority.

---

# 18. VOICE / TTS REFERENCE STACK

### Faster Whisper

https://github.com/SYSTRAN/faster-whisper

Study for efficient local transcription.

### Whisper.cpp

https://github.com/ggml-org/whisper.cpp

Study for lightweight native/local inference options.

### Silero VAD

https://github.com/snakers4/silero-vad

Study for VAD and voice activity boundaries.

### Piper

https://github.com/rhasspy/piper

Study for fast local neural TTS.

Note:
The original rhasspy/piper repository states development has moved to:
https://github.com/OHF-Voice/piper1-gpl

Verify the current upstream and current license before adopting it.

---

# 19. CAMERA / GESTURE SYSTEM — TWO HANDS, ZERO FREEZING

## 19.1 Fix one-hand-only behavior

The current system must support both left and right hands.

Do not hard-code a single hand.

Use per-hand identity / handedness.

Support:

- left hand only;
- right hand only;
- both hands;
- one hand entering/leaving frame;
- two hands appearing simultaneously;
- one hand temporarily occluding another;
- hand crossing.

All gesture state must be associated with a `hand_id` / handedness identity.

Do not let the disappearance of one hand invalidate the other.

## 19.2 Gesture abstraction

Create a normalized gesture system.

Example:

```text
GestureEvent {
  id
  hand
  gesture
  confidence
  x
  y
  dx
  dy
  scale
  velocity
  phase
  timestamp
}
```

Gesture phases:

- `START`
- `UPDATE`
- `END`

Do not execute discrete system actions every camera frame.

For example:

Bad:
`thumbs_up -> volume_up -> volume_up -> volume_up ...`

Better:
`gesture START -> one logical action`
with controlled repeat behavior only when intentionally designed.

## 19.3 Beginner-friendly gesture guide

The UI must contain a built-in guide.

Show:

- gesture image/animation;
- hand orientation;
- what to do;
- what EDITH interprets it as;
- confidence indicator;
- common mistakes;
- examples;
- sensitivity/tuning controls.

Include a dedicated:

`Gesture Tutorial`

and:

`Practice Mode`

Practice Mode should show:

- detected hand;
- handedness;
- landmarks;
- current gesture;
- confidence;
- action preview;

without executing dangerous OS actions.

Example:

> Right hand detected — Pinch  
> Action preview: Move cursor  
> Confidence: 94%

---

# 20. CAMERA PERFORMANCE — CAMERA MUST NOT MAKE THE ENTIRE PC SLOW

This is non-negotiable.

Do not let camera inference run at maximum resolution and maximum frequency on the UI/event loop.

Separate:

### Camera capture
Thread/process/async worker.

### Vision inference
Dedicated worker.

### Gesture state
Lightweight event processor.

### UI rendering
Independent.

### OS action execution
Independent.

Use:

- frame skipping;
- bounded queues;
- lower inference resolution;
- capped inference FPS;
- adaptive FPS;
- ROI/cropping where possible;
- throttled UI updates;
- background workers;
- inference only while gesture mode is enabled;
- immediate release of camera resources when disabled.

If the system is under load:

- drop frames;
- never block the UI.

Target behavior:

### Gesture OFF
Camera resources released.

### Gesture ON, idle
Low-cost tracking.

### Active gesture
Higher temporary inference rate.

### No hand visible
Low-power mode.

### System CPU/RAM pressure
Automatically degrade inference quality rather than freezing EDITH.

Expose:

- camera FPS;
- inference FPS;
- processing latency;
- CPU;
- RAM;

inside advanced diagnostics only.

---

# 21. MEDIAPIPE REFERENCE

Study:

https://github.com/google-ai-edge/mediapipe

Use it as a reference for efficient on-device perception and hand tracking.

If MediaPipe is used:

- do not run expensive pipelines unnecessarily;
- use the smallest appropriate model/task;
- separate camera capture and rendering;
- handle initialization failures cleanly;
- release resources reliably.

Be aware of its current privacy/metrics behavior and document any relevant dependency behavior in EDITH's dependency notes.

---

# 22. BACKGROUND / HOLOGRAPHIC UI

Current background behavior is unacceptable if the image exists but is effectively invisible.

Requirements:

- actual visible base image;
- controlled blur layer;
- controlled opacity;
- readable foreground;
- no accidental global blur;
- no heavy CSS filter over the whole scene;
- preserve image detail;
- smooth pan/zoom/pinch without turning the image into a translucent smear;
- GPU-friendly rendering where available.

Create explicit layers:

```text
Background Image
    ↓
Optional Blur Overlay
    ↓
Dark/Light Readability Overlay
    ↓
Holographic UI
    ↓
Interaction Layer
```

Do not apply blur to the entire application container when only the background should blur.

For pinch:

- zoom around pinch centroid;
- maintain stable focal point;
- clamp scale;
- avoid jitter;
- avoid runaway transforms;
- support reset.

Add:

- `Reset View`
- `Fit Background`
- `Background Opacity`
- `Background Blur`
- `Motion Effects`

Keep the default visually polished and readable.

---

# 23. UI/UX — STOP MAKING IT LOOK LIKE A DEVELOPER CONSOLE

EDITH's interface must be comprehensible to a beginner.

## Visual principles

- clean hierarchy;
- large primary action;
- minimal clutter;
- strong state indication;
- high readability;
- deliberate motion;
- consistent spacing;
- no meaningless animated noise;
- no random sci-fi decoration;
- no excessive glowing borders;
- no tiny status text for critical states.

## Main interaction should answer instantly

The user should always know:

1. Is EDITH listening?
2. Did EDITH hear me?
3. What did EDITH understand?
4. Is EDITH thinking?
5. Is EDITH executing something?
6. What action is happening?
7. Did it succeed?
8. If it failed, what can I do next?

Do not show:

`ANALYZE`

forever.

Show meaningful states such as:

`Listening`
`Heard: "Open Chrome"`
`Understanding`
`Opening Chrome`
`Done`

or:

`Could not open Chrome`
`Reason: Chrome was not found`
`Fix: Choose Chrome path`

---

# 24. UI INFORMATION ARCHITECTURE

Design a simple top-level layout.

Recommended concept:

### CENTER
EDITH visual identity / avatar / state orb.

### PRIMARY COMMAND
Large microphone / speak button.

### STATUS
One-line state.

### QUICK ACTIONS
Examples:

- Open Chrome
- Volume
- Screenshot
- Lock PC
- Files
- Camera/Gesture

### SECONDARY
Conversation/history, tools, system status.

### ADVANCED
Diagnostics, model routing, performance, device selection.

Do not expose every setting on the first screen.

---

# 25. BEGINNER + POWER USER MODES

## Beginner mode

Show only:

- microphone;
- command box;
- camera/gesture toggle;
- simple actions;
- short explanation;
- help/guide.

## Advanced mode

Expose:

- model;
- provider;
- microphone;
- VAD;
- gesture thresholds;
- inference FPS;
- camera resolution;
- automation backend;
- logs;
- debug overlay;
- performance metrics.

Do not force beginners to understand these concepts.

---

# 26. SAFETY / COMPUTER-CONTROL BOUNDARIES

OS automation is powerful.

Create explicit risk tiers.

### Low risk
- open application;
- focus window;
- volume;
- media controls.

### Medium risk
- type into application;
- move files;
- modify settings;
- close applications.

### High risk
- delete files;
- execute arbitrary shell commands;
- install software;
- modify security settings;
- send messages externally;
- perform financial or irreversible actions.

High-risk operations require confirmation.

Never let "AI confidence" equal "permission".

---

# 27. EMERGENCY STOP

Emergency stop must immediately halt:

- mouse control;
- keyboard automation;
- gesture actions;
- queued high-risk actions;
- TTS if needed;
- autonomous loops.

It must return the system to a safe idle state.

Every long-running worker must honor cancellation.

Test emergency stop during:

- gesture execution;
- keyboard typing;
- application launch;
- agent loop;
- TTS;
- browser automation.

---

# 28. SECURITY

Perform a real security audit.

Check:

- local server binding;
- remote/LAN access;
- tunnel exposure;
- unauthenticated endpoints;
- command injection;
- shell injection;
- path traversal;
- unsafe subprocess calls;
- arbitrary URL opening;
- untrusted tool arguments;
- model-generated shell commands;
- log leakage;
- secrets in logs;
- clipboard exposure;
- camera/microphone handling;
- file permissions;
- CSRF-like browser actions if applicable;
- WebSocket authentication;
- unauthorized remote automation.

Default local services to loopback unless remote access is explicitly enabled.

Do not keep cloud tunnels automatically enabled in the default offline build.

---

# 29. STATE MACHINE

Audit the state machine.

It should enforce legal transitions.

Example:

```text
BOOTING
  ↓
READY
  ↓
LISTENING
  ↓
CAPTURING
  ↓
UNDERSTANDING
  ↓
EXECUTING
  ↓
RESPONDING
  ↓
READY
```

Valid interrupts:

```text
ANY ACTIVE STATE -> CANCELLED
ANY ACTIVE STATE -> EMERGENCY_STOP
```

Invalid transitions should be rejected and logged.

No duplicate transitions from competing threads.

Use a single source of truth for assistant state.

---

# 30. OBSERVABILITY

Every request should have a correlation ID.

Example:

```text
REQ-20261007-000142
```

Log:

- input source;
- user command;
- transcription;
- selected intent;
- model/provider;
- tool;
- arguments after validation;
- start/end;
- duration;
- result;
- error;
- retry count;
- cancellation;
- final response.

Never log:

- API keys;
- passwords;
- tokens;
- full sensitive file contents.

Create a developer diagnostics screen that can show the execution timeline without exposing secrets.

---

# 31. PERFORMANCE BUDGET

Treat performance like a feature.

Track:

- UI FPS;
- gesture inference FPS;
- microphone latency;
- transcription latency;
- model latency;
- tool latency;
- TTS latency;
- startup time;
- RAM;
- CPU;
- camera overhead.

Do not optimize blindly.

Measure.

Prefer:

- lazy initialization;
- lazy model loading;
- worker pools;
- bounded queues;
- caching where safe;
- frame skipping;
- model quantization where appropriate;
- short-lived resources when idle.

The camera/gesture subsystem must be isolated from the main interaction loop.

---

# 32. MEMORY / CONTEXT DESIGN

Do not dump massive conversation history into every model request.

Separate:

- current turn;
- short-term context;
- durable memory;
- task state;
- tool results;
- system configuration.

Use summaries/checkpoints when needed.

Never let memory growth silently make every request slower.

Study OpenJarvis and Hermes for useful patterns, but keep the implementation proportional to EDITH.

---

# 33. SKILLS / TOOLS

Design tools as small deterministic modules.

Example registry:

```text
windows.open_app
windows.close_app
windows.focus_window
windows.window_action
windows.volume
windows.keyboard
windows.mouse
windows.clipboard

browser.open
browser.search

camera.start
camera.stop
camera.status

gesture.enable
gesture.disable
gesture.calibrate

system.status
system.screenshot

files.open
files.search
files.copy
files.move
```

Each tool should have:

- schema;
- validator;
- permission tier;
- timeout;
- cancellation;
- structured result;
- error category.

---

# 34. TESTING REQUIREMENTS

Do not finish until the following are tested.

## Voice

- [ ] microphone can be selected
- [ ] microphone can reconnect
- [ ] normal command transcribes
- [ ] silence does not create fake commands
- [ ] EDITH speech does not trigger clap/wake loop
- [ ] double clap triggers once
- [ ] double clap cooldown works
- [ ] barge-in works intentionally
- [ ] duplicate responses do not occur

## OS control

- [ ] open Chrome
- [ ] open Edge
- [ ] open Notepad
- [ ] activate a window
- [ ] minimize
- [ ] maximize
- [ ] close
- [ ] type text
- [ ] move mouse
- [ ] click
- [ ] volume up
- [ ] volume down
- [ ] mute/unmute

## Gesture

- [ ] left hand detected
- [ ] right hand detected
- [ ] both hands detected
- [ ] hand enters frame
- [ ] hand leaves frame
- [ ] pinch
- [ ] drag
- [ ] two-hand scale
- [ ] no action flood
- [ ] practice mode
- [ ] gesture guide

## Performance

- [ ] camera OFF returns CPU/RAM to normal
- [ ] gesture OFF releases resources
- [ ] camera ON does not freeze UI
- [ ] dropped frames do not freeze the system
- [ ] no unbounded queue growth

## Reliability

- [ ] Ollama unavailable
- [ ] cloud provider unavailable
- [ ] microphone unavailable
- [ ] camera unavailable
- [ ] Chrome unavailable
- [ ] automation backend exception
- [ ] TTS exception
- [ ] model timeout
- [ ] emergency stop during action

## Offline

After disabling network:

- [ ] UI starts
- [ ] local model works if installed
- [ ] microphone works
- [ ] TTS works if local TTS is installed
- [ ] OS tools work
- [ ] camera/gesture works
- [ ] no mandatory network calls are made
- [ ] failures degrade gracefully

---

# 35. REPOSITORY RESEARCH PROTOCOL

You are expected to inspect the reference repositories, but **do not clone everything blindly**.

For each repository:

1. read README;
2. inspect architecture;
3. inspect the specific subsystem relevant to EDITH;
4. extract 3–10 concrete design patterns;
5. compare them with the existing EDITH architecture;
6. adopt only improvements with measurable value.

Create an internal comparison table:

| Reference | What EDITH can learn | What NOT to copy |
|---|---|---|
| OpenJarvis | local-first agents, skills, tools, desktop architecture | wholesale rewrite |
| Hermes | skills, memory, agent workflows, provider abstraction | Linux/WSL-only assumptions |
| Open Interpreter | tool execution, computer use, agent loop, portability | turning EDITH into a coding agent |
| UI-TARS | GUI grounding/action abstraction | unnecessarily huge vision model |
| MagenticLite | approval/safety + compact agents | cloud/VM dependency |
| barehands | gesture UX and hand interaction | AGPL source copying |
| Ultron | cinematic assistant UX and voice flows | superficial effects |
| Jarvis Voice Assistant | Windows voice UX and system commands | blindly copying implementation |
| Leon | skills/actions/tools/memory | excess platform complexity |
| pywinauto | semantic Windows UI automation | none; use directly where appropriate |
| PyAutoGUI | deterministic input fallback | coordinate-only automation |
| MediaPipe | efficient on-device vision | always-on expensive inference |
| faster-whisper | efficient local STT | unnecessary huge models |
| Silero VAD | voice boundary detection | amplitude-only microphone logic |
| Piper | local TTS | obsolete upstream assumptions |
| Ollama | local model lifecycle | using LLM for deterministic OS control |
| Browser Use | browser-specific task automation | coupling browser automation to all OS control |
| MCP Servers | tool protocol ideas | adding networked tools unnecessarily |
| OpenAI CUA samples | persistent workers, verification, interruption | cloud dependence |

---

# 36. LICENSE / COPYRIGHT RULE

Before importing code from any external repository:

1. inspect its current license;
2. record it;
3. decide whether it is safe to copy, adapt, or only use as inspiration;
4. do not paste AGPL/GPL code into a closed-source EDITH implementation unless the licensing requirements are intentionally accepted and satisfied;
5. retain required notices where required;
6. prefer independently implemented ideas when licensing is undesirable.

Reference repositories are for engineering intelligence, not for code plagiarism.

---

# 37. IMPORTANT CURRENT REFERENCES

## Primary

OpenJarvis:
https://github.com/open-jarvis/OpenJarvis

Hermes Agent:
https://github.com/NousResearch/hermes-agent

Open Interpreter:
https://github.com/OpenInterpreter/open-interpreter

UI-TARS:
https://github.com/bytedance/UI-TARS

MagenticLite:
https://github.com/microsoft/magentic-ui

## Voice

Faster Whisper:
https://github.com/SYSTRAN/faster-whisper

Whisper.cpp:
https://github.com/ggml-org/whisper.cpp

Whisper:
https://github.com/openai/whisper

Silero VAD:
https://github.com/snakers4/silero-vad

Piper:
https://github.com/rhasspy/piper

Current Piper upstream indicated by repository:
https://github.com/OHF-Voice/piper1-gpl

## Desktop automation

pywinauto:
https://github.com/pywinauto/pywinauto

PyAutoGUI:
https://github.com/asweigart/pyautogui

WinAppDriver:
https://github.com/microsoft/WinAppDriver

## Computer use / browser

OpenAI CUA sample:
https://github.com/openai/openai-cua-sample-app

Browser Use:
https://github.com/browser-use/browser-use

## Gesture / vision

MediaPipe:
https://github.com/google-ai-edge/mediapipe

barehands:
https://github.com/jaredrhod/barehands

## Assistant UX

Ultron:
https://github.com/SAGAR-TAMANG/ultron-by-sagar-builds

JARVIS Voice Assistant:
https://github.com/sunkarakrwutarth9-ai/jarvis-voice-assistant

Leon:
https://github.com/leon-ai/leon

## Local model runtime

Ollama:
https://github.com/Ollama/ollama

## Tool protocol

Model Context Protocol servers:
https://github.com/modelcontextprotocol/servers

---

# 38. DO NOT OVERENGINEER

The goal is not to make EDITH contain every AI framework on GitHub.

The goal is to make EDITH **better than its current implementation**.

Do not add a dependency just because it is popular.

Before introducing any dependency, answer internally:

- What problem does it solve?
- Why can't current EDITH solve it?
- What is the runtime cost?
- Is it offline?
- Is it stable?
- Is it licensed appropriately?
- Can it be removed later?
- Does it improve measurable behavior?

If the answer is weak, do not add it.

---

# 39. UI QUALITY BAR

The finished interface should feel closer to a polished commercial desktop assistant than a GitHub demo.

Use:

- restrained motion;
- smooth transitions;
- coherent typography;
- clear iconography;
- strong contrast;
- responsive controls;
- sensible empty states;
- useful loading states;
- meaningful error states;
- graceful disabled states.

Every animation must serve a purpose.

Do not use "more effects" as a substitute for good design.

---

# 40. ERROR UX

Never show raw stack traces to normal users.

Instead:

### User view

> I couldn't open Chrome.  
> Chrome was not found on this PC.  
> [Choose Chrome] [Try Again]

### Developer view

Show:

- exception;
- subsystem;
- correlation ID;
- stack trace;
- environment;
- tool arguments;
- recovery path.

---

# 41. SELF-DIAGNOSTICS

Add a first-class EDITH diagnostics system.

Example:

```text
EDITH SYSTEM CHECK

Voice input        ✓
VAD                ✓
STT                ✓
TTS                ✓
Ollama             ✓
Windows automation ✓
Camera             ✓
Gesture engine     ✓
UI server          ✓
Emergency stop     ✓
Offline mode       ✓
```

Clicking an item should provide:

- current status;
- detected device;
- model;
- latency;
- troubleshooting steps.

This replaces guesswork.

---

# 42. ONBOARDING / FIRST-RUN EXPERIENCE

A beginner should be able to launch EDITH and understand it within minutes.

First run:

1. microphone test;
2. speaker test;
3. optional camera test;
4. local model detection;
5. automation permission check;
6. gesture calibration;
7. simple tutorial;
8. test command.

Do not ask the user to understand technical configuration before the basic assistant works.

---

# 43. GESTURE GUIDE CONTENT

The guide should explain concepts in plain language.

Example:

### Move pointer
`Point with one hand and pinch.`

### Click
`Pinch quickly.`

### Drag
`Pinch and move.`

### Two-hand zoom
`Pinch with both hands and move them apart/together.`

### Pause gestures
`Open the gesture control and switch Gesture Mode OFF.`

Include a visible live preview.

---

# 44. CAMERA PRIVACY

When camera is inactive:

- release camera;
- stop inference worker;
- clear frame buffers.

Show camera status.

Never secretly keep the camera active after the user disables it.

Same principle for microphone.

---

# 45. NETWORK / LOCAL SERVICES

Local services should default to:

`127.0.0.1`

Only bind to LAN interfaces when explicitly enabled.

If remote/mobile access exists:

- require explicit opt-in;
- show listening address;
- show authentication status;
- include a disable button;
- avoid automatic public tunnels.

Offline mode must disable network-dependent routes cleanly.

---

# 46. IMPLEMENTATION STRATEGY

Use this order:

## Phase A — Diagnose

- map architecture;
- reproduce failures;
- identify root causes;
- establish baseline.

## Phase B — Stabilize

Fix:

1. duplicated command execution;
2. clap recursion;
3. state-machine race;
4. missing Windows tool contract;
5. application launching;
6. Ollama boundary;
7. gesture event flooding.

## Phase C — Voice

- microphone manager;
- VAD;
- STT;
- turn detection;
- barge-in;
- TTS suppression/echo handling.

## Phase D — Desktop control

- deterministic Windows tools;
- window management;
- application launch;
- keyboard/mouse;
- structured results.

## Phase E — Gesture

- two-hand tracking;
- normalized gestures;
- event phases;
- calibration;
- beginner guide;
- practice mode.

## Phase F — Performance

- camera worker;
- frame dropping;
- adaptive inference;
- queue bounds;
- memory/CPU profiling.

## Phase G — UI/UX

- state clarity;
- clean visual hierarchy;
- background/holographic scene;
- diagnostics;
- onboarding;
- error states;
- accessibility.

## Phase H — Offline

- disable network;
- prove local functionality;
- clean provider fallbacks.

## Phase I — Security

- local binding;
- authorization;
- command validation;
- high-risk approval;
- secret handling.

## Phase J — Verification

- unit;
- integration;
- functional;
- performance;
- manual;
- failure injection.

---

# 47. CHANGE CONTROL

Do not silently delete a feature.

If a feature is broken:

- repair it;
- replace it with a strictly superior compatible implementation;
- or isolate it behind a feature flag.

Preserve public APIs where practical.

Avoid gratuitous file churn.

Avoid massive formatting changes.

Make the diff understandable.

---

# 48. WHAT "DONE" MEANS

The task is NOT complete when:

- the code runs;
- the UI opens;
- a screenshot looks good;
- a single voice command works.

It is complete when:

### Voice
A user can speak naturally and receive exactly one response.

### Desktop
A user can say:
- "Open Chrome"
- "Open Notepad"
- "Switch to Chrome"
- "Increase volume"

and EDITH actually performs the action.

### Gesture
A user can use either hand and both hands without the entire PC becoming sluggish.

### Camera
Camera/gesture mode can be enabled and disabled repeatedly without resource leakage.

### Offline
Core EDITH works with no internet.

### AI failure
Ollama failure does not break deterministic desktop controls.

### UI
The interface clearly communicates what EDITH is doing.

### Security
Dangerous actions cannot happen accidentally.

### Recovery
Failures are visible, diagnosable, and recoverable.

---

# 49. FINAL VERIFICATION COMMAND

At the end, do not merely say "tests passed".

Produce a compact verification report:

```text
EDITH FINAL VERIFICATION

VOICE
✓ microphone
✓ VAD
✓ STT
✓ duplicate prevention
✓ clap protection
✓ barge-in

DESKTOP
✓ launch
✓ windows
✓ keyboard
✓ mouse
✓ volume

GESTURES
✓ left hand
✓ right hand
✓ two hands
✓ calibration
✓ event debounce

PERFORMANCE
✓ camera isolation
✓ CPU measured
✓ RAM measured
✓ UI remains responsive

OFFLINE
✓ no-network boot
✓ local model
✓ local tools

SECURITY
✓ local binding
✓ dangerous action approval
✓ secrets protected

UI/UX
✓ onboarding
✓ beginner guide
✓ diagnostics
✓ error states
✓ background rendering

REGRESSIONS
✓ existing features re-tested
```

For anything not passing, state:

- exact blocker;
- why it remains;
- what has already been attempted;
- what user-side prerequisite is genuinely required.

Do not hide unfinished work.

---

# 50. FINAL EXECUTION COMMAND TO ANTIGRAVITY

Now begin.

Do not spend the first part of the session writing a giant essay.

Use the workspace.

Inspect the actual EDITH project.

Read the authoritative goal/specification.

Inspect current logs and reproduce the failures.

Study the relevant reference repositories.

Build a dependency/architecture map.

Then fix the system from the root.

Prioritize correctness over cosmetic shortcuts.

Prioritize measured performance over assumptions.

Prioritize deterministic tools over LLM guessing.

Prioritize offline operation over cloud convenience.

Prioritize user clarity over visual noise.

Prioritize recoverability over fragile "happy path" demos.

**Do not stop after one fix.**

**Do not declare success until the acceptance tests are actually exercised.**

**Do not optimize for the appearance of progress. Optimize for EDITH being genuinely reliable.**

The final target is not "EDITH with more features."

The target is:

> **EDITH as a coherent, offline-first, voice + desktop + gesture AI operating layer that is fast enough for everyday Windows use, understandable by a beginner, powerful enough for advanced automation, and engineered so that one broken subsystem does not collapse the rest of the assistant.**
