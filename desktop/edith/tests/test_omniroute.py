"""Unit tests for OmniRoute Provider and Controller."""

import asyncio
from edith.providers.omniroute_provider import OmniRouteController, OmniRouteProvider


def test_omniroute_controller_status():
    controller = OmniRouteController(base_url="http://127.0.0.1:9999", port=9999)
    status = controller.get_status()
    assert isinstance(status, dict)
    assert status["online"] is False
    assert status["model_count"] == 0

    summary = controller.get_butler_summary()
    assert "currently offline" in summary


def test_omniroute_provider_circuit_breaker():
    provider = OmniRouteProvider(base_url="http://127.0.0.1:9999", timeout=1.0)
    assert provider.circuit_breaker.can_execute() is True

    # Health check returns false when offline
    is_healthy = asyncio.run(provider.is_healthy())
    assert is_healthy is False
