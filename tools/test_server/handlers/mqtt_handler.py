import dataclasses
from typing import Optional, Dict, Any

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None


JSON = Dict[str, Any]


@dataclasses.dataclass
class MQTTConfig:
    host: str = "localhost"
    port: int = 1883
    topic: str = "effects"
    username: Optional[str] = None
    password: Optional[str] = None


class MQTTHandler:
    def __init__(
        self, global_dispatcher=None, config: Optional[MQTTConfig] = None
    ):
        self.dispatcher = global_dispatcher
        self.config = config or MQTTConfig()

    async def send(self, effect: JSON) -> bool:
        if mqtt is None:
            print("[MQTTHandler] paho-mqtt not installed; skipping send")
            return False
        try:
            import json

            payload = json.dumps(effect)

            def _publish():
                client = mqtt.Client()
                if self.config.username and self.config.password:
                    client.username_pw_set(
                        self.config.username, self.config.password
                    )
                client.connect(self.config.host, self.config.port, 60)
                client.publish(self.config.topic, payload)
                client.disconnect()
                return True

            import asyncio

            return await asyncio.to_thread(_publish)
        except Exception as e:
            print(f"[MQTTHandler] send failed: {e}")
            return False
