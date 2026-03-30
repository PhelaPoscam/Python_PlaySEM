"""Device management service extracted from the monolithic server."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ConnectedDevice:
    """Serializable in-memory representation of a connected device."""

    device_id: str
    device_name: str
    device_type: str
    capabilities: List[str] = field(default_factory=list)
    protocols: List[str] = field(default_factory=list)
    connection_mode: str = "direct"
    metadata: Dict[str, Any] = field(default_factory=dict)
    connected: bool = True


class DeviceService:
    """Owns in-memory device lifecycle for the modular app."""

    def __init__(self) -> None:
        self._devices: Dict[str, ConnectedDevice] = {}

    def register_device(
        self,
        *,
        device_id: str,
        device_name: str,
        device_type: str,
        capabilities: List[str],
        protocols: List[str],
        connection_mode: str = "direct",
        metadata: Dict[str, Any] | None = None,
    ) -> ConnectedDevice:
        device = ConnectedDevice(
            device_id=device_id,
            device_name=device_name,
            device_type=device_type,
            capabilities=list(capabilities),
            protocols=list(protocols),
            connection_mode=connection_mode,
            metadata=metadata or {},
        )
        self._devices[device_id] = device
        return device

    def connect_device(
        self, *, address: str, driver_type: str
    ) -> ConnectedDevice:
        device_id = f"{driver_type}_{address}"
        return self.register_device(
            device_id=device_id,
            device_name=address,
            device_type=driver_type,
            capabilities=[],
            protocols=[],
        )

    def get_device(self, device_id: str) -> ConnectedDevice | None:
        return self._devices.get(device_id)

    def has_device(self, device_id: str) -> bool:
        return device_id in self._devices

    def list_devices(self) -> List[Dict[str, Any]]:
        return [
            self._serialize_device(device) for device in self._devices.values()
        ]

    def count_devices(self) -> int:
        return len(self._devices)

    @staticmethod
    def _serialize_device(device: ConnectedDevice) -> Dict[str, Any]:
        return {
            "id": device.device_id,
            "device_id": device.device_id,
            "device_name": device.device_name,
            "device_type": device.device_type,
            "capabilities": list(device.capabilities),
            "protocols": list(device.protocols),
            "connection_mode": device.connection_mode,
            "connected": device.connected,
            "protocol_endpoints": device.metadata.get(
                "protocol_endpoints", {}
            ),
        }
