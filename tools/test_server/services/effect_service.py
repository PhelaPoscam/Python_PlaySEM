"""Effect orchestration service extracted from the monolithic server."""

from datetime import datetime, timezone
from typing import Any, Dict, List


class EffectService:
    """Tracks effect dispatch attempts and inbox entries."""

    def __init__(self) -> None:
        self._effects_sent = 0
        self._effect_inbox: List[Dict[str, Any]] = []

    @property
    def effects_sent(self) -> int:
        return self._effects_sent

    def send_effect(
        self, *, device_exists: bool, device_id: str, effect: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not device_exists:
            raise KeyError(device_id)

        self._effects_sent += 1
        return {
            "success": True,
            "device_id": device_id,
            "effect_type": effect.get("effect_type", "unknown"),
            "message": "Effect sent successfully",
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
