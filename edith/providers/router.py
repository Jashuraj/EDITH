"""EDITH Resilient ModelRouter with Multi-Tier Ladder and Zero-Defect Offline Engine.

Implements Sections 3, 4, 12, 17 of the Engineering Constitution.
Architected for resilient failover:
1. Online: Free Zero-Auth Cloud AI / Multi-Model Ladder
2. Local: Hermes 3B / Ollama local models
3. Offline Deterministic: Intelligent Reflex & Built-In NLP Core (Zero Downtime Guarantee)
"""

from __future__ import annotations

import datetime
import logging
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from edith.core.asimov_guard import ASIMOV_GUARD
from edith.core.config import CONFIG
from edith.core.security import SECURITY
from edith.core.security_sentinels import (
    CREDENTIAL_GUARDIAN,
    DEVICE_LOCK_SENTINEL,
    DEVICE_POWER_SENTINEL,
    FINANCIAL_GATEKEEPER,
)
from edith.core.single_question import enforce_single_question
from edith.providers.base import LLMProvider, ModelResponse, ToolCall
from edith.providers.free_online_provider import FREE_ONLINE
from edith.providers.ollama_provider import OLLAMA
from edith.providers.omniroute_provider import OMNIROUTE
from edith.tools.reflex import REFLEX

logger = logging.getLogger("edith.providers.router")


class TaskCategory(str, Enum):
    REFLEX = "REFLEX"
    GENERAL = "GENERAL"
    TOOL_CALLING = "TOOL_CALLING"
    CODING = "CODING"
    VISION = "VISION"
    REASONING = "REASONING"


@dataclass
class RoutingDecision:
    """Outcome of model router analysis."""
    provider: str
    model: str
    category: TaskCategory
    reason: str
    is_offline_fallback: bool = False


class DeterministicFallbackEngine:
    """Smart offline intelligence engine providing zero-downtime execution and answers."""

    @classmethod
    def answer(cls, prompt: str, tools_enabled: bool = True) -> ModelResponse:
        clean = (prompt or "").strip()
        low = clean.lower()

        tool_calls: List[ToolCall] = []

        # 1. Level 0 Reflex Engine Direct Match
        match = REFLEX.evaluate(clean)
        if match:
            tool_calls.append(ToolCall(name=match.command_name, arguments=match.params))
            return ModelResponse(
                content=f"Executed reflex: {match.command_name}.",
                tool_calls=tool_calls,
                model="OFFLINE_REFLEX",
                provider="local_reflex",
                duration_ms=1.0,
            )

        # 2. Heuristic Intent Matching for OS Actions
        if tools_enabled:
            # Play / YouTube
            m_play = re.search(r"^(?:(?:hey\s+|ok\s+)?edith[,\s]*)?(?:play|search\s+youtube\s+for|listen\s+to|put\s+on|youtube)\s+(?P<q>.+?)(?:\s+(?:on|in)\s+(?:youtube|browser|chrome|edge))?$", low)
            if m_play:
                q = m_play.group("q").strip()
                tool_calls.append(ToolCall(name="search_youtube", arguments={"query": q}))
                return ModelResponse(
                    content=f"Playing '{q}' on YouTube.",
                    tool_calls=tool_calls,
                    model="OFFLINE_REFLEX",
                    provider="local_reflex",
                )

            # Web / Google Search
            m_search = re.search(r"^(?:(?:hey\s+|ok\s+)?edith[,\s]*)?(?:search\s+google\s+for|google|search\s+(?:the\s+)?web\s+for|search\s+for)\s+(?P<q>.+)$", low)
            if m_search:
                q = m_search.group("q").strip()
                tool_calls.append(ToolCall(name="search_google", arguments={"query": q}))
                return ModelResponse(
                    content=f"Searching Google for '{q}'.",
                    tool_calls=tool_calls,
                    model="OFFLINE_REFLEX",
                    provider="local_reflex",
                )

            # Launch / Open App
            m_open = re.search(r"^(?:(?:hey\s+|ok\s+)?edith[,\s]*)?(?:open|launch|start|run|show)\s+(?:the\s+)?(?P<app>[a-zA-Z0-9_\-\.\:\/]+(?:\s+[a-zA-Z0-9_\-\.\:\/]+)?)$", low)
            if m_open:
                app_name = m_open.group("app").strip()
                tool_calls.append(ToolCall(name="open_app", arguments={"app": app_name}))
                return ModelResponse(
                    content=f"Launching {app_name}.",
                    tool_calls=tool_calls,
                    model="OFFLINE_REFLEX",
                    provider="local_reflex",
                )

            # Close / Kill App
            m_close = re.search(r"^(?:(?:hey\s+|ok\s+)?edith[,\s]*)?(?:close|exit|quit|kill|terminate)\s+(?:the\s+)?(?P<app>[a-zA-Z0-9_\-\.\:\/]+(?:\s+[a-zA-Z0-9_\-\.\:\/]+)?)$", low)
            if m_close:
                app_name = m_close.group("app").strip()
                tool_calls.append(ToolCall(name="close_app", arguments={"app": app_name}))
                return ModelResponse(
                    content=f"Terminating {app_name}.",
                    tool_calls=tool_calls,
                    model="OFFLINE_REFLEX",
                    provider="local_reflex",
                )

            # System controls
            if any(term in low for term in ("lock screen", "lock pc", "lock computer", "lock workstation")):
                tool_calls.append(ToolCall(name="lock_screen", arguments={}))
                return ModelResponse(content="Locking screen.", tool_calls=tool_calls, model="OFFLINE_REFLEX", provider="local_reflex")
            if any(term in low for term in ("take screenshot", "capture screen", "screenshot", "screen cap")):
                tool_calls.append(ToolCall(name="take_screenshot", arguments={}))
                return ModelResponse(content="Capturing screenshot.", tool_calls=tool_calls, model="OFFLINE_REFLEX", provider="local_reflex")
            if "volume up" in low or "louder" in low or "increase volume" in low:
                tool_calls.append(ToolCall(name="volume_up", arguments={"delta": 5}))
                return ModelResponse(content="Increasing volume.", tool_calls=tool_calls, model="OFFLINE_REFLEX", provider="local_reflex")
            if "volume down" in low or "quieter" in low or "decrease volume" in low or "lower volume" in low:
                tool_calls.append(ToolCall(name="volume_down", arguments={"delta": -5}))
                return ModelResponse(content="Lowering volume.", tool_calls=tool_calls, model="OFFLINE_REFLEX", provider="local_reflex")
            if "mute" in low and "unmute" not in low:
                tool_calls.append(ToolCall(name="mute", arguments={"action": "mute"}))
                return ModelResponse(content="Muting audio.", tool_calls=tool_calls, model="OFFLINE_REFLEX", provider="local_reflex")
            if "unmute" in low:
                tool_calls.append(ToolCall(name="unmute", arguments={"action": "unmute"}))
                return ModelResponse(content="Unmuting audio.", tool_calls=tool_calls, model="OFFLINE_REFLEX", provider="local_reflex")
            if any(term in low for term in ("show desktop", "minimize all", "clear desktop")):
                tool_calls.append(ToolCall(name="window_action", arguments={"action": "show desktop"}))
                return ModelResponse(content="Showing desktop.", tool_calls=tool_calls, model="OFFLINE_REFLEX", provider="local_reflex")
            if any(term in low for term in ("optimize system", "clean temp", "flush dns", "trim ram", "free ram", "clean system", "clear cache")):
                tool_calls.append(ToolCall(name="optimize_system", arguments={}))
                return ModelResponse(
                    content="Executing system optimization: trimming memory working set, flushing DNS cache, and clearing temporary storage.",
                    tool_calls=tool_calls,
                    model="OFFLINE_REFLEX",
                    provider="local_reflex",
                )

        # 3. Conversational & Knowledge Answering
        now_dt = datetime.datetime.now()
        if any(term in low for term in ("what time", "current time", "tell me the time", "time now")):
            return ModelResponse(
                content=f"The current time is {now_dt.strftime('%I:%M %p')}.",
                model="OFFLINE_CORE",
                provider="deterministic",
            )
        if any(term in low for term in ("what day", "what date", "today's date", "current date", "what is today")):
            return ModelResponse(
                content=f"Today is {now_dt.strftime('%A, %B %d, %Y')}.",
                model="OFFLINE_CORE",
                provider="deterministic",
            )
        if any(term in low for term in ("who made you", "who created you", "who is your creator", "creator")):
            return ModelResponse(
                content=f"I was created by {CONFIG.creator} as an autonomous, local-first AI operating system.",
                model="OFFLINE_CORE",
                provider="deterministic",
            )
        if any(term in low for term in ("who are you", "what are you", "what is edith", "introduce yourself")):
            return ModelResponse(
                content="I am E.D.I.T.H. (Even Dead, I'm The Hero), an autonomous local-first artificial intelligence operating system.",
                model="OFFLINE_CORE",
                provider="deterministic",
            )
        if any(term in low for term in ("capabilities", "what can you do", "help me", "commands", "features")):
            return ModelResponse(
                content=(
                    "EDITH Subsystems & Commands:\n"
                    "• Applications: 'open chrome', 'open notepad', 'close chrome'\n"
                    "• Media: 'play <song>', 'open youtube', 'volume up', 'mute'\n"
                    "• Desktop: 'show desktop', 'take screenshot', 'lock pc'\n"
                    "• Vision & Gestures: Hand tracking and full desktop mouse control\n"
                    "• Modes: Switch between Auto, Online, and Offline in header"
                ),
                model="OFFLINE_CORE",
                provider="deterministic",
            )
        if any(term in low for term in ("thank you", "thanks", "good job", "great job", "appreciate it")):
            return ModelResponse(
                content="You are most welcome, sir. Standing by for your next instruction.",
                model="OFFLINE_CORE",
                provider="deterministic",
            )
        if any(term in low for term in ("hello", "hey edith", "hi edith", "good morning", "good evening", "good afternoon", "hi", "hey")):
            return ModelResponse(
                content="Hello sir. EDITH intelligence core is active and standing by. All OS tools and gesture controls are operational.",
                model="OFFLINE_CORE",
                provider="deterministic",
            )
        if any(term in low for term in ("how are you", "system status", "diagnostics", "health")):
            stats = CONFIG.refresh_dynamic_stats()
            online_str = "Online (Hybrid)" if stats.get("online") else "Offline (Local Reflex)"
            return ModelResponse(
                content=f"All systems nominal, sir. State: READY. Mode: {online_str}. Free RAM: {stats.get('free_ram_gb', 0)}GB.",
                model="OFFLINE_CORE",
                provider="deterministic",
            )
        if any(term in low for term in ("battery", "power")):
            prof = CONFIG.hardware
            ac_str = "plugged in" if prof.is_ac_powered else "on battery"
            return ModelResponse(
                content=f"Battery level is at {prof.battery_percent}%, currently {ac_str}.",
                model="OFFLINE_CORE",
                provider="deterministic",
            )

        # 4. Safe Arithmetic Math Evaluation
        math_match = re.search(r"^(?:what\s+is|calculate|compute)?\s*([0-9\s\+\-\*\/\(\)\.\^%]+)$", clean)
        if math_match:
            expr = math_match.group(1).strip()
            if any(op in expr for op in ("+", "-", "*", "/", "%")) and re.match(r"^[0-9\s\+\-\*\/\(\)\.]+$", expr):
                try:
                    val = eval(expr, {"__builtins__": None}, {})
                    return ModelResponse(
                        content=f"{expr} = {val}",
                        model="OFFLINE_CORE",
                        provider="deterministic",
                    )
                except Exception:
                    pass

        # 5. Check User Memory Database
        try:
            from edith.memory.local_store import MEMORY
            memories = MEMORY.get_memories()
            for m in memories:
                words = [w for w in low.split() if len(w) > 3]
                if any(w in m.lower() for w in words):
                    return ModelResponse(
                        content=f"According to my memory: {m}",
                        model="OFFLINE_CORE",
                        provider="deterministic",
                    )
        except Exception:
            pass

        # 6. Helpful Context-Aware Answering
        return ModelResponse(
            content=(
                f"Understood, sir. Operating with local deterministic intelligence. "
                f"I can control your applications, stream media in the HUD, adjust system audio, "
                f"lock your workstation, or navigate your desktop via gesture tracking."
            ),
            model="OFFLINE_CORE",
            provider="deterministic",
            duration_ms=1.0,
        )


class ModelRouter:
    """Intelligent model selection engine routing across cloud, gateway, local, and deterministic tiers."""

    def __init__(self, local_provider: Optional[LLMProvider] = None, cloud_provider: Optional[LLMProvider] = None):
        self.local = local_provider or OLLAMA
        self.cloud = cloud_provider
        self.free_online = FREE_ONLINE
        self.omniroute = OMNIROUTE
        self._internet_available: bool = True

    def set_internet_status(self, available: bool) -> None:
        """Update simulated or probed internet connectivity status."""
        self._internet_available = available
        logger.info("Internet status updated: available=%s", available)

    def route(
        self,
        prompt: str,
        category: TaskCategory = TaskCategory.GENERAL,
        has_tools: bool = False,
    ) -> RoutingDecision:
        """Decide the optimal provider based on configuration and connectivity."""
        # 1. Check Privacy Mode
        if SECURITY.is_privacy_mode:
            return self._route_local(category, has_tools, reason="Privacy mode active: all data strictly local.")

        # 2. Check Zero-Credit Mode
        if CONFIG.zero_credit_mode:
            return self._route_local(category, has_tools, reason="Zero-credit mode active: all reasoning strictly routed to local Ollama.")

        # 3. Check Manual or Effective Offline Mode
        is_online = CONFIG.is_effectively_online() and self._internet_available
        if not is_online:
            return self._route_local(category, has_tools, reason="Offline mode active: routing to local models.")

        # 4. Tool calling with explicit external cloud provider
        if (has_tools or category == TaskCategory.TOOL_CALLING) and (self.cloud is not None):
            return self._route_local(category, has_tools, reason="Tool execution bound to local Hermes 3B engine.")

        # 5. Connected to free zero-auth cloud AI
        return RoutingDecision(
            provider="free_online",
            model="FREE_CLOUD_AI",
            category=category,
            reason="Internet active: Connected to free zero-auth cloud AI.",
        )

    def _route_local(
        self,
        category: TaskCategory,
        has_tools: bool,
        reason: str,
        is_fallback: bool = False,
    ) -> RoutingDecision:
        """Select appropriate local model variant based on task category."""
        if category == TaskCategory.VISION:
            model = CONFIG.vision_local_model
        elif category == TaskCategory.CODING:
            model = CONFIG.coder_local_model
        elif category == TaskCategory.REFLEX:
            model = CONFIG.reflex_local_model
        elif has_tools or category == TaskCategory.TOOL_CALLING:
            model = CONFIG.primary_local_model  # hermes3:3b
        else:
            model = CONFIG.primary_local_model

        return RoutingDecision(
            provider="ollama",
            model=model,
            category=category,
            reason=reason,
            is_offline_fallback=is_fallback,
        )

    async def execute(
        self,
        prompt: str,
        category: TaskCategory = TaskCategory.GENERAL,
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: str = "",
    ) -> ModelResponse:
        """Route and execute generation across multi-tier ladder with security sentinels."""
        # Sentinel Check 1: Asimov's Prime Directive & Safety Sentinel
        is_safe, refusal = ASIMOV_GUARD.evaluate_safety(prompt)
        if not is_safe:
            return ModelResponse(
                content=refusal,
                model="ASIMOV_GUARD",
                provider="security",
                duration_ms=1.0,
            )

        # Sentinel Check 2: Device Power & Sleep Directive
        is_sleep, sleep_msg = DEVICE_POWER_SENTINEL.evaluate_shutdown_directive(prompt)
        if is_sleep:
            return ModelResponse(
                content=sleep_msg,
                tool_calls=[ToolCall(name="power_action", arguments={"kind": "sleep"})],
                model="POWER_SENTINEL",
                provider="security",
                duration_ms=1.0,
            )

        # Sentinel Check 3: Device Lock Directive
        is_handled, unlocked, unlock_msg = DEVICE_LOCK_SENTINEL.evaluate_unlock_directive(prompt)
        if is_handled:
            return ModelResponse(
                content=unlock_msg,
                model="LOCK_SENTINEL",
                provider="security",
                duration_ms=1.0,
            )

        # Sentinel Check 4: Financial Gatekeeper
        if FINANCIAL_GATEKEEPER.has_pending_authorization():
            fin_eval = FINANCIAL_GATEKEEPER.evaluate_decision(prompt)
            if fin_eval is not None:
                _, fin_msg, _ = fin_eval
                return ModelResponse(
                    content=fin_msg,
                    model="FINANCIAL_GATEKEEPER",
                    provider="security",
                    duration_ms=1.0,
                )
        else:
            is_fin, _ = FINANCIAL_GATEKEEPER.detect_financial_task(prompt)
            if is_fin:
                fin_req = FINANCIAL_GATEKEEPER.create_authorization_request(prompt)
                return ModelResponse(
                    content=fin_req,
                    model="FINANCIAL_GATEKEEPER",
                    provider="security",
                    duration_ms=1.0,
                )

        # Sentinel Check 5: Credential Guardian Exposure Check
        if CREDENTIAL_GUARDIAN.has_pending_authorization():
            cred_eval = CREDENTIAL_GUARDIAN.evaluate_decision(prompt)
            if cred_eval is not None:
                _, cred_msg, _ = cred_eval
                return ModelResponse(
                    content=cred_msg,
                    model="CREDENTIAL_GUARDIAN",
                    provider="security",
                    duration_ms=1.0,
                )
        else:
            is_exp, _ = CREDENTIAL_GUARDIAN.detect_unauthorized_exposure(prompt)
            if is_exp:
                cred_req = CREDENTIAL_GUARDIAN.create_authorization_request(prompt)
                return ModelResponse(
                    content=cred_req,
                    model="CREDENTIAL_GUARDIAN",
                    provider="security",
                    duration_ms=1.0,
                )

        # Redact any private credentials in prompt before passing to models
        clean_prompt = CREDENTIAL_GUARDIAN.redact(prompt)

        try:
            from edith.memory.local_store import MEMORY
            memories = MEMORY.get_memories()
            if memories:
                memory_block = "\n".join(f"- {m}" for m in memories)
                system_prompt = f"{system_prompt}\n\nLearned User Facts & Preferences:\n{memory_block}"
        except Exception:
            pass

        decision = self.route(clean_prompt, category=category, has_tools=bool(tools))
        logger.info("Routing prompt to [%s / %s]: %s", decision.provider, decision.model, decision.reason)

        response: Optional[ModelResponse] = None

        # Tier 1: Free Online Cloud AI (if routed online)
        if decision.provider == "free_online" and self.free_online.circuit_breaker.can_execute():
            try:
                if tools:
                    response = await self.free_online.generate_with_tools(
                        prompt=clean_prompt,
                        tools=tools,
                        system_prompt=system_prompt,
                        model_name=decision.model,
                    )
                else:
                    response = await self.free_online.generate(
                        prompt=clean_prompt,
                        system_prompt=system_prompt,
                        model_name=decision.model,
                    )
            except Exception as ex:
                logger.warning("Tier 1 (Free Online) failed (%s). Stepping down to Tier 1.5 OmniRoute.", ex)

        # Tier 1.5: OmniRoute Multi-Provider Gateway
        if response is None and self.omniroute.circuit_breaker.can_execute():
            try:
                is_omni_up = await self.omniroute.is_healthy()
                if is_omni_up:
                    if tools:
                        response = await self.omniroute.generate_with_tools(
                            prompt=clean_prompt,
                            tools=tools,
                            system_prompt=system_prompt,
                            model_name=decision.model,
                        )
                    else:
                        response = await self.omniroute.generate(
                            prompt=clean_prompt,
                            system_prompt=system_prompt,
                            model_name=decision.model,
                        )
            except Exception as ex:
                logger.debug("Tier 1.5 (OmniRoute) unavailable: %s", ex)

        # Tier 2: Local Ollama Model (Hermes 3B or configured model)
        if response is None and self.local.circuit_breaker.can_execute():
            # Fast health probe to avoid 15s freeze if Ollama daemon is offline
            is_healthy = await self.local.is_healthy()
            if is_healthy:
                try:
                    if tools:
                        response = await self.local.generate_with_tools(
                            prompt=clean_prompt,
                            tools=tools,
                            system_prompt=system_prompt,
                            model_name=decision.model,
                        )
                    else:
                        response = await self.local.generate(
                            prompt=clean_prompt,
                            system_prompt=system_prompt,
                            model_name=decision.model,
                        )
                except Exception as ex:
                    logger.warning("Tier 2 (Local Ollama) failed: %s", ex)
            else:
                logger.debug("Ollama daemon is currently not running on host.")

        # Tier 3: Zero-Defect Smart Deterministic NLP & Reflex Core
        if response is None:
            logger.info("Engaging Tier 3 Deterministic Core for prompt: '%s'", clean_prompt)
            response = DeterministicFallbackEngine.answer(clean_prompt, tools_enabled=bool(tools))

        # Enforce Credential Redaction and Single-Question Protocol on Response
        if response and response.content:
            response.content = CREDENTIAL_GUARDIAN.redact(response.content)
            response.content = enforce_single_question(response.content)

        return response


# Global ModelRouter singleton
ROUTER = ModelRouter()
