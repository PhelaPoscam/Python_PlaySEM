#!/usr/bin/env python3
"""
Bluetooth Low Energy (BLE) Driver for wireless devices.

Provides connectivity to BLE sensory devices using the bleak library.
Supports device discovery, connection management, characteristic
read/write, and notification callbacks.

Example:
    >>> driver = BluetoothDriver()
    >>> devices = await driver.scan_devices(timeout=5.0)
    >>> await driver.connect(devices[0]['address'])
    >>> await driver.write_characteristic(uuid, b"\\x01\\xFF")
    >>> await driver.disconnect()
"""

import asyncio
import logging
import json
from typing import Optional, List, Dict, Callable, Any

try:
    from bleak import BleakScanner, BleakClient
    from bleak.backends.characteristic import BleakGATTCharacteristic

    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    BleakScanner = None
    BleakClient = None
    BleakGATTCharacteristic = None

from .base_driver import AsyncBaseDriver

logger = logging.getLogger(__name__)


class BluetoothDriver(AsyncBaseDriver):
    """
    Bluetooth Low Energy (BLE) driver for wireless devices.

    Manages BLE communication with connected hardware devices,
    including device discovery, GATT services/characteristics,
    and notification handling.

    Attributes:
        address: BLE device MAC address
        is_connected: Connection status
        device_name: Connected device name

    Example:
        >>> # Async usage
        >>> driver = BluetoothDriver()
        >>> devices = await driver.scan_devices()
        >>> print(f"Found: {devices[0]['name']}")
        >>>
        >>> await driver.connect(devices[0]['address'])
        >>> await driver.write_characteristic(
        ...     "0000ffe1-0000-1000-8000-00805f9b34fb",
        ...     b"\\xFF\\x00\\x64"
        ... )
        >>> await driver.disconnect()
    """

    def __init__(
        self,
        address: Optional[str] = None,
        device_name: Optional[str] = None,
        on_disconnect: Optional[Callable[[BleakClient], None]] = None,
    ):
        """
        Initialize Bluetooth driver.

        Args:
            address: BLE device MAC address (e.g., "AA:BB:CC:DD:EE:FF")
            device_name: Optional device name for discovery
            on_disconnect: Optional callback when device disconnects

        Raises:
            ImportError: If bleak is not installed
        """
        if not BLEAK_AVAILABLE:
            raise ImportError("bleak not installed. Run: pip install bleak")

        self.address = address
        self.device_name = device_name
        self.on_disconnect = on_disconnect

        self._client: Optional[BleakClient] = None
        self._is_connected = False
        self._services: Dict[str, Any] = {}
        self._notification_callbacks: Dict[str, Callable] = {}

        logger.info(
            f"BluetoothDriver initialized - "
            f"address: {address or 'not set'}, "
            f"name: {device_name or 'not set'}"
        )

    @staticmethod
    async def scan_devices(
        timeout: float = 5.0,
        name_filter: Optional[str] = None,
        service_uuids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Scan for nearby BLE devices.

        Args:
            timeout: Scan duration in seconds (default: 5.0)
            name_filter: Optional name pattern to filter devices
            service_uuids: Optional list of service UUIDs to filter

        Returns:
            List of dictionaries containing device information:
                - address: Device MAC address
                - name: Device name
                - rssi: Signal strength (dBm)
                - metadata: Additional device metadata

        Example:
            >>> devices = await BluetoothDriver.scan_devices(
            ...     timeout=10.0,
            ...     name_filter="Arduino"
            ... )
            >>> for device in devices:
            ...     print(f"{device['name']}: {device['address']}")
            Arduino Nano 33: AA:BB:CC:DD:EE:FF
        """
        if not BLEAK_AVAILABLE:
            logger.error("bleak not available for scanning")
            return []

        logger.info(f"Scanning for BLE devices (timeout: {timeout}s)...")

        try:
            # Scan with optional service UUID filter
            discovered = await BleakScanner.discover(
                timeout=timeout, service_uuids=service_uuids
            )

            devices = []
            for device in discovered:
                # Apply name filter if specified
                if name_filter and device.name:
                    if name_filter.lower() not in device.name.lower():
                        continue

                # Get RSSI from metadata or details (platform-dependent)
                rssi = None
                if hasattr(device, "rssi"):
                    rssi = device.rssi
                elif hasattr(device, "metadata") and device.metadata:
                    rssi = device.metadata.get("rssi")
                elif hasattr(device, "details") and device.details:
                    # Windows-specific: details might have signal strength
                    rssi = getattr(device.details, "SignalStrength", None)

                device_info = {
                    "address": device.address,
                    "name": device.name or "Unknown",
                    "rssi": rssi if rssi is not None else -999,
                    "metadata": (
                        device.metadata if hasattr(device, "metadata") else {}
                    ),
                }

                devices.append(device_info)
                logger.debug(
                    f"Found: {device_info['name']} "
                    f"({device_info['address']}) "
                    f"RSSI: {device_info['rssi']} dBm"
                )

            logger.info(f"Scan complete: found {len(devices)} device(s)")
            return devices

        except Exception as e:
            logger.error(f"Scan failed: {e}")
            return []

    @staticmethod
    async def find_device(
        name: Optional[str] = None,
        address: Optional[str] = None,
        timeout: float = 5.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Find a specific BLE device by name or address.

        Args:
            name: Device name to search for
            address: Device MAC address to search for
            timeout: Scan timeout in seconds

        Returns:
            Device info dict if found, None otherwise

        Example:
            >>> device = await BluetoothDriver.find_device(
            ...     name="Arduino Nano 33"
            ... )
            >>> if device:
            ...     print(f"Found at {device['address']}")
        """
        if not name and not address:
            logger.error("Must specify name or address")
            return None

        devices = await BluetoothDriver.scan_devices(
            timeout=timeout, name_filter=name
        )

        for device in devices:
            if address and device["address"] == address:
                return device
            if name and name.lower() in device["name"].lower():
                return device

        return None

    async def connect(
        self,
        address: Optional[str] = None,
        timeout: float = 10.0,
    ) -> bool:
        """
        Connect to BLE device.

        Args:
            address: Device MAC address (uses self.address if not provided)
            timeout: Connection timeout in seconds

        Returns:
            True if connection successful, False otherwise

        Example:
            >>> driver = BluetoothDriver()
            >>> if await driver.connect("AA:BB:CC:DD:EE:FF"):
            ...     print("Connected!")
        """
        if self._is_connected:
            logger.warning("Already connected")
            return True

        target_address = address or self.address
        if not target_address:
            logger.error("No address specified")
            return False

        try:
            logger.info(f"Connecting to {target_address}...")

            # Create client with disconnect callback
            self._client = BleakClient(
                target_address,
                disconnected_callback=self._handle_disconnect,
                timeout=timeout,
            )

            # Connect
            await self._client.connect()

            # Verify connection
            if not self._client.is_connected:
                logger.error("Connection failed")
                return False

            self.address = target_address
            self._is_connected = True

            # Discover services
            await self._discover_services()

            logger.info(
                f"Connected to {target_address} "
                f"({len(self._services)} services)"
            )
            return True

        except asyncio.TimeoutError:
            logger.error(f"Connection timeout to {target_address}")
            return False
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    async def disconnect(self):
        """
        Disconnect from BLE device.

        Stops all notifications and closes the connection.

        Example:
            >>> await driver.disconnect()
            >>> print(f"Connected: {driver.is_connected}")
            Connected: False
        """
        if not self._is_connected or not self._client:
            return

        try:
            # Stop all notifications
            for uuid in list(self._notification_callbacks.keys()):
                await self.stop_notify(uuid)

            # Disconnect
            await self._client.disconnect()

            logger.info(f"Disconnected from {self.address}")

        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
        finally:
            self._is_connected = False
            self._client = None
            self._services.clear()
            self._notification_callbacks.clear()

    async def write_characteristic(
        self,
        uuid: str,
        data: bytes,
        response: bool = True,
    ) -> bool:
        """
        Write data to a BLE characteristic.

        Args:
            uuid: Characteristic UUID (e.g., "0000ffe1-0000-1000-8000-00805f9b34fb")
            data: Bytes to write
            response: Wait for write response (default: True)

        Returns:
            True if write successful, False otherwise

        Example:
            >>> # Write effect command
            >>> await driver.write_characteristic(
            ...     "0000ffe1-0000-1000-8000-00805f9b34fb",
            ...     b"\\xFF\\x00\\x64"  # LED on at intensity 100
            ... )
            True
        """
        if not self._is_connected or not self._client:
            logger.error("Not connected")
            return False

        try:
            await self._client.write_gatt_char(uuid, data, response=response)

            logger.debug(
                f"Wrote {len(data)} bytes to {uuid[:8]}: {data.hex()}"
            )
            return True

        except Exception as e:
            logger.error(f"Write failed to {uuid}: {e}")
            return False

    async def read_characteristic(self, uuid: str) -> Optional[bytes]:
        """
        Read data from a BLE characteristic.

        Args:
            uuid: Characteristic UUID

        Returns:
            Bytes read, or None if error

        Example:
            >>> data = await driver.read_characteristic(
            ...     "0000ffe1-0000-1000-8000-00805f9b34fb"
            ... )
            >>> if data:
            ...     print(f"Read: {data.hex()}")
            Read: ff0064
        """
        if not self._is_connected or not self._client:
            logger.error("Not connected")
            return None

        try:
            data = await self._client.read_gatt_char(uuid)
            logger.debug(
                f"Read {len(data)} bytes from {uuid[:8]}: {data.hex()}"
            )
            return data

        except Exception as e:
            logger.error(f"Read failed from {uuid}: {e}")
            return None

    async def start_notify(
        self,
        uuid: str,
        callback: Callable[[int, bytearray], None],
    ) -> bool:
        """
        Start receiving notifications from a characteristic.

        Args:
            uuid: Characteristic UUID
            callback: Function to call when notification received
                Signature: callback(sender: int, data: bytearray)

        Returns:
            True if notifications started, False otherwise

        Example:
            >>> def on_notify(sender, data):
            ...     print(f"Notification: {data.hex()}")
            >>>
            >>> await driver.start_notify(
            ...     "0000ffe1-0000-1000-8000-00805f9b34fb",
            ...     on_notify
            ... )
        """
        if not self._is_connected or not self._client:
            logger.error("Not connected")
            return False

        try:
            await self._client.start_notify(uuid, callback)
            self._notification_callbacks[uuid] = callback

            logger.info(f"Started notifications on {uuid[:8]}")
            return True

        except Exception as e:
            logger.error(f"Failed to start notifications on {uuid}: {e}")
            return False

    async def stop_notify(self, uuid: str) -> bool:
        """
        Stop receiving notifications from a characteristic.

        Args:
            uuid: Characteristic UUID

        Returns:
            True if notifications stopped, False otherwise

        Example:
            >>> await driver.stop_notify(
            ...     "0000ffe1-0000-1000-8000-00805f9b34fb"
            ... )
        """
        if not self._is_connected or not self._client:
            return False

        try:
            await self._client.stop_notify(uuid)
            self._notification_callbacks.pop(uuid, None)

            logger.info(f"Stopped notifications on {uuid[:8]}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop notifications on {uuid}: {e}")
            return False

    async def get_services(self) -> Dict[str, Any]:
        """
        Get all GATT services and characteristics.

        Returns:
            Dictionary mapping service UUIDs to service info

        Example:
            >>> services = await driver.get_services()
            >>> for uuid, service in services.items():
            ...     print(f"Service: {service['uuid']}")
            ...     for char in service['characteristics']:
            ...         print(f"  Char: {char['uuid']}")
        """
        if not self._is_connected:
            return {}

        return self._services.copy()

    async def _discover_services(self):
        """Discover and cache GATT services."""
        if not self._client:
            return

        try:
            services = self._client.services

            for service in services:
                service_info = {
                    "uuid": service.uuid,
                    "description": service.description,
                    "characteristics": [],
                }

                for char in service.characteristics:
                    char_info = {
                        "uuid": char.uuid,
                        "properties": char.properties,
                        "descriptors": [d.uuid for d in char.descriptors],
                    }
                    service_info["characteristics"].append(char_info)

                self._services[service.uuid] = service_info

            logger.debug(f"Discovered {len(self._services)} services")

        except Exception as e:
            logger.error(f"Service discovery failed: {e}")

    def _handle_disconnect(self, client: BleakClient):
        """Handle unexpected disconnection."""
        logger.warning(f"Device disconnected: {self.address}")
        self._is_connected = False

        if self.on_disconnect:
            try:
                self.on_disconnect(client)
            except Exception as e:
                logger.error(f"Disconnect callback error: {e}")

    async def is_connected(self) -> bool:
        """Check if device is connected (AsyncBaseDriver interface)."""
        return self._is_connected and self._client is not None

    async def send_text(
        self,
        uuid: str,
        command: str,
        encoding: str = "utf-8",
    ) -> bool:
        """
        Send text command to characteristic.

        Args:
            uuid: Characteristic UUID to write to
            command: Text command to send
            encoding: Text encoding (default: 'utf-8')

        Returns:
            True if send successful, False otherwise

        Example:
            >>> await driver.send_text(
            ...     "0000ffe1-0000-1000-8000-00805f9b34fb",
            ...     "LED:ON\\n"
            ... )
        """
        return await self.write_characteristic(uuid, command.encode(encoding))

    # AsyncBaseDriver interface implementation
    async def send_command(
        self,
        device_id: str,
        command: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send command to device (AsyncBaseDriver interface).

        For BLE devices, device_id is treated as the characteristic UUID.
        Commands are sent as JSON or text.

        Args:
            device_id: Characteristic UUID
            command: Command string
            params: Optional parameters dictionary

        Returns:
            bool: True if command sent successfully

        Example:
            >>> await driver.send_command(
            ...     device_id="0000ffe1-0000-1000-8000-00805f9b34fb",
            ...     command="SET_LED",
            ...     params={"intensity": 255}
            ... )
            True
        """
        if not await self.is_connected():
            logger.warning("Cannot send command: not connected")
            return False

        try:
            # Build command message
            if params:
                # Send as JSON for structured data
                message = {
                    "command": command,
                    "params": params,
                }
                payload = json.dumps(message) + "\n"
            else:
                # Send as simple text command
                payload = f"{command}\n"

            # Send via BLE characteristic
            return await self.write_characteristic(
                device_id, payload.encode("utf-8")
            )

        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return False

    async def __aenter__(self):
        """Async context manager entry."""
        if self.address:
            await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    def get_capabilities(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Get device capabilities for BLE-connected devices.

        Returns generic haptic/vibration capabilities. For device-specific
        capabilities, query the device via BLE characteristics.
        """
        from ..device_capabilities import (
            DeviceCapabilities,
            EffectCapability,
            EffectType,
            ParameterCapability,
            ParameterType,
            create_standard_intensity_param,
            create_standard_duration_param,
        )

        # Create capabilities for BLE devices
        caps = DeviceCapabilities(
            device_id=device_id,
            device_type="BluetoothDevice",
            manufacturer="Unknown",
            model=f"BLE@{self.device_name or self.address}",
            driver_type="bluetooth",
            metadata={
                "address": self.address,
                "name": self.device_name,
                "services": (
                    list(self._services.keys()) if self._services else []
                ),
            },
        )

        # BLE devices typically support haptic/vibration effects
        haptic_effect = EffectCapability(
            effect_type=EffectType.HAPTIC,
            description="Bluetooth haptic feedback",
            parameters=[
                create_standard_intensity_param(),
                create_standard_duration_param(),
                ParameterCapability(
                    name="pattern",
                    type=ParameterType.ENUM,
                    enum_values=["pulse", "wave", "constant"],
                    default="constant",
                    description="Haptic pattern type",
                ),
            ],
        )
        caps.effects.append(haptic_effect)

        # Many BLE devices also support vibration
        vibration_effect = EffectCapability(
            effect_type=EffectType.VIBRATION,
            description="Vibration motor control",
            parameters=[
                create_standard_intensity_param(),
                create_standard_duration_param(),
            ],
        )
        caps.effects.append(vibration_effect)

        return caps.to_dict()

    def __repr__(self) -> str:
        """String representation."""
        status = "connected" if self._is_connected else "disconnected"
        return f"BluetoothDriver(address={self.address}, " f"status={status})"
