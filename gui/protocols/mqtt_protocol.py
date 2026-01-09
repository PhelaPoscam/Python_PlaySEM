"""
MQTT protocol implementation for GUI communication.
"""

import json
import logging
import asyncio
from typing import Optional, Dict, Any, Callable

from .base_protocol import BaseProtocol

logger = logging.getLogger(__name__)


class MQTTProtocol(BaseProtocol):
    """
    MQTT communication protocol.

    Uses pub/sub model for device communication.
    Note: paho-mqtt is required: pip install paho-mqtt
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 1883,
        client_id: str = "pythonplaysem_gui",
        username: Optional[str] = None,
        password: Optional[str] = None,
        on_message: Optional[Callable] = None,
    ):
        """
        Initialize MQTT protocol.

        Args:
            host: MQTT broker host
            port: MQTT broker port (default 1883)
            client_id: MQTT client ID
            username: Optional username for authentication
            password: Optional password for authentication
            on_message: Callback for incoming messages
        """
        super().__init__(host, port, on_message)
        self.client_id = client_id
        self.username = username
        self.password = password
        self.client = None

        # MQTT topics
        self.topic_request = "playsem/gui/request"
        self.topic_response = "playsem/backend/response"
        self.topic_devices = "playsem/backend/devices"
        self.topic_device_announce = "devices/announce"  # Device announcements

        try:
            import paho.mqtt.client as mqtt

            self.mqtt = mqtt
        except ImportError:
            logger.error(
                "paho-mqtt not installed. Install with: pip install paho-mqtt"
            )
            self.mqtt = None

    async def connect(self) -> bool:
        """
        Connect to MQTT broker.

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.mqtt:
                logger.error("MQTT library not available")
                return False

            logger.info(f"Connecting to MQTT broker: {self.host}:{self.port}")

            self.client = self.mqtt.Client(client_id=self.client_id)

            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_mqtt_message
            self.client.on_disconnect = self._on_disconnect

            # Optional authentication
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)

            # Connect to broker with retries
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    self.client.connect(self.host, self.port, keepalive=60)
                    # Start background thread for MQTT loop
                    self.client.loop_start()
                    # Wait for connection to establish
                    await asyncio.sleep(1)
                    self.is_connected = True
                    logger.info("MQTT connected")
                    return True
                except Exception:
                    if attempt < max_retries - 1:
                        logger.debug(
                            f"MQTT connection attempt {attempt + 1} failed, "
                            f"retrying in 1s..."
                        )
                        await asyncio.sleep(1)
                    else:
                        raise

        except Exception as e:
            logger.error(f"MQTT connection failed: {e}")
            self.is_connected = False
            return False

    async def disconnect(self) -> bool:
        """
        Disconnect from MQTT broker.

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
            self.is_connected = False
            logger.info("MQTT disconnected")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting MQTT: {e}")
            return False

    async def send(self, data: Dict[str, Any]) -> bool:
        """
        Send message via MQTT publish.

        Args:
            data: Dictionary to send (will be JSON-encoded)

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.is_connected or not self.client:
                logger.error("MQTT not connected")
                return False

            message = json.dumps(data)
            result = self.client.publish(self.topic_request, message)

            if result.rc != self.mqtt.MQTT_ERR_SUCCESS:
                logger.error(f"MQTT publish failed: {result.rc}")
                return False

            logger.debug(f"MQTT published: {message[:100]}...")
            return True
        except Exception as e:
            logger.error(f"Error sending MQTT message: {e}")
            return False

    async def listen(self):
        """
        Listen for incoming MQTT messages (blocking).

        Calls on_message callback for each message received.
        Note: MQTT uses background thread, this is a placeholder.
        """
        try:
            # Keep listening in background
            while self.is_connected:
                await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"MQTT listening error: {e}")
            self.is_connected = False

    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when MQTT client connects to broker."""
        if rc == 0:
            logger.info("MQTT broker connection successful")
            # Subscribe to response topics
            self.client.subscribe(self.topic_response)
            self.client.subscribe(self.topic_devices)
            self.client.subscribe(self.topic_device_announce)
            logger.debug(
                f"MQTT subscribed to: {self.topic_response}, "
                f"{self.topic_devices}, {self.topic_device_announce}"
            )
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def _on_mqtt_message(self, client, userdata, msg):
        """Callback for when MQTT message is received."""
        try:
            payload = msg.payload.decode("utf-8")
            data = json.loads(payload)

            logger.debug(f"MQTT received on {msg.topic}: {payload[:100]}")

            # Handle device announcements
            if msg.topic == self.topic_device_announce:
                # Convert device announcement to device_list format
                device = {
                    "id": data.get("device_id"),
                    "name": data.get("device_name"),
                    "type": data.get("device_type"),
                    "address": data.get("device_id"),
                    "protocols": data.get("protocols", ["mqtt"]),
                    "capabilities": data.get("capabilities", []),
                    "connection_mode": "isolated",
                }
                # Wrap in device_list message
                device_list_msg = {"type": "device_list", "devices": [device]}
                if self.on_message:
                    self.on_message(device_list_msg)
            else:
                # Call registered callback for other messages
                if self.on_message:
                    self.on_message(data)
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback for when MQTT client disconnects."""
        if rc != 0:
            logger.warning(f"MQTT disconnected unexpectedly with code {rc}")
        self.is_connected = False

    def get_connection_info(self) -> str:
        """Get human-readable connection info."""
        auth = f" (auth: {self.username})" if self.username else ""
        return f"MQTT {self.host}:{self.port}{auth}"
