"""Free Zero-Auth Online AI Provider for EDITH.

Implements completely free, keyless AI access when connected to the internet.
Uses anonymous public endpoints (Pollinations / Open Free LLMs) with automatic
support for free Groq, OpenRouter, and Gemini keys if set in environment.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from edith.providers.base import (
    LLMProvider,
    ModelResponse,
    ProviderUnavailableError,
    ToolCall,
)

logger = logging.getLogger("edith.providers.free_online")


class FreeOnlineProvider(LLMProvider):
    """Zero-auth cloud intelligence provider with graceful fallback."""

    def __init__(self):
        super().__init__(name="free_online", is_local=False)
        self.groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        self.openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        self.gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()

    async def is_healthy(self) -> bool:
        """Check internet connectivity to free public API."""
        try:
            req = urllib.request.Request(
                "https://text.pollinations.ai/health",
                headers={"User-Agent": "EDITH/1.0"},
            )
            with urllib.request.urlopen(req, timeout=3.0) as res:
                return res.status == 200
        except Exception:
            return False

    def _query_pollinations(
        self,
        messages: List[Dict[str, str]],
        timeout: float = 14.0,
    ) -> str:
        """Query free anonymous Pollinations endpoint with openai-fast model."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        }
        payload = {"messages": messages, "model": "openai-fast"}

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                "https://text.pollinations.ai/",
                data=data,
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as res:
                txt = res.read().decode("utf-8").strip()
                if txt and not txt.startswith("Error:"):
                    return txt
        except Exception as e:
            logger.debug("Pollinations primary query error (%s), trying simplified prompt", e)

        # Retry with concise single-message prompt if augmented prompt timed out
        try:
            last_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
            retry_payload = {"messages": [{"role": "user", "content": last_user_msg}], "model": "openai-fast"}
            retry_data = json.dumps(retry_payload).encode("utf-8")
            req = urllib.request.Request(
                "https://text.pollinations.ai/",
                data=retry_data,
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10.0) as res:
                txt = res.read().decode("utf-8").strip()
                if txt and not txt.startswith("Error:"):
                    return txt
        except Exception as ge:
            raise ProviderUnavailableError(f"Free online AI unreachable: {ge}")

    def _query_groq(
        self,
        messages: List[Dict[str, str]],
        timeout: float = 8.0,
    ) -> Optional[str]:
        """Optional query to Groq free tier if API key is present."""
        if not self.groq_key:
            return None
        try:
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": messages,
                "temperature": 0.2,
            }
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.groq_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as res:
                data = json.loads(res.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning("Groq query failed: %s", e)
            return None

    def _query_openrouter(
        self,
        messages: List[Dict[str, str]],
        timeout: float = 8.0,
    ) -> Optional[str]:
        """Optional query to OpenRouter free models if API key is present."""
        if not self.openrouter_key:
            return None
        try:
            payload = {
                "model": "meta-llama/llama-3.3-70b-instruct:free",
                "messages": messages,
                "temperature": 0.2,
            }
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.openrouter_key}",
                    "HTTP-Referer": "https://github.com/edith",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as res:
                data = json.loads(res.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning("OpenRouter query failed: %s", e)
            return None

    def _execute_chat(self, messages: List[Dict[str, str]]) -> str:
        """Execute chat across free keys or keyless public APIs."""
        # 1. Try free Groq key if configured
        groq_out = self._query_groq(messages)
        if groq_out:
            return groq_out

        # 2. Try free OpenRouter key if configured
        openrouter_out = self._query_openrouter(messages)
        if openrouter_out:
            return openrouter_out

        # 3. Default to free zero-auth public AI
        return self._query_pollinations(messages)

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model_name: Optional[str] = None,
        temperature: float = 0.2,
    ) -> ModelResponse:
        """Generate text completion via free online cloud AI."""
        if not self.circuit_breaker.can_execute():
            raise ProviderUnavailableError("Free online circuit breaker is OPEN.")

        t0 = time.perf_counter()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            content = self._execute_chat(messages)
            dt_ms = (time.perf_counter() - t0) * 1000.0
            self.circuit_breaker.record_success()
            return ModelResponse(
                content=content,
                model="FREE_CLOUD_AI",
                provider="cloud_free",
                duration_ms=round(dt_ms, 2),
            )
        except Exception as ex:
            self.circuit_breaker.record_failure(str(ex))
            raise ProviderUnavailableError(f"Free online AI generation failed: {ex}")

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = "",
        model_name: Optional[str] = None,
    ) -> ModelResponse:
        """Generate tool calls or natural text via free online cloud AI."""
        if not self.circuit_breaker.can_execute():
            raise ProviderUnavailableError("Free online circuit breaker is OPEN.")

        t0 = time.perf_counter()
        tool_descriptions = []
        for t in tools:
            fn = t.get("function", {})
            name = fn.get("name", "")
            desc = fn.get("description", "")
            params = fn.get("parameters", {}).get("properties", {})
            req = fn.get("parameters", {}).get("required", [])
            param_str = ", ".join(f"{p}: string" for p in params.keys())
            tool_descriptions.append(f"- {name}({param_str}): {desc}")

        tools_block = "\n".join(tool_descriptions)
        augmented_system = (
            f"{system_prompt}\n\n"
            "You have direct control over the user's Windows operating system.\n"
            "If the user asks to perform an action (open an app, search YouTube, search Google, type text, press keys, "
            "manage windows, open folders, adjust volume, take screenshot, lock screen, check battery), reply ONLY with a JSON object:\n"
            '{"tool": "<tool_name>", "parameters": {"<param_name>": "<value>"}}\n\n'
            f"Available tools:\n{tools_block}\n\n"
            "If the user is asking a conversational question, coding question, explanation, or greeting, reply normally in 1 to 2 concise sentences."
        )

        messages = [
            {"role": "system", "content": augmented_system},
            {"role": "user", "content": prompt},
        ]

        try:
            raw_text = self._execute_chat(messages)
            dt_ms = (time.perf_counter() - t0) * 1000.0
            self.circuit_breaker.record_success()

            # Multi-format tool call extraction
            tool_calls: List[ToolCall] = []
            cleaned_text = raw_text

            # Check if raw_text is a JSON response with tool_calls (OpenAI format from Pollinations)
            try:
                data_obj = json.loads(raw_text)
                if isinstance(data_obj, dict):
                    # Handle {"tool_calls": [...]}
                    tcs = data_obj.get("tool_calls") or []
                    for tc in tcs:
                        fn = tc.get("function", {})
                        fname = fn.get("name", "").strip()
                        fargs = fn.get("arguments", {})
                        if isinstance(fargs, str):
                            try:
                                fargs = json.loads(fargs)
                            except Exception:
                                pass
                        if isinstance(fargs, dict):
                            actual_name = fargs.get("tool") or fname
                            actual_params = fargs.get("parameters") or fargs
                            tool_calls.append(ToolCall(name=actual_name, arguments=actual_params))
                    # Handle direct {"tool": "...", "parameters": {...}}
                    if not tool_calls and "tool" in data_obj:
                        tool_calls.append(ToolCall(name=data_obj["tool"], arguments=data_obj.get("parameters", {})))
                    elif not tool_calls and "name" in data_obj and "arguments" in data_obj:
                        tool_calls.append(ToolCall(name=data_obj["name"], arguments=data_obj.get("arguments", {})))
            except Exception:
                pass

            # Fallback regex extraction from plain text / markdown
            if not tool_calls:
                # Strip markdown code blocks
                clean_json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
                target_json_str = clean_json_match.group(1) if clean_json_match else raw_text

                m1 = re.search(r"\{\s*\"tool\"\s*:\s*\"([^\"]+)\"\s*,\s*\"parameters\"\s*:\s*(\{.*?\})\s*\}", target_json_str, re.DOTALL)
                if m1:
                    name = m1.group(1).strip()
                    try:
                        params = json.loads(m1.group(2))
                        tool_calls.append(ToolCall(name=name, arguments=params))
                    except Exception:
                        pass
                else:
                    m2 = re.search(r"\{\s*\"name\"\s*:\s*\"([^\"]+)\"\s*,\s*\"arguments\"\s*:\s*(\{.*?\})\s*\}", target_json_str, re.DOTALL)
                    if m2:
                        name = m2.group(1).strip()
                        try:
                            params = json.loads(m2.group(2))
                            tool_calls.append(ToolCall(name=name, arguments=params))
                        except Exception:
                            pass

            if tool_calls:
                cleaned_text = f"Executing {tool_calls[0].name}..."

            return ModelResponse(
                content=cleaned_text,
                tool_calls=tool_calls,
                model="FREE_CLOUD_AI",
                provider="cloud_free",
                duration_ms=round(dt_ms, 2),
            )
        except Exception as ex:
            self.circuit_breaker.record_failure(str(ex))
            raise ProviderUnavailableError(f"Free online AI generation failed: {ex}")


# Global FreeOnlineProvider singleton
FREE_ONLINE = FreeOnlineProvider()
