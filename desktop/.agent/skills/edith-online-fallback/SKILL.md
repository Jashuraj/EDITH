---
name: edith-online-fallback
description: Multi-provider free-tier online AI fallback management.
---

# EDITH Online Fallback

## Strategy
- Use configured free tiers from verified providers.
- Obey rate limits and handle HTTP 429 status codes cleanly.
- Never store API keys in source control.
- Automatically downgrade to Ollama when providers exhaust quota.
