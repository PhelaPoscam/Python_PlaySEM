# src/device_driver/__init__.py
"""
Device drivers for PythonPlaySEM.

This package provides connectivity drivers for various sensory effect devices:
- Mock drivers for testing without hardware
- Serial drivers for USB/UART devices
- Bluetooth drivers for wireless devices
"""

from .mock_driver import (
    MockDeviceBase,
    MockLightDevice,
    MockWindDevice,
    MockVibrationDevice,
    MockScentDevice,
)

__all__ = [
    "MockDeviceBase",
    "MockLightDevice",
    "MockWindDevice",
    "MockVibrationDevice",
    "MockScentDevice",
]
