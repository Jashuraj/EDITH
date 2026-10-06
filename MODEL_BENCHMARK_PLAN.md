# EDITH Model Benchmark & Hierarchy Plan

## 1. Model Roles & Candidate Assignments

| Level | Role | Assigned Model | Parameters | VRAM/RAM Footprint | Expected Latency / TPS | Target Tasks |
|---|---|---|---|---|---|---|
| **Level 0** | Deterministic Reflex | None (Python / Regex / Native Win32) | 0 | <5 MB | <15 ms | App launch, volume, media, lock, battery status |
| **Level 1** | Fast Reflex AI | `tinydolphin:1.1b` or `llama3.2:1b` | 1.1B - 1.3B | ~1.2 GB | ~12 - 15 t/s (CPU) | Intent extraction, query classification, short confirmations |
| **Level 2** | Local General Assistant | `gemma3:1b` / `llama3.2:1b` | 1B - 1.3B | ~1.4 GB | ~10 - 14 t/s (CPU) | General conversational response, summarization, offline QA |
| **Level 3** | Local Agent & Tool Calling | `hermes3:3b` | 3.2B | ~2.5 GB | ~7.3 t/s (CPU) | Structured function calling, multi-step planning, bash/powershell synthesis |
| **Level 4** | Local Multimodal & Vision | `qwen3-vl:2b` | 2.2B | ~2.4 GB | ~5 - 8 t/s (CPU) | Screen reading, image/camera analysis, gesture intent confirmation |
| **Level 4** | Local Code Intelligence | `hhao/qwen2.5-coder-tools:0.5b` / `deepseek-coder:latest` | 0.5B - 1.3B | ~1.1 GB | ~15 - 20 t/s (CPU) | Syntax fixes, diff generation, script repair |
| **Level 5** | Cloud Reasoning | Gemini 3.8 Flash / Cloud Providers | Massive | 0 GB local | Network bound (~400 ms) | Complex architectural reasoning, open-web research when credits/network allow |

---

## 2. Benchmark Protocol

### Metrics
1. **Cold-load Latency:** Time to load model into RAM via Ollama `POST /api/generate` (`keep_alive=0`).
2. **Warm First-token Latency:** Time to first token when model is already warm (`keep_alive=5m`).
3. **Eval Throughput:** Tokens evaluated per second (`eval_count / eval_duration`).
4. **Tool Call Precision:** Percentage of synthetic JSON tool schemas parsed without formatting errors.
5. **Memory Overhead:** Total working set delta measured via Windows performance counters.

### Hardware Enforcement
- `OLLAMA_NUM_PARALLEL=1` to prevent CPU core starvation.
- Max loaded model limit = 1.
- Before loading `qwen3-vl:2b` for vision or `hermes3:3b` for agent tasks, unload idle models (`keep_alive=0`) if RAM headroom is under 2.5 GB.
