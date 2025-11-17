# tests/test_device_manager.py

import pytest
from unittest.mock import MagicMock
from src.device_manager import DeviceManager


@pytest.fixture
def device_manager():
    mock_client = MagicMock()
    # Inject the mock client so DeviceManager does not attempt a real MQTT connect
    return DeviceManager(client=mock_client)


def test_send_command(device_manager):
    device_manager.send_command(
        "test_device",
        "activate",
        {"intensity": "high"},
    )
    expected_payload = str({"command": "activate", "params": {"intensity": "high"}})
    device_manager.client.publish.assert_called_once_with("test_device", expected_payload)
