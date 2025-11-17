# src/device_manager.py

import paho.mqtt.client as mqtt
from typing import Dict, Optional


class DeviceManager:
    def __init__(
        self,
        broker_address: Optional[str] = None,
        client: object = None,
    ):
        """Manage device communication.

        Args:
            broker_address: address of the MQTT broker to connect to. If
                ``client`` is provided this will be ignored (useful for tests).
            client: optional pre-created mqtt client (used for dependency
                injection / testing). If provided, the manager will not call
                ``connect`` on it.
        """
        if client is not None:
            # Use injected client (no network operations in tests)
            self.client = client
        else:
            # Create a real client and connect if a broker address was given
            self.client = mqtt.Client()
            if broker_address is not None:
                self.client.connect(broker_address)

    def send_command(
        self,
        device_id: str,
        command: str,
        params: Dict[str, str],
    ):
        payload = {'command': command, 'params': params}
        self.client.publish(device_id, str(payload))
