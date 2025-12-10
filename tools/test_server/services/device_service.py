"""
Device Service - Device discovery, connection, and management.

Handles all device lifecycle operations including:
- Device scanning (Bluetooth, Serial, Mock)
- Device connection/disconnection
- Device registry management
"""

import asyncio
import time
from typing import Dict, Callable, Any

from fastapi import WebSocket

from playsem import DeviceManager, EffectDispatcher
from playsem.drivers import (
    BluetoothDriver,
    MQTTDriver,
    SerialDriver,
    MockLightDevice,
    MockWindDevice,
    MockVibrationDevice,
)

from ..models import ConnectedDevice


class DeviceService:
    """Service for managing device connections and discovery."""

    def __init__(self, global_dispatcher: EffectDispatcher):
        """Initialize device service.

        Args:
            global_dispatcher: Global effect dispatcher for all devices
        """
        self.devices: Dict[str, ConnectedDevice] = {}
        self.global_dispatcher = global_dispatcher
        self._device_update_callback: Callable[[Dict], None] | None = None

    def set_device_update_callback(self, callback: Callable[[Dict], None]):
        """Set callback for device updates.

        Args:
            callback: Function called when device list changes
        """
        self._device_update_callback = callback

    async def scan_devices(
        self,
        driver_type: str,
        websocket: WebSocket,
    ) -> None:
        """Scan for devices of given type.

        Args:
            driver_type: Type of driver ('bluetooth', 'serial', 'mock')
            websocket: WebSocket connection for sending discovery updates
        """
        if driver_type == "bluetooth":
            await self._scan_bluetooth(websocket)
        elif driver_type == "serial":
            await self._scan_serial(websocket)
        elif driver_type == "mock":
            await self._scan_mock(websocket)
        else:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": f"Unsupported driver type: {driver_type}",
                }
            )

    async def _scan_bluetooth(self, websocket: WebSocket) -> None:
        """Scan for Bluetooth devices.

        Args:
            websocket: WebSocket connection for sending discovery updates
        """
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
                await asyncio.sleep(0.1)

        except Exception as e:
            print(f"[x] Bluetooth scan error: {e}")
            await websocket.send_json(
                {
                    "type": "error",
                    "message": f"Bluetooth scan failed: {str(e)}",
                }
            )

    async def _scan_serial(self, websocket: WebSocket) -> None:
        """Scan for Serial devices.

        Args:
            websocket: WebSocket connection for sending discovery updates
        """
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

    async def _scan_mock(self, websocket: WebSocket) -> None:
        """Scan for Mock devices.

        Args:
            websocket: WebSocket connection for sending discovery updates
        """
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
        address: str,
        driver_type: str,
        websocket: WebSocket,
    ) -> bool:
        """Connect to a device.

        Args:
            address: Device address
            driver_type: Type of driver ('bluetooth', 'serial', 'mqtt', 'mock')
            websocket: WebSocket connection for sending status

        Returns:
            True if connection successful, False otherwise
        """
        print(f"[CONNECT] Connecting to {driver_type} device: {address}")

        try:
            safe_address = address.replace(":", "_").replace("/", "_")
            device_id = f"{driver_type}_{safe_address}"

            if device_id in self.devices:
                await websocket.send_json(
                    {"type": "error", "message": "Device already connected"}
                )
                return False

            # Handle mock devices
            if driver_type == "mock":
                return await self._connect_mock_device(
                    device_id, address, websocket
                )

            # Handle real drivers
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

            else:
                raise ValueError(f"Unsupported driver type: {driver_type}")

            # Create DeviceManager and EffectDispatcher
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

            await websocket.send_json(
                {"type": "success", "message": f"Connected to {name}"}
            )

            if self._device_update_callback:
                self._device_update_callback(self.get_device_list())

            return True

        except Exception as e:
            print(f"[x] Connection error: {e}")
            await websocket.send_json(
                {"type": "error", "message": f"Connection failed: {str(e)}"}
            )
            return False

    async def _connect_mock_device(
        self,
        device_id: str,
        address: str,
        websocket: WebSocket,
    ) -> bool:
        """Connect to a mock device.

        Args:
            device_id: Unique device ID
            address: Device address
            websocket: WebSocket connection

        Returns:
            True if successful
        """
        # Determine mock device type
        if "light" in address:
            mock_device = MockLightDevice(address)
        elif "wind" in address:
            mock_device = MockWindDevice(address)
        elif "vibration" in address:
            mock_device = MockVibrationDevice(address)
        else:
            mock_device = MockLightDevice(address)

        device_class_name = mock_device.__class__.__name__
        clean_name = (
            device_class_name.replace("Mock", "").replace("Device", "").strip()
        )
        name = f"Mock {clean_name} ({address})"

        # Store mock device
        device = ConnectedDevice(
            id=device_id,
            name=name,
            type="mock",
            address=address,
            driver=mock_device,
            manager=None,
            dispatcher=self.global_dispatcher,
            connected_at=time.time(),
        )
        self.devices[device_id] = device

        print(f"[OK] Connected to {name}")

        await websocket.send_json(
            {"type": "success", "message": f"Connected to {name}"}
        )

        if self._device_update_callback:
            self._device_update_callback(self.get_device_list())

        return True

    async def disconnect_device(
        self,
        device_id: str,
        websocket: WebSocket,
    ) -> bool:
        """Disconnect from a device.

        Args:
            device_id: ID of device to disconnect
            websocket: WebSocket connection

        Returns:
            True if successful
        """
        print(f"[DISCONNECT] Disconnecting from {device_id}")

        try:
            if device_id not in self.devices:
                await websocket.send_json(
                    {"type": "error", "message": "Device not connected"}
                )
                return False

            device = self.devices[device_id]

            # Disconnect driver if available
            if device.driver and hasattr(device.driver, "disconnect"):
                if hasattr(device.driver.disconnect, "__await__"):
                    await device.driver.disconnect()
                else:
                    device.driver.disconnect()

            del self.devices[device_id]

            print(f"✅ Disconnected from {device.name}")

            await websocket.send_json(
                {
                    "type": "success",
                    "message": f"Disconnected from {device.name}",
                }
            )

            if self._device_update_callback:
                self._device_update_callback(self.get_device_list())

            return True

        except Exception as e:
            print(f"[x] Disconnection error: {e}")
            await websocket.send_json(
                {"type": "error", "message": f"Disconnection failed: {str(e)}"}
            )
            return False

    def get_device_list(self) -> Dict[str, Any]:
        """Get list of connected devices.

        Returns:
            Dictionary with device information
        """
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

    def get_device(self, device_id: str) -> ConnectedDevice | None:
        """Get a specific device.

        Args:
            device_id: ID of device to retrieve

        Returns:
            ConnectedDevice or None if not found
        """
        return self.devices.get(device_id)
