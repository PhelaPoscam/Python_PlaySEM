"""
Protocol servers for receiving sensory effect requests.
"""

from playsem.utils import _optional_import

CoAPServer = _optional_import(
    "playsem.protocol_servers.coap_server", "CoAPServer"
)
HTTPServer = _optional_import(
    "playsem.protocol_servers.http_server", "HTTPServer"
)
MQTTServer = _optional_import(
    "playsem.protocol_servers.mqtt_server", "MQTTServer"
)
UPnPServer = _optional_import(
    "playsem.protocol_servers.upnp_server", "UPnPServer"
)
WebSocketServer = _optional_import(
    "playsem.protocol_servers.websocket_server", "WebSocketServer"
)

__all__ = [
    name
    for name in (
        "CoAPServer",
        "HTTPServer",
        "MQTTServer",
        "UPnPServer",
        "WebSocketServer",
    )
    if globals()[name] is not None
]
