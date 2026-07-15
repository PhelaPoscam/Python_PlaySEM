# tests/test_device_manager.py

import asyncio
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


def test_send_command_routing(mock_config_loader, mock_serial_driver, mock_mqtt_driver):
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
    mock_client.publish.assert_called_once_with("test_device", expected_payload)


def test_single_driver_mode():
    """Test the single connectivity driver mode."""
    mock_connectivity_driver = MagicMock(spec=BaseDriver)
    manager = DeviceManager(connectivity_driver=mock_connectivity_driver)

    params = {"power": "on"}
    manager.send_command("any_device", "set_power", params)

    mock_connectivity_driver.send_command.assert_called_once_with(
        "any_device", "set_power", params
    )


class TestAsyncWorkers:
    @pytest.fixture
    def manager_with_driver(self):
        """DeviceManager with a single mock driver, async workers running."""
        driver = MagicMock(spec=BaseDriver)
        driver.get_interface_name.return_value = "mock"
        driver.get_driver_type.return_value = "mock"
        driver.send_command.return_value = True
        driver.is_connected.return_value = True

        loader = MagicMock(spec=ConfigLoader)
        loader.load_devices_config.return_value = {
            "devices": [
                {
                    "deviceId": "dev1",
                    "connectivityInterface": "mock",
                }
            ]
        }

        manager = DeviceManager(drivers=[driver], config_loader=loader)
        return manager, driver

    @pytest.mark.asyncio
    async def test_async_submit_envelope_queues_by_priority(self, manager_with_driver):
        """Envelopes with lower priority numbers are processed first."""
        manager, driver = manager_with_driver
        await manager.start_async_workers()

        from playsem.command_envelope import CommandEnvelope
        from playsem.effect_metadata import EffectMetadata

        env_high = CommandEnvelope(
            effect=EffectMetadata(effect_type="light"),
            device_id="dev1",
            command="on",
            params={},
            priority=5,
        )
        env_low = CommandEnvelope(
            effect=EffectMetadata(effect_type="wind"),
            device_id="dev1",
            command="on",
            params={},
            priority=1,
        )
        env_med = CommandEnvelope(
            effect=EffectMetadata(effect_type="vibration"),
            device_id="dev1",
            command="on",
            params={},
            priority=10,
        )

        await manager.async_submit_envelope(env_high)
        await manager.async_submit_envelope(env_low)
        await manager.async_submit_envelope(env_med)

        # Give workers time to process
        await asyncio.sleep(0.2)
        await manager.stop_async_workers()

        calls = driver.send_command.call_args_list
        # Priority order: 1 (wind), 5 (light), 10 (vibration)
        assert calls[0][0][1] == "on"  # wind
        assert calls[1][0][1] == "on"  # light
        assert calls[2][0][1] == "on"  # vibration

    @pytest.mark.asyncio
    async def test_envelope_best_effort_no_retry(self, manager_with_driver):
        """best_effort delivery mode does not retry on failure."""
        manager, driver = manager_with_driver
        driver.send_command.return_value = False
        await manager.start_async_workers()

        from playsem.command_envelope import CommandEnvelope
        from playsem.effect_metadata import EffectMetadata

        env = CommandEnvelope(
            effect=EffectMetadata(effect_type="light"),
            device_id="dev1",
            command="on",
            params={},
            delivery_mode="best_effort",
        )
        await manager.async_submit_envelope(env)
        await asyncio.sleep(0.2)
        await manager.stop_async_workers()

        driver.send_command.assert_called_once()
        assert len(manager.dead_letter_queue) == 1

    @pytest.mark.asyncio
    async def test_envelope_at_least_once_retries(self, manager_with_driver):
        """at_least_once delivery mode retries up to 3 times."""
        manager, driver = manager_with_driver
        driver.send_command.side_effect = [False, False, True]
        await manager.start_async_workers()

        from playsem.command_envelope import CommandEnvelope
        from playsem.effect_metadata import EffectMetadata

        env = CommandEnvelope(
            effect=EffectMetadata(effect_type="light"),
            device_id="dev1",
            command="on",
            params={},
            delivery_mode="at_least_once",
        )
        await manager.async_submit_envelope(env)
        await asyncio.sleep(0.5)
        await manager.stop_async_workers()

        assert driver.send_command.call_count == 3


class TestCircuitBreaker:
    @pytest.fixture
    def manager_with_cb(self):
        """DeviceManager with circuit breaker enabled."""
        driver = MagicMock(spec=BaseDriver)
        driver.get_interface_name.return_value = "mock"
        driver.get_driver_type.return_value = "mock"
        driver.send_command.return_value = True
        driver.is_connected.return_value = True

        loader = MagicMock(spec=ConfigLoader)
        loader.load_devices_config.return_value = {
            "devices": [{"deviceId": "dev1", "connectivityInterface": "mock"}]
        }

        manager = DeviceManager(
            drivers=[driver],
            config_loader=loader,
            circuit_breaker_failure_threshold=2,
            circuit_breaker_reset_timeout=0.1,
        )
        return manager, driver

    def test_circuit_opens_after_threshold(self, manager_with_cb):
        """After N consecutive failures, circuit opens and blocks commands."""
        manager, driver = manager_with_cb
        driver.send_command.return_value = False

        manager.send_command("dev1", "on")
        manager.send_command("dev1", "on")

        info = manager.get_circuit_info("dev1")
        assert info["state"] == "open"

        # Third command should be blocked
        result = manager.send_command("dev1", "on")
        assert result is False
        # Driver still only called twice (third was blocked)
        assert driver.send_command.call_count == 2

    def test_circuit_half_open_allows_probe(self, manager_with_cb):
        """After reset timeout, a probe request is allowed through."""
        manager, driver = manager_with_cb
        driver.send_command.return_value = False

        manager.send_command("dev1", "on")
        manager.send_command("dev1", "on")

        import time

        time.sleep(0.15)  # Wait past reset_timeout (0.1s)

        # Third request is allowed as a probe (driver called 3 times)
        manager.send_command("dev1", "on")
        assert driver.send_command.call_count == 3

    def test_circuit_closes_on_success(self, manager_with_cb):
        """A successful command in half-open closes the circuit."""
        manager, driver = manager_with_cb
        driver.send_command.return_value = False

        manager.send_command("dev1", "on")
        manager.send_command("dev1", "on")

        import time

        time.sleep(0.15)

        # Success in half-open should close the circuit
        driver.send_command.return_value = True
        manager.send_command("dev1", "on")

        info = manager.get_circuit_info("dev1")
        assert info["state"] == "closed"
        assert info["failures"] == 0
