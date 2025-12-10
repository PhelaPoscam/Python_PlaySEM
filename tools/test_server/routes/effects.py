"""
Effect Routes - API endpoints for effect management.

Endpoints:
- POST /api/effects - Send effect to device
- POST /api/effects/protocol - Send effect via protocol
"""

from fastapi import APIRouter, WebSocket
from fastapi.responses import JSONResponse


class EffectRoutes:
    """Routes for effect management."""

    def __init__(self, router: APIRouter):
        """Initialize effect routes.

        Args:
            router: FastAPI router
        """
        self.router = router
        self._register_routes()

    def _register_routes(self):
        """Register effect routes."""

        @self.router.post("/api/effects")
        async def send_effect(
            device_id: str,
            effect_type: str,
            intensity: int = 50,
            duration: int = 1000,
            websocket: WebSocket = None,
            effect_service=None,
            devices=None,
            web_clients=None,
        ):
            """Send effect to a device.

            Args:
                device_id: Target device ID
                effect_type: Type of effect
                intensity: Effect intensity (0-100)
                duration: Duration in milliseconds
                websocket: WebSocket for status updates
                effect_service: Effect service instance
                devices: Devices dictionary
                web_clients: Web clients dictionary

            Returns:
                JSON response with result
            """
            try:
                effect_data = {
                    "effect_type": effect_type,
                    "intensity": intensity,
                    "duration": duration,
                }

                if websocket and effect_service:
                    await effect_service.send_effect(
                        websocket=websocket,
                        device_id=device_id,
                        effect_data=effect_data,
                        devices=devices or {},
                        web_clients=web_clients or {},
                    )

                return JSONResponse(
                    {
                        "type": "effect_result",
                        "success": True,
                        "device_id": device_id,
                        "effect_type": effect_type,
                    }
                )

            except Exception as e:
                print(f"[x] Effect error: {e}")
                return JSONResponse(
                    {
                        "type": "effect_result",
                        "success": False,
                        "error": str(e),
                    },
                    status_code=500,
                )

        @self.router.post("/api/effects/protocol")
        async def send_effect_protocol(
            protocol: str,
            effect_type: str,
            intensity: int = 50,
            duration: int = 1000,
            websocket: WebSocket = None,
            effect_service=None,
            mqtt_server=None,
            http_api_server=None,
            coap_server=None,
            upnp_server=None,
            web_clients=None,
        ):
            """Send effect via specific protocol.

            Args:
                protocol: Protocol name (websocket, mqtt, http, coap, upnp)
                effect_type: Type of effect
                intensity: Effect intensity
                duration: Duration in milliseconds
                websocket: WebSocket for status updates
                effect_service: Effect service instance
                mqtt_server: MQTT server instance
                http_api_server: HTTP API server instance
                coap_server: CoAP server instance
                upnp_server: UPnP server instance
                web_clients: Web clients dictionary

            Returns:
                JSON response with result
            """
            try:
                effect_data = {
                    "effect_type": effect_type,
                    "intensity": intensity,
                    "duration": duration,
                }

                if websocket and effect_service:
                    await effect_service.send_effect_protocol(
                        websocket=websocket,
                        protocol=protocol,
                        effect_data=effect_data,
                        mqtt_server=mqtt_server,
                        http_api_server=http_api_server,
                        coap_server=coap_server,
                        upnp_server=upnp_server,
                        web_clients=web_clients or {},
                    )

                return JSONResponse(
                    {
                        "type": "effect_protocol_result",
                        "success": True,
                        "protocol": protocol,
                        "effect_type": effect_type,
                    }
                )

            except Exception as e:
                print(f"[x] Effect protocol error: {e}")
                return JSONResponse(
                    {
                        "type": "effect_protocol_result",
                        "success": False,
                        "error": str(e),
                    },
                    status_code=500,
                )
