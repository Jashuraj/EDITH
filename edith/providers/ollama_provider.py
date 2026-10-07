"""Ollama Local Provider Implementation.

Implements Sections 8, 9, 10 of the Engineering Constitution.
Integrates Hermes 3B, Llama 3.2, and local tools via Ollama REST API.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from edith.core.config import CONFIG
from edith.providers.base import (
    LLMProvider,
    ModelResponse,
    ProviderUnavailableError,
    ToolCall,
)

logger = logging.getLogger("edith.providers.ollama")


class OllamaProvider(LLMProvider):
    """Local inference provider wrapping the host Ollama runtime."""

    def __init__(self, base_url: Optional[str] = None, default_model: Optional[str] = None):
        super().__init__(name="ollama", is_local=True)
        self.base_url = (base_url or CONFIG.hardware.ollama_endpoint).rstrip("/")
        self.default_model = default_model or CONFIG.primary_local_model

    def set_model(self, model_name: str) -> None:
        """Switch active local model dynamically."""
        self.default_model = model_name
        CONFIG.primary_local_model = model_name
        logger.info("Switched active local model to: %s", model_name)

    async def is_healthy(self) -> bool:
        """Ping Ollama API tags endpoint and auto-recover circuit breaker."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=1.0) as res:
                if res.status == 200:
                    self.circuit_breaker.record_success()
                    return True
                return False
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        """Fetch list of all installed Ollama model names with fast timeout."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=1.0) as res:
                data = json.loads(res.read().decode("utf-8"))
                return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.debug("Ollama not responding on %s: %s", self.base_url, e)
            return []

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model_name: Optional[str] = None,
        temperature: float = 0.2,
    ) -> ModelResponse:
        """Generate text completion via /api/generate."""
        if not self.circuit_breaker.can_execute():
            raise ProviderUnavailableError("Ollama circuit breaker is OPEN.")

        model = model_name or self.default_model
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }

        t0 = time.perf_counter()
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=35.0) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            duration_ms = (time.perf_counter() - t0) * 1000.0
            self.circuit_breaker.record_success()

            return ModelResponse(
                content=result.get("response", ""),
                model=model,
                provider="ollama",
                eval_count=result.get("eval_count", 0),
                duration_ms=round(duration_ms, 2),
            )
        except Exception as e:
            self.circuit_breaker.record_failure(str(e))
            raise ProviderUnavailableError(f"Ollama generation failed: {e}") from e

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = "",
        model_name: Optional[str] = None,
    ) -> ModelResponse:
        """Invoke Ollama chat with structured tools for Hermes 3B."""
        if not self.circuit_breaker.can_execute():
            raise ProviderUnavailableError("Ollama circuit breaker is OPEN.")

        model = model_name or self.default_model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "stream": False,
        }

        t0 = time.perf_counter()
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/api/chat",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=35.0) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            duration_ms = (time.perf_counter() - t0) * 1000.0
            self.circuit_breaker.record_success()

            msg = result.get("message", {})
            raw_content = msg.get("content", "")
            raw_tool_calls = msg.get("tool_calls", [])

            parsed_calls: List[ToolCall] = []

            # 1. Parse standard Ollama tool_calls
            if raw_tool_calls:
                for tc in raw_tool_calls:
                    fn = tc.get("function", {})
                    name = fn.get("name", "").strip()
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            args = {"app": args} if "app" in name else {"input": args}
                    if isinstance(args, dict):
                        if "app_name" in args and "app" not in args:
                            args["app"] = args.pop("app_name")
                    parsed_calls.append(ToolCall(name=name, arguments=args))

            # 2. Hermes 3 text fallback: extract embedded JSON or <tool_call> from raw_content
            import re
            cleaned_content = raw_content

            if not parsed_calls and raw_content:
                # Find all JSON-like chunks with name or arguments
                tc_pattern = re.findall(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", raw_content, re.DOTALL)
                if not tc_pattern:
                    tc_pattern = re.findall(r"(\{[^{}]*(?:\"name\"|\"arguments\")[^{}]*\})", raw_content, re.DOTALL)

                for chunk in tc_pattern:
                    try:
                        parsed_json = json.loads(chunk)
                        call_name = parsed_json.get("name", "").strip()
                        raw_args = parsed_json.get("arguments", {})

                        # Handle Hermes 3 monologue format: {"arguments": "open_app,app:taskmanager", "name": "function"}
                        if (call_name in {"function", "tool", ""} or not call_name) and isinstance(raw_args, str) and "," in raw_args:
                            parts = raw_args.split(",", 1)
                            call_name = parts[0].strip()
                            rest = parts[1].strip()
                            if ":" in rest:
                                k, v = rest.split(":", 1)
                                raw_args = {k.strip(): v.strip()}
                            else:
                                raw_args = {"app": rest}
                        elif isinstance(raw_args, str):
                            try:
                                raw_args = json.loads(raw_args)
                            except Exception:
                                raw_args = {"app": raw_args} if "app" in call_name else {"input": raw_args}

                        if isinstance(raw_args, dict) and "app_name" in raw_args and "app" not in raw_args:
                            raw_args["app"] = raw_args.pop("app_name")

                        if call_name and call_name not in {"function", "tool"}:
                            parsed_calls.append(ToolCall(name=call_name, arguments=raw_args))
                            cleaned_content = cleaned_content.replace(chunk, "")
                    except Exception as e:
                        logger.debug("Failed parsing text tool chunk: %s", e)

            # Clean preamble artifacts, thinking tags, and monologue blocks
            cleaned_content = re.sub(r"</?(?:INNER_MONOLOGUE|thought|tool_call)>", "", cleaned_content, flags=re.IGNORECASE)
            cleaned_content = re.sub(r"^\s*Goldberg\s*", "", cleaned_content, flags=re.IGNORECASE)
            cleaned_content = re.sub(r"\{[^{}]*(?:\"name\"|\"arguments\")[^{}]*\}", "", cleaned_content)
            cleaned_content = cleaned_content.strip(" ,\n\r\t")

            return ModelResponse(
                content=cleaned_content,
                tool_calls=parsed_calls,
                model=model,
                provider="ollama",
                duration_ms=round(duration_ms, 2),
            )
        except Exception as e:
            self.circuit_breaker.record_failure(str(e))
            raise ProviderUnavailableError(f"Ollama tool-calling failed: {e}") from e


# Global Ollama provider singleton
OLLAMA = OllamaProvider()
