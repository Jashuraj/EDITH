# EDITH Model Routing Specification

**Creator:** Jashwanth Raj  
**Runtime:** EDITH ModelRouter  

---

## 1. Routing Matrix

```mermaid
flowchart TD
    Prompt[User Input / Goal] --> ReflexCheck{Matches Level 0 Regex?}
    ReflexCheck -->|Yes| ReflexExec[Level 0: Instant Win32 & Tool Action <1ms]
    ReflexCheck -->|No| PolicyCheck{Privacy or Offline Mode?}
    
    PolicyCheck -->|Yes| LocalOllama[Level 3: Ollama Hermes 3B / Llama 3.2]
    PolicyCheck -->|No| CloudCheck{Cloud Available & Credits OK?}
    
    CloudCheck -->|Yes & High Complexity| CloudExec[Level 5: Gemini 3.8 Flash]
    CloudCheck -->|No / Failed| LocalOllama
```

---

## 2. Model Assignments

| Category | Primary Provider | Primary Model | Fallback Model |
|---|---|---|---|
| **Fast Reflex** | Deterministic / Local | Level 0 Regex | `tinydolphin:1.1b` |
| **Tool Calling / Agent** | Ollama | `hermes3:3b` | `llama3.2:1b` |
| **Vision & Screen** | Ollama | `qwen3-vl:2b` | Deterministic OCR |
| **Coding Intelligence** | Ollama | `hhao/qwen2.5-coder-tools:0.5b` | `deepseek-coder:latest` |
| **Deep Reasoning** | Cloud (Optional) | `gemini-2.5-flash` | `deepseek-r1:1.5b` |
