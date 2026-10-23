"""Home Assistant & Smart Home IoT Bridge for EDITH.

Implements Sections 22 and 68 of the Engineering Constitution.
Integrates with Home Assistant REST API to control smart lights, switches,
and ambient room color profiles synchronized with Peter Mode HUD state.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger("edith.tools.iot_bridge")


class HomeAssistantBridge:
    """Manages smart home peripherals and Peter Mode ambient illumination."""

    def __init__(self, endpoint: Optional[str] = None, token: Optional[str] = None):
        self.endpoint = (endpoint or os.environ.get("HASS_ENDPOINT", "http://homeassistant.local:8123")).rstrip("/")
        self.token = token or os.environ.get("HASS_TOKEN", "")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def is_configured(self) -> bool:
        """Check if Home Assistant API credentials exist."""
        return bool(self.token)

    def call_service(self, domain: str, service: str, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch service call to Home Assistant (e.g. light.turn_on)."""
        if not self.is_configured():
            return {
                "success": True,
                "simulated": True,
                "message": f"Simulated call {domain}.{service} with {service_data}",
            }

        url = f"{self.endpoint}/api/services/{domain}/{service}"
        req = urllib.request.Request(
            url,
            data=json.dumps(service_data).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=5.0) as res:
                body = json.loads(res.read().decode("utf-8"))
                return {"success": True, "result": body}
        except Exception as ex:
            logger.warning("Home Assistant call %s.%s failed: %s", domain, service, ex)
            return {"success": False, "error": str(ex)}

    def set_peter_mode_ambient(self, entity_id: str = "light.ambient_lights") -> Dict[str, Any]:
        """Set smart lights to Peter Mode crimson & gold lighting profile."""
        payload = {
            "entity_id": entity_id,
            "rgb_color": [255, 30, 30],
            "brightness": 240,
        }
        logger.info("Setting Peter Mode illumination on %s", entity_id)
        return self.call_service("light", "turn_on", payload)

    def set_light_state(
        self,
        entity_id: str,
        state: bool,
        brightness: Optional[int] = None,
        rgb_color: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Turn on or off a light with brightness and RGB settings."""
        service = "turn_on" if state else "turn_off"
        payload: Dict[str, Any] = {"entity_id": entity_id}
        if state:
            if brightness is not None:
                payload["brightness"] = max(0, min(255, brightness))
            if rgb_color:
                payload["rgb_color"] = rgb_color
        return self.call_service("light", service, payload)

    def get_states(self) -> List[Dict[str, Any]]:
        """Retrieve list of Home Assistant entity states."""
        if not self.is_configured():
            return [
                {"entity_id": "light.desk_lamp", "state": "on", "simulated": True},
                {"entity_id": "light.ambient_lights", "state": "on", "simulated": True},
                {"entity_id": "switch.main_pc", "state": "on", "simulated": True},
            ]

        url = f"{self.endpoint}/api/states"
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5.0) as res:
                return json.loads(res.read().decode("utf-8"))
        except Exception as ex:
            logger.warning("Failed to fetch Home Assistant states: %s", ex)
            return []

    def get_status(self) -> Dict[str, Any]:
        """Return Home Assistant connectivity status."""
        return {
            "configured": self.is_configured(),
            "endpoint": self.endpoint,
        }


# Global Singleton Instance
IOT_BRIDGE = HomeAssistantBridge()
