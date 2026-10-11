"""OmniRoute Gateway Provider and Controller for EDITH.

Inspired by jarvis-omniroute and upstream diegosouzapw/OmniRoute.
Provides multi-provider gateway telemetry, circuit-breaker guarded model inference,
and local server orchestration.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from edith.core.config import CONFIG
from edith.providers.base import CircuitBreaker, LLMProvider, ModelResponse, ToolCall

logger = logging.getLogger("edith.providers.omniroute")


class OmniRouteProvider(LLMProvider):
    """Integrates OmniRoute Multi-Provider Gateway into EDITH provider ladder."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 12.0,
    ):
        self.base_url = (base_url or os.environ.get("OMNIROUTE_BASE_URL", "http://127.0.0.1:8000")).rstrip("/")
        self.api_key = api_key or os.environ.get("OMNIROUTE_API_KEY", "")
        self.timeout = timeout
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=30.0)

    async def is_healthy(self) -> bool:
        """Probe gateway health via lightweight GET /models request."""
        if not self.circuit_breaker.can_execute():
            return False

        req = urllib.request.Request(f"{self.base_url}/models", method="GET")
        if self.api_key:
            req.add_header("Authorization", f"Bearer {self.api_key}")

        try:
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    self.circuit_breaker.record_success()
                    return True
        except Exception:
            pass
        return False

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model_name: Optional[str] = None,
    ) -> ModelResponse:
        """Execute text completion via OmniRoute OpenAI-compatible endpoint."""
        if not self.circuit_breaker.can_execute():
            raise RuntimeError("OmniRoute circuit breaker is OPEN.")

        model = model_name or "default"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt or "You are EDITH, an elite personal AI."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(f"{self.base_url}/chat/completions", data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        if self.api_key:
            req.add_header("Authorization", f"Bearer {self.api_key}")

        start_time = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                dur_ms = (time.monotonic() - start_time) * 1000.0
                data = json.loads(raw)
                self.circuit_breaker.record_success()

                choices = data.get("choices", [])
                if choices:
                    msg = choices[0].get("message", {})
                    content = msg.get("content", "").strip()
                    return ModelResponse(
                        content=content,
                        model=model,
                        provider="omniroute",
                        duration_ms=dur_ms,
                    )
                return ModelResponse(
                    content="",
                    model=model,
                    provider="omniroute",
                    duration_ms=dur_ms,
                )
        except Exception as ex:
            self.circuit_breaker.record_failure()
            logger.warning("OmniRoute completion failed: %s", ex)
            raise

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = "",
        model_name: Optional[str] = None,
    ) -> ModelResponse:
        """Execute tool-augmented generation via OmniRoute gateway."""
        if not self.circuit_breaker.can_execute():
            raise RuntimeError("OmniRoute circuit breaker is OPEN.")

        model = model_name or "default"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt or "You are EDITH, an elite personal AI."},
                {"role": "user", "content": prompt},
            ],
            "tools": [{"type": "function", "function": t} for t in tools],
            "temperature": 0.1,
        }

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(f"{self.base_url}/chat/completions", data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        if self.api_key:
            req.add_header("Authorization", f"Bearer {self.api_key}")

        start_time = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                dur_ms = (time.monotonic() - start_time) * 1000.0
                data = json.loads(raw)
                self.circuit_breaker.record_success()

                choices = data.get("choices", [])
                if choices:
                    msg = choices[0].get("message", {})
                    content = msg.get("content", "") or ""
                    tool_calls: List[ToolCall] = []

                    raw_calls = msg.get("tool_calls", [])
                    for rc in raw_calls:
                        fn = rc.get("function", {})
                        fname = fn.get("name", "")
                        fargs_raw = fn.get("arguments", "{}")
                        try:
                            fargs = json.loads(fargs_raw) if isinstance(fargs_raw, str) else fargs_raw
                        except Exception:
                            fargs = {}
                        if fname:
                            tool_calls.append(ToolCall(name=fname, arguments=fargs))

                    return ModelResponse(
                        content=content.strip(),
                        tool_calls=tool_calls,
                        model=model,
                        provider="omniroute",
                        duration_ms=dur_ms,
                    )
                return ModelResponse(
                    content="",
                    model=model,
                    provider="omniroute",
                    duration_ms=dur_ms,
                )
        except Exception as ex:
            self.circuit_breaker.record_failure()
            logger.warning("OmniRoute tool generation failed: %s", ex)
            raise


class OmniRouteController:
    """Manages OmniRoute local gateway telemetry and lifecycle."""

    def __init__(self, base_url: Optional[str] = None, port: int = 8000):
        self.base_url = (base_url or os.environ.get("OMNIROUTE_BASE_URL", f"http://127.0.0.1:{port}")).rstrip("/")
        self.port = port
        self.upstream = "https://github.com/diegosouzapw/OmniRoute"

    def get_status(self) -> Dict[str, Any]:
        """Poll the local OmniRoute instance and return status dictionary."""
        req = urllib.request.Request(f"{self.base_url}/models", method="GET")
        start = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                latency_ms = round((time.monotonic() - start) * 1000.0, 1)
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = data.get("data", [])
                    return {
                        "online": True,
                        "status_code": 200,
                        "latency_ms": latency_ms,
                        "model_count": len(models),
                        "base_url": self.base_url,
                        "upstream": self.upstream,
                        "message": f"OmniRoute Gateway active with {len(models)} models ({latency_ms}ms)",
                    }
                return {
                    "online": False,
                    "status_code": resp.status,
                    "latency_ms": latency_ms,
                    "model_count": 0,
                    "base_url": self.base_url,
                    "upstream": self.upstream,
                    "message": f"OmniRoute returned HTTP {resp.status}",
                }
        except Exception as err:
            return {
                "online": False,
                "status_code": 0,
                "latency_ms": 0,
                "model_count": 0,
                "base_url": self.base_url,
                "upstream": self.upstream,
                "message": f"OmniRoute Gateway unreachable: {err}",
            }

    def get_butler_summary(self) -> str:
        """Produce spoken status summary suitable for EDITH voice."""
        status = self.get_status()
        if status["online"]:
            cnt = status["model_count"]
            return f"OmniRoute gateway is online at port {self.port}, sir, with {cnt} models available."
        return f"OmniRoute gateway is currently offline at port {self.port}, sir."


OMNIROUTE = OmniRouteProvider()
OMNIROUTE_CONTROLLER = OmniRouteController()
