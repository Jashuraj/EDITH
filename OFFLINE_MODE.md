# EDITH Offline & Zero-Credit Operational Protocol

**Invariants:**
1. Internet loss does not crash or freeze EDITH.
2. Zero API credits or 429 rate limits trip the circuit breaker and transfer workload directly to Ollama.
3. Local capabilities are fully self-sufficient:
   - Voice synthesis (Windows SAPI)
   - Speech detection
   - SQLite local state persistence
   - Windows desktop & process automation
   - Sandboxed workspace filesystem tooling
   - Local tool calling with Hermes 3B
   - Holographic Web HUD on localhost:8794
