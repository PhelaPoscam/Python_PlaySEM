# src/device_driver/__init__.py
"""
Device drivers for PythonPlaySEM.

This package provides connectivity drivers for various sensory effect devices:
- Base driver interface (BaseDriver, AsyncBaseDriver)
- MQTT driver for network-based communication
- Serial drivers for USB/UART devices
- Bluetooth drivers for wireless BLE devices
- Mock drivers for testing without hardware
"""

from .base_driver import BaseDriver, AsyncBaseDriver
from .mqtt_driver import MQTTDriver
from .serial_driver import SerialDriver
from .bluetooth_driver import BluetoothDriver
from .mock_driver import (
    MockDeviceBase,
    MockLightDevice,
    MockWindDevice,
    MockVibrationDevice,
    MockScentDevice,
)

__all__ = [
    # Driver interfaces
    "BaseDriver",
    "AsyncBaseDriver",
    # Connectivity drivers
    "MQTTDriver",
    "SerialDriver",
    "BluetoothDriver",
    # Mock devices
    "MockDeviceBase",
    "MockLightDevice",
    "MockWindDevice",
    "MockVibrationDevice",
    "MockScentDevice",
]
