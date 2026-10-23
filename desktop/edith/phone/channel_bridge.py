"""ChannelBridge External Messaging Adapter for EDITH.

Implements Sections 69, 70, 71 of the Engineering Constitution.
Connects EDITH to external chat platforms (WhatsApp, Telegram, Discord, and Webhooks).
Receives incoming messages, dispatches through Reflex & ModelRouter, and delivers responses.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from edith.core.config import CONFIG
from edith.core.security import SECURITY
from edith.providers.router import ROUTER, TaskCategory
from edith.tools.reflex import REFLEX
from edith.tools.registry import REGISTRY

logger = logging.getLogger("edith.phone.channel_bridge")


@dataclass
class ChannelMessage:
    """Normalized incoming or outgoing channel communication."""
    channel: str  # "whatsapp", "telegram", "discord", "webhook"
    sender_id: str
    sender_name: str
    text: str
    is_outbound: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ChannelBridge:
    """Universal messaging router connecting external chat apps directly to EDITH."""

    def __init__(self):
        self._history: List[ChannelMessage] = []
        self._lock = threading.Lock()
        self.telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.whatsapp_token = os.environ.get("WHATSAPP_API_TOKEN", "")
        self.whatsapp_phone_id = os.environ.get("WHATSAPP_PHONE_ID", "")
        self.webhook_auth_token = os.environ.get("EDITH_CHANNEL_TOKEN", "edith-local-channel-key")

    def handle_incoming_message(
        self,
        channel: str,
        sender_id: str,
        sender_name: str,
        text: str,
    ) -> Dict[str, Any]:
        """Process inbound message from WhatsApp, Telegram, or Webhook."""
        msg = ChannelMessage(
            channel=channel,
            sender_id=sender_id,
            sender_name=sender_name,
            text=text.strip(),
        )
        with self._lock:
            self._history.append(msg)
            if len(self._history) > 200:
                self._history = self._history[-200:]

        clean_text = text.strip()
        if not clean_text:
            return {"success": False, "reply": "Empty message received."}

        logger.info("Channel [%s] from %s: %s", channel, sender_name or sender_id, clean_text)

        # 1. Reflex Fast Path
        match = REFLEX.evaluate(clean_text)
        if match:
            try:
                res = REFLEX.execute_match(match, executor=lambda name, params: REGISTRY.execute_tool(name, params))
                reply_text = res.get("message") if isinstance(res, dict) else str(res)
                self._record_outbound(channel, sender_id, reply_text)
                return {"success": True, "reply": reply_text, "source": "reflex"}
            except Exception as ex:
                err_reply = f"Action error: {ex}"
                self._record_outbound(channel, sender_id, err_reply)
                return {"success": False, "reply": err_reply, "source": "reflex"}

        # 2. ModelRouter Intelligent Execution
        loop = asyncio.new_event_loop()
        try:
            resp = loop.run_until_complete(
                ROUTER.execute(prompt=clean_text, category=TaskCategory.GENERAL)
            )
            reply_text = resp.content if resp and resp.content else "Command acknowledged."
        except Exception as ex:
            logger.error("Channel processing error: %s", ex)
            reply_text = f"Processing error: {ex}"
        finally:
            loop.close()

        self._record_outbound(channel, sender_id, reply_text)
        return {"success": True, "reply": reply_text, "source": "model_router"}

    def _record_outbound(self, channel: str, sender_id: str, text: str) -> None:
        """Store outbound reply in channel history."""
        out = ChannelMessage(
            channel=channel,
            sender_id=sender_id,
            sender_name="EDITH",
            text=text,
            is_outbound=True,
        )
        with self._lock:
            self._history.append(out)

    def send_whatsapp_message(self, recipient_number: str, text: str) -> Dict[str, Any]:
        """Dispatch outbound message via WhatsApp Cloud API or local bridge."""
        if not self.whatsapp_token or not self.whatsapp_phone_id:
            # Fallback record
            self._record_outbound("whatsapp", recipient_number, text)
            return {"success": False, "status": "simulated", "message": "WhatsApp credentials not set in environment."}

        url = f"https://graph.facebook.com/v18.0/{self.whatsapp_phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_number,
            "type": "text",
            "text": {"body": text},
        }
        headers = {
            "Authorization": f"Bearer {self.whatsapp_token}",
            "Content-Type": "application/json",
        }
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=8.0) as res:
                body = json.loads(res.read().decode("utf-8"))
                self._record_outbound("whatsapp", recipient_number, text)
                return {"success": True, "data": body}
        except Exception as ex:
            logger.warning("WhatsApp dispatch error: %s", ex)
            return {"success": False, "error": str(ex)}

    def get_recent_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return audit history of channel interactions."""
        with self._lock:
            return [
                {
                    "channel": m.channel,
                    "sender_id": m.sender_id,
                    "sender_name": m.sender_name,
                    "text": m.text,
                    "is_outbound": m.is_outbound,
                    "timestamp": m.timestamp,
                }
                for m in self._history[-limit:]
            ]

    def get_status(self) -> Dict[str, Any]:
        """Query channel connection health."""
        return {
            "channels": {
                "whatsapp": {"configured": bool(self.whatsapp_token and self.whatsapp_phone_id)},
                "telegram": {"configured": bool(self.telegram_token)},
                "webhook": {"active": True, "endpoint": "/api/channels/message"},
            },
            "history_count": len(self._history),
        }


# Global Singleton Instance
CHANNEL_BRIDGE = ChannelBridge()
