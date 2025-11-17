#!/usr/bin/env python3
"""
Driver Factory for automatic driver creation from configuration.

Provides factory functions to instantiate the appropriate connectivity
driver based on configuration files or connection parameters.
"""

import logging
from typing import Dict, Any, Optional

from .base_driver import BaseDriver
from .mqtt_driver import MQTTDriver
from .serial_driver import SerialDriver
from .bluetooth_driver import BluetoothDriver

logger = logging.getLogger(__name__)


def create_driver_from_config(config: Dict[str, Any]) -> Optional[BaseDriver]:
    """
    Create driver instance from configuration dictionary.

    Args:
        config: Configuration dictionary with driver parameters
            Required keys:
            - type: "mqtt", "serial", "bluetooth", or "mock"
            Additional keys depend on driver type

    Returns:
        BaseDriver: Configured driver instance
        None: If configuration is invalid

    Example:
        >>> config = {
        ...     "type": "mqtt",
        ...     "broker": "localhost",
        ...     "port": 1883
        ... }
        >>> driver = create_driver_from_config(config)
        >>> driver.connect()

        >>> config = {
        ...     "type": "serial",
        ...     "port": "COM3",
        ...     "baudrate": 9600
        ... }
        >>> driver = create_driver_from_config(config)
    """
    driver_type = config.get("type", "").lower()

    try:
        if driver_type == "mqtt":
            return _create_mqtt_driver(config)
        elif driver_type == "serial":
            return _create_serial_driver(config)
        elif driver_type == "bluetooth" or driver_type == "ble":
            return _create_bluetooth_driver(config)
        else:
            logger.error(f"Unknown driver type: {driver_type}")
            return None

    except Exception as e:
        logger.error(f"Failed to create {driver_type} driver: {e}")
        return None


def _create_mqtt_driver(config: Dict[str, Any]) -> MQTTDriver:
    """Create MQTT driver from config."""
    broker = config.get("broker")
    if not broker:
        raise ValueError("MQTT config must specify 'broker'")

    return MQTTDriver(
        broker=broker,
        port=config.get("port", 1883),
        client_id=config.get("client_id"),
        username=config.get("username"),
        password=config.get("password"),
        use_tls=config.get("use_tls", False),
        qos=config.get("qos", 1),
        retain=config.get("retain", False),
    )


def _create_serial_driver(config: Dict[str, Any]) -> SerialDriver:
    """Create Serial driver from config."""
    port = config.get("port")
    if not port:
        raise ValueError("Serial config must specify 'port'")

    return SerialDriver(
        port=port,
        baudrate=config.get("baudrate", 9600),
        timeout=config.get("timeout", 1.0),
        bytesize=config.get("bytesize", 8),
        parity=config.get("parity", "N"),
        stopbits=config.get("stopbits", 1),
    )


def _create_bluetooth_driver(config: Dict[str, Any]) -> BluetoothDriver:
    """Create Bluetooth driver from config."""
    address = config.get("address")
    # Address is optional for scanning mode
    return BluetoothDriver(
        address=address,
        device_name=config.get("device_name"),
    )


def auto_detect_driver(
    mqtt_broker: Optional[str] = None,
    serial_port: Optional[str] = None,
    bluetooth_address: Optional[str] = None,
) -> Optional[BaseDriver]:
    """
    Auto-detect and create driver based on available parameters.

    Priority order: MQTT > Serial > Bluetooth

    Args:
        mqtt_broker: MQTT broker address
        serial_port: Serial port name
        bluetooth_address: Bluetooth device address

    Returns:
        BaseDriver: First available driver, or None if none specified

    Example:
        >>> # Will create Serial driver
        >>> driver = auto_detect_driver(serial_port="COM3")
        >>>
        >>> # Will create MQTT driver (priority over serial)
        >>> driver = auto_detect_driver(
        ...     mqtt_broker="localhost",
        ...     serial_port="COM3"
        ... )
    """
    if mqtt_broker:
        logger.info(f"Auto-detected MQTT driver (broker: {mqtt_broker})")
        return MQTTDriver(broker=mqtt_broker)

    if serial_port:
        logger.info(f"Auto-detected Serial driver (port: {serial_port})")
        return SerialDriver(port=serial_port)

    if bluetooth_address:
        logger.info(
            f"Auto-detected Bluetooth driver (address: {bluetooth_address})"
        )
        return BluetoothDriver(address=bluetooth_address)

    logger.warning("No driver parameters provided for auto-detection")
    return None


def create_driver(driver_type: str, **kwargs) -> Optional[BaseDriver]:
    """
    Create driver by type with keyword arguments.

    Args:
        driver_type: "mqtt", "serial", or "bluetooth"
        **kwargs: Driver-specific parameters

    Returns:
        BaseDriver: Configured driver instance

    Example:
        >>> driver = create_driver("mqtt", broker="localhost", port=1883)
        >>> driver = create_driver("serial", port="COM3", baudrate=9600)
        >>> driver = create_driver("bluetooth", address="AA:BB:CC:DD:EE:FF")
    """
    config = {"type": driver_type, **kwargs}
    return create_driver_from_config(config)
