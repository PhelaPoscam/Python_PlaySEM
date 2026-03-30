"""Protocol management service for modular server endpoints."""

from typing import Any, Dict, List


class ProtocolService:
    """Provides protocol bootstrap helpers for device registration."""

    def __init__(
        self,
        *,
        server_port: int,
        mqtt_port: int,
        coap_port: int,
        upnp_http_port: int,
    ) -> None:
        self.server_port = server_port
        self.mqtt_port = mqtt_port
        self.coap_port = coap_port
        self.upnp_http_port = upnp_http_port

    async def ensure_protocol_servers(self, protocols: List[str]) -> None:
        # Bootstrap wiring will move here from monolith in later steps.
        _ = protocols

    def build_protocol_endpoints(
        self,
        *,
        device_id: str,
        protocols: List[str],
        provided_endpoints: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        endpoints = dict(provided_endpoints or {})

        if "mqtt" in protocols and "mqtt" not in endpoints:
            endpoints["mqtt"] = {
                "host": "localhost",
                "port": self.mqtt_port,
                "topic": f"effects/{device_id}",
                "ws_port": 9001,
            }

        if "coap" in protocols and "coap" not in endpoints:
            endpoints["coap"] = {
                "host": "localhost",
                "port": self.coap_port,
                "path": "effects",
            }

        if "http" in protocols and "http" not in endpoints:
            endpoints["http"] = {
                "url": f"http://localhost:{self.server_port}/api/effects/inbox"
            }

        if "upnp" in protocols and "upnp" not in endpoints:
            endpoints["upnp"] = {
                "control_url": (
                    f"http://localhost:{self.upnp_http_port}/control"
                )
            }

        return endpoints
