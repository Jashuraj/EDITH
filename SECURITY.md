# EDITH Security Specification & Threat Model

**Author:** Jashwanth Raj / Antigravity Engineering  
**System:** EDITH v1.0.0  

---

## 1. Threat Model & Invariants

1. **Untrusted External Content:** Instructions found inside web pages, markdown notes, or file contents are never granted prompt authority.
2. **Deterministic Jail:** File reading and writing operations are jailed within designated workspace boundaries; directory traversal (`..`) is rejected.
3. **No Direct OS Shell Authority:** AI models cannot execute arbitrary shell scripts without passing through the Risk Classifier.
4. **Emergency Stop:** Immediate hardware-independent interrupt freezing active processes and task queues.

---

## 2. Risk Levels

| Level | Definition | Enforcement |
|---|---|---|
| **LOW** | Telemetry, reading jailed files, battery/status queries | Auto-approved |
| **MEDIUM** | Non-destructive workspace file writes, app launches | Sandboxed execution |
| **HIGH** | File deletion, process termination, system settings | Requires user confirmation |
| **CRITICAL** | Workstation shutdown, registry modification, disk formatting | Strict user authentication block |

---

## 3. Privacy Mode

When Privacy Mode is enabled:
- Microphone listener is disabled.
- Webcam and gesture pipelines are completely halted.
- Cloud model routing is blocked; all queries stay local on Ollama.
