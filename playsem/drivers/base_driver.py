#!/usr/bin/env python3
"""
Base Driver Interface for Device Connectivity.

Defines the common asynchronous interface that all connectivity drivers must implement,
enabling DeviceManager to work with MQTT, Serial, Bluetooth, and Mock drivers
through a unified API.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class BaseDiscovery(ABC):
    """
    Abstract base class for device discovery/scanning.

    Any connectivity driver or dedicated scanner module can implement
    this interface to allow runtime device discovery.
    """

    @abstractmethod
    async def discover_devices(self) -> List[Dict[str, Any]]:
        """
        Scan and discover devices on this interface.

        Returns:
            List[Dict[str, Any]]: List of discovered devices, e.g.:
                [{"id": "...", "name": "...", "type": "...", "address": "...", "protocols": ["..."]}]
        """
        pass

    @abstractmethod
    def get_interface_name(self) -> str:
        """
        Get the name of the connectivity interface (e.g. 'serial', 'bluetooth', 'upnp').
        """
        pass


class BaseDriver(ABC):
    """
    Abstract base class for all device connectivity drivers.

    All drivers (MQTT, Serial, Bluetooth, Mock) must implement this
    asynchronous interface to be compatible with DeviceManager.
    """

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the device or broker.

        Returns:
            bool: True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Close connection and cleanup resources.

        Returns:
            bool: True if disconnect successful, False otherwise
        """
        pass

    @abstractmethod
    async def send_command(
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
        """
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """
        Check if driver is currently connected.

        Returns:
            bool: True if connected, False otherwise
        """
        pass

    def get_driver_type(self) -> str:
        """
        Get the type/name of this driver.

        Returns:
            str: Driver type identifier (e.g., "mqtt", "serial", "bluetooth")
        """
        return self.__class__.__name__.lower().replace("driver", "")

    async def get_driver_info(self) -> Dict[str, Any]:
        """
        Get information about the driver configuration.

        Returns:
            dict: Driver configuration and status information
        """
        return {
            "type": self.get_driver_type(),
            "interface_name": self.get_interface_name(),
            "connected": await self.is_connected(),
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
        """
        # Default implementation returns None
        # Subclasses should override to provide actual capabilities
        return None


# Alias for backward compatibility
AsyncBaseDriver = BaseDriver
