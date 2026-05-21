"""
Protocol servers for receiving sensory effect requests.
"""

# Optional protocol servers (require extra dependencies)
try:
    from .coap_server import CoAPServer
except ImportError:
    CoAPServer = None  # type: ignore

try:
    from .http_server import HTTPServer
except ImportError:
    HTTPServer = None  # type: ignore

try:
    from .mqtt_server import MQTTServer
except ImportError:
    MQTTServer = None  # type: ignore

try:
    from .upnp_server import UPnPServer
except ImportError:
    UPnPServer = None  # type: ignore

try:
    from .websocket_server import WebSocketServer
except ImportError:
    WebSocketServer = None  # type: ignore

__all__ = []

if CoAPServer is not None:
    __all__.append("CoAPServer")
if HTTPServer is not None:
    __all__.append("HTTPServer")
if MQTTServer is not None:
    __all__.append("MQTTServer")
if UPnPServer is not None:
    __all__.append("UPnPServer")
if WebSocketServer is not None:
    __all__.append("WebSocketServer")
