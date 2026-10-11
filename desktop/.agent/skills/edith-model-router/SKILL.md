---
name: edith-model-router
description: Dynamic LLM provider routing and fallback across local and cloud providers.
---

# EDITH Model Router

## Router Architecture
- Route inference via `edith/providers/router.py`.
- Select fastest and lowest-cost eligible provider.
- Handle failover automatically across Groq, Cerebras, OpenRouter, Gemini, and Mistral.
- Fall back to local Ollama on network loss or rate limits.
