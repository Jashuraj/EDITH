"""Model Context Protocol (MCP) Client for EDITH.

Implements open-standard tool server connection (stdio & JSON-RPC over HTTP).
Dynamically discovers external MCP tools and mounts them into the EDITH ToolRegistry.
"""

from __future__ import annotations

import json
import logging
import subprocess
import threading
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional

from edith.core.security import RiskLevel

logger = logging.getLogger("edith.tools.mcp_client")


class MCPClient:
    """Manages connections to external Model Context Protocol (MCP) servers."""

    def __init__(self):
        self._servers: Dict[str, Dict[str, Any]] = {}
        self._tools_cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def connect_http_server(self, server_id: str, base_url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Connect to an HTTP-based MCP server endpoint."""
        url_clean = base_url.rstrip("/")
        req_headers = {"Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }

        try:
            req = urllib.request.Request(
                f"{url_clean}/mcp",
                data=json.dumps(payload).encode("utf-8"),
                headers=req_headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5.0) as res:
                body = json.loads(res.read().decode("utf-8"))
                tools = body.get("result", {}).get("tools", [])
        except Exception:
            # Fallback direct endpoint
            try:
                req = urllib.request.Request(
                    url_clean,
                    data=json.dumps(payload).encode("utf-8"),
                    headers=req_headers,
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=5.0) as res:
                    body = json.loads(res.read().decode("utf-8"))
                    tools = body.get("result", {}).get("tools", [])
            except Exception as ex:
                logger.warning("MCP connection failed for %s (%s): %s", server_id, base_url, ex)
                return {"success": False, "server_id": server_id, "error": str(ex), "tools_count": 0}

        with self._lock:
            self._servers[server_id] = {
                "type": "http",
                "url": url_clean,
                "headers": req_headers,
                "tools": tools,
            }
            for t in tools:
                full_name = f"mcp_{server_id}_{t.get('name')}"
                self._tools_cache[full_name] = {
                    "server_id": server_id,
                    "raw_name": t.get("name"),
                    "description": t.get("description", ""),
                    "schema": t.get("inputSchema", {}),
                }

        logger.info("Connected to MCP server '%s' with %d tools.", server_id, len(tools))
        return {"success": True, "server_id": server_id, "tools_count": len(tools), "tools": [t.get("name") for t in tools]}

    def call_mcp_tool(self, server_id: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a remote tool call via MCP server."""
        server = self._servers.get(server_id)
        if not server:
            raise ValueError(f"Unknown MCP server: '{server_id}'")

        if server["type"] == "http":
            payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments or {},
                },
            }
            url = f"{server['url']}/mcp" if "/mcp" not in server["url"] else server["url"]
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=server.get("headers", {}),
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15.0) as res:
                body = json.loads(res.read().decode("utf-8"))
                return body.get("result", body)

        raise NotImplementedError(f"Unsupported MCP server transport: {server['type']}")

    def register_mcp_tools(self, registry) -> int:
        """Register all discovered MCP tools into EDITH ToolRegistry."""
        count = 0
        with self._lock:
            for full_name, t_meta in self._tools_cache.items():
                s_id = t_meta["server_id"]
                r_name = t_meta["raw_name"]
                desc = t_meta["description"] or f"External MCP tool {r_name} from {s_id}"

                def _make_fn(server_id: str, tool_name: str) -> Callable:
                    return lambda **kwargs: MCP_CLIENT.call_mcp_tool(server_id, tool_name, kwargs)

                registry.register(
                    name=full_name,
                    description=desc,
                    action_pack="MCP_PACK",
                    risk=RiskLevel.MEDIUM,
                    fn=_make_fn(s_id, r_name),
                    parameters_schema=t_meta.get("schema", {}),
                )
                count += 1
        return count

    def get_status(self) -> Dict[str, Any]:
        """Return connected MCP servers and cached tools."""
        return {
            "servers": list(self._servers.keys()),
            "tools_count": len(self._tools_cache),
            "tools": list(self._tools_cache.keys()),
        }


# Global Singleton Instance
MCP_CLIENT = MCPClient()
