"""
Abstract base class for communication protocols.

This allows the GUI to be protocol-agnostic. Any protocol (WebSocket, MQTT,
CoAP, HTTP, etc.) can be plugged in by implementing this interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable
import logging

logger = logging.getLogger(__name__)


class BaseProtocol(ABC):
    """
    Abstract base class for all communication protocols.

    Subclasses implement WebSocket, MQTT, CoAP, HTTP, etc.
    """

    def __init__(
        self, host: str, port: int, on_message: Optional[Callable] = None
    ):
        """
        Initialize protocol handler.

        Args:
            host: Server host/address
            port: Server port
            on_message: Callback function for incoming messages
                       Signature: on_message(data: Dict[str, Any])
        """
        self.host = host
        self.port = port
        self.on_message = on_message
        self.is_connected = False

    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to the server.

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Disconnect from the server.

        Returns:
            True if disconnection successful, False otherwise
        """
        pass

    @abstractmethod
    async def send(self, data: Dict[str, Any]) -> bool:
        """
        Send a message to the server.

        Args:
            data: Dictionary to send

        Returns:
            True if send successful, False otherwise
        """
        pass

    @abstractmethod
    async def listen(self):
        """
        Listen for incoming messages (blocking).

        Should call self.on_message(data) when messages arrive.
        """
        pass

    def get_connection_info(self) -> str:
        """Get human-readable connection info."""
        return f"{self.__class__.__name__} ({self.host}:{self.port})"
