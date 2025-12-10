"""
Factory for creating protocol instances.

Allows easy registration and instantiation of different protocols.
"""

import logging
from typing import Dict, Type, Optional, Callable

from .base_protocol import BaseProtocol
from .websocket_protocol import WebSocketProtocol
from .http_protocol import HTTPProtocol
from .mqtt_protocol import MQTTProtocol

logger = logging.getLogger(__name__)


class ProtocolFactory:
    """Factory for creating protocol instances."""

    _protocols: Dict[str, Type[BaseProtocol]] = {
        "websocket": WebSocketProtocol,
        "http": HTTPProtocol,
        "mqtt": MQTTProtocol,
        # Future: Add more protocols
        # "coap": CoAPProtocol,
    }

    @classmethod
    def register(cls, name: str, protocol_class: Type[BaseProtocol]):
        """
        Register a new protocol.

        Args:
            name: Protocol name (e.g., "mqtt")
            protocol_class: Protocol class (must inherit from BaseProtocol)
        """
        if not issubclass(protocol_class, BaseProtocol):
            raise ValueError(
                f"{protocol_class} must inherit from BaseProtocol"
            )
        cls._protocols[name.lower()] = protocol_class
        logger.info(f"Registered protocol: {name}")

    @classmethod
    def create(
        cls,
        protocol: str,
        host: str = "127.0.0.1",
        port: int = 8090,
        on_message: Optional[Callable] = None,
        **kwargs,
    ) -> Optional[BaseProtocol]:
        """
        Create a protocol instance.

        Args:
            protocol: Protocol name (e.g., "websocket", "http")
            host: Server host
            port: Server port
            on_message: Callback for incoming messages
            **kwargs: Additional protocol-specific arguments

        Returns:
            Protocol instance or None if protocol not found
        """
        protocol_lower = protocol.lower()
        if protocol_lower not in cls._protocols:
            logger.error(f"Unknown protocol: {protocol}")
            logger.info(f"Available protocols: {list(cls._protocols.keys())}")
            return None

        protocol_class = cls._protocols[protocol_lower]
        try:
            return protocol_class(
                host=host, port=port, on_message=on_message, **kwargs
            )
        except Exception as e:
            logger.error(f"Failed to create {protocol} protocol: {e}")
            return None

    @classmethod
    def available_protocols(cls) -> list:
        """Get list of available protocol names."""
        return list(cls._protocols.keys())
