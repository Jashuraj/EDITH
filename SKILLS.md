# EDITH Skill System & Extensibility

**Design:** Section 50 of the Engineering Constitution

---

## Skill Architecture

Skills are self-contained modular capabilities providing:
- Tool definitions
- Specialized prompts
- Permission requirements
- Validation hooks

Registered dynamically into EDITH Action Packs without recompilation.

---

## Registered Core & Extended Skills

1. `edith-core`: Master operating invariants, event bus, and core lifecycle.
2. `edith-terminal-control`: Safe Windows shell and terminal execution via PowerShell and CMD.
3. `edith-coding-agent`: Principal engineering standards, refactoring, and code generation.
4. `edith-computer-control`: Windows Win32 API management, application lifecycle, and desktop input.
5. `edith-project-context`: Repository indexing, persistent memory, and workspace state understanding.
6. `edith-verification`: Evidence-based verification, unit testing, and behavior confirmation.
7. `edith-model-router`: Dynamic LLM provider routing and fallback across local and cloud providers.
8. `edith-ollama`: Local Ollama runtime execution, context window management, and offline inference.
9. `edith-online-fallback`: Multi-provider free-tier online AI fallback management.
10. `edith-web-research`: Autonomous web querying, documentation reading, and fact verification.
11. `edith-git`: Git version control operations, atomic commits, and repository hygiene.
12. `edith-recovery`: Failure recovery, error diagnosis, and state rollback mechanisms.
13. `edith-remote-desktop`: Low-latency remote desktop streaming, RAT input dispatch, and touch coordinate translation.
14. `edith-gamestream`: Open-source Sunshine and Moonlight game streaming integration and management.
15. `edith-virtual-gamepad`: Mobile touch virtual gamepad, 360-degree analog joystick, and tactile key bindings.
16. `edith-vnc-portal`: Zero-dependency HTML5 canvas VNC web portal and browser desktop streaming.
17. `edith-holographic-gestures`: MediaPipe dual-hand holographic gesture engine and 3D Three.js HUD controls.
18. `edith-screen-vision`: Live desktop vision capture, active window localization, and contextual screen analysis.
19. `edith-voice-clap`: Acoustic double-clap wake detection, voice synthesis, and cross-browser audio fallback.
20. `edith-mobile-gateway`: Mobile LAN gateway, pinned static cloud tunnel, pairing token auth, and responsive UI.
21. `edith-command-guide`: Interactive tactical command guide drawer and quick-tap execution chips for mobile HUD.
22. `edith-telemetry-monitoring`: Glitch-free real-time system telemetry streaming and vitals monitoring.
23. `edith-asimov-guard`: Three Laws of Robotics compliance, safety sentinels, and high-risk action confirmation.
