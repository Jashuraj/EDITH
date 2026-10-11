"""Unit tests for Provider Resolver inspired by ECC."""

from edith.providers.free_online_provider import FreeOnlineProvider
from edith.providers.ollama_provider import OllamaProvider
from edith.providers.omniroute_provider import OmniRouteProvider
from edith.providers.resolver import ProviderType, get_provider, resolve_provider_type


def test_resolve_provider_type():
    assert resolve_provider_type("ollama") == ProviderType.OLLAMA
    assert resolve_provider_type("free_online") == ProviderType.FREE_ONLINE
    assert resolve_provider_type("omniroute") == ProviderType.OMNIROUTE
    assert resolve_provider_type("UNKNOWN") == ProviderType.OLLAMA


def test_get_provider_instances():
    ollama = get_provider("ollama")
    assert isinstance(ollama, OllamaProvider)

    free_online = get_provider("free_online")
    assert isinstance(free_online, FreeOnlineProvider)

    omniroute = get_provider("omniroute")
    assert isinstance(omniroute, OmniRouteProvider)
