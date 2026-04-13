#!/usr/bin/env python3
"""
PlaySEM Test Server - for testing and UI demos.
"""

import sys
import os
from unittest.mock import call, MagicMock
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import yaml

# --- Configurable Ports (can be overridden by environment variables) ---
DEFAULT_SERVER_PORT = int(os.environ.get("PLAYSEM_SERVER_PORT", 8090))
DEFAULT_MQTT_PORT = int(os.environ.get("PLAYSEM_MQTT_PORT", 1883))
DEFAULT_COAP_PORT = int(os.environ.get("PLAYSEM_COAP_PORT", 5683))
DEFAULT_UPNP_HTTP_PORT = int(os.environ.get("PLAYSEM_UPNP_HTTP_PORT", 8008))
# --------------------------------------------------------------------

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from tools.test_server.handlers import (
    HTTPHandler,
    HTTPConfig,
    CoAPHandler,
    CoAPConfig,
    MQTTHandler,
    MQTTConfig,
    WebSocketHandler,
    WebSocketConfig,
    UPnPHandler,
    UPnPConfig,
)
from tools.test_server.app import create_app
from tools.test_server.config import ServerConfig
from playsem.protocol_servers import MQTTServer, CoAPServer, UPnPServer


class ConnectedDevice:
    """Mock connected device."""

    def __init__(
        self,
        device_id: str,
        device_name: str,
        device_type: str,
        capabilities: List[str],
        protocols: List[str],
        connection_mode: str = "direct",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.device_id = device_id
        self.device_name = device_name
        self.name = device_name
        self.device_type = device_type
        self.capabilities = capabilities
        self.protocols = protocols
        self.connection_mode = connection_mode
        self.connected = True
        self.websocket: Optional[WebSocket] = None
        self.metadata: Dict[str, Any] = metadata or {}


class ControlPanelServer:
    """PlaySEM Control Panel Server."""

    def __init__(self):
        self.app = FastAPI(title="PlaySEM Test Server")
        self.devices: Dict[str, ConnectedDevice] = {}
        self.effects_sent = 0
        self.errors = 0
        self.start_time = datetime.now()
        self.active_connections: List[WebSocket] = []
        self.clients = set()  # WebSocket clients for broadcasts
        self.web_clients: Dict[str, WebSocket] = (
            {}
        )  # Device-id keyed websockets
        self.effect_inbox: List[dict] = (
            []
        )  # simple HTTP inbox for observed effects
        # Protocol handlers
        self.http_handler = HTTPHandler(config=HTTPConfig())
        self.coap_handler = CoAPHandler(config=CoAPConfig())
        self.mqtt_handler = MQTTHandler(config=MQTTConfig())
        self.websocket_handler = WebSocketHandler(config=WebSocketConfig())
        self.upnp_handler = UPnPHandler(config=UPnPConfig())

        # Minimal timeline player stub for shutdown tests
        class _DummyTimeline:
            def stop(self):
                print("[TIMELINE] stop called")

        self.timeline_player = _DummyTimeline()
        # Embedded protocol servers (started on-demand)
        self.mqtt_server: Optional[MQTTServer] = None
        self.mqtt_port = DEFAULT_MQTT_PORT
        self.coap_server: Optional[CoAPServer] = None
        self.coap_port = DEFAULT_COAP_PORT
        self.upnp_server: Optional[UPnPServer] = None
        self.upnp_http_port = DEFAULT_UPNP_HTTP_PORT
        self.mqtt_ready = False
        self.coap_ready = False
        self.upnp_ready = False
        self._setup_routes()

    class _DummyDispatcher:
        """Minimal dispatcher to satisfy protocol servers."""

        def dispatch_effect_metadata(self, effect):
            print(
                f"[DISPATCH] Effect received by embedded server: {getattr(effect, 'effect_type', 'unknown')}"
            )

    async def _ensure_protocol_servers(self, protocols: List[str]):
        """Start embedded servers needed for requested protocols."""

        if "mqtt" in protocols and not self.mqtt_ready:
            try:
                self.mqtt_server = MQTTServer(
                    dispatcher=self._DummyDispatcher(),
                    host="0.0.0.0",
                    port=self.mqtt_port,
                )
                # MQTTServer.start() is sync (spawns thread)
                await asyncio.to_thread(self.mqtt_server.start)
                self.mqtt_ready = True
                print(
                    f"[BOOT] Embedded MQTT broker started on 0.0.0.0:{self.mqtt_port}"
                )
            except Exception as e:
                print(f"[BOOT] Failed to start embedded MQTT broker: {e}")
                self.mqtt_ready = False  # Ensure not marked ready on failure

        if "coap" in protocols and not self.coap_ready:
            try:
                self.coap_server = CoAPServer(
                    host="0.0.0.0",
                    port=self.coap_port,
                    dispatcher=self._DummyDispatcher(),
                )
                await self.coap_server.start()
                self.coap_ready = True
                print(
                    f"[BOOT] Embedded CoAP server started on coap://0.0.0.0:{self.coap_port}/effects"
                )
            except Exception as e:
                print(f"[BOOT] Failed to start embedded CoAP server: {e}")
                self.coap_ready = False  # Ensure not marked ready on failure

        if "upnp" in protocols and not self.upnp_ready:
            try:
                # Use local host detection from server; advertise control at /control
                self.upnp_server = UPnPServer(
                    friendly_name="PlaySEM Test Server",
                    http_port=self.upnp_http_port,
                )
                await self.upnp_server.start()
                await self.upnp_server.wait_until_ready()
                self.upnp_ready = True
                print(
                    f"[BOOT] Embedded UPnP server started at http://{self.upnp_server.http_host}:{self.upnp_server.http_port}"
                )
            except Exception as e:
                print(f"[BOOT] Failed to start embedded UPnP server: {e}")
                self.upnp_ready = False  # Ensure not marked ready on failure

    def _setup_routes(self):
        """Setup FastAPI routes."""

        async def route_effect(
            protocol: str, effect_msg: dict, endpoint: Optional[Dict[str, Any]]
        ) -> bool:
            protocol = (protocol or "websocket").lower()
            endpoint = endpoint or {}

            if protocol == "websocket":
                return False  # handled by WS path
            if protocol == "mqtt":
                # Endpoint overrides config
                cfg = (
                    MQTTConfig(
                        **{**self.mqtt_handler.config.__dict__, **endpoint}
                    )
                    if endpoint
                    else self.mqtt_handler.config
                )
                handler = MQTTHandler(config=cfg)
                return await handler.send(effect_msg)
            if protocol == "http":
                cfg = (
                    HTTPConfig(
                        **{**self.http_handler.config.__dict__, **endpoint}
                    )
                    if endpoint
                    else self.http_handler.config
                )
                handler = HTTPHandler(config=cfg)
                return await handler.send(effect_msg)
            if protocol == "coap":
                cfg = (
                    CoAPConfig(
                        **{**self.coap_handler.config.__dict__, **endpoint}
                    )
                    if endpoint
                    else self.coap_handler.config
                )
                handler = CoAPHandler(config=cfg)
                return await handler.send(effect_msg)
            if protocol == "serial":
                # Serial handled inline (keep existing logic)
                try:
                    import serial
                except ImportError:
                    print(
                        "[PROTO] Serial send skipped: pyserial not installed"
                    )
                    return False

                port = endpoint.get("port") if endpoint else None
                baudrate = int((endpoint or {}).get("baudrate", 115200))
                if not port:
                    print("[PROTO] Serial send skipped: no port provided")
                    return False

                effect_type = effect_msg.get("effect_type", "UNKNOWN").upper()
                intensity = int(effect_msg.get("intensity", 0))
                duration = int(effect_msg.get("duration", 0))
                command = (
                    f"EFFECT:{effect_type}:{intensity}:{duration}\n".encode(
                        "utf-8"
                    )
                )

                def _send():
                    with serial.Serial(
                        port=port, baudrate=baudrate, timeout=1
                    ) as ser:
                        ser.write(command)
                    return True

                try:
                    return await asyncio.to_thread(_send)
                except Exception as e:
                    print(f"[PROTO] Serial send failed: {e}")
                    return False
            if protocol == "upnp":
                cfg = (
                    UPnPConfig(
                        **{**self.upnp_handler.config.__dict__, **endpoint}
                    )
                    if endpoint
                    else self.upnp_handler.config
                )
                handler = UPnPHandler(config=cfg)
                return await handler.send(effect_msg)
            print(f"[PROTO] Unknown protocol '{protocol}', skipping")
            return False

        @self.app.get("/")
        async def root():
            return HTMLResponse(
                f"<h1>PlaySEM Test Server</h1><p>Running on port {DEFAULT_SERVER_PORT}</p>"
            )

        @self.app.get("/health")
        async def health():
            return {"status": "ok"}

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for UI demos."""
            await websocket.accept()
            self.active_connections.append(websocket)
            device_id_on_this_conn = None

            try:
                # Send current devices on connection
                await websocket.send_json(
                    {
                        "type": "device_list",
                        "devices": [
                            {
                                "id": d.device_id,
                                "name": d.device_name,
                                "type": d.device_type,
                                "capabilities": d.capabilities,
                                "protocols": d.protocols,
                                "connection_mode": d.connection_mode,
                                "connected": d.connected,
                            }
                            for d in self.devices.values()
                        ],
                    }
                )

                while True:
                    data = await websocket.receive_json()
                    msg_type = data.get("type", "")

                    if msg_type == "effect":
                        # Simple broadcast effect
                        message = {
                            "type": "effect_broadcast",
                            "effect_type": data.get("effect_type"),
                            "intensity": data.get("intensity"),
                            "duration": data.get("duration"),
                        }
                        for conn in self.active_connections:
                            await conn.send_json(message)
                        continue

                    if msg_type == "scan_serial":
                        # Return mock serial devices
                        devices = [
                            {
                                "port": "COM3",
                                "name": "Mock Light 1",
                                "type": "light",
                            },
                            {
                                "port": "COM4",
                                "name": "Mock Device 2",
                                "type": "vibrator",
                            },
                            {
                                "port": "COM5",
                                "name": "Mock Receiver",
                                "type": "receiver",
                            },
                        ]
                        await websocket.send_json(
                            {"type": "serial_scan_result", "devices": devices}
                        )

                    elif msg_type in ("create_device", "register_device"):
                        # Create a new device (from super_receiver registration)
                        device_id = data.get(
                            "device_id", f"device_{len(self.devices)}"
                        )
                        device_name = data.get("device_name", device_id)
                        device_type = data.get("device_type", "unknown")
                        connection_mode = data.get("connection_mode", "direct")

                        print(
                            f"[REGISTER] Device: {device_name} ({device_id}) Type: {device_type} Mode: {connection_mode}"
                        )

                        await self._ensure_protocol_servers(
                            data.get("protocols", [])
                        )

                        # Build/augment protocol endpoints
                        provided_endpoints = (
                            data.get("metadata")
                            or data.get("protocol_endpoints")
                            or data.get("endpoints")
                            or {}
                        )
                        endpoints = (
                            provided_endpoints
                            if isinstance(provided_endpoints, dict)
                            else {}
                        )

                        if isinstance(endpoints, dict):
                            if (
                                "mqtt" in data.get("protocols", [])
                                and "mqtt" not in endpoints
                            ):
                                endpoints["mqtt"] = {
                                    "host": "localhost",
                                    "port": self.mqtt_port,
                                    "topic": f"effects/{device_id}",
                                    "ws_port": 9001,
                                }
                            if (
                                "coap" in data.get("protocols", [])
                                and "coap" not in endpoints
                            ):
                                endpoints["coap"] = {
                                    "host": "localhost",
                                    "port": self.coap_port,
                                    "path": "effects",
                                }
                            if (
                                "http" in data.get("protocols", [])
                                and "http" not in endpoints
                            ):
                                endpoints["http"] = {
                                    "url": f"http://localhost:{DEFAULT_SERVER_PORT}/api/effects/inbox",
                                }
                            if (
                                "upnp" in data.get("protocols", [])
                                and "upnp" not in endpoints
                            ):
                                control_host = "localhost"
                                control_port = self.upnp_http_port
                                endpoints["upnp"] = {
                                    "control_url": f"http://{control_host}:{control_port}/control",
                                }

                        device = ConnectedDevice(
                            device_id=device_id,
                            device_name=device_name,
                            device_type=device_type,
                            capabilities=data.get("capabilities", []),
                            protocols=data.get("protocols", []),
                            connection_mode=connection_mode,
                            metadata={"protocol_endpoints": endpoints},
                        )
                        device.websocket = websocket  # Track which connection owns this device
                        self.devices[device_id] = device
                        device_id_on_this_conn = device_id

                        # Broadcast updated device list to all clients
                        message = {
                            "type": "device_list",
                            "devices": [
                                {
                                    "id": d.device_id,
                                    "name": d.device_name,
                                    "type": d.device_type,
                                    "capabilities": d.capabilities,
                                    "protocols": d.protocols,
                                    "connection_mode": d.connection_mode,
                                    "connected": d.connected,
                                    "protocol_endpoints": d.metadata.get(
                                        "protocol_endpoints", {}
                                    ),
                                }
                                for d in self.devices.values()
                            ],
                        }
                        for conn in self.active_connections:
                            try:
                                await conn.send_json(message)
                            except:
                                pass

                        # Send confirmation to the registering device
                        if msg_type == "register_device":
                            await websocket.send_json(
                                {
                                    "type": "device_registered",
                                    "device_id": device_id,
                                    "status": "ok",
                                }
                            )

                    elif msg_type == "get_devices":
                        # Send current devices list
                        await websocket.send_json(
                            {
                                "type": "device_list",
                                "devices": [
                                    {
                                        "id": d.device_id,
                                        "name": d.device_name,
                                        "type": d.device_type,
                                        "capabilities": d.capabilities,
                                        "protocols": d.protocols,
                                        "connection_mode": d.connection_mode,
                                        "connected": d.connected,
                                    }
                                    for d in self.devices.values()
                                ],
                            }
                        )

                    elif msg_type == "send_effect":
                        # Route effect to specific device
                        device_id = data.get("device_id")
                        effect = data.get("effect", {})

                        print(f"[SEND_EFFECT] Raw payload: {data}")

                        print(
                            f"[SEND_EFFECT] Attempting to send effect to device: {device_id}"
                        )
                        print(
                            f"[SEND_EFFECT] Available devices: {list(self.devices.keys())}"
                        )

                        if not device_id:
                            await websocket.send_json(
                                {
                                    "type": "error",
                                    "message": "device_id required",
                                }
                            )
                            continue

                        if device_id not in self.devices:
                            print(
                                f"[SEND_EFFECT] Device {device_id} not found!"
                            )
                            await websocket.send_json(
                                {
                                    "type": "effect_result",
                                    "device_id": device_id,
                                    "success": False,
                                    "error": f"Device {device_id} not found",
                                }
                            )
                            continue

                        device = self.devices[device_id]
                        self.effects_sent += 1

                        print(
                            f"[SEND_EFFECT] Device found: {device.device_name}, has websocket: {device.websocket is not None}"
                        )

                        # Send effect to the device's WebSocket
                        effect_type = (
                            effect.get("effect_type")
                            or effect.get("type")
                            or data.get("effect_type")
                            or data.get("modality")
                            or "vibration"
                        )
                        intensity = effect.get(
                            "intensity", data.get("intensity", 50)
                        )
                        duration = effect.get(
                            "duration", data.get("duration", 500)
                        )

                        chosen_protocol = data.get("protocol", "websocket")

                        effect_msg = {
                            "type": "effect",
                            "device_id": device_id,
                            "effect_type": effect_type,
                            "intensity": intensity,
                            "duration": duration,
                            "protocol": chosen_protocol,
                        }

                        # Try protocol-specific route first if endpoint is provided
                        endpoint = None
                        meta = device.metadata or {}
                        endpoints = (
                            meta.get("protocol_endpoints")
                            or meta.get("endpoints")
                            or meta
                        )
                        if isinstance(endpoints, dict):
                            endpoint = endpoints.get(chosen_protocol)

                        sent = False
                        if endpoint:
                            # Strip UI-only keys that the handler config does not accept
                            endpoint_clean = dict(endpoint)
                            if chosen_protocol == "mqtt":
                                endpoint_clean.pop("ws_port", None)
                            sent = await route_effect(
                                chosen_protocol, effect_msg, endpoint_clean
                            )
                            if sent:
                                print(
                                    f"[SEND_EFFECT] Sent via {chosen_protocol} endpoint: {endpoint}"
                                )

                        # Fallback to device websocket if not already sent
                        if not sent and device.websocket:
                            try:
                                print(
                                    f"[SEND_EFFECT] Sending effect to device connection: {effect_msg}"
                                )
                                await device.websocket.send_json(effect_msg)
                                sent = True
                                print(
                                    f"[SEND_EFFECT] Effect sent successfully to device!"
                                )
                            except Exception as e:
                                print(
                                    f"[SEND_EFFECT] Failed to send to device websocket: {e}"
                                )

                        # Fallback: broadcast to all other connections (e.g., if device websocket changed)
                        if not sent:
                            print(
                                "[SEND_EFFECT] Fallback broadcast to other connections"
                            )
                            for conn in self.active_connections:
                                if conn != websocket:
                                    try:
                                        await conn.send_json(effect_msg)
                                        sent = True
                                    except Exception as e:
                                        print(
                                            f"[SEND_EFFECT] Fallback send failed: {e}"
                                        )

                        # Send success acknowledgement to controller
                        await websocket.send_json(
                            {
                                "type": "effect_result",
                                "device_id": device_id,
                                "success": sent,
                            }
                        )

                    elif msg_type == "send_effect_protocol":
                        await self.send_effect_protocol(
                            websocket,
                            data.get("protocol", "websocket"),
                            data.get("effect", {}),
                        )

                    elif msg_type == "start_protocol_server":
                        await self.start_protocol_server(
                            websocket, data.get("protocol")
                        )

                    elif msg_type == "stop_protocol_server":
                        await self.stop_protocol_server(
                            websocket, data.get("protocol")
                        )

            except WebSocketDisconnect:
                self.active_connections.remove(websocket)
                # Mark device as disconnected if one was registered on this connection
                if (
                    device_id_on_this_conn
                    and device_id_on_this_conn in self.devices
                ):
                    del self.devices[device_id_on_this_conn]
                    # Broadcast updated device list
                    message = {
                        "type": "device_list",
                        "devices": [
                            {
                                "id": d.device_id,
                                "name": d.device_name,
                                "type": d.device_type,
                                "capabilities": d.capabilities,
                                "protocols": d.protocols,
                                "connection_mode": d.connection_mode,
                                "connected": d.connected,
                            }
                            for d in self.devices.values()
                        ],
                    }
                    for conn in self.active_connections:
                        try:
                            await conn.send_json(message)
                        except:
                            pass
            except Exception as e:
                print(f"WebSocket error: {e}")
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)
                await websocket.close(code=1000)

        @self.app.get("/api/stats")
        async def stats():
            """Get server statistics."""
            uptime = (datetime.now() - self.start_time).total_seconds()
            return {
                "effects_sent": self.effects_sent,
                "errors": self.errors,
                "connected_devices": len(self.devices),
                "uptime_seconds": uptime,
            }

        @self.app.post("/api/devices/register")
        async def register_device(body: dict):
            """Register a device."""
            device_id = body.get("device_id")
            if not device_id:
                raise HTTPException(
                    status_code=400, detail="device_id required"
                )

            await self._ensure_protocol_servers(body.get("protocols", []))
            provided_endpoints = (
                body.get("metadata")
                or body.get("protocol_endpoints")
                or body.get("endpoints")
                or {}
            )
            endpoints = (
                provided_endpoints
                if isinstance(provided_endpoints, dict)
                else {}
            )
            if isinstance(endpoints, dict):
                if (
                    "mqtt" in body.get("protocols", [])
                    and "mqtt" not in endpoints
                ):
                    endpoints["mqtt"] = {
                        "host": "localhost",
                        "port": self.mqtt_port,
                        "topic": f"effects/{device_id}",
                        "ws_port": 9001,
                    }
                if (
                    "coap" in body.get("protocols", [])
                    and "coap" not in endpoints
                ):
                    endpoints["coap"] = {
                        "host": "localhost",
                        "port": self.coap_port,
                        "path": "effects",
                    }
                if (
                    "http" in body.get("protocols", [])
                    and "http" not in endpoints
                ):
                    endpoints["http"] = {
                        "url": f"http://localhost:{DEFAULT_SERVER_PORT}/api/effects/inbox"
                    }
                if (
                    "upnp" in body.get("protocols", [])
                    and "upnp" not in endpoints
                ):
                    endpoints["upnp"] = {
                        "control_url": f"http://localhost:{self.upnp_http_port}/control"
                    }

            device = ConnectedDevice(
                device_id=device_id,
                device_name=body.get("device_name", device_id),
                device_type=body.get("device_type", "unknown"),
                capabilities=body.get("capabilities", []),
                protocols=body.get("protocols", []),
                metadata={"protocol_endpoints": endpoints},
            )
            self.devices[device_id] = device
            return {
                "success": True,
                "device_id": device_id,
                "status": "registered",
            }

        @self.app.post("/api/connect")
        async def connect_device(body: dict):
            """Connect a device."""
            address = body.get("address")
            driver_type = body.get("driver_type", "unknown")
            if not address:
                raise HTTPException(status_code=400, detail="address required")

            device_id = f"{driver_type}_{address}"
            device = ConnectedDevice(
                device_id=device_id,
                device_name=address,
                device_type=driver_type,
                capabilities=[],
                protocols=[],
            )
            self.devices[device_id] = device
            self.effects_sent += 1
            return {
                "type": "success",
                "device_id": device_id,
                "message": f"Connected to {address}",
            }

        @self.app.post("/api/effect")
        async def send_effect(body: dict):
            """Send effect to a device."""
            device_id = body.get("device_id")
            effect = body.get("effect", {})

            if not device_id:
                raise HTTPException(
                    status_code=400, detail="device_id required"
                )

            if device_id not in self.devices:
                raise HTTPException(
                    status_code=404, detail=f"Device {device_id} not found"
                )

            self.effects_sent += 1
            return {
                "success": True,
                "device_id": device_id,
                "effect_type": effect.get("effect_type", "unknown"),
                "message": "Effect sent successfully",
            }

        @self.app.post("/api/effects/inbox")
        async def inbox_add(effect: dict):
            """Store an incoming effect for observation (lightweight HTTP inbox)."""
            effect_record = {
                "received_at": datetime.utcnow().isoformat() + "Z",
                "effect": effect,
            }
            self.effect_inbox.append(effect_record)
            return {"stored": True, "count": len(self.effect_inbox)}

        @self.app.get("/api/effects/inbox")
        async def inbox_list():
            """List (and optionally clear) observed effects."""
            clear = False
            items = list(self.effect_inbox)
            if clear:
                self.effect_inbox.clear()
            return {"effects": items, "count": len(items)}

        @self.app.get("/api/device-templates")
        async def list_device_templates():
            """List available device config files."""
            config_dir = Path(__file__).resolve().parents[2] / "config"
            templates = []
            for yaml_file in sorted(config_dir.glob("device_*.yaml")):
                try:
                    with open(yaml_file) as f:
                        data = yaml.safe_load(f)
                    device_info = data.get("device", {})
                    templates.append(
                        {
                            "file": yaml_file.name,
                            "id": device_info.get("id", "unknown"),
                            "name": device_info.get("name", "Unknown Device"),
                            "type": device_info.get("type", "unknown"),
                            "protocol": device_info.get("connection", {}).get(
                                "protocol", "unknown"
                            ),
                        }
                    )
                except Exception as e:
                    print(f"[CONFIG] Error reading {yaml_file.name}: {e}")
            return {"templates": templates}

        @self.app.post("/api/device-load")
        async def load_device(body: dict):
            """Load and register a device from YAML config."""
            config_file = body.get("file")
            if not config_file:
                raise HTTPException(
                    status_code=400, detail="file parameter required"
                )

            config_dir = Path(__file__).resolve().parents[2] / "config"
            yaml_path = config_dir / config_file

            if not yaml_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Config file {config_file} not found",
                )

            try:
                with open(yaml_path) as f:
                    data = yaml.safe_load(f)

                device_info = data.get("device", {})
                device_id = device_info.get("id")
                if not device_id:
                    raise HTTPException(
                        status_code=400, detail="Device config missing 'id'"
                    )

                protocols = []
                connection = device_info.get("connection", {})
                if connection.get("protocol"):
                    protocols = [connection["protocol"]]

                endpoints = device_info.get("protocol_endpoints", {})

                # Start protocol servers as needed
                await self._ensure_protocol_servers(protocols)

                # Create and register device
                device = ConnectedDevice(
                    device_id=device_id,
                    device_name=device_info.get("name", device_id),
                    device_type=device_info.get("type", "unknown"),
                    capabilities=device_info.get("capabilities", []),
                    protocols=protocols,
                    connection_mode=connection.get("mode", "direct"),
                    metadata={"protocol_endpoints": endpoints},
                )
                self.devices[device_id] = device

                print(
                    f"[LOADED] Device from config: {device_id} ({device.device_name})"
                )

                return {
                    "success": True,
                    "device_id": device_id,
                    "device_name": device.device_name,
                    "protocols": protocols,
                }
            except yaml.YAMLError as e:
                raise HTTPException(
                    status_code=400, detail=f"YAML parse error: {e}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Failed to load device: {e}"
                )

        @self.app.get("/api/devices")
        async def list_devices():
            """List all devices."""
            return {
                "devices": [
                    {
                        "id": d.device_id,
                        "device_id": d.device_id,
                        "device_name": d.device_name,
                        "device_type": d.device_type,
                        "capabilities": d.capabilities,
                        "protocols": d.protocols,
                        "connection_mode": d.connection_mode,
                        "connected": d.connected,
                        "protocol_endpoints": d.metadata.get(
                            "protocol_endpoints", {}
                        ),
                    }
                    for d in self.devices.values()
                ]
            }

        @self.app.get("/api/capabilities/{device_id}")
        async def get_capabilities(device_id: str):
            """Get device capabilities."""
            if device_id not in self.devices:
                raise HTTPException(
                    status_code=404, detail=f"Device {device_id} not found"
                )

            device = self.devices[device_id]
            return {
                "device_id": device_id,
                "capabilities": device.capabilities,
                "protocols": device.protocols,
                "type": device.device_type,
            }

    def _device_to_dict(self, device):
        """Serialize device-like object to dict for API/WS responses."""
        return {
            "id": getattr(device, "device_id", getattr(device, "id", None)),
            "device_id": getattr(
                device, "device_id", getattr(device, "id", None)
            ),
            "device_name": getattr(
                device, "device_name", getattr(device, "name", "")
            ),
            "device_type": getattr(
                device, "device_type", getattr(device, "type", "")
            ),
            "name": getattr(
                device, "device_name", getattr(device, "name", "")
            ),
            "type": getattr(
                device, "device_type", getattr(device, "type", "")
            ),
            "capabilities": getattr(device, "capabilities", []),
            "protocols": getattr(device, "protocols", []),
            "connection_mode": getattr(device, "connection_mode", "direct"),
            "connected": getattr(device, "connected", True),
            "protocol_endpoints": getattr(device, "metadata", {}).get(
                "protocol_endpoints", {}
            ),
        }

    async def send_device_list(self, websocket: WebSocket):
        """Send current device list to a websocket client."""
        devices = [self._device_to_dict(d) for d in self.devices.values()]
        await websocket.send_json({"type": "device_list", "devices": devices})

    async def broadcast_device_list(self):
        """Broadcast device list to all tracked websocket clients."""
        devices = [self._device_to_dict(d) for d in self.devices.values()]
        message = {"type": "device_list", "devices": devices}
        for ws in list(self.clients):
            try:
                await ws.send_json(message)
            except Exception as e:
                print(f"[BROADCAST] Failed to send device list: {e}")

    async def register_web_device(self, websocket: WebSocket, data: dict):
        """Register a device coming from WebSocket message."""
        device = ConnectedDevice(
            device_id=data.get("device_id"),
            device_name=data.get(
                "device_name", data.get("device_id", "device")
            ),
            device_type=data.get("device_type", "generic"),
            capabilities=data.get("capabilities", []),
            protocols=data.get("protocols", []),
            connection_mode=data.get("connection_mode", "direct"),
            metadata={
                "protocol_endpoints": data.get("protocol_endpoints", {})
            },
        )
        device.websocket = websocket
        self.devices[device.device_id] = device
        self.web_clients[device.device_id] = websocket
        self.clients.add(websocket)
        await self.broadcast_device_list()
        return device

    async def handle_message(self, websocket: WebSocket, message: dict):
        """Handle basic incoming WebSocket messages used by tests."""
        msg_type = message.get("type")
        if msg_type == "get_devices":
            await self.send_device_list(websocket)
        elif msg_type == "register_device":
            await self.register_web_device(websocket, message)
        elif msg_type == "send_effect_protocol":
            await self.send_effect_protocol(
                websocket,
                message.get("protocol", "websocket"),
                message.get("effect", {}),
            )

    async def start_protocol_server(self, websocket: WebSocket, protocol: str):
        """Start embedded protocol server and notify caller."""
        await self._ensure_protocol_servers([protocol])
        if websocket is not None:
            payload = {
                "type": "protocol_status",
                "protocol": protocol,
                "running": True,
            }
            try:
                await websocket.send_json(payload)
            except Exception as e:
                print(f"[PROTO_STATUS] send_json failed: {e}")
        return True

    async def stop_protocol_server(self, websocket: WebSocket, protocol: str):
        """Stop notification hook; servers are lightweight so no-op for now."""
        if websocket is not None:
            payload = {
                "type": "protocol_status",
                "protocol": protocol,
                "running": False,
            }
            try:
                await websocket.send_json(payload)
            except Exception as e:
                print(f"[PROTO_STATUS] send_json failed: {e}")
        return True

    async def send_effect_protocol(
        self, websocket: WebSocket, protocol: str, effect: dict
    ):
        """Simulate sending an effect over a given protocol and acknowledge."""
        self.effects_sent += 1
        if websocket is not None:
            payload = {
                "type": "effect_protocol_result",
                "protocol": protocol,
                "success": True,
                "effect": effect,
            }
            try:
                await websocket.send_json(payload)
            except Exception as e:
                print(f"[EFFECT_PROTO] send_json failed: {e}")
        return True

    async def send_effect(
        self, websocket: WebSocket, device_id: str, effect: dict
    ):
        """Route effect to a device based on connection mode and protocols."""
        device = self.devices.get(device_id)
        if not device:
            return False

        protocols = list(getattr(device, "protocols", []) or [])
        connection_mode = getattr(device, "connection_mode", "direct")

        # Isolated mode: prefer first non-websocket protocol
        if connection_mode == "isolated":
            target_proto = next(
                (p for p in protocols if p != "websocket"), "websocket"
            )
        else:
            # Direct mode prefers websocket if we have a socket, even if not listed
            if device_id in self.web_clients:
                target_proto = "websocket"
            else:
                target_proto = (
                    "websocket"
                    if "websocket" in protocols
                    else (protocols[0] if protocols else "websocket")
                )

        # If using websocket and we have a device websocket, send directly
        if target_proto == "websocket" and device_id in self.web_clients:
            try:
                await self.web_clients[device_id].send_json(
                    {"type": "effect", **effect}
                )
                return True
            except Exception as e:
                print(f"[SEND_EFFECT] websocket send failed: {e}")

        # Otherwise dispatch via protocol handler shim
        await self.send_effect_protocol(websocket, target_proto, effect)
        return True

    async def _shutdown(self):
        """Gracefully close websocket clients and stop timeline player."""
        for ws in list(self.clients):
            try:
                await ws.close()
            except Exception:
                pass
        self.clients.clear()
        self.web_clients.clear()
        try:
            self.timeline_player.stop()
        except Exception:
            pass
        if os.environ.get("PLAYSEM_FORCE_EXIT") == "1":
            os._exit(0)


# Keep legacy server object for tests that instantiate or patch
# ControlPanelServer internals directly.
server = ControlPanelServer()
legacy_app = server.app


def create_compat_app():
    """Return modular app for runtime entrypoint compatibility."""

    return create_app(
        ServerConfig(host="0.0.0.0", port=DEFAULT_SERVER_PORT, debug=False)
    )


# Runtime app now comes from modular architecture.
app = create_compat_app()


if __name__ == "__main__":
    print("=" * 70)
    print("PlaySEM Test Server")
    print("=" * 70)
    print("\nUI Demos:")
    print("\n" + "=" * 70 + "\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=DEFAULT_SERVER_PORT,
        log_level="info",
    )
