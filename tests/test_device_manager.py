# tests/test_device_manager.py

import pytest
from unittest.mock import MagicMock, patch

from playsem.device_manager import DeviceManager
from playsem.drivers.base_driver import BaseDriver
from playsem.config.loader import ConfigLoader


@pytest.fixture
def mock_config_loader():
    """Fixture for a mocked ConfigLoader."""
    loader = MagicMock(spec=ConfigLoader)
    mock_devices_config = {
        "devices": [
            {
                "deviceId": "serial_device_1",
                "name": "Serial Device",
                "connectivityInterface": "serial",
            },
            {
                "deviceId": "mqtt_device_1",
                "name": "MQTT Device",
                "connectivityInterface": "mqtt",
            },
            {
                "deviceId": "no_driver_device",
                "name": "Device with no driver",
                "connectivityInterface": "unknown",
            },
        ]
    }
    loader.load_devices_config.return_value = mock_devices_config
    return loader


@pytest.fixture
def mock_serial_driver():
    """Fixture for a mocked SerialDriver."""
    driver = MagicMock(spec=BaseDriver)
    driver.get_interface_name.return_value = "serial"
    driver.get_driver_type.return_value = "Serial"
    driver.send_command.return_value = True
    driver.is_connected.return_value = False
    return driver


@pytest.fixture
def mock_mqtt_driver():
    """Fixture for a mocked MQTTDriver."""
    driver = MagicMock(spec=BaseDriver)
    driver.get_interface_name.return_value = "mqtt"
    driver.get_driver_type.return_value = "MQTT"
    driver.send_command.return_value = True
    driver.is_connected.return_value = False
    return driver


def test_initialization_and_mapping(
    mock_config_loader, mock_serial_driver, mock_mqtt_driver
):
    """Test that DeviceManager initializes and maps devices to drivers correctly."""
    drivers = [mock_serial_driver, mock_mqtt_driver]
    manager = DeviceManager(drivers=drivers, config_loader=mock_config_loader)

    # Check that drivers are mapped by interface
    assert manager.drivers_by_interface["serial"] == mock_serial_driver
    assert manager.drivers_by_interface["mqtt"] == mock_mqtt_driver

    # Check that devices are mapped to the correct driver
    assert manager.device_to_driver["serial_device_1"] == mock_serial_driver
    assert manager.device_to_driver["mqtt_device_1"] == mock_mqtt_driver

    # Check that device with no driver is not in the map
    assert "no_driver_device" not in manager.device_to_driver

    # Check that drivers were connected
    mock_serial_driver.connect.assert_called_once()
    mock_mqtt_driver.connect.assert_called_once()


def test_send_command_routing(
    mock_config_loader, mock_serial_driver, mock_mqtt_driver
):
    """Test that send_command routes to the correct driver."""
    drivers = [mock_serial_driver, mock_mqtt_driver]
    manager = DeviceManager(drivers=drivers, config_loader=mock_config_loader)

    # Send command to serial device
    params = {"speed": 100}
    result = manager.send_command("serial_device_1", "set_speed", params)
    assert result is True
    mock_serial_driver.send_command.assert_called_once_with(
        "serial_device_1", "set_speed", params
    )
    mock_mqtt_driver.send_command.assert_not_called()

    # Reset mocks and send command to MQTT device
    mock_serial_driver.reset_mock()
    mock_mqtt_driver.reset_mock()

    params = {"topic": "test", "payload": "hello"}
    result = manager.send_command("mqtt_device_1", "publish", params)
    assert result is True
    mock_mqtt_driver.send_command.assert_called_once_with(
        "mqtt_device_1", "publish", params
    )
    mock_serial_driver.send_command.assert_not_called()


def test_send_command_to_unknown_device(
    mock_config_loader, mock_serial_driver, mock_mqtt_driver
):
    """Test sending a command to a deviceId that has no driver."""
    drivers = [mock_serial_driver, mock_mqtt_driver]
    manager = DeviceManager(drivers=drivers, config_loader=mock_config_loader)

    result = manager.send_command("unknown_device", "some_command")

    assert result is False
    mock_serial_driver.send_command.assert_not_called()
    mock_mqtt_driver.send_command.assert_not_called()


def test_connect_and_disconnect_all(
    mock_config_loader, mock_serial_driver, mock_mqtt_driver
):
    """Test that connect_all and disconnect_all call all drivers."""
    drivers = [mock_serial_driver, mock_mqtt_driver]
    # Reset connect mock since it's called in __init__
    mock_serial_driver.reset_mock()
    mock_mqtt_driver.reset_mock()
    # After init, drivers are connected, so is_connected returns True
    mock_serial_driver.is_connected.return_value = True
    mock_mqtt_driver.is_connected.return_value = True

    manager = DeviceManager(drivers=drivers, config_loader=mock_config_loader)

    # Test disconnection
    manager.disconnect_all()
    mock_serial_driver.disconnect.assert_called_once()
    mock_mqtt_driver.disconnect.assert_called_once()

    # Now they should report as disconnected
    mock_serial_driver.is_connected.return_value = False
    mock_mqtt_driver.is_connected.return_value = False

    # Test connection again
    mock_serial_driver.reset_mock()
    mock_mqtt_driver.reset_mock()
    manager.connect_all()
    mock_serial_driver.connect.assert_called_once()
    mock_mqtt_driver.connect.assert_called_once()


def test_legacy_mode():
    """Test the legacy client mode for backward compatibility."""
    mock_client = MagicMock()
    manager = DeviceManager(client=mock_client)

    params = {"intensity": "high"}
    manager.send_command("test_device", "activate", params)

    expected_payload = str({"command": "activate", "params": params})
    mock_client.publish.assert_called_once_with(
        "test_device", expected_payload
    )


def test_single_driver_mode():
    """Test the single connectivity driver mode."""
    mock_connectivity_driver = MagicMock(spec=BaseDriver)
    manager = DeviceManager(connectivity_driver=mock_connectivity_driver)

    params = {"power": "on"}
    manager.send_command("any_device", "set_power", params)

    mock_connectivity_driver.send_command.assert_called_once_with(
        "any_device", "set_power", params
    )
