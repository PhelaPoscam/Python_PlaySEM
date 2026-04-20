"""Protocol handlers package for test server."""

from .http_handler import HTTPHandler, HTTPConfig
from .coap_handler import CoAPHandler, CoAPConfig
from .upnp_handler import UPnPHandler, UPnPConfig
from .mqtt_handler import MQTTHandler, MQTTConfig
from .websocket_handler import WebSocketHandler, WebSocketConfig

# Export handler classes and configs to match test expectations and satisfy linting
__all__ = [
    "HTTPHandler",
    "HTTPConfig",
    "CoAPHandler",
    "CoAPConfig",
    "UPnPHandler",
    "UPnPConfig",
    "MQTTHandler",
    "MQTTConfig",
    "WebSocketHandler",
    "WebSocketConfig",
]
