# EDITH — Autonomous Local-First AI Operating System

**Developer / Creator:** Jashwanth Raj  
**Target Platform:** Windows 11 (Dell Latitude 5490, Intel Core i5-8350U, 8GB RAM)  
**Version:** 1.0.0  

---

## What is EDITH?

EDITH is an autonomous personal AI operating system inspired by JARVIS, EDITH, and ULTRON. Unlike web chatbots or cloud-only wrappers, EDITH is built local-first:
- Operates offline and survives zero cloud credits.
- Features sub-millisecond (<1ms) Level 0 deterministic reflexes.
- Integrates local Ollama models (`hermes3:3b`, `llama3.2:1b`, `qwen3-vl:2b`, `deepseek-coder`).
- Features a holographic 3D particle orb & glass stage adapted from ULTRON and barehands.
- Provides a persistent multi-step task engine with checkpoints and self-healing.
- Pairs securely with Android mobile devices over local Wi-Fi.

---

## Quick Start

### 1. Run Health Check (Doctor)
```powershell
python -m edith.main doctor
```

### 2. Execute Commands
Fast Level 0 deterministic reflex:
```powershell
python -m edith.main run "what is your status"
python -m edith.main run "show battery level"
python -m edith.main run "open chrome"
```

Local AI tool-calling via Hermes 3B:
```powershell
python -m edith.main run "list files in this directory"
```

### 3. Launch Holographic HUD & Phone Gateway
```powershell
python -m edith.main serve
```
- Holographic Web Stage: [http://127.0.0.1:8794](http://127.0.0.1:8794)
- Phone Gateway API: [http://127.0.0.1:8795](http://127.0.0.1:8795)

### 4. Run Automated Test Suite
```powershell
python -m unittest discover -s edith/tests -p "test_*.py"
```
48/48 tests passing across all subsystems.

---

## Architectural Principles

1. **EDITH is Not a Model:** Models are swappable providers. The core runtime governs security, memory, state, and tools.
2. **Offline & Zero-Credit Guarantee:** When internet drops or cloud credits hit 0, EDITH automatically falls back to local models without halting.
3. **Controlled Autonomy:** Every destructive action is guarded by risk classification, confirmation gates, and an immediate Emergency Stop.
4. **Hardware-First Optimization:** Tuned specifically for low RAM (8GB) and CPU-first execution.
