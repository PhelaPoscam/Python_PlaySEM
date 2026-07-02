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
from playsem.drivers.rgb_light_driver import RGBLightDriver  # noqa: F401
from playsem.drivers.upnp_discovery import UPnPDiscovery  # noqa: F401
from playsem.drivers.mock_driver import (  # noqa: F401
    MockConnectivityDriver,
    MockLightDevice,
    MockVibrationDevice,
    MockWindDevice,
    MockScentDevice,
)

SerialDriver = _optional_import(
    "playsem.drivers.serial_driver", "SerialDriver"
)
MQTTDriver = _optional_import("playsem.drivers.mqtt_driver", "MQTTDriver")
BluetoothDriver = _optional_import(
    "playsem.drivers.bluetooth_driver", "BluetoothDriver"
)

__all__ = [
    "BaseDriver",
    "BaseDiscovery",
    "UPnPDiscovery",
    "RetryPolicy",
    "RGBLightDriver",
    "MockConnectivityDriver",
    "MockLightDevice",
    "MockVibrationDevice",
    "MockWindDevice",
    "MockScentDevice",
] + [
    name
    for name in ("SerialDriver", "MQTTDriver", "BluetoothDriver")
    if globals()[name] is not None
]
