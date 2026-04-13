# tests/test_device_manager.py

import asyncio
import pytest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

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
    """Test DeviceManager initialization and driver/device mapping."""
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


@pytest.mark.asyncio
async def test_single_driver_mode_async_send_command_bridge():
    """Single-driver mode should execute async send_command safely."""

    class AsyncConnectivityDriver:
        async def send_command(self, device_id, command, params):
            return True

    manager = DeviceManager(connectivity_driver=AsyncConnectivityDriver())
    assert manager.send_command("device_async", "pulse", {"a": 1}) is True


@pytest.mark.asyncio
async def test_single_driver_mode_async_connect_disconnect_bridge():
    """Single-driver mode should execute async connect/disconnect."""

    state = {"connected": False}

    class AsyncConnectivityDriver:
        async def connect(self):
            state["connected"] = True
            return True

        async def disconnect(self):
            state["connected"] = False
            return True

        async def send_command(self, device_id, command, params):
            return state["connected"]

    manager = DeviceManager(connectivity_driver=AsyncConnectivityDriver())
    manager.connect()
    assert state["connected"] is True

    manager.disconnect()
    assert state["connected"] is False


@pytest.mark.asyncio
async def test_mapped_mode_async_driver_connect_and_send_bridge():
    """Mapped mode resolves async driver connect/is_connected/send paths."""

    class AsyncMappedDriver:
        def __init__(self):
            self.connected = False
            self.send_calls = 0

        def get_interface_name(self):
            return "async_if"

        def get_driver_type(self):
            return "asyncmapped"

        async def connect(self):
            self.connected = True
            return True

        async def disconnect(self):
            self.connected = False
            return True

        async def is_connected(self):
            return self.connected

        async def send_command(self, device_id, command, params):
            self.send_calls += 1
            return self.connected

    loader = MagicMock(spec=ConfigLoader)
    loader.load_devices_config.return_value = {
        "devices": [
            {
                "deviceId": "async_device_1",
                "connectivityInterface": "async_if",
            }
        ]
    }

    driver = AsyncMappedDriver()
    manager = DeviceManager(drivers=[driver], config_loader=loader)

    assert driver.connected is True
    assert manager.send_command("async_device_1", "pulse", {"x": 1}) is True
    assert driver.send_calls == 1


@pytest.mark.asyncio
async def test_mapped_mode_async_driver_disconnect_all_bridge():
    """Mapped mode resolves async disconnect and updates connection state."""

    class AsyncMappedDriver:
        def __init__(self):
            self.connected = False

        def get_interface_name(self):
            return "async_if"

        def get_driver_type(self):
            return "asyncmapped"

        async def connect(self):
            self.connected = True
            return True

        async def disconnect(self):
            self.connected = False
            return True

        async def is_connected(self):
            return self.connected

        async def send_command(self, device_id, command, params):
            return self.connected

    loader = MagicMock(spec=ConfigLoader)
    loader.load_devices_config.return_value = {
        "devices": [
            {
                "deviceId": "async_device_1",
                "connectivityInterface": "async_if",
            }
        ]
    }

    driver = AsyncMappedDriver()
    manager = DeviceManager(drivers=[driver], config_loader=loader)
    assert driver.connected is True

    manager.disconnect_all()
    assert driver.connected is False


@pytest.mark.asyncio
async def test_single_driver_async_bridge_timeout_returns_false():
    """Timeout guard should fail fast for hanging async driver sends."""

    class SlowAsyncDriver:
        async def send_command(self, device_id, command, params):
            await asyncio.sleep(0.2)
            return True

    manager = DeviceManager(
        connectivity_driver=SlowAsyncDriver(),
        async_bridge_timeout=0.05,
    )

    assert manager.send_command("slow", "pulse", {}) is False


@pytest.mark.asyncio
async def test_mapped_mode_mixed_sync_async_burst_dispatch():
    """Mixed sync/async mapped drivers should handle burst dispatch."""

    class SyncDriver:
        def __init__(self):
            self.count = 0
            self.connected = False

        def get_interface_name(self):
            return "sync_if"

        def get_driver_type(self):
            return "sync"

        def connect(self):
            self.connected = True
            return True

        def disconnect(self):
            self.connected = False
            return True

        def is_connected(self):
            return self.connected

        def send_command(self, device_id, command, params):
            self.count += 1
            return self.connected

    class AsyncDriver:
        def __init__(self):
            self.count = 0
            self.connected = False

        def get_interface_name(self):
            return "async_if"

        def get_driver_type(self):
            return "async"

        async def connect(self):
            self.connected = True
            return True

        async def disconnect(self):
            self.connected = False
            return True

        async def is_connected(self):
            return self.connected

        async def send_command(self, device_id, command, params):
            self.count += 1
            return self.connected

    loader = MagicMock(spec=ConfigLoader)
    loader.load_devices_config.return_value = {
        "devices": [
            {
                "deviceId": "sync_device",
                "connectivityInterface": "sync_if",
            },
            {
                "deviceId": "async_device",
                "connectivityInterface": "async_if",
            },
        ]
    }

    sync_driver = SyncDriver()
    async_driver = AsyncDriver()
    manager = DeviceManager(
        drivers=[sync_driver, async_driver],
        config_loader=loader,
        async_bridge_timeout=1.0,
    )

    def _send_sync(i: int) -> bool:
        return bool(manager.send_command("sync_device", "set", {"i": i}))

    def _send_async(i: int) -> bool:
        return bool(manager.send_command("async_device", "set", {"i": i}))

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for i in range(40):
            futures.append(executor.submit(_send_sync, i))
            futures.append(executor.submit(_send_async, i))

        results = [f.result(timeout=2.0) for f in futures]

    assert all(results)
    assert sync_driver.count == 40
    assert async_driver.count == 40
