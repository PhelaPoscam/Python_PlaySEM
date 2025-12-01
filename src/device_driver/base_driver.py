#!/usr/bin/env python3
"""
Base Driver Interface for Device Connectivity.

Defines the common interface that all connectivity drivers must implement,
enabling DeviceManager to work with MQTT, Serial, Bluetooth, and Mock drivers
through a unified API.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseDriver(ABC):
    """
    Abstract base class for all device connectivity drivers.

    All drivers (MQTT, Serial, Bluetooth, Mock) must implement this
    interface to be compatible with DeviceManager.

    Example:
        >>> class MyDriver(BaseDriver):
        ...     def connect(self):
        ...         # Implementation
        ...         pass
        ...
        ...     def send_command(self, device_id, command, params):
        ...         # Implementation
        ...         pass
    """

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the device or broker.

        Returns:
            bool: True if connection successful, False otherwise

        Example:
            >>> driver = MQTTDriver(broker="localhost")
            >>> if driver.connect():
            ...     print("Connected!")
        """
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """
        Close connection and cleanup resources.

        Returns:
            bool: True if disconnect successful, False otherwise

        Example:
            >>> driver.disconnect()
            True
        """
        pass

    @abstractmethod
    def send_command(
        self,
        device_id: str,
        command: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send a command to a specific device.

        Args:
            device_id: Unique identifier of the target device
            command: Command type (e.g., "set_intensity", "turn_on")
            params: Optional dictionary of command parameters

        Returns:
            bool: True if command sent successfully, False otherwise

        Example:
            >>> driver.send_command(
            ...     device_id="light_001",
            ...     command="set_intensity",
            ...     params={"intensity": 255, "duration": 1000}
            ... )
            True
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if driver is currently connected.

        Returns:
            bool: True if connected, False otherwise

        Example:
            >>> if driver.is_connected():
            ...     driver.send_command("light_001", "turn_on")
        """
        pass

    def get_driver_type(self) -> str:
        """
        Get the type/name of this driver.

        Returns:
            str: Driver type identifier (e.g., "mqtt", "serial", "bluetooth")

        Example:
            >>> driver.get_driver_type()
            'mqtt'
        """
        return self.__class__.__name__.lower().replace("driver", "")

    def get_driver_info(self) -> Dict[str, Any]:
        """
        Get information about the driver configuration.

        Returns:
            dict: Driver configuration and status information

        Example:
            >>> driver.get_driver_info()
            {'type': 'mqtt', 'interface_name': 'mqtt_interface_0', 'connected': True}
        """
        return {
            "type": self.get_driver_type(),
            "interface_name": self.get_interface_name(),
            "connected": self.is_connected(),
        }

    @abstractmethod
    def get_interface_name(self) -> str:
        """
        Get the unique name of the connectivity interface this driver handles.

        This name corresponds to the 'name' field in the 'connectivityInterfaces'
        section of the configuration.

        Returns:
            str: The unique interface name.
        """
        pass

    def get_capabilities(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Get device capabilities description.

        Returns a dictionary describing what effects and parameters
        the device supports. This enables clients to discover device
        features and validate commands before sending.

        Args:
            device_id: Unique identifier of the device

        Returns:
            dict: Device capabilities in JSON-serializable format,
                  or None if capabilities are not available

        Example:
            >>> caps = driver.get_capabilities("light_001")
            >>> print(caps["effects"])
            [{'effect_type': 'light', 'parameters': [...]}]
        """
        # Default implementation returns None
        # Subclasses should override to provide actual capabilities
        return None


class AsyncBaseDriver(ABC):
    """
    Abstract base class for async connectivity drivers.

    For drivers that require async/await patterns (e.g., Bluetooth BLE).

    Example:
        >>> class MyAsyncDriver(AsyncBaseDriver):
        ...     async def connect(self):
        ...         # Async implementation
        ...         pass
    """

    @abstractmethod
    async def connect(self) -> bool:
        """Async connect to device or broker."""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Async disconnect and cleanup."""
        pass

    @abstractmethod
    async def send_command(
        self,
        device_id: str,
        command: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Async send command to device."""
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """Async check connection status."""
        pass

    def get_driver_type(self) -> str:
        """Get driver type identifier."""
        return self.__class__.__name__.lower().replace("driver", "")

    def get_driver_info(self) -> Dict[str, Any]:
        """Get driver configuration info (synchronous)."""
        return {
            "type": self.get_driver_type(),
            "async": True,
        }

    def get_capabilities(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Get device capabilities description (synchronous).

        Args:
            device_id: Unique identifier of the device

        Returns:
            dict: Device capabilities or None if not available
        """
        return None
