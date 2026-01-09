"""
HTTP/REST protocol implementation for GUI communication.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Callable

import httpx

from .base_protocol import BaseProtocol

logger = logging.getLogger(__name__)


class HTTPProtocol(BaseProtocol):
    """
    HTTP/REST communication protocol.

    Uses HTTP requests instead of WebSocket for stateless communication.
    Polling-based for receiving messages.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8090,
        on_message: Optional[Callable] = None,
        poll_interval: float = 1.0,
    ):
        """
        Initialize HTTP protocol.

        Args:
            host: HTTP server host
            port: HTTP server port
            on_message: Callback for incoming messages
            poll_interval: Time between polls (seconds)
        """
        super().__init__(host, port, on_message)
        self.base_url = f"http://{host}:{port}/api"
        self.client: Optional[httpx.AsyncClient] = None
        self.poll_interval = poll_interval
        self._polling = False

    async def connect(self) -> bool:
        """
        Connect to HTTP server.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Connecting to HTTP: {self.base_url}")
            self.client = httpx.AsyncClient(timeout=10.0)
            # Test connection with /devices endpoint
            response = await self.client.get(f"{self.base_url}/devices")
            if response.status_code >= 200 and response.status_code < 300:
                self.is_connected = True
                logger.info("HTTP connected")
                return True
            else:
                logger.error(f"HTTP server returned {response.status_code}")
                self.is_connected = False
                return False
        except Exception as e:
            logger.error(f"HTTP connection failed: {e}")
            self.is_connected = False
            return False

    async def disconnect(self) -> bool:
        """
        Disconnect from HTTP server.

        Returns:
            True if successful, False otherwise
        """
        try:
            self._polling = False
            if self.client:
                await self.client.aclose()
            self.is_connected = False
            logger.info("HTTP disconnected")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting HTTP: {e}")
            return False

    async def send(self, data: Dict[str, Any]) -> bool:
        """
        Send message via HTTP POST.

        Args:
            data: Dictionary to send

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.is_connected or not self.client:
                logger.error("HTTP not connected")
                return False

            endpoint = data.get("endpoint", "/effect")
            response = await self.client.post(
                f"{self.base_url}{endpoint}", json=data
            )

            if response.status_code >= 200 and response.status_code < 300:
                logger.debug("HTTP sent successfully")
                return True
            else:
                logger.error(f"HTTP error: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error sending HTTP message: {e}")
            return False

    async def listen(self):
        """
        Listen for messages via HTTP polling (blocking).

        Periodically polls the server for updates.
        """
        self._polling = True
        while self._polling and self.is_connected:
            try:
                # Poll for device updates
                response = await self.client.get(f"{self.base_url}/devices")
                if response.status_code == 200:
                    data = response.json()
                    if self.on_message:
                        self.on_message({"type": "devices", "data": data})

                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"HTTP polling error: {e}")
                await asyncio.sleep(self.poll_interval)
