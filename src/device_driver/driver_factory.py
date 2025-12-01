# src/device_driver/driver_factory.py
import logging
from typing import Dict, Any, Optional

from .base_driver import BaseDriver
from .mqtt_driver import MQTTDriver
from .serial_driver import SerialDriver
from .bluetooth_driver import BluetoothDriver
from .mock_driver import MockConnectivityDriver

logger = logging.getLogger(__name__)


class DriverFactory:
    """
    Factory class to instantiate connectivity drivers from configuration.
    """

    @classmethod
    def create_driver(
        cls, interface_config: Dict[str, Any]
    ) -> Optional[BaseDriver]:
        """
        Create a driver instance from an interface configuration dictionary.

        Args:
            interface_config: A dictionary representing one entry from the
                              'connectivityInterfaces' list in the config.

        Returns:
            A configured BaseDriver instance, or None if the config is invalid.
        """
        protocol = interface_config.get("protocol", "").lower()
        logger.info(f"Attempting to create driver for protocol: '{protocol}'")

        try:
            if protocol == "serial":
                return cls._create_serial_driver(interface_config)
            elif protocol == "mqtt":
                return cls._create_mqtt_driver(interface_config)
            elif protocol in ["bluetooth", "ble"]:
                return cls._create_bluetooth_driver(interface_config)
            elif protocol == "mock":
                return cls._create_mock_driver(interface_config)
            else:
                logger.error(f"Unknown driver protocol: {protocol}")
                return None
        except (ValueError, KeyError) as e:
            logger.error(
                f"Failed to create '{protocol}' driver due to invalid configuration: {e}"
            )
            return None
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while creating driver '{protocol}': {e}"
            )
            return None

    @staticmethod
    def _create_serial_driver(config: Dict[str, Any]) -> SerialDriver:
        """Create Serial driver from config."""
        if "port" not in config:
            raise ValueError("Serial config must specify a 'port'")
        if "name" not in config:
            raise ValueError(
                "Serial config must specify a 'name' for the interface"
            )

        return SerialDriver(
            interface_name=config["name"],
            port=config["port"],
            baudrate=int(config.get("baudrate", 9600)),
            timeout=float(config.get("timeout", 1.0)),
            data_format=config.get("dataFormat", "json"),
        )

    @staticmethod
    def _create_mqtt_driver(config: Dict[str, Any]) -> MQTTDriver:
        """Create MQTT driver from config."""
        if "broker" not in config:
            raise ValueError("MQTT config must specify a 'broker'")
        if "name" not in config:
            raise ValueError(
                "MQTT config must specify a 'name' for the interface"
            )

        return MQTTDriver(
            interface_name=config["name"],
            broker=config["broker"],
            port=int(config.get("port", 1883)),
            username=config.get("username"),
            password=config.get("password"),
            data_format=config.get("dataFormat", "json"),
        )

    @staticmethod
    def _create_bluetooth_driver(config: Dict[str, Any]) -> BluetoothDriver:
        """Create Bluetooth driver from config."""
        if "name" not in config:
            raise ValueError(
                "Bluetooth config must specify a 'name' for the interface"
            )

        # Address is optional for scanning mode
        return BluetoothDriver(
            interface_name=config["name"],
            address=config.get("address"),
            device_name=config.get("device_name"),
        )

    @staticmethod
    def _create_mock_driver(config: Dict[str, Any]) -> MockConnectivityDriver:
        """Create Mock driver from config."""
        if "name" not in config:
            raise ValueError(
                "Mock config must specify a 'name' for the interface"
            )

        return MockConnectivityDriver(
            interface_name=config["name"],
            data_format=config.get("dataFormat", "json"),
        )
