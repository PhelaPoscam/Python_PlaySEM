from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from tools.test_server.handlers import (
    HTTPHandler, HTTPConfig,
    CoAPHandler, CoAPConfig,
    MQTTHandler, MQTTConfig,
    UPnPHandler, UPnPConfig
)

logger = logging.getLogger(__name__)


class EffectService:
    """Tracks effect dispatch attempts and inbox entries."""

    def __init__(self) -> None:
        self._effects_sent = 0
        self._effect_inbox: List[Dict[str, Any]] = []

    @property
    def effects_sent(self) -> int:
        return self._effects_sent

    async def send_effect(
        self,
        *,
        device_exists: bool,
        device_id: str,
        effect: Dict[str, Any],
        protocol: Optional[str] = None,
        endpoint: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Dispatch an effect via a specific protocol or default (WS)."""
        if not device_exists:
            raise KeyError(device_id)

        self._effects_sent += 1
        protocol = (protocol or "websocket").lower()
        success = True
        
        if protocol == "mqtt":
            cfg = MQTTConfig(**endpoint) if endpoint else MQTTConfig()
            handler = MQTTHandler(config=cfg)
            success = await handler.send(effect)
        elif protocol == "coap":
            cfg = CoAPConfig(**endpoint) if endpoint else CoAPConfig()
            handler = CoAPHandler(config=cfg)
            success = await handler.send(effect)
        elif protocol == "http":
            cfg = HTTPConfig(**endpoint) if endpoint else HTTPConfig()
            handler = HTTPHandler(config=cfg)
            success = await handler.send(effect)
        elif protocol == "upnp":
            cfg = UPnPConfig(**endpoint) if endpoint else UPnPConfig()
            handler = UPnPHandler(config=cfg)
            success = await handler.send(effect)
        
        return {
            "success": success,
            "device_id": device_id,
            "effect_type": effect.get("effect_type", "unknown"),
            "protocol": protocol,
            "message": "Effect dispatched" if success else "Dispatch failed",
        }

    def store_inbox_effect(self, effect: Dict[str, Any]) -> Dict[str, Any]:
        record = {
            "received_at": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "effect": effect,
        }
        self._effect_inbox.append(record)
        return {"stored": True, "count": len(self._effect_inbox)}

    def list_inbox(self) -> Dict[str, Any]:
        items = list(self._effect_inbox)
        return {"effects": items, "count": len(items)}
