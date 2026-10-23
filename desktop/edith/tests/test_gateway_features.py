"""Unit tests for integrated EDITH Gateway and Host Agent features."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from edith.tools.reflex import REFLEX
from edith.tools.registry import REGISTRY


def test_gateway_status_tool_offline():
    """Verify gateway_status tool returns offline when gateway is down."""
    tool = REGISTRY.get("gateway_status")
    assert tool is not None
    res = tool.fn(url="http://127.0.0.1:99999")
    assert res["online"] is False
    assert "gateway_url" in res
    assert res["version"] == "2.1.0"


def test_gateway_status_tool_online():
    """Verify gateway_status tool parses status when gateway is online."""
    tool = REGISTRY.get("gateway_status")
    assert tool is not None

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps({"ok": True, "state": "nominal"}).encode()
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = tool.fn(url="http://127.0.0.1:3000")
        assert res["online"] is True
        assert res["data"]["state"] == "nominal"


def test_host_agent_status_tool(tmp_path, monkeypatch):
    """Verify host_agent_status tool reflects configuration presence."""
    tool = REGISTRY.get("host_agent_status")
    assert tool is not None

    monkeypatch.setenv("APPDATA", str(tmp_path))
    res = tool.fn()
    assert res["installed"] is False
    assert res["paired"] is False

    edith_dir = tmp_path / "EDITH"
    edith_dir.mkdir(parents=True)
    cfg = edith_dir / "host_agent.json"
    cfg.write_text(json.dumps({"gateway": "http://127.0.0.1:3000", "name": "Workstation", "token": "tok_123"}), encoding="utf-8")

    res2 = tool.fn()
    assert res2["installed"] is True
    assert res2["paired"] is True
    assert res2["device_name"] == "Workstation"


def test_gateway_reflex_patterns():
    """Verify reflex regex matches gateway queries."""
    m1 = REFLEX.evaluate("check gateway")
    assert m1 is not None
    assert m1.command_name == "gateway_status"

    m2 = REFLEX.evaluate("hey edith gateway status")
    assert m2 is not None
    assert m2.command_name == "gateway_status"

    m3 = REFLEX.evaluate("check host agent")
    assert m3 is not None
    assert m3.command_name == "host_agent_status"

    res = REFLEX.execute_match(m1)
    assert "EDITH Gateway" in res


def test_gateway_ui_assets_present():
    """Verify that all gateway scripts, styles, and pairing assets exist in ui/public."""
    ui_public = Path(__file__).resolve().parent.parent / "ui" / "public"
    assert (ui_public / "edith-gateway.js").is_file()
    assert (ui_public / "edith-gateway.css").is_file()
    assert (ui_public / "mobile" / "edith-pair.js").is_file()
    assert (ui_public / "edith-gateway.js").stat().st_size > 10000
    assert (ui_public / "edith-gateway.css").stat().st_size > 1000
    assert (ui_public / "mobile" / "edith-pair.js").stat().st_size > 500
