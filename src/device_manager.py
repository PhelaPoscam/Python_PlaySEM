# src/device_manager.py

import logging
from typing import Dict, Optional, Any
import paho.mqtt.client as mqtt

from .device_driver.base_driver import BaseDriver
from .device_driver.mqtt_driver import MQTTDriver

logger = logging.getLogger(__name__)


class DeviceManager:
    """
    Manage device communication through multiple connectivity drivers.

    Supports MQTT, Serial, Bluetooth, and Mock drivers through a unified
    interface. Can be configured with a specific driver or fall back to
    MQTT for backward compatibility.

    Attributes:
        driver: Connectivity driver instance (BaseDriver)

    Example:
        >>> # Using MQTT driver (default)
        >>> manager = DeviceManager(broker_address="localhost")
        >>> manager.send_command("light_001", "set_intensity", {"value": 255})
        >>>
        >>> # Using Serial driver
        >>> from device_driver.serial_driver import SerialDriver
        >>> serial_driver = SerialDriver(port="COM3", baudrate=9600)
        >>> manager = DeviceManager(connectivity_driver=serial_driver)
        >>> manager.send_command("arduino_001", "turn_on")
    """

    def __init__(
        self,
        connectivity_driver: Optional[BaseDriver] = None,
        broker_address: Optional[str] = None,
        client: Optional[mqtt.Client] = None,
        **mqtt_kwargs,
    ):
        """
        Initialize DeviceManager with a connectivity driver.

        Args:
            connectivity_driver: Driver instance (MQTT, Serial, Bluetooth, Mock)
                If None, falls back to MQTT driver for backward compatibility
            broker_address: MQTT broker address (used if connectivity_driver is None)
            client: Legacy MQTT client (for backward compatibility with tests)
            **mqtt_kwargs: Additional MQTT driver arguments (port, username, etc.)

        Example:
            >>> # New way: explicit driver
            >>> from device_driver.serial_driver import SerialDriver
            >>> driver = SerialDriver(port="COM3")
            >>> manager = DeviceManager(connectivity_driver=driver)
            >>>
            >>> # Old way: MQTT (backward compatible)
            >>> manager = DeviceManager(broker_address="localhost")
        """
        if connectivity_driver is not None:
            # New way: use provided driver
            self.driver = connectivity_driver
            self._auto_connect = True
            logger.info(
                f"DeviceManager initialized with "
                f"{self.driver.get_driver_type()} driver"
            )

        elif client is not None:
            # Legacy: wrap injected MQTT client for testing
            # Create a minimal wrapper that acts like a driver
            self.driver = _LegacyMQTTClientWrapper(client)
            self._auto_connect = False
            logger.info("DeviceManager initialized with legacy MQTT client")

        else:
            # Backward compatibility: create MQTT driver from broker address
            if broker_address is None:
                raise ValueError(
                    "Must provide either connectivity_driver or broker_address"
                )

            self.driver = MQTTDriver(broker=broker_address, **mqtt_kwargs)
            self._auto_connect = True
            logger.info(
                f"DeviceManager initialized with MQTT driver "
                f"(broker: {broker_address})"
            )

        # Auto-connect if needed
        if self._auto_connect:
            self.connect()

    def connect(self) -> bool:
        """
        Connect the driver to its target (broker/device).

        Returns:
            bool: True if connection successful

        Example:
            >>> manager.connect()
            True
        """
        if not self.driver.is_connected():
            return self.driver.connect()
        return True

    def disconnect(self) -> bool:
        """
        Disconnect the driver.

        Returns:
            bool: True if disconnect successful

        Example:
            >>> manager.disconnect()
            True
        """
        return self.driver.disconnect()

    def send_command(
        self,
        device_id: str,
        command: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send command to device through the configured driver.

        Args:
            device_id: Device identifier (topic for MQTT, port for Serial, UUID for BLE)
            command: Command type (e.g., "set_intensity", "turn_on")
            params: Optional command parameters

        Returns:
            bool: True if command sent successfully

        Example:
            >>> manager.send_command(
            ...     "devices/light_001",
            ...     "set_intensity",
            ...     {"intensity": 255, "duration": 1000}
            ... )
            True
        """
        if params is None:
            params = {}

        return self.driver.send_command(device_id, command, params)

    def is_connected(self) -> bool:
        """
        Check if driver is connected.

        Returns:
            bool: True if connected

        Example:
            >>> if manager.is_connected():
            ...     manager.send_command("device_001", "ping")
        """
        return self.driver.is_connected()

    def get_driver_info(self) -> Dict[str, Any]:
        """
        Get information about the configured driver.

        Returns:
            dict: Driver configuration and status

        Example:
            >>> info = manager.get_driver_info()
            >>> print(f"Driver: {info['type']}, Connected: {info['connected']}")
        """
        return self.driver.get_driver_info()

    def reconfigure(self, config_data: Dict[str, Any]) -> bool:
        """
        Reconfigure the DeviceManager's underlying driver.

        Args:
            config_data: Dictionary containing new configuration settings.

        Returns:
            bool: True if reconfiguration was successful, False otherwise.
        """
        logger.info(
            f"Attempting to reconfigure DeviceManager with: {config_data}"
        )

        if isinstance(self.driver, MQTTDriver):
            mqtt_config = config_data.get("mqtt_driver", {})
            new_broker_address = mqtt_config.get("broker")
            new_port = mqtt_config.get("port")

            if new_broker_address or new_port:
                logger.info(
                    f"Reconfiguring MQTTDriver. New broker: {new_broker_address}, new port: {new_port}"
                )

                # Disconnect current driver
                self.disconnect()

                # Create a new MQTTDriver instance with updated settings
                # Preserve existing settings if not provided in config_data
                current_broker = self.driver.broker
                current_port = self.driver.port

                updated_broker = (
                    new_broker_address
                    if new_broker_address is not None
                    else current_broker
                )
                updated_port = (
                    new_port if new_port is not None else current_port
                )

                try:
                    new_driver = MQTTDriver(
                        broker=updated_broker, port=updated_port
                    )
                    self.driver = new_driver
                    self.connect()  # Reconnect with new driver
                    logger.info(
                        f"MQTTDriver reconfigured to {updated_broker}:{updated_port}"
                    )
                    return True
                except Exception as e:
                    logger.error(f"Failed to reconfigure MQTTDriver: {e}")
                    return False
            else:
                logger.warning(
                    "No MQTT driver specific configuration found in reconfigure data."
                )
                return False
        else:
            logger.warning(
                f"Reconfiguration not supported for current driver type: "
                f"{self.driver.get_driver_type()}"
            )
            return False


class _LegacyMQTTClientWrapper(BaseDriver):
    """
    Wrapper for legacy MQTT client to maintain backward compatibility.

    This allows existing tests that inject an MQTT client to continue working
    while using the new driver architecture.
    """

    def __init__(self, client: mqtt.Client):
        """Wrap legacy MQTT client."""
        self.client = client
        self._connected = False

    def connect(self) -> bool:
        """No-op for legacy wrapper (already connected)."""
        self._connected = True
        return True

    def disconnect(self) -> bool:
        """Disconnect MQTT client."""
        try:
            self.client.disconnect()
            self._connected = False
            return True
        except Exception:
            return False

    def send_command(
        self,
        device_id: str,
        command: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send via legacy MQTT client."""
        payload = {"command": command, "params": params or {}}
        self.client.publish(device_id, str(payload))
        return True

    def is_connected(self) -> bool:
        """Check connection status."""
        return self._connected

    def get_driver_type(self) -> str:
        """Get driver type."""
        return "mqtt_legacy"
