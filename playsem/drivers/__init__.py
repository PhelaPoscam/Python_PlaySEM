"""
Device drivers for hardware communication.

Available Drivers:
    - SerialDriver: USB/Serial devices (Arduino, ESP32, etc.)
    - MQTTDriver: MQTT-enabled devices
    - BluetoothDriver: BLE devices
    - MockDriver: Testing/simulation devices
"""

from playsem.drivers.base_driver import BaseDriver
from playsem.drivers.retry_policy import RetryPolicy
from playsem.drivers.rgb_light_driver import RGBLightDriver
from playsem.drivers.mock_driver import (
    MockConnectivityDriver,
    MockLightDevice,
    MockVibrationDevice,
    MockWindDevice,
    MockScentDevice,
)

# Optional drivers (require extra dependencies)
try:
    from playsem.drivers.serial_driver import SerialDriver
except ImportError:
    SerialDriver = None  # type: ignore

try:
    from playsem.drivers.mqtt_driver import MQTTDriver
except ImportError:
    MQTTDriver = None  # type: ignore

try:
    from playsem.drivers.bluetooth_driver import BluetoothDriver
except ImportError:
    BluetoothDriver = None  # type: ignore

__all__ = [
    "BaseDriver",
    "RetryPolicy",
    "RGBLightDriver",
    "MockConnectivityDriver",
    "MockLightDevice",
    "MockVibrationDevice",
    "MockWindDevice",
    "MockScentDevice",
]

if SerialDriver:
    __all__.append("SerialDriver")
if MQTTDriver:
    __all__.append("MQTTDriver")
if BluetoothDriver:
    __all__.append("BluetoothDriver")
