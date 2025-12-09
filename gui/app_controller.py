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

        # Callbacks for UI updates
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_device_list_updated: Optional[Callable] = None
        self.on_effect_sent: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

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

            message = {"type": "request", "action": "get_devices"}

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

            if msg_type == "devices":
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
