"""Provider Factory and Resolver for EDITH.

Inspired by affaan-m/ECC src/llm/providers/resolver.py architecture.
Provides modular discovery, dynamic environment configuration (.llm.env),
and unified access across local, edge, gateway, and cloud LLM providers.
"""

from __future__ import annotations

import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Type

from edith.providers.base import LLMProvider
from edith.providers.free_online_provider import FREE_ONLINE, FreeOnlineProvider
from edith.providers.ollama_provider import OLLAMA, OllamaProvider
from edith.providers.omniroute_provider import OMNIROUTE, OmniRouteProvider

logger = logging.getLogger("edith.providers.resolver")


class ProviderType(str, Enum):
    """Enumeration of recognized LLM provider backends."""
    OLLAMA = "ollama"
    FREE_ONLINE = "free_online"
    OMNIROUTE = "omniroute"
    OPENAI = "openai"
    CLAUDE = "claude"


_PROVIDER_MAP: Dict[ProviderType, Type[LLMProvider]] = {
    ProviderType.OLLAMA: OllamaProvider,
    ProviderType.FREE_ONLINE: FreeOnlineProvider,
    ProviderType.OMNIROUTE: OmniRouteProvider,
}

_SINGLETON_MAP: Dict[ProviderType, LLMProvider] = {
    ProviderType.OLLAMA: OLLAMA,
    ProviderType.FREE_ONLINE: FREE_ONLINE,
    ProviderType.OMNIROUTE: OMNIROUTE,
}

LLM_ENV_FILE = ".llm.env"


def strip_env_value(value: str) -> str:
    """Strip surrounding quotes and whitespace from an env file value."""
    val = value.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in {"'", '"'}:
        return val[1:-1]
    return val


def read_saved_llm_config(env_path: Optional[Path] = None) -> Dict[str, str]:
    """Parse local environment configuration from file."""
    path = env_path or (Path(__file__).resolve().parent.parent.parent / LLM_ENV_FILE)
    if not path.is_file():
        return {}

    config: Dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            k, v = stripped.split("=", 1)
            config[k.strip()] = strip_env_value(v)
    except Exception as ex:
        logger.debug("Could not read LLM env config: %s", ex)
    return config


def resolve_provider_type(requested: Optional[str] = None) -> ProviderType:
    """Resolve active provider type prioritizing arguments, env, and config."""
    if requested:
        try:
            return ProviderType(requested.lower().strip())
        except ValueError:
            pass

    env_provider = os.environ.get("LLM_PROVIDER")
    if env_provider:
        try:
            return ProviderType(strip_env_value(env_provider).lower())
        except ValueError:
            pass

    saved = read_saved_llm_config()
    saved_type = saved.get("LLM_PROVIDER")
    if saved_type:
        try:
            return ProviderType(saved_type.lower())
        except ValueError:
            pass

    return ProviderType.OLLAMA


def get_provider(provider_type: Optional[str] = None) -> LLMProvider:
    """Retrieve instance of designated provider type."""
    resolved = resolve_provider_type(provider_type)
    if resolved in _SINGLETON_MAP:
        return _SINGLETON_MAP[resolved]

    cls = _PROVIDER_MAP.get(resolved)
    if not cls:
        raise ValueError(f"No provider registered for type: {resolved}")
    return cls()


def register_provider(ptype: ProviderType, provider_cls: Type[LLMProvider], instance: Optional[LLMProvider] = None) -> None:
    """Dynamically register a new provider implementation."""
    _PROVIDER_MAP[ptype] = provider_cls
    if instance is not None:
        _SINGLETON_MAP[ptype] = instance
    logger.info("Registered dynamic provider: %s", ptype.value)
