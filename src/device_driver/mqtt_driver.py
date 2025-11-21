#!/usr/bin/env python3
"""
MQTT Connectivity Driver.

Implements BaseDriver interface for MQTT-based device communication.
Wraps paho-mqtt client for integration with DeviceManager.
"""

import logging
import json
from typing import Dict, Any, Optional
import paho.mqtt.client as mqtt

from .base_driver import BaseDriver

logger = logging.getLogger(__name__)


class MQTTDriver(BaseDriver):
    """
    MQTT connectivity driver for network-based devices.

    Uses paho-mqtt client to communicate with devices via MQTT broker.
    Supports pub/sub messaging with QoS and retain options.

    Attributes:
        broker: MQTT broker address
        port: MQTT broker port
        is_connected: Connection status

    Example:
        >>> driver = MQTTDriver(broker="localhost", port=1883)
        >>> driver.connect()
        >>> driver.send_command(
        ...     device_id="devices/light_001",
        ...     command="set_intensity",
        ...     params={"intensity": 255}
        ... )
        >>> driver.disconnect()
    """

    def __init__(
        self,
        broker: str,
        port: int = 1883,
        client_id: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = False,
        qos: int = 1,
        retain: bool = False,
    ):
        """
        Initialize MQTT driver.

        Args:
            broker: MQTT broker hostname or IP
            port: MQTT broker port (default: 1883)
            client_id: Optional MQTT client ID
            username: Optional MQTT username
            password: Optional MQTT password
            use_tls: Enable TLS/SSL encryption
            qos: Quality of Service level (0, 1, or 2)
            retain: Retain messages on broker
        """
        self.broker = broker
        self.port = port
        self.qos = qos
        self.retain = retain
        self._is_connected = False

        # Create MQTT client
        self.client = mqtt.Client(client_id=client_id)

        # Set authentication if provided
        if username and password:
            self.client.username_pw_set(username, password)

        # Enable TLS if requested
        if use_tls:
            self.client.tls_set()

        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

        logger.info(
            f"MQTTDriver initialized - broker: {broker}:{port}, "
            f"tls: {use_tls}, qos: {qos}"
        )

    def connect(self) -> bool:
        """
        Connect to MQTT broker.

        Returns:
            bool: True if connection successful

        Example:
            >>> driver = MQTTDriver(broker="localhost")
            >>> driver.connect()
            True
        """
        try:
            logger.info(f"Connecting to MQTT broker {self.broker}:{self.port}")
            self.client.connect(self.broker, self.port)
            self.client.loop_start()  # Start background thread
            return True
        except Exception as e:
            logger.error(f"MQTT connection failed: {e}")
            return False

    def disconnect(self) -> bool:
        """
        Disconnect from MQTT broker.

        Returns:
            bool: True if disconnect successful

        Example:
            >>> driver.disconnect()
            True
        """
        try:
            logger.info("Disconnecting from MQTT broker")
            self.client.loop_stop()  # Stop background thread
            self.client.disconnect()
            self._is_connected = False
            return True
        except Exception as e:
            logger.error(f"MQTT disconnect failed: {e}")
            return False

    def send_command(
        self,
        device_id: str,
        command: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send command to device via MQTT topic.

        Args:
            device_id: MQTT topic for the device
            command: Command type
            params: Command parameters

        Returns:
            bool: True if message published successfully

        Example:
            >>> driver.send_command(
            ...     "devices/light_001",
            ...     "set_intensity",
            ...     {"intensity": 255, "duration": 1000}
            ... )
            True
        """
        if not self._is_connected:
            logger.warning("Cannot send command: not connected to broker")
            return False

        try:
            # Build payload
            payload = {"command": command}
            if params:
                payload["params"] = params

            # Convert to JSON
            message = json.dumps(payload)

            # Publish to topic
            result = self.client.publish(
                topic=device_id,
                payload=message,
                qos=self.qos,
                retain=self.retain,
            )

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(
                    f"Published to {device_id}: {command} "
                    f"(params: {params})"
                )
                return True
            else:
                logger.error(f"Publish failed: {mqtt.error_string(result.rc)}")
                return False

        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return False

    def is_connected(self) -> bool:
        """
        Check if connected to MQTT broker.

        Returns:
            bool: True if connected

        Example:
            >>> driver.is_connected()
            True
        """
        return self._is_connected

    def get_driver_info(self) -> Dict[str, Any]:
        """
        Get MQTT driver configuration.

        Returns:
            dict: Driver information

        Example:
            >>> driver.get_driver_info()
            {'type': 'mqtt', 'broker': 'localhost', 'port': 1883, ...}
        """
        return {
            "type": "mqtt",
            "broker": self.broker,
            "port": self.port,
            "qos": self.qos,
            "retain": self.retain,
            "connected": self._is_connected,
        }

    def get_capabilities(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Get device capabilities for MQTT-connected devices.

        Returns generic capabilities. MQTT devices should publish their
        capabilities to a specific topic for accurate information.
        """
        from ..device_capabilities import (
            DeviceCapabilities,
            EffectCapability,
            EffectType,
            create_standard_intensity_param,
            create_standard_duration_param,
        )

        # Create capabilities for MQTT devices
        caps = DeviceCapabilities(
            device_id=device_id,
            device_type="MQTTDevice",
            manufacturer="Unknown",
            model=f"MQTT@{self.broker}:{self.port}",
            driver_type="mqtt",
            metadata={
                "broker": self.broker,
                "port": self.port,
            },
        )

        # MQTT devices typically support multiple effect types
        for effect_type in [
            EffectType.LIGHT,
            EffectType.WIND,
            EffectType.VIBRATION,
            EffectType.SCENT,
        ]:
            effect = EffectCapability(
                effect_type=effect_type,
                description=f"MQTT-controlled {effect_type.value} device",
                parameters=[
                    create_standard_intensity_param(),
                    create_standard_duration_param(),
                ],
            )
            caps.effects.append(effect)

        return caps.to_dict()

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to broker."""
        if rc == 0:
            self._is_connected = True
            logger.info("Connected to MQTT broker")
        else:
            logger.error(
                f"MQTT connection failed with code {rc}: "
                f"{mqtt.connack_string(rc)}"
            )

    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from broker."""
        self._is_connected = False
        if rc == 0:
            logger.info("Disconnected from MQTT broker")
        else:
            logger.warning(
                f"Unexpected disconnect (code {rc}): "
                f"{mqtt.error_string(rc)}"
            )

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
