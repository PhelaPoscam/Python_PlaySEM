"""
Central Device Registry for PlaySEM Platform

Provides protocol-agnostic device storage and management.
Devices registered via ANY protocol are visible to ALL protocols.

Key Features:
- Thread-safe operations
- Protocol-agnostic storage
- Event notifications on device changes
- Query by protocol, type, capability, etc.
- Automatic device lifecycle management

Usage:
    registry = DeviceRegistry()

    # Register device from any protocol
    registry.register_device({
        "id": "device_123",
        "name": "Smart Light",
        "type": "light",
        "protocols": ["mqtt"],
        "capabilities": ["light", "color"]
    }, source_protocol="mqtt")

    # Query all devices (regardless of protocol)
    all_devices = registry.get_all_devices()

    # Query by protocol
    mqtt_devices = registry.get_devices_by_protocol("mqtt")
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """
    Device information stored in registry.

    Attributes:
        id: Unique device identifier
        name: Human-readable device name
        type: Device type (light, vibration, wind, etc.)
        address: Device address (MAC, IP, serial port, etc.)
        protocols: List of protocols this device supports
        capabilities: List of effect types device can handle
        connection_mode: How device connects (direct, isolated, hub)
        metadata: Additional device-specific information
        registered_at: Timestamp when device was registered
        last_seen: Timestamp of last activity
        source_protocol: Protocol that registered this device
    """

    id: str
    name: str
    type: str
    address: str
    protocols: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    connection_mode: str = "direct"
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    source_protocol: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "address": self.address,
            "protocols": self.protocols,
            "capabilities": self.capabilities,
            "connection_mode": self.connection_mode,
            "metadata": self.metadata,
            "registered_at": self.registered_at.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "source_protocol": self.source_protocol,
        }

    def update_last_seen(self):
        """Update last seen timestamp."""
        self.last_seen = datetime.now()


class DeviceRegistry:
    """
    Central registry for all devices across all protocols.

    Thread-safe device storage that allows devices connected via
    any protocol to be visible and accessible from all protocols.

    This solves the "protocol isolation" problem where MQTT devices
    couldn't be seen by WebSocket clients, etc.

    Args:
        enable_protocol_isolation: If True, devices are only visible to their
            source protocol (like Super Controller Device Simulator).
            If False (default), devices are visible across all protocols.
    """

    def __init__(self, enable_protocol_isolation: bool = False):
        """
        Initialize the device registry.

        Args:
            enable_protocol_isolation: Enable protocol isolation mode.
                When True, devices registered via MQTT are only visible to MQTT clients,
                WebSocket devices only to WebSocket clients, etc.
                When False (default), all devices are visible to all protocols.
        """
        self._devices: Dict[str, DeviceInfo] = {}
        self._lock = threading.RLock()
        self._listeners: List[Callable] = []
        self._protocol_isolation = enable_protocol_isolation

        mode = "ISOLATED" if enable_protocol_isolation else "SHARED"
        logger.info(f"Device Registry initialized (mode: {mode})")

    def register_device(
        self, device_data: Dict[str, Any], source_protocol: str
    ) -> DeviceInfo:
        """
        Register a device from any protocol.

        Args:
            device_data: Device information dictionary
            source_protocol: Protocol that registered this device

        Returns:
            DeviceInfo object

        Example:
            >>> registry.register_device({
            ...     "id": "light_123",
            ...     "name": "Smart Light",
            ...     "type": "light",
            ...     "protocols": ["mqtt", "websocket"],
            ...     "capabilities": ["light", "color"]
            ... }, source_protocol="mqtt")
        """
        with self._lock:
            device_id = device_data.get("id") or device_data.get("device_id")

            if not device_id:
                raise ValueError("Device must have an 'id' or 'device_id'")

            # Check if device already exists
            if device_id in self._devices:
                # Update existing device
                existing = self._devices[device_id]
                existing.update_last_seen()

                # Merge protocols if new one provided
                new_protocols = device_data.get("protocols", [])
                if source_protocol not in existing.protocols:
                    existing.protocols.append(source_protocol)
                for proto in new_protocols:
                    if proto not in existing.protocols:
                        existing.protocols.append(proto)

                logger.info(
                    f"Updated device: {device_id} (now supports: {existing.protocols})"
                )
                self._notify_listeners("device_updated", existing)
                return existing

            # Create new device
            device = DeviceInfo(
                id=device_id,
                name=device_data.get("name")
                or device_data.get("device_name", f"Device {device_id}"),
                type=device_data.get("type")
                or device_data.get("device_type", "unknown"),
                address=device_data.get("address", device_id),
                protocols=device_data.get("protocols", [source_protocol]),
                capabilities=device_data.get("capabilities", []),
                connection_mode=device_data.get("connection_mode", "isolated"),
                metadata=device_data.get("metadata", {}),
                source_protocol=source_protocol,
            )

            # Ensure source protocol is in protocols list
            if source_protocol not in device.protocols:
                device.protocols.append(source_protocol)

            self._devices[device_id] = device

            logger.info(
                f"Registered device: {device.name} ({device_id}) "
                f"via {source_protocol} - protocols: {device.protocols}"
            )

            self._notify_listeners("device_registered", device)
            return device

    def unregister_device(self, device_id: str) -> bool:
        """
        Remove a device from the registry.

        Args:
            device_id: Device identifier

        Returns:
            True if device was removed, False if not found
        """
        with self._lock:
            if device_id in self._devices:
                device = self._devices.pop(device_id)
                logger.info(
                    f"Unregistered device: {device.name} ({device_id})"
                )
                self._notify_listeners("device_unregistered", device)
                return True
            return False

    def get_device(
        self, device_id: str, requesting_protocol: Optional[str] = None
    ) -> Optional[DeviceInfo]:
        """
        Get device by ID.

        Args:
            device_id: Device identifier
            requesting_protocol: Protocol making the request (only used if protocol isolation is enabled)

        Returns:
            DeviceInfo if found and accessible, None otherwise
        """
        with self._lock:
            device = self._devices.get(device_id)
            if device and self._protocol_isolation and requesting_protocol:
                # In isolation mode, only return device if protocol matches
                if requesting_protocol not in device.protocols:
                    return None
            return device

    def get_all_devices(
        self, requesting_protocol: Optional[str] = None
    ) -> List[DeviceInfo]:
        """
        Get all registered devices.

        Args:
            requesting_protocol: Protocol making the request (only used if protocol isolation is enabled)

        Returns:
            List of all DeviceInfo objects (filtered by protocol if isolation is enabled)
        """
        with self._lock:
            devices = list(self._devices.values())

            if self._protocol_isolation and requesting_protocol:
                # In isolation mode, only return devices that support the requesting protocol
                devices = [
                    d for d in devices if requesting_protocol in d.protocols
                ]

            return devices

    def get_devices_by_protocol(self, protocol: str) -> List[DeviceInfo]:
        """
        Get devices that support a specific protocol.

        Args:
            protocol: Protocol name (mqtt, websocket, http, etc.)

        Returns:
            List of DeviceInfo objects supporting the protocol
        """
        with self._lock:
            return [
                device
                for device in self._devices.values()
                if protocol in device.protocols
            ]

    def get_devices_by_type(self, device_type: str) -> List[DeviceInfo]:
        """
        Get devices of a specific type.

        Args:
            device_type: Device type (light, vibration, wind, etc.)

        Returns:
            List of DeviceInfo objects of specified type
        """
        with self._lock:
            return [
                device
                for device in self._devices.values()
                if device.type == device_type
            ]

    def get_devices_by_capability(self, capability: str) -> List[DeviceInfo]:
        """
        Get devices with a specific capability.

        Args:
            capability: Capability name

        Returns:
            List of DeviceInfo objects with specified capability
        """
        with self._lock:
            return [
                device
                for device in self._devices.values()
                if capability in device.capabilities
            ]

    def device_exists(self, device_id: str) -> bool:
        """
        Check if device is registered.

        Args:
            device_id: Device identifier

        Returns:
            True if device exists, False otherwise
        """
        with self._lock:
            return device_id in self._devices

    def update_device_activity(self, device_id: str):
        """
        Update the last_seen timestamp for a device.

        Args:
            device_id: Device identifier
        """
        with self._lock:
            if device_id in self._devices:
                self._devices[device_id].update_last_seen()

    def add_listener(self, callback: Callable[[str, DeviceInfo], None]):
        """
        Add a listener for device events.

        Args:
            callback: Function called on device events
                     Signature: callback(event_type: str, device: DeviceInfo)
                     Event types: "device_registered", "device_updated", "device_unregistered"
        """
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)
                logger.debug(
                    f"Added device registry listener: {callback.__name__}"
                )

    def remove_listener(self, callback: Callable):
        """
        Remove a listener.

        Args:
            callback: Function to remove
        """
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)
                logger.debug(
                    f"Removed device registry listener: {callback.__name__}"
                )

    def _notify_listeners(self, event_type: str, device: DeviceInfo):
        """Notify all listeners of a device event."""
        for listener in self._listeners:
            try:
                listener(event_type, device)
            except Exception as e:
                logger.error(f"Error in device registry listener: {e}")

    def is_protocol_isolation_enabled(self) -> bool:
        """
        Check if protocol isolation mode is enabled.

        Returns:
            True if protocol isolation is enabled, False otherwise
        """
        return self._protocol_isolation

    def set_protocol_isolation(self, enabled: bool):
        """
        Enable or disable protocol isolation mode.

        Args:
            enabled: True to enable isolation, False to disable
        """
        with self._lock:
            old_mode = "ISOLATED" if self._protocol_isolation else "SHARED"
            new_mode = "ISOLATED" if enabled else "SHARED"

            if old_mode != new_mode:
                self._protocol_isolation = enabled
                logger.info(
                    f"Protocol isolation mode changed: {old_mode} → {new_mode}"
                )

    def get_stats(
        self, requesting_protocol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get registry statistics.

        Args:
            requesting_protocol: Protocol making the request (only used if protocol isolation is enabled)

        Returns:
            Dictionary with registry stats
        """
        with self._lock:
            # Get devices visible to this protocol
            devices = self.get_all_devices(requesting_protocol)

            protocols_count = {}
            types_count = {}

            for device in devices:
                # Count protocols
                for protocol in device.protocols:
                    protocols_count[protocol] = (
                        protocols_count.get(protocol, 0) + 1
                    )

                # Count types
                types_count[device.type] = types_count.get(device.type, 0) + 1

            return {
                "total_devices": len(devices),
                "devices_by_protocol": protocols_count,
                "devices_by_type": types_count,
                "protocols": list(protocols_count.keys()),
                "protocol_isolation_enabled": self._protocol_isolation,
            }

    def clear(self):
        """Clear all devices from registry."""
        with self._lock:
            count = len(self._devices)
            self._devices.clear()
            logger.info(f"Cleared {count} devices from registry")

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """
        Convert all devices to dictionary list for serialization.

        Returns:
            List of device dictionaries
        """
        with self._lock:
            return [device.to_dict() for device in self._devices.values()]
