"""EDITH Tool Registry and Dynamic Action Pack Architecture.

Implements Sections 22 and 51 of the Engineering Constitution.
Manages tool definitions, OpenAI/Ollama compatible JSON schemas, and pack activation.
"""

from __future__ import annotations

import inspect
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from edith.core.security import RiskLevel, SECURITY

logger = logging.getLogger("edith.tools.registry")


@dataclass
class ToolDefinition:
    """Metadata and execution pointer for a registered system tool."""
    name: str
    description: str
    action_pack: str
    risk: RiskLevel
    fn: Callable[..., Any]
    parameters_schema: Dict[str, Any]

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to standard function-calling JSON schema format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }


class ToolRegistry:
    """Registry managing available tools and scoped action packs."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._action_packs: Dict[str, Set[str]] = {
            "WINDOWS_PACK": set(),
            "FILES_PACK": set(),
            "CODING_PACK": set(),
            "BROWSER_PACK": set(),
            "VISION_PACK": set(),
            "RESEARCH_PACK": set(),
            "ANDROID_PACK": set(),
        }
        self._active_packs: Set[str] = {"WINDOWS_PACK", "FILES_PACK"}

    def register(
        self,
        name: str,
        description: str,
        action_pack: str,
        risk: RiskLevel,
        fn: Callable[..., Any],
        parameters_schema: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a tool and associate it with an action pack."""
        schema = parameters_schema or {"type": "object", "properties": {}, "required": []}
        definition = ToolDefinition(
            name=name,
            description=description,
            action_pack=action_pack,
            risk=risk,
            fn=fn,
            parameters_schema=schema,
        )
        self._tools[name] = definition

        if action_pack not in self._action_packs:
            self._action_packs[action_pack] = set()
        self._action_packs[action_pack].add(name)
        logger.debug("Registered tool: %s in %s (Risk: %s)", name, action_pack, risk.value)

    def activate_pack(self, pack_name: str) -> None:
        """Enable an action pack for LLM exposure."""
        if pack_name in self._action_packs:
            self._active_packs.add(pack_name)
            logger.info("Activated action pack: %s", pack_name)

    def deactivate_pack(self, pack_name: str) -> None:
        """Deactivate an action pack."""
        self._active_packs.discard(pack_name)
        logger.info("Deactivated action pack: %s", pack_name)

    def get_active_tools(self) -> List[ToolDefinition]:
        """Return all tools belonging to currently active action packs."""
        active_tool_names: Set[str] = set()
        for pack in self._active_packs:
            active_tool_names.update(self._action_packs.get(pack, set()))
        return [self._tools[name] for name in active_tool_names if name in self._tools]

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return OpenAI / Ollama compatible function definitions for active tools."""
        return [tool.to_openai_schema() for tool in self.get_active_tools()]

    def execute_tool(self, tool_name: str, params: Any, is_autonomous: bool = False) -> Any:
        """Safely execute a tool through the security policy gate."""
        if tool_name not in self._tools:
            raise KeyError(f"Tool '{tool_name}' not found in registry.")

        tool = self._tools[tool_name]

        # Normalize arguments
        clean_params = params
        if isinstance(clean_params, str):
            try:
                clean_params = json.loads(clean_params)
            except Exception:
                # Wrap scalar into primary expected parameter
                if tool.parameters_schema.get("properties"):
                    first_prop = list(tool.parameters_schema["properties"].keys())[0]
                    clean_params = {first_prop: clean_params}
                else:
                    clean_params = {}

        if not isinstance(clean_params, dict):
            clean_params = {}

        # Normalize common key mismatches
        if "app_name" in clean_params and "app" in tool.parameters_schema.get("properties", {}):
            clean_params["app"] = clean_params.pop("app_name")

        raw_result = SECURITY.authorize_and_execute(
            tool_name=tool.name,
            params=clean_params,
            executor=tool.fn,
            is_autonomous=is_autonomous,
        )

        if isinstance(raw_result, dict):
            return raw_result.get("message") or raw_result.get("result") or json.dumps(raw_result)
        return raw_result


# Global registry singleton
REGISTRY = ToolRegistry()

# Automatically populate built-in tools
try:
    from edith.tools.builtin import register_builtin_tools
    register_builtin_tools(REGISTRY)
except Exception as _ex:
    logger.debug("Deferred builtin tools registration: %s", _ex)
