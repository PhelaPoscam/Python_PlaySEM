#!/usr/bin/env python3
"""
Control Panel Backend Server

Provides a FastAPI + WebSocket backend for the web-based control panel.
Supports real-time device discovery, connection, and effect testing.

Features:
- WebSocket for real-time bidirectional communication
- Device discovery for Bluetooth, Serial, and MQTT
- Live device connection management
- Effect dispatch with latency tracking
- System statistics and monitoring
"""

import sys
from pathlib import Path

# Add parent directory to path to allow importing from 'src'
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Dict, Set

import uvicorn
import httpx
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse

from src.device_driver import (
    BluetoothDriver,
    MQTTDriver,
    SerialDriver,
)  # noqa: E402
from src.device_driver.mock_driver import (  # noqa: E402
    MockLightDevice,
    MockVibrationDevice,
    MockWindDevice,
)
from src.device_manager import DeviceManager  # noqa: E402
from src.effect_dispatcher import EffectDispatcher  # noqa: E402
from src.effect_metadata import (
    EffectMetadataParser,
    create_effect,
)  # noqa: E402
from src.protocol_server import (  # noqa: E402
    CoAPServer,
    HTTPServer,
    MQTTServer,
    UPnPServer,
    WebSocketServer,
)
from src.timeline import Timeline  # noqa: E402


@dataclass
class ConnectedDevice:
    """Represents a connected device."""

    id: str
    name: str
    type: str  # 'bluetooth', 'serial', 'mqtt'
    address: str
    driver: any
    manager: DeviceManager
    dispatcher: EffectDispatcher
    connected_at: float


class ControlPanelServer:
    """Backend server for the control panel."""

    def __init__(self):
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def lifespan(app):
            # Startup
            yield
            # Shutdown
            await self._shutdown()

        self.app = FastAPI(
            title="PythonPlaySEM Control Panel API", lifespan=lifespan
        )
        self.devices: Dict[str, ConnectedDevice] = {}
        self.clients: Set[WebSocket] = set()
        self.web_clients: Dict[str, WebSocket] = {}  # device_id -> websocket
        self.stats = {
            "effects_sent": 0,
            "errors": 0,
            "start_time": time.time(),
        }

        # Create a global device manager and dispatcher for protocol servers
        # This allows external clients (MQTT, CoAP, HTTP, UPnP) to send effects
        # to all connected devices
        mock_client = type("MockClient", (), {"publish": lambda *args: None})()
        self.global_device_manager = DeviceManager(client=mock_client)
        self.global_dispatcher = EffectDispatcher(self.global_device_manager)

        # Protocol servers
        self.mqtt_server = None
        self.coap_server = None
        self.upnp_server = None
        self.http_api_server = None
        self.websocket_protocol_server = None  # For SEM effects

        # Timeline player
        self.timeline_player = Timeline(
            effect_dispatcher=self.global_dispatcher,
            tick_interval=0.01,  # 10ms precision
        )
        self.current_timeline = None
        self.timeline_player.set_callbacks(
            on_effect=self._on_timeline_effect,
            on_complete=self._on_timeline_complete,
        )

        self._setup_routes()

    async def _shutdown(self):
        """Handle shutdown of all servers."""
        print("\n[SHUTDOWN] Stopping all protocol servers...")

        # Create a list of stop tasks
        stop_tasks = []

        # Stop MQTT server (sync in thread, but stop is blocking)
        if self.mqtt_server and self.mqtt_server.is_running():
            print("[SHUTDOWN] Stopping MQTT server...")
            try:
                # Run sync stop in a thread with timeout to avoid hanging
                await asyncio.wait_for(
                    asyncio.to_thread(self.mqtt_server.stop), timeout=2.0
                )
                print("[OK] MQTT server stopped.")
            except asyncio.TimeoutError:
                print(
                    "[WARNING] MQTT server stop timed out, forcing shutdown..."
                )
            except Exception as e:
                print(f"[WARNING] MQTT server stop error: {e}")

        # Stop CoAP server (async)
        if self.coap_server and self.coap_server.is_running():
            print("[SHUTDOWN] Stopping CoAP server...")
            stop_tasks.append(self.coap_server.stop())

        # Stop HTTP server (async)
        if self.http_api_server:
            print("[SHUTDOWN] Stopping HTTP API server...")
            stop_tasks.append(self.http_api_server.stop())

        # Stop UPnP server (async)
        if self.upnp_server and self.upnp_server.is_running():
            print("[SHUTDOWN] Stopping UPnP server...")
            stop_tasks.append(self.upnp_server.stop())

        # Stop WebSocket protocol server (async)
        if (
            self.websocket_protocol_server
            and self.websocket_protocol_server.is_running()
        ):
            print("[SHUTDOWN] Stopping WebSocket protocol server...")
            stop_tasks.append(self.websocket_protocol_server.stop())

        # Run all async stop tasks concurrently with timeout
        if stop_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*stop_tasks, return_exceptions=True),
                    timeout=3.0,
                )
                print("[OK] All async servers stopped.")
            except asyncio.TimeoutError:
                print("[WARNING] Some servers timed out during shutdown")
            except Exception as e:
                print(f"[WARNING] Error during server shutdown: {e}")

        # Stop timeline player
        try:
            self.timeline_player.stop()
            print("[OK] Timeline player stopped.")
        except Exception as e:
            print(f"[WARNING] Timeline stop error: {e}")

        print("[OK] Shutdown complete.")

    def _setup_routes(self):
        """Set up FastAPI routes."""

        @self.app.get("/")
        async def root():
            """Redirect to the super controller."""
            from fastapi.responses import RedirectResponse

            return RedirectResponse(url="/super_controller")

        @self.app.get("/controller")
        async def get_controller():
            """Serve the controller HTML."""
            path = Path(__file__).parent.parent / "ui" / "controller.html"
            with open(path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())

        @self.app.get("/receiver")
        async def get_receiver():
            """Serve the receiver HTML."""
            path = Path(__file__).parent.parent / "ui" / "receiver.html"
            with open(path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())

        @self.app.get("/super_controller")
        async def get_super_controller():
            """Serve the super_controller HTML."""
            path = (
                Path(__file__).parent.parent / "ui" / "super_controller.html"
            )
            with open(path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())

        @self.app.get("/super_receiver")
        async def get_super_receiver():
            """Serve the super_receiver HTML."""
            path = Path(__file__).parent.parent / "ui" / "super_receiver.html"
            with open(path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())

        @self.app.get("/mobile_device")
        async def get_mobile_device():
            """Serve the mobile device client HTML."""
            path = Path(__file__).parent.parent / "ui" / "mobile_device.html"
            with open(path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time communication."""
            await self.handle_client(websocket)

        @self.app.get("/api/devices")
        async def get_devices():
            """Get list of connected devices."""
            return {
                "devices": [
                    {
                        "id": dev.id,
                        "name": dev.name,
                        "type": dev.type,
                        "address": dev.address,
                        "uptime": time.time() - dev.connected_at,
                    }
                    for dev in self.devices.values()
                ]
            }

        @self.app.get("/api/stats")
        async def get_stats():
            """Get system statistics."""
            uptime = time.time() - self.stats["start_time"]
            return {
                "effects_sent": self.stats["effects_sent"],
                "errors": self.stats["errors"],
                "connected_devices": len(self.devices),
                "uptime_seconds": uptime,
            }

        @self.app.get("/api/capabilities/{device_id}")
        async def get_capabilities(device_id: str):
            """Return capability description for a given device id.

            This prefers the connected device's driver when available. For mock
            devices or when the driver lacks capability reporting, it falls back
            to inferred generic capabilities.
            """
            # Prefer connected device
            dev = self.devices.get(device_id)
            try:
                # If we have a real connectivity driver with get_capabilities
                if (
                    dev
                    and dev.manager
                    and getattr(dev.manager, "connectivity_driver", None)
                ):
                    drv = dev.manager.connectivity_driver
                    if hasattr(drv, "get_capabilities"):
                        caps = drv.get_capabilities(device_id)
                        if caps:
                            return caps

                # Mock devices: synthesize via MockConnectivityDriver
                if (dev and dev.type == "mock") or device_id.startswith(
                    "mock_"
                ):
                    try:
                        from src.device_driver.mock_driver import (
                            MockConnectivityDriver,
                        )

                        mdrv = MockConnectivityDriver()
                        caps = mdrv.get_capabilities(device_id)
                        if caps:
                            return caps
                    except Exception:
                        pass

                # Fallbacks by driver type
                # Serial
                try:
                    from src.device_driver.serial_driver import SerialDriver

                    sdrv = SerialDriver()
                    if hasattr(sdrv, "get_capabilities"):
                        caps = sdrv.get_capabilities(device_id)
                        if caps:
                            return caps
                except Exception:
                    pass

                # Bluetooth
                try:
                    from src.device_driver.bluetooth_driver import (
                        BluetoothDriver,
                    )

                    bdrv = BluetoothDriver()
                    if hasattr(bdrv, "get_capabilities"):
                        caps = bdrv.get_capabilities(device_id)
                        if caps:
                            return caps
                except Exception:
                    pass

                # MQTT
                try:
                    from src.device_driver.mqtt_driver import MQTTDriver

                    mqd = MQTTDriver(broker="localhost")
                    if hasattr(mqd, "get_capabilities"):
                        caps = mqd.get_capabilities(device_id)
                        if caps:
                            return caps
                except Exception:
                    pass

                return {
                    "device_id": device_id,
                    "effects": [],
                    "note": "Capabilities not available",
                }
            except Exception as e:
                return {"error": str(e)}

        @self.app.post("/api/scan")
        async def scan_devices_http(data: dict):
            """HTTP endpoint for device scanning."""
            driver_type = data.get("driver_type")
            results = []

            try:
                if driver_type == "bluetooth":
                    driver = BluetoothDriver()
                    devices = await driver.scan_devices(timeout=5.0)
                    for device in devices:
                        results.append(
                            {
                                "name": device.get("name") or "Unknown Device",
                                "address": device.get("address"),
                                "type": "bluetooth",
                                "rssi": (
                                    f"{device.get('rssi')} dBm"
                                    if device.get("rssi")
                                    and device.get("rssi") != -999
                                    else "N/A"
                                ),
                            }
                        )
                elif driver_type == "serial":
                    ports = SerialDriver.list_ports()
                    for port_info in ports:
                        results.append(
                            {
                                "name": port_info.get(
                                    "description", "Unknown Serial Device"
                                ),
                                "address": port_info.get("device", "Unknown"),
                                "type": "serial",
                                "rssi": None,
                            }
                        )
                elif driver_type == "mock":
                    # Return predefined mock devices
                    mock_devices = [
                        {
                            "name": "Mock Light Device",
                            "address": "mock_light_1",
                            "type": "mock",
                            "rssi": None,
                        },
                        {
                            "name": "Mock Wind Device",
                            "address": "mock_wind_1",
                            "type": "mock",
                            "rssi": None,
                        },
                        {
                            "name": "Mock Vibration Device",
                            "address": "mock_vibration_1",
                            "type": "mock",
                            "rssi": None,
                        },
                    ]
                    results.extend(mock_devices)
            except Exception as e:
                return {"type": "error", "message": str(e)}

            return {"type": "scan_complete", "devices": results}

        @self.app.post("/api/connect")
        async def connect_device_http(data: dict):
            """HTTP endpoint for device connection."""
            address = data.get("address")
            driver_type = data.get("driver_type")

            # Reuse existing WebSocket connection logic
            try:
                safe_address = address.replace(":", "_").replace("/", "_")
                device_id = f"{driver_type}_{safe_address}"

                if device_id in self.devices:
                    return {
                        "type": "error",
                        "message": "Device already connected",
                    }

                if driver_type == "bluetooth":
                    driver = BluetoothDriver(address=address)
                    await driver.connect()
                    name = f"BLE Device ({address})"
                elif driver_type == "serial":
                    driver = SerialDriver(port=address, baudrate=9600)
                    driver.connect()
                    name = f"Serial Device ({address})"
                elif driver_type == "mqtt":
                    driver = MQTTDriver(broker=address)
                    driver.connect()
                    name = f"MQTT Device ({address})"
                elif driver_type == "mock":
                    # Create appropriate mock device based on address
                    if "light" in address:
                        driver = MockLightDevice(address)
                    elif "wind" in address:
                        driver = MockWindDevice(address)
                    elif "vibration" in address:
                        driver = MockVibrationDevice(address)
                    else:
                        driver = MockLightDevice(address)  # Default
                    name = f"Mock Device ({address})"
                else:
                    return {
                        "type": "error",
                        "message": f"Unsupported driver: {driver_type}",
                    }

                manager = DeviceManager(connectivity_driver=driver)
                dispatcher = EffectDispatcher(manager)

                device = ConnectedDevice(
                    id=device_id,
                    name=name,
                    type=driver_type,
                    address=address,
                    driver=driver,
                    manager=manager,
                    dispatcher=dispatcher,
                    connected_at=time.time(),
                )
                self.devices[device_id] = device

                return {"type": "success", "message": f"Connected to {name}"}
            except Exception as e:
                return {"type": "error", "message": str(e)}

        @self.app.post("/api/disconnect")
        async def disconnect_device_http(data: dict):
            """HTTP endpoint for device disconnection."""
            device_id = data.get("device_id")

            if device_id not in self.devices:
                return {"type": "error", "message": "Device not found"}

            try:
                device = self.devices[device_id]
                if device.type == "bluetooth":
                    await device.driver.disconnect()
                else:
                    device.manager.disconnect()

                del self.devices[device_id]
                return {
                    "type": "success",
                    "message": f"Disconnected {device.name}",
                }
            except Exception as e:
                return {"type": "error", "message": str(e)}

        @self.app.post("/api/effect")
        async def send_effect_http(data: dict):
            """HTTP endpoint for sending effects."""
            device_id = data.get("device_id")
            effect_data = data.get("effect")

            if device_id not in self.devices:
                return {"type": "error", "message": "Device not found"}

            try:
                device = self.devices[device_id]
                effect = create_effect(
                    effect_type=effect_data.get("effect_type", "vibration"),
                    intensity=effect_data.get("intensity", 50),
                    duration=effect_data.get("duration", 1000),
                    timestamp=0,
                    parameters=effect_data.get("parameters", {}),
                )

                start_time = time.time()
                device.dispatcher.dispatch_effect_metadata(effect)
                latency = int((time.time() - start_time) * 1000)

                self.stats["effects_sent"] += 1

                return {
                    "type": "effect_result",
                    "success": True,
                    "latency": latency,
                    "device_id": device_id,
                }
            except Exception as e:
                self.stats["errors"] += 1
                return {
                    "type": "effect_result",
                    "success": False,
                    "error": str(e),
                    "device_id": device_id,
                }

        @self.app.post("/api/timeline/upload")
        async def upload_timeline(file: UploadFile = File(...)):
            """Upload and parse XML timeline."""
            try:
                xml_content = await file.read()
                xml_str = xml_content.decode("utf-8")

                timeline = EffectMetadataParser.parse_mpegv_xml(xml_str)
                self.current_timeline = timeline
                self.timeline_player.load_timeline(timeline)

                return {
                    "type": "timeline_loaded",
                    "success": True,
                    "effect_count": len(timeline.effects),
                    "duration": timeline.total_duration,
                    "metadata": timeline.metadata,
                }
            except Exception as e:
                return {
                    "type": "timeline_error",
                    "success": False,
                    "error": str(e),
                }

    def _on_timeline_effect(self, effect):
        """Callback when timeline effect is executed."""
        # Broadcast to all connected clients
        asyncio.create_task(self._broadcast_timeline_effect(effect))

    def _on_timeline_complete(self):
        """Callback when timeline completes."""
        asyncio.create_task(self._broadcast_timeline_status())

    async def _broadcast_timeline_effect(self, effect):
        """Broadcast timeline effect execution to all clients."""
        message = {
            "type": "timeline_effect",
            "effect_type": effect.effect_type,
            "intensity": effect.intensity,
            "duration": effect.duration,
        }
        for client in list(self.clients):
            try:
                await client.send_json(message)
            except Exception:
                self.clients.discard(client)

    async def _broadcast_timeline_status(self):
        """Broadcast timeline status to all clients."""
        status = self.timeline_player.get_status()
        message = {"type": "timeline_status", **status}
        for client in list(self.clients):
            try:
                await client.send_json(message)
            except Exception:
                self.clients.discard(client)

    async def handle_client(self, websocket: WebSocket):
        """Handle WebSocket client connection."""
        await websocket.accept()
        self.clients.add(websocket)
        registered_device_id = None

        print(f"[OK] Client connected. Total clients: {len(self.clients)}")

        try:
            # Handle incoming messages
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    if "protocol" in message and "effect" in message:
                        await self.handle_super_controller_message(
                            websocket, message
                        )
                    elif message.get("type") == "register_device":
                        registered_device_id = await self.register_web_device(
                            websocket, message
                        )
                    else:
                        await self.handle_message(websocket, message)
                except json.JSONDecodeError:
                    await self.handle_message(websocket, {"type": data})
                except Exception:
                    await self.handle_message(websocket, {"type": data})

        except WebSocketDisconnect:
            print(
                f"[x] Client disconnected. Remaining clients: {len(self.clients) - 1}"
            )
        except Exception as e:
            print(f"[x] WebSocket error: {e}")
        finally:
            self.clients.discard(websocket)
            if registered_device_id:
                await self.unregister_web_device(registered_device_id)

    async def handle_super_controller_message(
        self, websocket: WebSocket, message: dict
    ):
        """Handle incoming WebSocket message from the super controller."""
        protocol = message.get("protocol")
        effect_data = message.get("effect")
        # The super controller sends 'modality', but create_effect expects 'effect_type'
        effect_data["effect_type"] = effect_data.get("modality")
        print(
            f"[RECV] Received super controller message for protocol {protocol}"
        )

        await self.send_effect_protocol(websocket, protocol, effect_data)

    async def register_web_device(
        self, websocket: WebSocket, message: dict
    ) -> str:
        """Register a web client as a device."""
        device_id = message.get("device_id")
        device_name = message.get("device_name", "Web Device")
        device_type = message.get("device_type", "web_client")
        capabilities = message.get("capabilities", [])

        print(
            f"[REGISTER] Web device: {device_id} ({device_name}) "
            f"with capabilities: {capabilities}"
        )

        # Store WebSocket connection
        self.web_clients[device_id] = websocket

        # Add to devices list
        self.devices[device_id] = ConnectedDevice(
            id=device_id,
            name=device_name,
            type=device_type,
            address="websocket",
            driver=None,
            manager=None,
            dispatcher=None,
            connected_at=time.time(),
        )

        # Send confirmation
        await websocket.send_json(
            {
                "type": "device_registered",
                "device_id": device_id,
                "message": f"Registered as {device_name}",
            }
        )

        # Broadcast device list update to all clients
        await self.broadcast_device_list()

        return device_id

    async def unregister_web_device(self, device_id: str):
        """Unregister a web device."""
        if device_id in self.web_clients:
            del self.web_clients[device_id]
        if device_id in self.devices:
            del self.devices[device_id]
            print(f"[UNREGISTER] Web device: {device_id}")
            await self.broadcast_device_list()

    async def broadcast_device_list(self):
        """Broadcast updated device list to all connected clients."""
        devices = [
            {
                "id": dev.id,
                "name": dev.name,
                "type": dev.type,
                "address": dev.address,
            }
            for dev in self.devices.values()
        ]

        message = {"type": "device_list", "devices": devices}

        # Send to all clients
        for client in list(self.clients):
            try:
                await client.send_json(message)
            except Exception:
                pass

    async def handle_message(self, websocket: WebSocket, message: dict):
        """Handle incoming WebSocket message."""
        msg_type = message.get("type")

        print(f"[RECV] Received message: {msg_type}")

        if msg_type == "get_devices":
            await self.send_device_list(websocket)

        elif msg_type == "scan_devices":
            driver_type = message.get("driver_type")
            await self.scan_devices(websocket, driver_type)

        elif msg_type == "connect_device":
            address = message.get("address")
            driver_type = message.get("driver_type")
            await self.connect_device(websocket, address, driver_type)

        elif msg_type == "disconnect_device":
            device_id = message.get("device_id")
            await self.disconnect_device(websocket, device_id)

        elif msg_type == "send_effect":
            device_id = message.get("device_id")
            effect_data = message.get("effect")
            await self.send_effect(websocket, device_id, effect_data)

        elif msg_type == "send_effect_protocol":
            protocol = message.get("protocol")
            effect_data = message.get("effect")
            await self.send_effect_protocol(websocket, protocol, effect_data)

        elif (
            msg_type == "effect"
        ):  # New handler for simple, broadcast-only effects
            print("[DEBUG] Handling simple 'effect' message.")
            effect = create_effect(
                effect_type=message.get("effect_type", "vibration"),
                intensity=message.get("intensity", 50),
                duration=message.get("duration", 1000),
            )
            print(f"[DEBUG] Created effect: {effect.effect_type}")
            await self._broadcast_effect(effect, "broadcast", "websocket")

        elif msg_type == "start_protocol_server":
            protocol = message.get("protocol")
            await self.start_protocol_server(websocket, protocol)

        elif msg_type == "stop_protocol_server":
            protocol = message.get("protocol")
            await self.stop_protocol_server(websocket, protocol)

        elif msg_type == "upload_timeline":
            file_content = message.get("file_content")
            file_type = message.get("file_type")
            await self.handle_timeline_upload(
                websocket, file_content, file_type
            )

        elif msg_type == "play_timeline":
            await self.play_timeline(websocket)

        elif msg_type == "pause_timeline":
            await self.pause_timeline(websocket)

        elif msg_type == "resume_timeline":
            await self.resume_timeline(websocket)

        elif msg_type == "stop_timeline":
            await self.stop_timeline(websocket)

        elif msg_type == "get_timeline_status":
            await self.get_timeline_status(websocket)

        else:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                }
            )

    async def send_device_list(self, websocket: WebSocket):
        """Send list of connected devices to client."""
        devices = [
            {
                "id": dev.id,
                "name": dev.name,
                "type": dev.type,
                "address": dev.address,
            }
            for dev in self.devices.values()
        ]

        await websocket.send_json({"type": "device_list", "devices": devices})

    async def scan_devices(self, websocket: WebSocket, driver_type: str):
        """Scan for available devices."""
        print(f"[SCAN] Scanning for {driver_type} devices...")

        try:
            if driver_type == "bluetooth":
                await self.scan_bluetooth(websocket)
            elif driver_type == "serial":
                await self.scan_serial(websocket)
            elif driver_type == "mock":
                await self.scan_mock(websocket)
            elif driver_type == "mqtt":
                await websocket.send_json(
                    {
                        "type": "info",
                        "message": "MQTT devices require manual configuration",
                    }
                )
            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Unknown driver type: {driver_type}",
                    }
                )

        except Exception as e:
            print(f"[x] Scan error: {e}")
            await websocket.send_json(
                {"type": "error", "message": f"Scan failed: {str(e)}"}
            )

    async def scan_bluetooth(self, websocket: WebSocket):
        """Scan for Bluetooth devices."""
        try:
            driver = BluetoothDriver()
            devices = await driver.scan_devices(timeout=5.0)

            print(f"[OK] Found {len(devices)} Bluetooth devices")

            for device in devices:
                await websocket.send_json(
                    {
                        "type": "device_discovered",
                        "device": {
                            "name": device.get("name") or "Unknown Device",
                            "address": device.get("address"),
                            "type": "bluetooth",
                            "rssi": (
                                f"{device.get('rssi')} dBm"
                                if device.get("rssi")
                                and device.get("rssi") != -999
                                else "N/A"
                            ),
                        },
                    }
                )
                await asyncio.sleep(0.1)  # Small delay for UI updates

        except Exception as e:
            print(f"[x] Bluetooth scan error: {e}")
            await websocket.send_json(
                {
                    "type": "error",
                    "message": f"Bluetooth scan failed: {str(e)}",
                }
            )

    async def scan_serial(self, websocket: WebSocket):
        """Scan for Serial devices."""
        try:
            ports = SerialDriver.list_ports()

            print(f"[OK] Found {len(ports)} Serial ports")

            for port_info in ports:
                await websocket.send_json(
                    {
                        "type": "device_discovered",
                        "device": {
                            "name": port_info.get(
                                "description", "Unknown Serial Device"
                            ),
                            "address": port_info.get("device", "Unknown"),
                            "type": "serial",
                            "rssi": None,
                        },
                    }
                )
                await asyncio.sleep(0.1)

        except Exception as e:
            print(f"[x] Serial scan error: {e}")
            await websocket.send_json(
                {"type": "error", "message": f"Serial scan failed: {str(e)}"}
            )

    async def scan_mock(self, websocket: WebSocket):
        """Scan for Mock devices (always returns predefined devices)."""
        try:
            mock_devices = [
                {"name": "Mock Light Device", "address": "mock_light_1"},
                {"name": "Mock Wind Device", "address": "mock_wind_1"},
                {
                    "name": "Mock Vibration Device",
                    "address": "mock_vibration_1",
                },
            ]

            print(f"[OK] Found {len(mock_devices)} Mock devices")

            for device in mock_devices:
                await websocket.send_json(
                    {
                        "type": "device_discovered",
                        "device": {
                            "name": device["name"],
                            "address": device["address"],
                            "type": "mock",
                            "rssi": None,
                        },
                    }
                )
                await asyncio.sleep(0.1)

        except Exception as e:
            print(f"[x] Mock scan error: {e}")
            await websocket.send_json(
                {"type": "error", "message": f"Mock scan failed: {str(e)}"}
            )

    async def connect_device(
        self,
        websocket: WebSocket,
        address: str,
        driver_type: str,
    ):
        """Connect to a device."""
        print(f"[CONNECT] Connecting to {driver_type} device: {address}")

        try:
            safe_address = address.replace(":", "_").replace("/", "_")
            device_id = f"{driver_type}_{safe_address}"

            if device_id in self.devices:
                await websocket.send_json(
                    {"type": "error", "message": "Device already connected"}
                )
                return

            # Create appropriate driver
            if driver_type == "bluetooth":
                driver = BluetoothDriver(address=address)
                await driver.connect()
                name = f"BLE Device ({address})"

            elif driver_type == "serial":
                driver = SerialDriver(port=address, baudrate=9600)
                driver.connect()
                name = f"Serial Device ({address})"

            elif driver_type == "mqtt":
                driver = MQTTDriver(broker=address)
                driver.connect()
                name = f"MQTT Device ({address})"

            elif driver_type == "mock":
                # Mock devices work differently - they don't use drivers
                # They connect directly and use the global dispatcher
                if "light" in address:
                    mock_device = MockLightDevice(address)
                elif "wind" in address:
                    mock_device = MockWindDevice(address)
                elif "vibration" in address:
                    mock_device = MockVibrationDevice(address)
                else:
                    mock_device = MockLightDevice(address)  # Default
                device_class_name = mock_device.__class__.__name__
                clean_name = (
                    device_class_name.replace("Mock", "")
                    .replace("Device", "")
                    .strip()
                )
                name = f"Mock {clean_name} ({address})"

                # Store mock device directly (no manager/driver needed)
                device = ConnectedDevice(
                    id=device_id,
                    name=name,
                    type=driver_type,
                    address=address,
                    driver=mock_device,  # Store mock device as "driver"
                    manager=None,  # Mock devices don't use manager
                    dispatcher=self.global_dispatcher,  # Use global dispatcher
                    connected_at=time.time(),
                )
                self.devices[device_id] = device

                print(f"[OK] Connected to {name}")

                # Notify all clients
                await self.broadcast_device_list()

                await websocket.send_json(
                    {"type": "success", "message": f"Connected to {name}"}
                )
                return  # Early return for mock devices

            else:
                raise ValueError(f"Unsupported driver type: {driver_type}")

            # Create DeviceManager and EffectDispatcher for real drivers
            manager = DeviceManager(connectivity_driver=driver)
            dispatcher = EffectDispatcher(manager)

            # Store device
            device = ConnectedDevice(
                id=device_id,
                name=name,
                type=driver_type,
                address=address,
                driver=driver,
                manager=manager,
                dispatcher=dispatcher,
                connected_at=time.time(),
            )
            self.devices[device_id] = device

            print(f"✅ Connected to {name}")

            # Notify all clients
            await self.broadcast_device_list()

            await websocket.send_json(
                {"type": "success", "message": f"Connected to {name}"}
            )

        except Exception as e:
            print(f"[x] Connection error: {e}")
            self.stats["errors"] += 1
            await websocket.send_json(
                {"type": "error", "message": f"Connection failed: {str(e)}"}
            )

    async def disconnect_device(self, websocket: WebSocket, device_id: str):
        """Disconnect a device."""
        if device_id not in self.devices:
            await websocket.send_json(
                {"type": "error", "message": "Device not found"}
            )
            return

        try:
            device = self.devices[device_id]

            # Disconnect driver
            if device.type == "mock":
                # Mock devices don't need disconnection
                pass
            elif device.type == "bluetooth":
                await device.driver.disconnect()
            else:
                if device.manager:
                    device.manager.disconnect()

            # Remove from devices
            del self.devices[device_id]

            print(f"[OK] Disconnected {device.name}")

            # Notify all clients
            await self.broadcast_device_list()

            await websocket.send_json(
                {"type": "success", "message": f"Disconnected {device.name}"}
            )

        except Exception as e:
            print(f"[x] Disconnect error: {e}")
            await websocket.send_json(
                {"type": "error", "message": f"Disconnect failed: {str(e)}"}
            )

    async def send_effect(
        self,
        websocket: WebSocket,
        device_id: str,
        effect_data: dict,
    ):
        """Send effect to a device."""
        if device_id not in self.devices:
            await websocket.send_json(
                {"type": "error", "message": "Device not found"}
            )
            return

        try:
            device = self.devices[device_id]
            start_time = time.time()

            # Create the effect object first to use for dispatch and broadcast
            effect = create_effect(
                effect_type=effect_data.get("effect_type", "vibration"),
                intensity=effect_data.get("intensity", 50),
                duration=effect_data.get("duration", 1000),
                timestamp=0,
                parameters=effect_data.get("parameters", {}),
            )

            if device.type == "mock":
                # Mock devices handle effects directly
                mock_device = device.driver
                if effect.effect_type == "light":
                    brightness = int(effect.intensity * 2.55)
                    mock_device.send_command(
                        "set_brightness", {"brightness": brightness}
                    )
                elif effect.effect_type == "wind":
                    mock_device.send_command(
                        "set_speed", {"speed": effect.intensity}
                    )
                elif effect.effect_type == "vibration":
                    mock_device.send_command(
                        "set_intensity",
                        {
                            "intensity": effect.intensity,
                            "duration": effect.duration,
                        },
                    )
                else:
                    mock_device.send_command(
                        effect.effect_type,
                        {
                            "intensity": effect.intensity,
                            "duration": effect.duration,
                        },
                    )

                print(
                    f"[OK] Mock device '{mock_device.device_id}' received "
                    f"{effect.effect_type.upper()} command: "
                    f"intensity={effect.intensity}, duration={effect.duration}"
                )
            else:
                # Real devices use effect dispatcher
                device.dispatcher.dispatch_effect_metadata(effect)

            latency = int((time.time() - start_time) * 1000)
            self.stats["effects_sent"] += 1

            print(f"[OK] Effect sent to {device.name} (latency: {latency}ms)")

            # Send private confirmation to the sender
            await websocket.send_json(
                {
                    "type": "effect_result",
                    "success": True,
                    "latency": latency,
                    "device_id": device_id,
                    "effect_type": effect.effect_type,  # Include for client-side logic
                }
            )

            # Broadcast the effect to all clients (for receivers)
            await self._broadcast_effect(effect, device_id, "websocket")

        except Exception as e:
            print(f"[x] Effect send error: {e}")
            self.stats["errors"] += 1
            await websocket.send_json(
                {
                    "type": "effect_result",
                    "success": False,
                    "error": str(e),
                    "device_id": device_id,
                }
            )

    async def send_effect_protocol(
        self, websocket: WebSocket, protocol: str, effect_data: dict
    ):
        """Send effect over a specific protocol."""
        try:
            effect = create_effect(
                effect_type=effect_data.get("effect_type", "vibration"),
                intensity=effect_data.get("intensity", 50),
                duration=effect_data.get("duration", 1000),
                timestamp=0,
            )

            if protocol == "websocket":
                print("[OK] Effect sent via WebSocket broadcast")

            elif protocol == "mqtt":
                if not self.mqtt_server or not self.mqtt_server.is_running():
                    await self.start_protocol_server(websocket, "mqtt")

                if self.mqtt_server and self.mqtt_server.internal_client:
                    payload = json.dumps(
                        {
                            "effect_type": effect.effect_type,
                            "intensity": effect.intensity,
                            "duration": effect.duration,
                        }
                    )
                    # The topic needs to be correct, see MQTTServer implementation
                    self.mqtt_server.internal_client.publish(
                        "effects/sem", payload
                    )
                    print("[OK] Effect sent via MQTT")
                else:
                    raise Exception("MQTT server not available")

            elif protocol == "http":
                if not self.http_api_server:
                    await self.start_protocol_server(websocket, "http")

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "http://localhost:8081/api/effects",
                        json={
                            "effect_type": effect.effect_type,
                            "intensity": effect.intensity,
                            "duration": effect.duration,
                        },
                    )
                    response.raise_for_status()
                print("[OK] Effect sent via HTTP")

            elif protocol == "coap":
                if not self.coap_server:
                    await self.start_protocol_server(websocket, "coap")

                # This is a bit more complex, as it requires a CoAP client.
                # For now, let's just log it.
                print(
                    "[INFO] CoAP protocol selected, but client not implemented yet."
                )
                await websocket.send_json(
                    {
                        "type": "info",
                        "message": "CoAP client not implemented yet.",
                    }
                )

            elif protocol == "upnp":
                # This is also complex and requires a UPnP client.
                print(
                    "[INFO] UPnP protocol selected, but client not implemented yet."
                )
                await websocket.send_json(
                    {
                        "type": "info",
                        "message": "UPnP client not implemented yet.",
                    }
                )

            else:
                raise ValueError(f"Unsupported protocol: {protocol}")

            # Broadcast the effect to all WebSocket clients (receivers)
            await self._broadcast_effect(effect, "broadcast", protocol)

            await websocket.send_json(
                {
                    "type": "effect_protocol_result",
                    "success": True,
                    "protocol": protocol,
                    "effect_type": effect.effect_type,
                }
            )

        except Exception as e:
            print(f"[x] Effect protocol send error: {e}")
            await websocket.send_json(
                {
                    "type": "effect_protocol_result",
                    "success": False,
                    "error": str(e),
                    "protocol": protocol,
                }
            )

    async def _broadcast_effect(
        self, effect, device_id: str, protocol: str = "websocket"
    ):
        """Broadcast that an effect was executed to all clients."""
        print(
            f"[DEBUG] Broadcasting effect '{effect.effect_type}' to"
            f" {len(self.clients)} clients."
        )
        message = {
            "type": "effect_broadcast",
            "effect_type": effect.effect_type,
            "duration": effect.duration,
            "intensity": effect.intensity,
            "device_id": device_id,
            "protocol": protocol,
        }
        # Copy client set to avoid issues with modification during iteration
        for client in list(self.clients):
            try:
                await client.send_json(message)
            except Exception:
                # Client is likely disconnected, remove them
                self.clients.discard(client)

    async def start_protocol_server(self, websocket: WebSocket, protocol: str):
        """Start a protocol server (MQTT, CoAP, UPnP, HTTP)."""
        print(f"[START] Starting {protocol.upper()} server...")

        try:
            if protocol == "mqtt":
                if self.mqtt_server and self.mqtt_server.is_running():
                    await websocket.send_json(
                        {
                            "type": "protocol_status",
                            "protocol": protocol,
                            "running": True,
                            "error": "Server already running",
                        }
                    )
                    return

                # Create and start the embedded MQTT broker
                self.mqtt_server = MQTTServer(
                    dispatcher=self.global_dispatcher,
                    host="0.0.0.0",
                    port=1883,
                    subscribe_topic="effects/#",
                )
                self.mqtt_server.start()

            elif protocol == "coap":
                if self.coap_server and self.coap_server.is_running():
                    await websocket.send_json(
                        {
                            "type": "protocol_status",
                            "protocol": protocol,
                            "running": True,
                            "error": "Server already running",
                        }
                    )
                    return

                # Create CoAP server with proper dispatcher
                # Use localhost - aiocoap doesn't support 0.0.0.0
                self.coap_server = CoAPServer(
                    host="127.0.0.1",
                    port=5683,
                    dispatcher=self.global_dispatcher,
                )
                print("[i]  CoAP server binding to 127.0.0.1:5683")
                # CoAP server has async start - run in background
                asyncio.create_task(self.coap_server.start())
                await asyncio.sleep(0.5)  # Give it time to start

            elif protocol == "http":
                if self.http_api_server and self.http_api_server.is_running():
                    await websocket.send_json(
                        {
                            "type": "protocol_status",
                            "protocol": protocol,
                            "running": True,
                            "error": "Server already running",
                        }
                    )
                    return

                # Create HTTP server with proper dispatcher
                # Use port 8081 to avoid conflict with control panel
                self.http_api_server = HTTPServer(
                    host="0.0.0.0",
                    port=8081,
                    dispatcher=self.global_dispatcher,
                )
                print("[i]  HTTP REST API starting on port 8081")
                # HTTP server has async start - run in background
                asyncio.create_task(self.http_api_server.start())
                await asyncio.sleep(0.5)  # Give it time to start

            elif protocol == "upnp":
                if self.upnp_server and self.upnp_server.is_running():
                    await websocket.send_json(
                        {
                            "type": "protocol_status",
                            "protocol": protocol,
                            "running": True,
                            "error": "Server already running",
                        }
                    )
                    return

                # Create UPnP server with proper dispatcher
                self.upnp_server = UPnPServer(
                    friendly_name="PlaySEM Control Panel",
                    dispatcher=self.global_dispatcher,
                )
                # UPnP server has async start - run in background
                asyncio.create_task(self.upnp_server.start())
                await asyncio.sleep(0.5)  # Give it time to start

            elif protocol == "websocket":
                if (
                    self.websocket_protocol_server
                    and self.websocket_protocol_server.is_running()
                ):
                    await websocket.send_json(
                        {
                            "type": "protocol_status",
                            "protocol": protocol,
                            "running": True,
                            "error": "Server already running",
                        }
                    )
                    return

                # Create WebSocket protocol server for SEM effects
                # Port 8765 for SEM effects (8090 is for control panel UI)
                self.websocket_protocol_server = WebSocketServer(
                    host="0.0.0.0",
                    port=8765,
                    dispatcher=self.global_dispatcher,
                )
                print("[i]  WebSocket SEM server starting on port 8765")
                print("   (Port 8090 is for control panel UI only)")
                # WebSocket server has async start - run in background
                asyncio.create_task(self.websocket_protocol_server.start())
                await asyncio.sleep(0.5)  # Give it time to start

            else:
                await websocket.send_json(
                    {
                        "type": "protocol_status",
                        "protocol": protocol,
                        "running": False,
                        "error": f"Unknown protocol: {protocol}",
                    }
                )
                return

            print(f"[OK] {protocol.upper()} server started successfully")
            await websocket.send_json(
                {
                    "type": "protocol_status",
                    "protocol": protocol,
                    "running": True,
                }
            )

        except Exception as e:
            print(f"[x] Failed to start {protocol.upper()} server: {e}")
            await websocket.send_json(
                {
                    "type": "protocol_status",
                    "protocol": protocol,
                    "running": False,
                    "error": str(e),
                }
            )

    async def stop_protocol_server(self, websocket: WebSocket, protocol: str):
        """Stop a protocol server."""
        print(f"[STOP] Stopping {protocol.upper()} server...")

        try:
            if protocol == "mqtt":
                if self.mqtt_server:
                    self.mqtt_server.stop()
                    self.mqtt_server = None

            elif protocol == "coap":
                if self.coap_server:
                    # CoAP server has async stop
                    await self.coap_server.stop()
                    self.coap_server = None

            elif protocol == "http":
                if self.http_api_server:
                    # HTTP server has async stop
                    await self.http_api_server.stop()
                    self.http_api_server = None

            elif protocol == "upnp":
                if self.upnp_server:
                    # UPnP server has async stop
                    await self.upnp_server.stop()
                    self.upnp_server = None

            elif protocol == "websocket":
                if self.websocket_protocol_server:
                    # WebSocket protocol server has async stop
                    await self.websocket_protocol_server.stop()
                    self.websocket_protocol_server = None

            else:
                await websocket.send_json(
                    {
                        "type": "protocol_status",
                        "protocol": protocol,
                        "running": False,
                        "error": f"Unknown protocol: {protocol}",
                    }
                )
                return

            print(f"[OK] {protocol.upper()} server stopped")
            await websocket.send_json(
                {
                    "type": "protocol_status",
                    "protocol": protocol,
                    "running": False,
                }
            )

        except Exception as e:
            print(f"[x] Failed to stop {protocol.upper()} server: {e}")
            await websocket.send_json(
                {
                    "type": "protocol_status",
                    "protocol": protocol,
                    "running": False,
                    "error": str(e),
                }
            )

    async def handle_timeline_upload(
        self,
        websocket: WebSocket,
        file_content: str,
        file_type: str,
    ):
        """Handle timeline upload via WebSocket, supporting XML, JSON, and YAML."""
        try:
            timeline = None
            if file_type == "xml":
                timeline = EffectMetadataParser.parse_mpegv_xml(file_content)
            elif file_type == "json":
                timeline = EffectMetadataParser.parse_json_timeline(
                    file_content
                )
            elif file_type == "yaml":
                timeline = EffectMetadataParser.parse_yaml_timeline(
                    file_content
                )
            else:
                raise ValueError(
                    f"Unsupported timeline file type: {file_type}"
                )

            self.current_timeline = timeline
            self.timeline_player.load_timeline(timeline)

            await websocket.send_json(
                {
                    "type": "timeline_loaded",
                    "success": True,
                    "effect_count": len(timeline.effects),
                    "duration": timeline.total_duration,
                    "metadata": timeline.metadata,
                }
            )
        except Exception as e:
            await websocket.send_json(
                {"type": "timeline_error", "success": False, "error": str(e)}
            )

    async def play_timeline(self, websocket: WebSocket):
        """Start playing the loaded timeline."""
        try:
            if not self.current_timeline:
                await websocket.send_json(
                    {"type": "timeline_error", "error": "No timeline loaded"}
                )
                return

            self.timeline_player.start()
            await websocket.send_json(
                {
                    "type": "timeline_status",
                    "is_running": True,
                    "message": "Timeline playback started",
                }
            )
        except Exception as e:
            await websocket.send_json(
                {"type": "timeline_error", "error": str(e)}
            )

    async def pause_timeline(self, websocket: WebSocket):
        """Pause timeline playback."""
        try:
            self.timeline_player.pause()
            await websocket.send_json(
                {
                    "type": "timeline_status",
                    "is_paused": True,
                    "message": "Timeline paused",
                }
            )
        except Exception as e:
            await websocket.send_json(
                {"type": "timeline_error", "error": str(e)}
            )

    async def resume_timeline(self, websocket: WebSocket):
        """Resume timeline playback."""
        try:
            self.timeline_player.resume()
            await websocket.send_json(
                {
                    "type": "timeline_status",
                    "is_paused": False,
                    "message": "Timeline resumed",
                }
            )
        except Exception as e:
            await websocket.send_json(
                {"type": "timeline_error", "error": str(e)}
            )

    async def stop_timeline(self, websocket: WebSocket):
        """Stop timeline playback."""
        try:
            self.timeline_player.stop()
            await websocket.send_json(
                {
                    "type": "timeline_status",
                    "is_running": False,
                    "message": "Timeline stopped",
                }
            )
        except Exception as e:
            await websocket.send_json(
                {"type": "timeline_error", "error": str(e)}
            )

    async def get_timeline_status(self, websocket: WebSocket):
        """Get current timeline status."""
        try:
            status = self.timeline_player.get_status()
            await websocket.send_json({"type": "timeline_status", **status})
        except Exception as e:
            await websocket.send_json(
                {"type": "timeline_error", "error": str(e)}
            )

    def run(
        self,
        host: str = "0.0.0.0",
        port: int = 8090,
        enable_all_protocols: bool = False,
    ):
        """Run the control panel server."""
        print("\n" + "=" * 60)
        print("[+] PythonPlaySEM Control Panel Server")
        print("=" * 60)
        print("\n[WEB] Server running at:")
        print(f"   HTTP: http://{host}:{port}")
        print(f"   WebSocket: ws://{host}:{port}/ws")

        if enable_all_protocols:
            print("\n[PROTOCOLS] Additional Protocol Servers:")
            print(f"   MQTT: mqtt://{host}:1883")
            print(f"   CoAP: coap://{host}:5683")
            print(f"   HTTP API: http://{host}:{port}/api")
            print("   UPnP: SSDP discovery on 239.255.255.250:1900")
            print(
                "\n[!]  Note: MQTT, CoAP, and UPnP servers run in background"
            )
            print("   Use respective client libraries to connect")

        print("\n[i] Open your browser and navigate to:")
        print(f"   http://localhost:{port}")
        print("\n[i] Features:")
        print("   [OK] Real-time device discovery (Bluetooth, Serial, MQTT)")
        print("   [OK] Live device connection management")
        print(
            "   [OK] Multi-protocol support (WebSocket, HTTP, MQTT, CoAP, UPnP)"
        )
        print("   [OK] Effect testing with presets")
        print("   [OK] System monitoring and statistics")
        print("\n[SETTINGS]  Press Ctrl+C to stop")
        print("=" * 60 + "\n")

        uvicorn.run(self.app, host=host, port=port, log_level="info")


def main():
    """Main entry point."""
    import argparse
    import signal

    parser = argparse.ArgumentParser(
        description="PythonPlaySEM Control Panel Server"
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Server host (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8090, help="Server port (default: 8090)"
    )
    parser.add_argument(
        "--all-protocols",
        action="store_true",
        help="Enable all protocol servers (MQTT, CoAP, UPnP)",
    )
    args = parser.parse_args()

    server = ControlPanelServer()

    # Set up signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        print("\n\n[!]  Received shutdown signal, stopping servers...")
        # The uvicorn shutdown will trigger our cleanup
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, signal_handler)

    try:
        server.run(
            host=args.host,
            port=args.port,
            enable_all_protocols=args.all_protocols,
        )
    except KeyboardInterrupt:
        print("[!]  Shutting down control panel server...")
        print("[!]  Please wait for graceful shutdown...")
    except Exception as e:
        print(f"\n[x] Fatal error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
