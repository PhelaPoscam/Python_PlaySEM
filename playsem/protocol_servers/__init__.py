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

if CoAPServer:
    __all__.append("CoAPServer")
if HTTPServer:
    __all__.append("HTTPServer")
if MQTTServer:
    __all__.append("MQTTServer")
if UPnPServer:
    __all__.append("UPnPServer")
if WebSocketServer:
    __all__.append("WebSocketServer")
