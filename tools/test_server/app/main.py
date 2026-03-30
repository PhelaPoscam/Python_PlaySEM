"""FastAPI app factory for the modular PlaySEM test server."""

import os
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from tools.test_server.config import ServerConfig
from tools.test_server.routes import (
    devices_router,
    effects_router,
    ui_router,
)
from tools.test_server.services import (
    DeviceService,
    EffectService,
    ProtocolService,
)


DEFAULT_SERVER_PORT = int(os.environ.get("PLAYSEM_SERVER_PORT", 8090))
DEFAULT_MQTT_PORT = int(os.environ.get("PLAYSEM_MQTT_PORT", 1883))
DEFAULT_COAP_PORT = int(os.environ.get("PLAYSEM_COAP_PORT", 5683))
DEFAULT_UPNP_HTTP_PORT = int(os.environ.get("PLAYSEM_UPNP_HTTP_PORT", 8008))


def create_app(config: ServerConfig | None = None) -> FastAPI:
    """Create and configure the modular test server application."""

    server_config = config or ServerConfig()
    app = FastAPI(title=server_config.app_title)
    device_service = DeviceService()
    effect_service = EffectService()
    protocol_service = ProtocolService(
        server_port=DEFAULT_SERVER_PORT,
        mqtt_port=DEFAULT_MQTT_PORT,
        coap_port=DEFAULT_COAP_PORT,
        upnp_http_port=DEFAULT_UPNP_HTTP_PORT,
    )

    app.state.device_service = device_service
    app.state.effect_service = effect_service
    app.state.protocol_service = protocol_service
    app.state.server_config = server_config
    app.state.start_time = datetime.now()

    app.include_router(devices_router)
    app.include_router(effects_router)
    app.include_router(ui_router)

    # Keep minimal baseline routes so examples and factory tests can run.
    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/stats")
    async def stats() -> dict:
        uptime = (datetime.now() - app.state.start_time).total_seconds()
        return {
            "effects_sent": effect_service.effects_sent,
            "errors": 0,
            "connected_devices": device_service.count_devices(),
            "uptime_seconds": uptime,
        }

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                message = await websocket.receive_json()
                msg_type = message.get("type")

                if msg_type == "get_devices":
                    await websocket.send_json(
                        {
                            "type": "device_list",
                            "devices": device_service.list_devices(),
                        }
                    )
                elif msg_type == "register_device":
                    device_id = message.get("device_id")
                    if device_id:
                        device_service.register_device(
                            device_id=device_id,
                            device_name=message.get("device_name", device_id),
                            device_type=message.get("device_type", "unknown"),
                            capabilities=message.get("capabilities", []),
                            protocols=message.get("protocols", []),
                            connection_mode=message.get(
                                "connection_mode", "direct"
                            ),
                            metadata={
                                "protocol_endpoints": message.get(
                                    "protocol_endpoints", {}
                                )
                            },
                        )
                        await websocket.send_json(
                            {
                                "type": "device_list",
                                "devices": device_service.list_devices(),
                            }
                        )
                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            return

    return app
