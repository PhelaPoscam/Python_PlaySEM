import dataclasses
from typing import Optional, Dict, Any

try:
    import websockets
except ImportError:
    websockets = None


JSON = Dict[str, Any]


@dataclasses.dataclass
class WebSocketConfig:
    url: str = "ws://localhost:8090/ws"


class WebSocketHandler:
    def __init__(
        self, global_dispatcher=None, config: Optional[WebSocketConfig] = None
    ):
        self.dispatcher = global_dispatcher
        self.config = config or WebSocketConfig()

    async def send(self, effect: JSON) -> bool:
        if websockets is None:
            print("[WebSocketHandler] websockets not installed; skipping send")
            return False
        try:
            async with websockets.connect(self.config.url) as ws:
                import json

                await ws.send(json.dumps(effect))
                return True
        except Exception as e:
            print(f"[WebSocketHandler] send failed: {e}")
            return False
