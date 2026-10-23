"""Llama.cpp High-Performance Local Model Provider for EDITH.

Implements direct GGUF inference and llama-server local HTTP compatibility.
Enables low-latency, quantized personal AI execution completely offline.
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
from typing import Any, Dict, List, Optional

from edith.providers.base import (
    LLMProvider,
    ModelResponse,
    ProviderUnavailableError,
    ToolCall,
)

logger = logging.getLogger("edith.providers.llamacpp")


class LlamaCppProvider(LLMProvider):
    """Local inference provider communicating with llama-server or llama.cpp daemon."""

    def __init__(self, endpoint: Optional[str] = None):
        super().__init__(name="llama_cpp", is_local=True)
        self.endpoint = endpoint or os.environ.get("LLAMACPP_ENDPOINT", "http://127.0.0.1:8080")
        self.default_model = os.environ.get("LLAMACPP_MODEL", "local-gguf")
        self.timeout = 25.0

    async def is_healthy(self) -> bool:
        """Check if llama-server / llama.cpp HTTP daemon is responsive."""
        if not self.circuit_breaker.can_execute():
            return False
        try:
            req = urllib.request.Request(f"{self.endpoint.rstrip('/')}/health", method="GET")
            with urllib.request.urlopen(req, timeout=1.5) as res:
                return res.status in (200, 204)
        except Exception:
            # Try /v1/models fallback
            try:
                req = urllib.request.Request(f"{self.endpoint.rstrip('/')}/v1/models", method="GET")
                with urllib.request.urlopen(req, timeout=1.5) as res:
                    return res.status == 200
            except Exception:
                return False

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model_name: Optional[str] = None,
        temperature: float = 0.2,
    ) -> ModelResponse:
        """Generate text completion via llama.cpp OpenAI-compatible or /completion endpoint."""
        if not self.circuit_breaker.can_execute():
            raise ProviderUnavailableError("Llama.cpp circuit breaker is OPEN.")

        t0 = time.perf_counter()
        m = model_name or self.default_model

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": m,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1024,
            "stream": False,
        }

        # Try /v1/chat/completions first
        req = urllib.request.Request(
            f"{self.endpoint.rstrip('/')}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                dt_ms = (time.perf_counter() - t0) * 1000.0
                body = json.loads(res.read().decode("utf-8"))
                choice = body.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "").strip()
                self.circuit_breaker.record_success()
                return ModelResponse(
                    content=content,
                    model=f"LLAMACPP:{m}",
                    provider="llama_cpp",
                    duration_ms=dt_ms,
                )
        except Exception as ex:
            # Fall back to native /completion endpoint if server is llama-server native
            try:
                native_payload = {
                    "prompt": (f"<|system|>\n{system_prompt}\n<|user|>\n{prompt}\n<|assistant|>\n" if system_prompt else f"<|user|>\n{prompt}\n<|assistant|>\n"),
                    "temperature": temperature,
                    "n_predict": 1024,
                }
                nat_req = urllib.request.Request(
                    f"{self.endpoint.rstrip('/')}/completion",
                    data=json.dumps(native_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(nat_req, timeout=self.timeout) as res:
                    dt_ms = (time.perf_counter() - t0) * 1000.0
                    body = json.loads(res.read().decode("utf-8"))
                    content = body.get("content", "").strip()
                    self.circuit_breaker.record_success()
                    return ModelResponse(
                        content=content,
                        model=f"LLAMACPP:{m}",
                        provider="llama_cpp",
                        duration_ms=dt_ms,
                    )
            except Exception as inner_ex:
                self.circuit_breaker.record_failure(str(inner_ex))
                raise ProviderUnavailableError(f"Llama.cpp inference failed: {inner_ex}") from inner_ex

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = "",
        model_name: Optional[str] = None,
    ) -> ModelResponse:
        """Generate with function calling schemas via structured JSON or tool calls."""
        if not self.circuit_breaker.can_execute():
            raise ProviderUnavailableError("Llama.cpp circuit breaker is OPEN.")

        t0 = time.perf_counter()
        m = model_name or self.default_model

        formatted_tools = [
            {
                "type": "function",
                "function": {
                    "name": t.get("name"),
                    "description": t.get("description", ""),
                    "parameters": t.get("parameters", {}),
                },
            }
            for t in tools
        ]

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": m,
            "messages": messages,
            "tools": formatted_tools,
            "tool_choice": "auto",
            "temperature": 0.1,
            "max_tokens": 1024,
        }

        req = urllib.request.Request(
            f"{self.endpoint.rstrip('/')}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                dt_ms = (time.perf_counter() - t0) * 1000.0
                body = json.loads(res.read().decode("utf-8"))
                choice = body.get("choices", [{}])[0]
                msg = choice.get("message", {})
                content = msg.get("content", "") or ""

                tool_calls: List[ToolCall] = []
                for tc in msg.get("tool_calls", []):
                    fn = tc.get("function", {})
                    fn_name = fn.get("name", "")
                    raw_args = fn.get("arguments", "{}")
                    parsed_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    if fn_name:
                        tool_calls.append(ToolCall(name=fn_name, arguments=parsed_args))

                self.circuit_breaker.record_success()
                return ModelResponse(
                    content=content.strip(),
                    tool_calls=tool_calls,
                    model=f"LLAMACPP:{m}",
                    provider="llama_cpp",
                    duration_ms=dt_ms,
                )
        except Exception:
            # Fall back to text generation
            return await self.generate(prompt=prompt, system_prompt=system_prompt, model_name=model_name)


# Global Singleton Instance
LLAMACPP = LlamaCppProvider()
