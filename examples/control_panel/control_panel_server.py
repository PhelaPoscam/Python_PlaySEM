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
import asyncio
import time
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

from src.device_driver import SerialDriver, BluetoothDriver, MQTTDriver
from src.device_driver.mock_driver import (
    MockLightDevice,
    MockWindDevice,
    MockVibrationDevice,
)
from src.device_manager import DeviceManager
from src.effect_dispatcher import EffectDispatcher
from src.effect_metadata import create_effect
from src.protocol_server import (
    MQTTServer,
    CoAPServer,
    UPnPServer,
    HTTPServer,
    WebSocketServer,
)
from src.timeline import Timeline
from src.effect_metadata import EffectMetadataParser


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
        self.app = FastAPI(title="PythonPlaySEM Control Panel API")
        self.devices: Dict[str, ConnectedDevice] = {}
        self.clients: Set[WebSocket] = set()
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
            tick_interval=0.01  # 10ms precision
        )
        self.current_timeline = None
        self.timeline_player.set_callbacks(
            on_effect=self._on_timeline_effect,
            on_complete=self._on_timeline_complete
        )

        self._setup_routes()

    def _setup_routes(self):
        """Set up FastAPI routes."""

        @self.app.get("/")
        async def root():
            """Serve the control panel HTML."""
            control_panel_path = Path(__file__).parent / "control_panel.html"
            with open(control_panel_path, "r", encoding="utf-8") as f:
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
                device_id = f"{driver_type}_{address.replace(':', '_').replace('/', '_')}"

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
                xml_str = xml_content.decode('utf-8')
                
                timeline = EffectMetadataParser.parse_mpegv_xml(xml_str)
                self.current_timeline = timeline
                self.timeline_player.load_timeline(timeline)
                
                return {
                    "type": "timeline_loaded",
                    "success": True,
                    "effect_count": len(timeline.effects),
                    "duration": timeline.total_duration,
                    "metadata": timeline.metadata
                }
            except Exception as e:
                return {
                    "type": "timeline_error",
                    "success": False,
                    "error": str(e)
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
            "duration": effect.duration
        }
        for client in list(self.clients):
            try:
                await client.send_json(message)
            except Exception:
                self.clients.discard(client)

    async def _broadcast_timeline_status(self):
        """Broadcast timeline status to all clients."""
        status = self.timeline_player.get_status()
        message = {
            "type": "timeline_status",
            **status
        }
        for client in list(self.clients):
            try:
                await client.send_json(message)
            except Exception:
                self.clients.discard(client)

    async def handle_client(self, websocket: WebSocket):
        """Handle WebSocket client connection."""
        await websocket.accept()
        self.clients.add(websocket)

        print(f"✅ Client connected. Total clients: {len(self.clients)}")

        try:
            # Send initial device list
            await self.send_device_list(websocket)

            # Handle incoming messages
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                await self.handle_message(websocket, message)

        except WebSocketDisconnect:
            print(
                f"❌ Client disconnected. Remaining clients: {len(self.clients) - 1}"
            )
        except Exception as e:
            print(f"❌ WebSocket error: {e}")
        finally:
            self.clients.discard(websocket)

    async def handle_message(self, websocket: WebSocket, message: dict):
        """Handle incoming WebSocket message."""
        msg_type = message.get("type")

        print(f"📨 Received message: {msg_type}")

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

        elif msg_type == "start_protocol_server":
            protocol = message.get("protocol")
            await self.start_protocol_server(websocket, protocol)

        elif msg_type == "stop_protocol_server":
            protocol = message.get("protocol")
            await self.stop_protocol_server(websocket, protocol)

        elif msg_type == "upload_timeline":
            xml_content = message.get("xml_content")
            await self.handle_timeline_upload(websocket, xml_content)

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
        print(f"🔍 Scanning for {driver_type} devices...")

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
            print(f"❌ Scan error: {e}")
            await websocket.send_json(
                {"type": "error", "message": f"Scan failed: {str(e)}"}
            )

    async def scan_bluetooth(self, websocket: WebSocket):
        """Scan for Bluetooth devices."""
        try:
            driver = BluetoothDriver()
            devices = await driver.scan_devices(timeout=5.0)

            print(f"✅ Found {len(devices)} Bluetooth devices")

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
            print(f"❌ Bluetooth scan error: {e}")
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

            print(f"✅ Found {len(ports)} Serial ports")

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
            print(f"❌ Serial scan error: {e}")
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

            print(f"✅ Found {len(mock_devices)} Mock devices")

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
            print(f"❌ Mock scan error: {e}")
            await websocket.send_json(
                {"type": "error", "message": f"Mock scan failed: {str(e)}"}
            )

    async def connect_device(
        self, websocket: WebSocket, address: str, driver_type: str
    ):
        """Connect to a device."""
        print(f"🔌 Connecting to {driver_type} device: {address}")

        try:
            device_id = (
                f"{driver_type}_{address.replace(':', '_').replace('/', '_')}"
            )

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
                name = f"Mock {mock_device.__class__.__name__.replace('Mock', '').replace('Device', '')} ({address})"

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

                print(f"✅ Connected to {name}")

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
            print(f"❌ Connection error: {e}")
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

            print(f"✅ Disconnected {device.name}")

            # Notify all clients
            await self.broadcast_device_list()

            await websocket.send_json(
                {"type": "success", "message": f"Disconnected {device.name}"}
            )

        except Exception as e:
            print(f"❌ Disconnect error: {e}")
            await websocket.send_json(
                {"type": "error", "message": f"Disconnect failed: {str(e)}"}
            )

    async def send_effect(
        self, websocket: WebSocket, device_id: str, effect_data: dict
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

            if device.type == "mock":
                # Mock devices handle effects directly
                effect_type = effect_data.get("effect_type", "vibration")
                intensity = effect_data.get("intensity", 50)
                duration = effect_data.get("duration", 1000)

                mock_device = device.driver  # Mock device stored as driver

                # Send command based on effect type
                if effect_type == "light":
                    # Map intensity (0-100) to brightness (0-255)
                    brightness = int(intensity * 2.55)
                    mock_device.send_command(
                        "set_brightness", {"brightness": brightness}
                    )
                elif effect_type == "wind":
                    mock_device.send_command("set_speed", {"speed": intensity})
                elif effect_type == "vibration":
                    mock_device.send_command(
                        "set_intensity",
                        {"intensity": intensity, "duration": duration},
                    )
                else:
                    # Generic command for other types
                    mock_device.send_command(
                        effect_type,
                        {"intensity": intensity, "duration": duration},
                    )

                print(
                    f"✅ Mock device '{mock_device.device_id}' received {effect_type.upper()} command: intensity={intensity}, duration={duration}"
                )
            else:
                # Real devices use effect dispatcher
                effect = create_effect(
                    effect_type=effect_data.get("effect_type", "vibration"),
                    intensity=effect_data.get("intensity", 50),
                    duration=effect_data.get("duration", 1000),
                    timestamp=0,
                )
                device.dispatcher.dispatch_effect_metadata(effect)

            latency = int((time.time() - start_time) * 1000)
            self.stats["effects_sent"] += 1

            print(f"✅ Effect sent to {device.name} (latency: {latency}ms)")

            await websocket.send_json(
                {
                    "type": "effect_result",
                    "success": True,
                    "latency": latency,
                    "device_id": device_id,
                }
            )

        except Exception as e:
            print(f"❌ Effect send error: {e}")
            self.stats["errors"] += 1
            await websocket.send_json(
                {
                    "type": "effect_result",
                    "success": False,
                    "error": str(e),
                    "device_id": device_id,
                }
            )

    async def start_protocol_server(self, websocket: WebSocket, protocol: str):
        """Start a protocol server (MQTT, CoAP, UPnP, HTTP)."""
        print(f"🚀 Starting {protocol.upper()} server...")

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

                # Create MQTT server with proper dispatcher
                # Use public test broker if localhost fails
                self.mqtt_server = MQTTServer(
                    broker_address="test.mosquitto.org",
                    dispatcher=self.global_dispatcher,
                    subscribe_topic="effects/#",
                    port=1883,
                )
                print("ℹ️  Using public test broker: test.mosquitto.org")
                print("   (For production, install local Mosquitto broker)")
                # MQTT server has synchronous start
                await asyncio.to_thread(self.mqtt_server.start)

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
                print("ℹ️  CoAP server binding to 127.0.0.1:5683")
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
                print("ℹ️  HTTP REST API starting on port 8081")
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
                print("ℹ️  WebSocket SEM server starting on port 8765")
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

            print(f"✅ {protocol.upper()} server started successfully")
            await websocket.send_json(
                {
                    "type": "protocol_status",
                    "protocol": protocol,
                    "running": True,
                }
            )

        except Exception as e:
            print(f"❌ Failed to start {protocol.upper()} server: {e}")
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
        print(f"🛑 Stopping {protocol.upper()} server...")

        try:
            if protocol == "mqtt":
                if self.mqtt_server:
                    # MQTT server has synchronous stop
                    await asyncio.to_thread(self.mqtt_server.stop)
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

            print(f"✅ {protocol.upper()} server stopped")
            await websocket.send_json(
                {
                    "type": "protocol_status",
                    "protocol": protocol,
                    "running": False,
                }
            )

        except Exception as e:
            print(f"❌ Failed to stop {protocol.upper()} server: {e}")
            await websocket.send_json(
                {
                    "type": "protocol_status",
                    "protocol": protocol,
                    "running": False,
                    "error": str(e),
                }
            )

    async def handle_timeline_upload(self, websocket: WebSocket, xml_content: str):
        """Handle XML timeline upload via WebSocket."""
        try:
            timeline = EffectMetadataParser.parse_mpegv_xml(xml_content)
            self.current_timeline = timeline
            self.timeline_player.load_timeline(timeline)
            
            await websocket.send_json({
                "type": "timeline_loaded",
                "success": True,
                "effect_count": len(timeline.effects),
                "duration": timeline.total_duration,
                "metadata": timeline.metadata
            })
        except Exception as e:
            await websocket.send_json({
                "type": "timeline_error",
                "success": False,
                "error": str(e)
            })

    async def play_timeline(self, websocket: WebSocket):
        """Start playing the loaded timeline."""
        try:
            if not self.current_timeline:
                await websocket.send_json({
                    "type": "timeline_error",
                    "error": "No timeline loaded"
                })
                return
            
            self.timeline_player.start()
            await websocket.send_json({
                "type": "timeline_status",
                "is_running": True,
                "message": "Timeline playback started"
            })
        except Exception as e:
            await websocket.send_json({
                "type": "timeline_error",
                "error": str(e)
            })

    async def pause_timeline(self, websocket: WebSocket):
        """Pause timeline playback."""
        try:
            self.timeline_player.pause()
            await websocket.send_json({
                "type": "timeline_status",
                "is_paused": True,
                "message": "Timeline paused"
            })
        except Exception as e:
            await websocket.send_json({
                "type": "timeline_error",
                "error": str(e)
            })

    async def resume_timeline(self, websocket: WebSocket):
        """Resume timeline playback."""
        try:
            self.timeline_player.resume()
            await websocket.send_json({
                "type": "timeline_status",
                "is_paused": False,
                "message": "Timeline resumed"
            })
        except Exception as e:
            await websocket.send_json({
                "type": "timeline_error",
                "error": str(e)
            })

    async def stop_timeline(self, websocket: WebSocket):
        """Stop timeline playback."""
        try:
            self.timeline_player.stop()
            await websocket.send_json({
                "type": "timeline_status",
                "is_running": False,
                "message": "Timeline stopped"
            })
        except Exception as e:
            await websocket.send_json({
                "type": "timeline_error",
                "error": str(e)
            })

    async def get_timeline_status(self, websocket: WebSocket):
        """Get current timeline status."""
        try:
            status = self.timeline_player.get_status()
            await websocket.send_json({
                "type": "timeline_status",
                **status
            })
        except Exception as e:
            await websocket.send_json({
                "type": "timeline_error",
                "error": str(e)
            })

    async def broadcast_device_list(self):
        """Broadcast device list to all connected clients."""
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

        # Send to all connected clients
        for client in list(self.clients):
            try:
                await client.send_json(message)
            except Exception:
                self.clients.discard(client)

    def run(
        self,
        host: str = "0.0.0.0",
        port: int = 8090,
        enable_all_protocols: bool = False,
    ):
        """Run the control panel server."""
        print("\n" + "=" * 60)
        print("🎮 PythonPlaySEM Control Panel Server")
        print("=" * 60)
        print(f"\n🌐 Server running at:")
        print(f"   HTTP: http://{host}:{port}")
        print(f"   WebSocket: ws://{host}:{port}/ws")

        if enable_all_protocols:
            print(f"\n📡 Additional Protocol Servers:")
            print(f"   MQTT: mqtt://{host}:1883")
            print(f"   CoAP: coap://{host}:5683")
            print(f"   HTTP API: http://{host}:{port}/api")
            print(f"   UPnP: SSDP discovery on 239.255.255.250:1900")
            print(f"\n⚠️  Note: MQTT, CoAP, and UPnP servers run in background")
            print(f"   Use respective client libraries to connect")

        print(f"\n📱 Open your browser and navigate to:")
        print(f"   http://localhost:{port}")
        print(f"\n💡 Features:")
        print(f"   ✅ Real-time device discovery (Bluetooth, Serial, MQTT)")
        print(f"   ✅ Live device connection management")
        print(
            f"   ✅ Multi-protocol support (WebSocket, HTTP, MQTT, CoAP, UPnP)"
        )
        print(f"   ✅ Effect testing with presets")
        print(f"   ✅ System monitoring and statistics")
        print(f"\n⚙️  Press Ctrl+C to stop")
        print("=" * 60 + "\n")

        uvicorn.run(self.app, host=host, port=port, log_level="info")


def main():
    """Main entry point."""
    import argparse

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

    try:
        server.run(
            host=args.host,
            port=args.port,
            enable_all_protocols=args.all_protocols,
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Shutting down control panel server...")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
