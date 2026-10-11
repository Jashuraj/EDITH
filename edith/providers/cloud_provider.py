"""Multi-Provider Cloud AI Engine for EDITH.

Implements direct OpenAI-compatible API integration across:
- Google Gemini
- Groq
- OpenAI
- OpenRouter
- OmniRoute / Local Gateway

Enables user-configured API keys to execute high-speed reasoning, coding, and tool execution.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from edith.providers.base import (
    LLMProvider,
    ModelResponse,
    ProviderUnavailableError,
    ToolCall,
)

logger = logging.getLogger("edith.providers.cloud")

LLM_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".llm.env"

PROVIDER_METADATA: Dict[str, Dict[str, str]] = {
    "gemini": {
        "name": "Google Gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-2.5-flash",
        "key_env": "GEMINI_API_KEY",
        "doc_url": "https://aistudio.google.com/apikey",
    },
    "groq": {
        "name": "Groq",
        "url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "key_env": "GROQ_API_KEY",
        "doc_url": "https://console.groq.com/keys",
    },
    "openai": {
        "name": "OpenAI",
        "url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "key_env": "OPENAI_API_KEY",
        "doc_url": "https://platform.openai.com/api-keys",
    },
    "openrouter": {
        "name": "OpenRouter",
        "url": "https://openrouter.ai/api/v1",
        "default_model": "openai/gpt-4o-mini",
        "key_env": "OPENROUTER_API_KEY",
        "doc_url": "https://openrouter.ai/settings/keys",
    },
    "gateway": {
        "name": "OmniRoute / local gateway",
        "url": "http://127.0.0.1:8000/v1",
        "default_model": "auto",
        "key_env": "OMNIROUTE_API_KEY",
        "doc_url": "",
    },
}


class UniversalCloudProvider(LLMProvider):
    """Direct, multi-provider cloud caller with unified OpenAI format."""

    def __init__(self):
        super().__init__(name="cloud_ai", is_local=False)
        self.active_provider: str = "auto"
        self.keys: Dict[str, str] = {}
        self.models: Dict[str, str] = {}
        self.gateway_url: str = "http://127.0.0.1:8000/v1"
        self.reload_config()

    def reload_config(self) -> None:
        """Load API keys from .llm.env and environment variables."""
        # 1. Environment variables
        for pid, meta in PROVIDER_METADATA.items():
            k = os.environ.get(meta["key_env"], "").strip()
            if k:
                self.keys[pid] = k
        if os.environ.get("GOOGLE_API_KEY"):
            self.keys["gemini"] = os.environ.get("GOOGLE_API_KEY", "").strip()
        if os.environ.get("OMNIROUTE_BASE_URL"):
            self.gateway_url = os.environ.get("OMNIROUTE_BASE_URL", "").strip()

        # 2. .llm.env file
        if LLM_ENV_FILE.is_file():
            try:
                for line in LLM_ENV_FILE.read_text(encoding="utf-8").splitlines():
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#") or "=" not in stripped:
                        continue
                    k, v = stripped.split("=", 1)
                    k = k.strip().upper()
                    v = v.strip().strip("'\"")
                    if k in ("GEMINI_API_KEY", "GOOGLE_API_KEY") and v:
                        self.keys["gemini"] = v
                    elif k == "GROQ_API_KEY" and v:
                        self.keys["groq"] = v
                    elif k == "OPENAI_API_KEY" and v:
                        self.keys["openai"] = v
                    elif k == "OPENROUTER_API_KEY" and v:
                        self.keys["openrouter"] = v
                    elif k == "OMNIROUTE_API_KEY" and v:
                        self.keys["gateway"] = v
                    elif k == "OMNIROUTE_BASE_URL" and v:
                        self.gateway_url = v
                    elif k == "ACTIVE_AI_PROVIDER" and v:
                        self.active_provider = v.lower()
                    elif k.endswith("_MODEL") and v:
                        prefix = k.replace("_MODEL", "").lower()
                        if prefix in PROVIDER_METADATA:
                            self.models[prefix] = v
            except Exception as ex:
                logger.debug("Error reading .llm.env: %s", ex)

        logger.info(
            "Cloud AI configured with keys for: %s (Active: %s)",
            [k for k, v in self.keys.items() if v],
            self.active_provider,
        )

    def save_provider_config(
        self,
        provider: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Persist API keys and active provider selection."""
        p_clean = provider.strip().lower()
        if api_key is not None and p_clean in PROVIDER_METADATA:
            self.keys[p_clean] = api_key.strip()
        if model is not None and p_clean in PROVIDER_METADATA:
            self.models[p_clean] = model.strip()
        if base_url is not None and p_clean == "gateway":
            self.gateway_url = base_url.strip()
        if p_clean in ("auto", "local") or p_clean in PROVIDER_METADATA:
            self.active_provider = p_clean

        # Write to .llm.env
        lines = [
            "# E.D.I.T.H. LLM Configuration Environment",
            f"ACTIVE_AI_PROVIDER={self.active_provider}",
        ]
        if "gemini" in self.keys and self.keys["gemini"]:
            lines.append(f"GEMINI_API_KEY={self.keys['gemini']}")
        if "groq" in self.keys and self.keys["groq"]:
            lines.append(f"GROQ_API_KEY={self.keys['groq']}")
        if "openai" in self.keys and self.keys["openai"]:
            lines.append(f"OPENAI_API_KEY={self.keys['openai']}")
        if "openrouter" in self.keys and self.keys["openrouter"]:
            lines.append(f"OPENROUTER_API_KEY={self.keys['openrouter']}")
        if "gateway" in self.keys and self.keys["gateway"]:
            lines.append(f"OMNIROUTE_API_KEY={self.keys['gateway']}")
        lines.append(f"OMNIROUTE_BASE_URL={self.gateway_url}")

        for pid, m in self.models.items():
            if m:
                lines.append(f"{pid.upper()}_MODEL={m}")

        try:
            LLM_ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception as ex:
            logger.warning("Could not persist to .llm.env: %s", ex)

        return self.get_public_providers()

    def get_public_providers(self) -> Dict[str, Any]:
        """Return provider connection state for UI consumption."""
        result = []
        for pid, meta in PROVIDER_METADATA.items():
            has_key = bool(self.keys.get(pid))
            configured = has_key or (pid == "gateway" and bool(self.gateway_url))
            active_model = self.models.get(pid) or meta["default_model"]
            result.append({
                "id": pid,
                "name": meta["name"],
                "model": active_model,
                "configured": configured,
                "doc_url": meta["doc_url"],
            })

        return {
            "active_provider": self.active_provider,
            "providers": result,
            "keys": {pid: (self.keys[pid][:6] + "..." + self.keys[pid][-4:]) if len(self.keys.get(pid, "")) > 10 else ("*" * len(self.keys.get(pid, ""))) for pid in self.keys},
            "models": self.models,
        }

    def resolve_target(self) -> Optional[Tuple[str, str, str, str]]:
        """Resolve (provider_id, base_url, api_key, model_name)."""
        if self.active_provider == "local":
            return None

        target_pid = self.active_provider
        if target_pid == "auto":
            # Pick first configured provider with a valid key
            found = False
            for candidate in ("gemini", "groq", "openai", "openrouter", "gateway"):
                if self.keys.get(candidate):
                    target_pid = candidate
                    found = True
                    break
            if not found:
                return None

        if target_pid not in PROVIDER_METADATA:
            return None

        key = self.keys.get(target_pid, "")
        if target_pid != "gateway" and not key:
            return None

        meta = PROVIDER_METADATA[target_pid]
        url = self.gateway_url if target_pid == "gateway" else meta["url"]
        model = self.models.get(target_pid) or meta["default_model"]
        return target_pid, url, key, model

    def test_connection(
        self,
        provider: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Test API connection with low-latency prompt."""
        p_clean = provider.strip().lower()
        if p_clean == "local":
            return {"ok": True, "model": "Local reflex & Ollama", "latency": 1}

        meta = PROVIDER_METADATA.get(p_clean)
        if not meta:
            return {"ok": False, "error": f"Unknown provider: '{provider}'"}

        key = (api_key or self.keys.get(p_clean, "")).strip()
        url = meta["url"]
        target_model = (model or self.models.get(p_clean) or meta["default_model"]).strip()

        if p_clean != "gateway" and not key:
            return {"ok": False, "error": f"No API key provided for {meta['name']}."}

        t0 = time.perf_counter()
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "EDITH-OS/3.0",
        }
        if key:
            headers["Authorization"] = f"Bearer {key}"

        payload = {
            "model": target_model,
            "messages": [
                {"role": "user", "content": "Reply with only the word READY"}
            ],
            "max_tokens": 10,
        }

        req = urllib.request.Request(
            f"{url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10.0) as res:
                dt_ms = int((time.perf_counter() - t0) * 1000)
                body = json.loads(res.read().decode("utf-8"))
                content = body.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                return {
                    "ok": True,
                    "model": target_model,
                    "latency": dt_ms,
                    "text": content or "Connected",
                }
        except urllib.error.HTTPError as he:
            err_text = he.read().decode("utf-8", errors="replace")
            logger.warning("Test connection HTTP error: %s - %s", he.code, err_text)
            return {"ok": False, "error": f"HTTP {he.code}: {err_text[:120]}"}
        except Exception as ex:
            return {"ok": False, "error": str(ex)}

    async def is_healthy(self) -> bool:
        """Check if active cloud provider is configured."""
        target = self.resolve_target()
        return target is not None

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model_name: Optional[str] = None,
    ) -> ModelResponse:
        """Generate response via active OpenAI-compatible cloud endpoint."""
        target = self.resolve_target()
        if not target:
            raise ProviderUnavailableError("No cloud provider configured with valid API key.")

        pid, url, key, default_m = target
        m = model_name or default_m

        t0 = time.perf_counter()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "EDITH-OS/3.0",
        }
        if key:
            headers["Authorization"] = f"Bearer {key}"

        payload = {
            "model": m,
            "messages": messages,
            "max_tokens": 1200,
            "temperature": 0.7,
        }

        req = urllib.request.Request(
            f"{url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=18.0) as res:
                dt_ms = (time.perf_counter() - t0) * 1000.0
                body = json.loads(res.read().decode("utf-8"))
                choice = body.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "").strip()
                self.circuit_breaker.record_success()
                return ModelResponse(
                    content=content,
                    model=f"{pid.upper()}:{m}",
                    provider="cloud_ai",
                    duration_ms=dt_ms,
                )
        except Exception as ex:
            self.circuit_breaker.record_failure(str(ex))
            raise ProviderUnavailableError(f"Cloud provider {pid} error: {ex}") from ex

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = "",
        model_name: Optional[str] = None,
    ) -> ModelResponse:
        """Generate with tool schemas."""
        target = self.resolve_target()
        if not target:
            raise ProviderUnavailableError("No cloud provider configured for tool calling.")

        pid, url, key, default_m = target
        m = model_name or default_m

        t0 = time.perf_counter()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "EDITH-OS/3.0",
        }
        if key:
            headers["Authorization"] = f"Bearer {key}"

        # Standard OpenAI tools payload
        formatted_tools = []
        for t in tools:
            formatted_tools.append({
                "type": "function",
                "function": {
                    "name": t.get("name"),
                    "description": t.get("description", ""),
                    "parameters": t.get("parameters", {}),
                }
            })

        payload = {
            "model": m,
            "messages": messages,
            "tools": formatted_tools,
            "tool_choice": "auto",
            "max_tokens": 1200,
        }

        req = urllib.request.Request(
            f"{url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=22.0) as res:
                dt_ms = (time.perf_counter() - t0) * 1000.0
                body = json.loads(res.read().decode("utf-8"))
                choice = body.get("choices", [{}])[0]
                msg = choice.get("message", {})
                content = msg.get("content", "") or ""

                tool_calls: List[ToolCall] = []
                raw_tcs = msg.get("tool_calls", [])
                for rtc in raw_tcs:
                    fn = rtc.get("function", {})
                    fn_name = fn.get("name", "")
                    raw_args = fn.get("arguments", "{}")
                    try:
                        parsed_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except Exception:
                        parsed_args = {}
                    if fn_name:
                        tool_calls.append(ToolCall(name=fn_name, arguments=parsed_args))

                self.circuit_breaker.record_success()
                return ModelResponse(
                    content=content.strip(),
                    tool_calls=tool_calls,
                    model=f"{pid.upper()}:{m}",
                    provider="cloud_ai",
                    duration_ms=dt_ms,
                )
        except Exception as ex:
            # Fall back to text generation
            logger.debug("Tool call syntax not supported by provider %s, falling back to generate: %s", pid, ex)
            return await self.generate(prompt=prompt, system_prompt=system_prompt, model_name=model_name)


# Global UniversalCloudProvider singleton
CLOUD_AI = UniversalCloudProvider()
