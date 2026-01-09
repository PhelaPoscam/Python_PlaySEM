"""
WebSocket protocol implementation for GUI communication.
"""

import json
import logging
from typing import Optional, Dict, Any, Callable

import websockets
from websockets.exceptions import WebSocketException

from .base_protocol import BaseProtocol

logger = logging.getLogger(__name__)


class WebSocketProtocol(BaseProtocol):
    """
    WebSocket communication protocol.

    Connects to a WebSocket server (typically the FastAPI backend).
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8090,
        on_message: Optional[Callable] = None,
    ):
        """
        Initialize WebSocket protocol.

        Args:
            host: WebSocket server host
            port: WebSocket server port
            on_message: Callback for incoming messages
        """
        super().__init__(host, port, on_message)
        self.uri = f"ws://{host}:{port}/ws"
        self.websocket = None

    async def connect(self) -> bool:
        """
        Connect to WebSocket server.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Connecting to WebSocket: {self.uri}")
            self.websocket = await websockets.connect(self.uri)
            self.is_connected = True
            logger.info("WebSocket connected")
            return True
        except WebSocketException as e:
            logger.error(f"WebSocket connection failed: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting WebSocket: {e}")
            self.is_connected = False
            return False

    async def disconnect(self) -> bool:
        """
        Disconnect from WebSocket server.

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.websocket:
                await self.websocket.close()
            self.is_connected = False
            logger.info("WebSocket disconnected")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket: {e}")
            return False

    async def send(self, data: Dict[str, Any]) -> bool:
        """
        Send message via WebSocket.

        Args:
            data: Dictionary to send (will be JSON-encoded)

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.is_connected or not self.websocket:
                logger.error("WebSocket not connected")
                return False

            message = json.dumps(data)
            await self.websocket.send(message)
            logger.debug(f"WebSocket sent: {message[:100]}...")
            return True
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
            self.is_connected = False
            return False

    async def listen(self):
        """
        Listen for incoming WebSocket messages (blocking).

        Calls on_message callback for each message received.
        """
        try:
            if not self.websocket:
                logger.error("WebSocket not connected, cannot listen")
                return

            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    if self.on_message:
                        self.on_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse WebSocket message: {e}")
        except Exception as e:
            logger.error(f"WebSocket listening error: {e}")
            self.is_connected = False
