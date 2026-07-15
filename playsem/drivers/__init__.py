"""
Device drivers for hardware communication.

Available Drivers:
    - SerialDriver: USB/Serial devices (Arduino, ESP32, etc.)
    - MQTTDriver: MQTT-enabled devices
    - BluetoothDriver: BLE devices
    - MockDriver: Testing/simulation devices
"""

from playsem.utils import _optional_import
from playsem.drivers.base_driver import BaseDriver, BaseDiscovery  # noqa: F401
from playsem.drivers.retry_policy import RetryPolicy  # noqa: F401
from playsem.drivers.upnp_discovery import UPnPDiscovery  # noqa: F401
from playsem.drivers.mock_driver import (  # noqa: F401
    MockConnectivityDriver,
    MockLightDevice,
    MockVibrationDevice,
    MockWindDevice,
    MockScentDevice,
)

# Optional drivers — silently None if the dependency isn't installed
for _mod, _cls in [
    ("serial_driver", "SerialDriver"),
    ("mqtt_driver", "MQTTDriver"),
    ("bluetooth_driver", "BluetoothDriver"),
]:
    globals()[_cls] = _optional_import(f"playsem.drivers.{_mod}", _cls)

__all__ = [
    "BaseDriver",
    "BaseDiscovery",
    "UPnPDiscovery",
    "RetryPolicy",
    "MockConnectivityDriver",
    "MockLightDevice",
    "MockVibrationDevice",
    "MockWindDevice",
    "MockScentDevice",
] + [
    name
    for name in ("SerialDriver", "MQTTDriver", "BluetoothDriver")
    if globals().get(name) is not None
]
