"""
Main application controller.

Manages protocol communication and application state.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field

from .protocols import ProtocolFactory, BaseProtocol

logger = logging.getLogger(__name__)


@dataclass
class ConnectionConfig:
    """Configuration for connecting to the backend."""

    protocol: str = "websocket"
    host: str = "127.0.0.1"
    port: int = 8090
    extra_options: Dict[str, Any] = field(default_factory=dict)


class AppController:
    """
    Main application controller.

    Manages communication with the backend through a protocol abstraction.
    Emits signals for UI updates.
    """

    def __init__(self):
        """Initialize the application controller."""
        self.protocol: Optional[BaseProtocol] = None
        self.config: Optional[ConnectionConfig] = None
        self.devices: Dict[str, Any] = {}
        self.is_running = False
        self.mqtt_broker_running = False
        self.coap_server_running = False
        self.upnp_server_running = False
        self.http_server_running = False

        # Callbacks for UI updates
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_device_list_updated: Optional[Callable] = None
        self.on_effect_sent: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        self.on_server_status_changed: Optional[Callable] = None

    def set_callbacks(
        self,
        on_connected: Optional[Callable] = None,
        on_disconnected: Optional[Callable] = None,
        on_device_list_updated: Optional[Callable] = None,
        on_effect_sent: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ):
        """
        Set UI callback functions.

        Args:
            on_connected: Called when connection established
            on_disconnected: Called when connection lost
            on_device_list_updated: Called with device list
            on_effect_sent: Called with effect data
            on_error: Called with error message
        """
        if on_connected:
            self.on_connected = on_connected
        if on_disconnected:
            self.on_disconnected = on_disconnected
        if on_device_list_updated:
            self.on_device_list_updated = on_device_list_updated
        if on_effect_sent:
            self.on_effect_sent = on_effect_sent
        if on_error:
            self.on_error = on_error

    async def connect(self, config: ConnectionConfig) -> bool:
        """
        Connect to the backend server.

        Args:
            config: Connection configuration

        Returns:
            True if successful, False otherwise
        """
        try:
            self.config = config
            logger.info(
                f"Connecting via {config.protocol} to {config.host}:{config.port}"
            )

            # If using MQTT, first auto-start the backend MQTT broker via WebSocket
            if config.protocol == "mqtt":
                logger.info(
                    "MQTT requested: Auto-starting backend MQTT broker..."
                )
                if not await self._start_backend_mqtt_broker(
                    config.host, 8090
                ):
                    logger.warning(
                        "Failed to auto-start MQTT broker, will try direct "
                        "connection..."
                    )
                else:
                    self.mqtt_broker_running = True

            # Create protocol instance
            self.protocol = ProtocolFactory.create(
                protocol=config.protocol,
                host=config.host,
                port=config.port,
                on_message=self._handle_message,
                **config.extra_options,
            )

            if not self.protocol:
                raise ValueError(
                    f"Failed to create {config.protocol} protocol"
                )

            # Connect
            if not await self.protocol.connect():
                raise ConnectionError("Protocol connection failed")

            self.is_running = True
            logger.info(f"Connected: {self.protocol.get_connection_info()}")

            if self.on_connected:
                self.on_connected()

            # Start listening for messages (async task)
            asyncio.create_task(self._listen_loop())

            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            if self.on_error:
                self.on_error(str(e))
            return False

    async def start_mqtt_broker(
        self, host: str = "127.0.0.1", ws_port: int = 8090
    ) -> bool:
        """Attempt to start the backend MQTT broker via WebSocket control."""
        result = await self._start_backend_mqtt_broker(host, ws_port)
        self.mqtt_broker_running = result
        if self.on_server_status_changed:
            self.on_server_status_changed("mqtt", result)
        if not result and self.on_error:
            self.on_error("Failed to start MQTT broker on backend")
        return result

    async def start_protocol_server(
        self, protocol: str, host: str = "127.0.0.1", ws_port: int = 8090
    ) -> bool:
        """Start a protocol server (coap, upnp, http) via WebSocket control."""
        try:
            if not self.protocol or not self.protocol.is_connected:
                raise ConnectionError("Not connected to backend")

            message = {"type": "start_protocol_server", "protocol": protocol}
            if await self.protocol.send(message):
                # Mark as running (best-effort; may need response validation)
                if protocol == "coap":
                    self.coap_server_running = True
                elif protocol == "upnp":
                    self.upnp_server_running = True
                elif protocol == "http":
                    self.http_server_running = True
                if self.on_server_status_changed:
                    self.on_server_status_changed(protocol, True)
                logger.info(f"{protocol.upper()} server started")
                return True
            else:
                raise RuntimeError(
                    f"Failed to send start command for {protocol}"
                )
        except Exception as e:
            logger.error(f"Error starting {protocol} server: {e}")
            if self.on_error:
                self.on_error(f"Failed to start {protocol}: {e}")
            return False

    async def stop_protocol_server(
        self, protocol: str, host: str = "127.0.0.1", ws_port: int = 8090
    ) -> bool:
        """Stop a protocol server via WebSocket control."""
        try:
            if not self.protocol or not self.protocol.is_connected:
                raise ConnectionError("Not connected to backend")

            message = {"type": "stop_protocol_server", "protocol": protocol}
            if await self.protocol.send(message):
                # Mark as not running
                if protocol == "coap":
                    self.coap_server_running = False
                elif protocol == "upnp":
                    self.upnp_server_running = False
                elif protocol == "http":
                    self.http_server_running = False
                if self.on_server_status_changed:
                    self.on_server_status_changed(protocol, False)
                logger.info(f"{protocol.upper()} server stopped")
                return True
            else:
                raise RuntimeError(
                    f"Failed to send stop command for {protocol}"
                )
        except Exception as e:
            logger.error(f"Error stopping {protocol} server: {e}")
            if self.on_error:
                self.on_error(f"Failed to stop {protocol}: {e}")
            return False

    async def _start_backend_mqtt_broker(
        self, host: str, ws_port: int
    ) -> bool:
        """
        Connect via WebSocket and send command to start MQTT broker on backend.

        Args:
            host: Backend host
            ws_port: WebSocket port (usually 8090)

        Returns:
            True if MQTT broker started, False otherwise
        """
        try:
            import websockets
            import json

            uri = f"ws://{host}:{ws_port}/ws"
            logger.debug(
                f"Attempting to start MQTT broker via WebSocket: {uri}"
            )

            async with websockets.connect(uri, ping_interval=20) as websocket:
                # Send command to start MQTT protocol server
                command = {"type": "start_protocol_server", "protocol": "mqtt"}
                await websocket.send(json.dumps(command))
                logger.info("Sent MQTT broker start command to backend")

                # Wait for response with timeout
                response = await asyncio.wait_for(
                    websocket.recv(), timeout=5.0
                )
                response_data = json.loads(response)

                if (
                    response_data.get("type") == "protocol_status"
                    and response_data.get("protocol") == "mqtt"
                ):
                    if response_data.get("running"):
                        logger.info(
                            "MQTT broker started successfully on backend"
                        )
                        await asyncio.sleep(1)  # Give broker time to start
                        return True
                    else:
                        error_msg = response_data.get("error", "Unknown error")
                        logger.error(
                            f"MQTT broker failed to start: {error_msg}"
                        )
                        return False
                else:
                    logger.warning(f"Unexpected response: {response_data}")
                    return False

        except asyncio.TimeoutError:
            logger.debug("Timeout waiting for MQTT broker startup response")
            return False
        except Exception as e:
            logger.debug(
                f"Failed to auto-start MQTT broker via WebSocket: {e}"
            )
            return False

    async def disconnect(self) -> bool:
        """
        Disconnect from the backend server.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.is_running = False
            if self.protocol:
                await self.protocol.disconnect()

            logger.info("Disconnected")
            if self.on_disconnected:
                self.on_disconnected()

            return True
        except Exception as e:
            logger.error(f"Disconnection error: {e}")
            return False

    async def send_effect(self, effect_data: Dict[str, Any]) -> bool:
        """
        Send an effect command to the backend.

        Args:
            effect_data: Effect parameters

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.protocol or not self.protocol.is_connected:
                raise ConnectionError("Not connected")

            message = {"type": "effect", "payload": effect_data}

            if await self.protocol.send(message):
                logger.info(
                    f"Effect sent: {effect_data.get('effect_type', 'unknown')}"
                )
                if self.on_effect_sent:
                    self.on_effect_sent(effect_data)
                return True
            else:
                raise RuntimeError("Send failed")
        except Exception as e:
            logger.error(f"Error sending effect: {e}")
            if self.on_error:
                self.on_error(f"Failed to send effect: {e}")
            return False

    async def scan_devices(self) -> bool:
        """
        Request device list from backend.

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.protocol or not self.protocol.is_connected:
                raise ConnectionError("Not connected")

            message = {"type": "get_devices"}

            return await self.protocol.send(message)
        except Exception as e:
            logger.error(f"Error scanning devices: {e}")
            if self.on_error:
                self.on_error(str(e))
            return False

    async def connect_device(self, device_info: Dict[str, Any]) -> bool:
        """
        Connect to a specific device.

        Args:
            device_info: Device information

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.protocol or not self.protocol.is_connected:
                raise ConnectionError("Not connected")

            message = {
                "type": "request",
                "action": "connect_device",
                "device": device_info,
            }

            return await self.protocol.send(message)
        except Exception as e:
            logger.error(f"Error connecting device: {e}")
            if self.on_error:
                self.on_error(str(e))
            return False

    def _handle_message(self, data: Dict[str, Any]):
        """
        Handle incoming message from backend.

        Args:
            data: Message data
        """
        try:
            msg_type = data.get("type", "")

            if msg_type == "device_list":
                devices = data.get("devices", [])
                self.devices = {d["id"]: d for d in devices}
                if self.on_device_list_updated:
                    self.on_device_list_updated(devices)

            elif msg_type == "devices":
                # Legacy support for different format
                self.devices = {d["id"]: d for d in data.get("payload", [])}
                if self.on_device_list_updated:
                    self.on_device_list_updated(data.get("payload", []))

            elif msg_type == "effect":
                logger.info(f"Effect status: {data.get('payload', {})}")

            elif msg_type == "error":
                error_msg = data.get("payload", "Unknown error")
                logger.error(f"Backend error: {error_msg}")
                if self.on_error:
                    self.on_error(error_msg)

            else:
                logger.debug(f"Received message: {msg_type}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def _listen_loop(self):
        """Listen for incoming messages (async loop)."""
        try:
            await self.protocol.listen()
        except Exception as e:
            logger.error(f"Listen loop error: {e}")
            self.is_running = False
            if self.on_disconnected:
                self.on_disconnected()
