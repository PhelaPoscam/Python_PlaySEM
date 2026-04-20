"""Protocol handlers package for test server."""

from .http_handler import HTTPHandler, HTTPConfig  # noqa: F401
from .coap_handler import CoAPHandler, CoAPConfig  # noqa: F401
from .upnp_handler import UPnPHandler, UPnPConfig  # noqa: F401
from .mqtt_handler import MQTTHandler, MQTTConfig  # noqa: F401
from .websocket_handler import WebSocketHandler, WebSocketConfig  # noqa: F401

# Export only handler classes to match test expectations
__all__ = [
    "HTTPHandler",
    "CoAPHandler",
    "UPnPHandler",
    "MQTTHandler",
    "WebSocketHandler",
]
