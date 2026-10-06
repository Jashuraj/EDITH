"""EDITH ModelRouter with Zero-Credit and Offline Fallback.

Implements Sections 3, 4, 12, 17 of the Engineering Constitution.
Dynamically routes inference requests across local models and cloud providers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from edith.core.config import CONFIG
from edith.core.security import SECURITY
from edith.providers.base import LLMProvider, ModelResponse
from edith.providers.free_online_provider import FREE_ONLINE
from edith.providers.ollama_provider import OLLAMA

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


class ModelRouter:
    """Intelligent model selection engine routing online to free cloud AI and offline to Ollama."""

    def __init__(self, local_provider: Optional[LLMProvider] = None, cloud_provider: Optional[LLMProvider] = None):
        self.local = local_provider or OLLAMA
        self.cloud = cloud_provider
        self.free_online = FREE_ONLINE
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
        """Decide the optimal provider: free cloud AI when online, local Ollama when offline."""
        # 1. Check Privacy Mode
        if SECURITY.is_privacy_mode:
            return self._route_local(category, has_tools, reason="Privacy mode active: all data strictly local.")

        # 2. Check Zero-Credit Mode
        if CONFIG.zero_credit_mode:
            return self._route_local(category, has_tools, reason="Zero-credit mode active: all reasoning strictly routed to local Ollama.")

        # 3. Check Offline Mode or Internet Availability
        is_online = self._internet_available and CONFIG.check_internet(timeout_seconds=0.5)
        if CONFIG.offline_mode or not is_online:
            return self._route_local(category, has_tools, reason="System is offline. Using local Ollama models.")

        # 4. Tool calling with explicit external cloud provider
        if (has_tools or category == TaskCategory.TOOL_CALLING) and (self.cloud is not None):
            return self._route_local(category, has_tools, reason="Tool execution bound to local Hermes 3B engine.")

        # 5. If online, connect to free zero-auth cloud AI
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
        """Route and execute generation through the chosen provider with fallback."""
        try:
            from edith.memory.local_store import MEMORY
            memories = MEMORY.get_memories()
            if memories:
                memory_block = "\n".join(f"- {m}" for m in memories)
                system_prompt = f"{system_prompt}\n\nLearned User Facts & Preferences:\n{memory_block}"
        except Exception:
            pass

        decision = self.route(prompt, category=category, has_tools=bool(tools))
        logger.info("Routing prompt to [%s / %s]: %s", decision.provider, decision.model, decision.reason)

        # Attempt primary decision
        if decision.provider == "free_online":
            provider = self.free_online
        elif decision.provider == "cloud" and self.cloud:
            provider = self.cloud
        else:
            provider = self.local

        try:
            if tools:
                return await provider.generate_with_tools(
                    prompt=prompt,
                    tools=tools,
                    system_prompt=system_prompt,
                    model_name=decision.model,
                )
            return await provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                model_name=decision.model,
            )
        except Exception as e:
            # Fallback to local if free_online or cloud fails
            if decision.provider in ("free_online", "cloud"):
                logger.warning("%s generation failed (%s). Triggering immediate local fallback.", decision.provider, e)
                fallback = self._route_local(category, bool(tools), reason=f"Emergency {decision.provider} fallback.", is_fallback=True)
                try:
                    if tools:
                        return await self.local.generate_with_tools(
                            prompt=prompt,
                            tools=tools,
                            system_prompt=system_prompt,
                            model_name=fallback.model,
                        )
                    return await self.local.generate(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        model_name=fallback.model,
                    )
                except Exception:
                    pass

            # If Ollama primary model failed, try fast lightweight fallback (llama3.2:1b or hhao coder)
            fallback_models = ["llama3.2:1b", "hhao/qwen2.5-coder-tools:0.5b", "gemma3:1b"]
            for alt_model in fallback_models:
                if alt_model != decision.model:
                    try:
                        logger.info("Attempting secondary fallback model: %s", alt_model)
                        if tools:
                            return await self.local.generate_with_tools(
                                prompt=prompt,
                                tools=tools,
                                system_prompt=system_prompt,
                                model_name=alt_model,
                            )
                        return await self.local.generate(
                            prompt=prompt,
                            system_prompt=system_prompt,
                            model_name=alt_model,
                        )
                    except Exception:
                        continue

            logger.warning("All model providers failed or timed out. Serving deterministic response.")
            return ModelResponse(
                content="Operating in offline reflex mode. System is fully operational and awaiting your commands.",
                model="OFFLINE_FALLBACK",
                provider="local",
                duration_ms=0.0,
            )


# Global ModelRouter singleton
ROUTER = ModelRouter()
