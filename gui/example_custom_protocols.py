"""
Example demonstrating how to extend PythonPlaySEM GUI with custom protocols.

This shows how to add MQTT, CoAP, or any custom protocol.
"""

import logging
from gui.protocols import BaseProtocol, ProtocolFactory
from typing import Optional, Dict, Any, Callable

logger = logging.getLogger(__name__)


# Example: Custom MQTT Protocol Implementation
class MQTTProtocol(BaseProtocol):
    """
    Example MQTT protocol implementation.

    To use:
        1. Install paho-mqtt: pip install paho-mqtt
        2. Register: ProtocolFactory.register("mqtt", MQTTProtocol)
        3. Use in GUI: Select "mqtt" in protocol dropdown
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 1883,
        on_message: Optional[Callable] = None,
        topic: str = "pythonplaysem/#",
    ):
        super().__init__(host, port, on_message)
        self.topic = topic
        self.client = None

        try:
            import paho.mqtt.client as mqtt

            self.mqtt = mqtt
        except ImportError:
            logger.error(
                "paho-mqtt not installed. Install with: pip install paho-mqtt"
            )
            self.mqtt = None

    async def connect(self) -> bool:
        if not self.mqtt:
            return False

        try:
            self.client = self.mqtt.Client()
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message

            self.client.connect(self.host, self.port, keepalive=60)
            self.client.loop_start()

            self.is_connected = True
            logger.info(f"MQTT connected: {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"MQTT connection failed: {e}")
            return False

    async def disconnect(self) -> bool:
        try:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
            self.is_connected = False
            logger.info("MQTT disconnected")
            return True
        except Exception as e:
            logger.error(f"MQTT disconnection error: {e}")
            return False

    async def send(self, data: Dict[str, Any]) -> bool:
        try:
            if not self.client:
                return False

            import json

            message = json.dumps(data)
            self.client.publish(self.topic, message)
            logger.debug(f"MQTT sent to {self.topic}")
            return True
        except Exception as e:
            logger.error(f"MQTT send error: {e}")
            return False

    async def listen(self):
        """MQTT listening is handled by loop_start()"""
        # Keep the coroutine running
        import asyncio

        try:
            while self.is_connected:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"MQTT listen error: {e}")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("MQTT broker connection successful")
            client.subscribe(self.topic)
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            import json

            data = json.loads(msg.payload.decode())
            if self.on_message:
                self.on_message(data)
        except Exception as e:
            logger.error(f"MQTT message parse error: {e}")


# Example: Custom CoAP Protocol Implementation
class CoAPProtocol(BaseProtocol):
    """
    Example CoAP protocol implementation.

    To use:
        1. Install aiocoap: pip install aiocoap
        2. Register: ProtocolFactory.register("coap", CoAPProtocol)
        3. Use in GUI: Select "coap" in protocol dropdown
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5683,
        on_message: Optional[Callable] = None,
    ):
        super().__init__(host, port, on_message)
        try:
            import aiocoap
            from aiocoap import Message, Code

            self.aiocoap = aiocoap
            self.Message = Message
            self.Code = Code
            self.context = None
        except ImportError:
            logger.error(
                "aiocoap not installed. Install with: pip install aiocoap"
            )
            self.aiocoap = None

    async def connect(self) -> bool:
        if not self.aiocoap:
            return False

        try:
            self.context = await self.aiocoap.Context.create_client_context()
            self.is_connected = True
            logger.info(f"CoAP connected: {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"CoAP connection failed: {e}")
            return False

    async def disconnect(self) -> bool:
        try:
            if self.context:
                await self.context.shutdown()
            self.is_connected = False
            logger.info("CoAP disconnected")
            return True
        except Exception as e:
            logger.error(f"CoAP disconnection error: {e}")
            return False

    async def send(self, data: Dict[str, Any]) -> bool:
        try:
            if not self.context:
                return False

            import json

            payload = json.dumps(data).encode("utf-8")
            uri = f"coap://{self.host}:{self.port}/effects"

            request = self.Message(
                code=self.Code.POST, uri=uri, payload=payload
            )

            response = await self.context.request(request).response
            logger.debug(f"CoAP response: {response.code}")
            return True
        except Exception as e:
            logger.error(f"CoAP send error: {e}")
            return False

    async def listen(self):
        """CoAP doesn't have a persistent connection"""
        import asyncio

        try:
            while self.is_connected:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"CoAP listen error: {e}")


def register_custom_protocols():
    """
    Register all custom protocol implementations.

    Call this function before creating the MainWindow:
        register_custom_protocols()
        app = MainWindow()
    """
    try:
        ProtocolFactory.register("mqtt", MQTTProtocol)
        logger.info("✓ MQTT protocol registered")
    except Exception as e:
        logger.warning(f"✗ Could not register MQTT: {e}")

    try:
        ProtocolFactory.register("coap", CoAPProtocol)
        logger.info("✓ CoAP protocol registered")
    except Exception as e:
        logger.warning(f"✗ Could not register CoAP: {e}")


if __name__ == "__main__":
    # Example: Show available protocols
    print("Available protocols:")
    for protocol in ProtocolFactory.available_protocols():
        print(f"  - {protocol}")
