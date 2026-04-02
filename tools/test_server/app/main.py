"""FastAPI app factory for the modular PlaySEM test server."""

import os
import logging
from datetime import datetime
from typing import Dict

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

logger = logging.getLogger(__name__)

DEFAULT_SERVER_PORT = int(os.environ.get("PLAYSEM_SERVER_PORT", 8090))
DEFAULT_MQTT_PORT = int(os.environ.get("PLAYSEM_MQTT_PORT", 1883))
DEFAULT_COAP_PORT = int(os.environ.get("PLAYSEM_COAP_PORT", 5683))
DEFAULT_UPNP_HTTP_PORT = int(os.environ.get("PLAYSEM_UPNP_HTTP_PORT", 8008))


def _can_receive_broadcast(
    device_service: DeviceService,
    device_id: str,
) -> bool:
    """Return True when a websocket-bound device may receive broadcasts."""
    if not device_id:
        return False

    device = device_service.get_device(device_id)
    if not device:
        return False

    connection_mode = getattr(device, "connection_mode", "")
    return connection_mode.strip().lower() != "isolated"


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

    # Track active WebSocket connections and the device they represent.
    active_connections: Dict[WebSocket, str] = {}

    app.include_router(devices_router)
    app.include_router(effects_router)
    app.include_router(ui_router)

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

    async def broadcast_device_list() -> None:
        """Send current device list to all connected clients."""
        message = {
            "type": "device_list",
            "devices": device_service.list_devices(),
        }
        for conn in list(active_connections.keys()):
            try:
                await conn.send_json(message)
            except Exception:
                active_connections.pop(conn, None)

    async def broadcast_to_web(message: dict) -> None:
        """Send a message to web clients while respecting isolation."""
        is_broadcast = (
            message.get("device_id") == "broadcast"
            or message.get("type") in {"effect_broadcast", "effect"}
            or bool(message.get("broadcast"))
        )
        for conn, dev_id in list(active_connections.items()):
            try:
                # If it's a broadcast, skip isolated devices
                if is_broadcast:
                    if not _can_receive_broadcast(device_service, dev_id):
                        continue
                await conn.send_json(message)
            except Exception:
                if conn in active_connections:
                    active_connections.pop(conn, None)

    # Bridge protocol-received effects to web clients
    protocol_service.set_effect_callback(broadcast_to_web)

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        # Anonymous until register_device/create_device binds a device_id.
        active_connections[websocket] = ""

        try:
            # Send current device list on connect
            await websocket.send_json(
                {
                    "type": "device_list",
                    "devices": device_service.list_devices(),
                }
            )

            while True:
                message = await websocket.receive_json()
                msg_type = message.get("type", "")

                if msg_type == "get_devices":
                    await websocket.send_json(
                        {
                            "type": "device_list",
                            "devices": device_service.list_devices(),
                        }
                    )

                elif msg_type in (
                    "register_device",
                    "create_device",
                ):
                    device_id = message.get(
                        "device_id",
                        f"device_{device_service.count_devices()}",
                    )

                    # Associate this connection with the device ID
                    active_connections[websocket] = device_id

                    protocols = message.get("protocols", ["websocket"])
                    provided = (
                        message.get("metadata")
                        or message.get("protocol_endpoints")
                        or message.get("endpoints")
                        or {}
                    )
                    endpoints = protocol_service.build_protocol_endpoints(
                        device_id=device_id,
                        protocols=protocols,
                        provided_endpoints=(
                            provided if isinstance(provided, dict) else {}
                        ),
                    )
                    device_service.register_device(
                        device_id=device_id,
                        device_name=message.get("device_name", device_id),
                        device_type=message.get("device_type", "unknown"),
                        capabilities=message.get("capabilities", []),
                        protocols=protocols,
                        connection_mode=message.get(
                            "connection_mode", "direct"
                        ),
                        metadata={"protocol_endpoints": endpoints},
                    )

                    # Ensure required protocol servers are started
                    await protocol_service.ensure_protocol_servers(protocols)

                    await broadcast_device_list()
                    if msg_type == "register_device":
                        await websocket.send_json(
                            {
                                "type": "device_registered",
                                "device_id": device_id,
                                "status": "ok",
                            }
                        )

                elif msg_type == "send_effect":
                    # Route effect to a specific device
                    target_device_id = message.get("device_id")
                    effect = message.get("effect", {})

                    if not target_device_id:
                        await websocket.send_json(
                            {"type": "error", "message": "device_id required"}
                        )
                        continue

                    if not device_service.has_device(target_device_id):
                        error_msg = f"Device {target_device_id} not found"
                        await websocket.send_json(
                            {
                                "type": "effect_result",
                                "device_id": target_device_id,
                                "success": False,
                                "error": error_msg,
                            }
                        )
                        continue

                    await effect_service.send_effect(
                        device_exists=True,
                        device_id=target_device_id,
                        effect=effect,
                    )
                    effect_type = (
                        effect.get("effect_type")
                        or effect.get("type")
                        or "unknown"
                    )
                    intensity = effect.get("intensity", 50)
                    duration = effect.get("duration", 500)
                    logger.info(
                        "[SEND_EFFECT] %s -> %s (intensity=%s, duration=%s)",
                        effect_type,
                        target_device_id,
                        intensity,
                        duration,
                    )

                    # Dispatch to the specific targeted device simulation
                    effect_msg = {
                        "type": "effect",
                        "device_id": target_device_id,
                        "effect_type": effect_type,
                        "intensity": intensity,
                        "duration": duration,
                        "parameters": effect.get("parameters", {}),
                    }
                    for conn, d_id in list(active_connections.items()):
                        # Send only to the target device connection(s)
                        if d_id == target_device_id and conn != websocket:
                            try:
                                await conn.send_json(effect_msg)
                            except Exception:
                                active_connections.pop(conn, None)

                    await websocket.send_json(
                        {
                            "type": "effect_result",
                            "device_id": target_device_id,
                            "success": True,
                            "latency": 0,
                        }
                    )

                elif msg_type == "send_effect_protocol":
                    # Send effect via a chosen protocol
                    protocol = message.get("protocol", "websocket")
                    effect = message.get("effect", {})
                    await effect_service.send_effect(
                        device_exists=True,
                        device_id="broadcast",
                        effect=effect,
                        protocol=protocol,
                    )

                    # Multicast simulation to web simulation clients
                    broadcast_msg = {
                        "type": "effect",
                        "device_id": "broadcast",
                        "broadcast": True,
                        "effect_type": effect.get("effect_type", "unknown"),
                        "intensity": effect.get("intensity", 50),
                        "duration": effect.get("duration", 500),
                        "parameters": effect.get("parameters", {}),
                    }

                    # Filter: Only send broadcasts to non-isolated devices
                    for conn, d_id in list(active_connections.items()):
                        if conn != websocket:
                            if not _can_receive_broadcast(
                                device_service,
                                d_id,
                            ):
                                continue
                            try:
                                await conn.send_json(broadcast_msg)
                            except Exception:
                                active_connections.pop(conn, None)

                    logger.info(
                        "[SEND_EFFECT_PROTOCOL] %s via %s",
                        effect.get("effect_type", "unknown"),
                        protocol,
                    )
                    await websocket.send_json(
                        {
                            "type": "effect_protocol_result",
                            "protocol": protocol,
                            "success": True,
                            "effect_type": effect.get(
                                "effect_type", "unknown"
                            ),
                            "intensity": effect.get("intensity", 50),
                            "duration": effect.get("duration", 500),
                        }
                    )

                elif msg_type == "effect":
                    # Legacy simple broadcast to all non-isolated connections
                    broadcast_msg = {
                        "type": "effect_broadcast",
                        "device_id": "broadcast",
                        "broadcast": True,
                        "effect_type": message.get("effect_type"),
                        "intensity": message.get("intensity"),
                        "duration": message.get("duration"),
                    }
                    for conn, d_id in list(active_connections.items()):
                        if not _can_receive_broadcast(device_service, d_id):
                            continue
                        try:
                            await conn.send_json(broadcast_msg)
                        except Exception:
                            active_connections.pop(conn, None)

                elif msg_type in (
                    "scan_devices",
                    "scan_serial",
                ):
                    # Return mock serial devices
                    mock_devices = [
                        {
                            "port": "COM3",
                            "name": "Mock Light 1",
                            "type": "light",
                        },
                        {
                            "port": "COM4",
                            "name": "Mock Vibrator",
                            "type": "vibration",
                        },
                        {
                            "port": "COM5",
                            "name": "Mock Wind Fan",
                            "type": "wind",
                        },
                    ]
                    await websocket.send_json(
                        {
                            "type": "serial_scan_result",
                            "devices": mock_devices,
                        }
                    )

                elif msg_type == "start_protocol_server":
                    protocol = message.get("protocol", "")
                    logger.info(
                        "[PROTO] Start requested: %s",
                        protocol,
                    )
                    await websocket.send_json(
                        {
                            "type": "protocol_status",
                            "protocol": protocol,
                            "running": True,
                        }
                    )

                elif msg_type == "stop_protocol_server":
                    protocol = message.get("protocol", "")
                    logger.info(
                        "[PROTO] Stop requested: %s",
                        protocol,
                    )
                    await websocket.send_json(
                        {
                            "type": "protocol_status",
                            "protocol": protocol,
                            "running": False,
                        }
                    )

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

                else:
                    logger.debug(
                        "Unknown WS message type: %s",
                        msg_type,
                    )

        except WebSocketDisconnect:
            pass
        finally:
            if websocket in active_connections:
                active_connections.pop(websocket, None)

    return app
