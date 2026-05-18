import pytest
import asyncio
from unittest.mock import MagicMock
from playsem.device_manager import DeviceManager
from playsem.effect_dispatcher import EffectDispatcher
from playsem.effect_metadata import EffectMetadata
from playsem.drivers.base_driver import BaseDriver


class DummyAsyncDriver(BaseDriver):
    def __init__(self, interface_name="dummy"):
        self.interface_name = interface_name
        self.connected = True
        self.commands_received = []

    def get_interface_name(self) -> str:
        return self.interface_name

    def connect(self):
        self.connected = True
        return True

    def disconnect(self):
        self.connected = False
        return True

    def is_connected(self) -> bool:
        return self.connected

    async def send_command(self, device_id: str, command: str, params: dict):
        self.commands_received.append((device_id, command, params))
        await asyncio.sleep(0.01)
        return True

    def get_driver_type(self) -> str:
        return "DummyAsync"

    def get_driver_info(self):
        return {"type": "DummyAsync"}


@pytest.mark.asyncio
async def test_device_manager_async_send_command():
    driver = DummyAsyncDriver()
    mock_config = MagicMock()
    mock_config.load_devices_config.return_value = {
        "devices": [{"deviceId": "dev1", "connectivityInterface": "dummy"}]
    }

    manager = DeviceManager(drivers=[driver], config_loader=mock_config)
    success = await manager.async_send_command(
        "dev1", "set_intensity", {"intensity": 100}
    )

    assert success is True
    assert len(driver.commands_received) == 1
    assert driver.commands_received[0] == (
        "dev1",
        "set_intensity",
        {"intensity": 100},
    )


@pytest.mark.asyncio
async def test_effect_dispatcher_async_dispatch():
    driver = DummyAsyncDriver()
    mock_config = MagicMock()
    mock_config.load_devices_config.return_value = {
        "devices": [
            {"deviceId": "light_device", "connectivityInterface": "dummy"}
        ]
    }

    manager = DeviceManager(drivers=[driver], config_loader=mock_config)
    await manager.start_async_workers()

    dispatcher = EffectDispatcher(device_manager=manager, managed_mode=False)

    # default mapping maps 'light' to 'light_device' with command 'set_brightness'
    result = await dispatcher.async_dispatch_effect_result(
        "light", {"value": 50}
    )

    assert result.accepted is True
    assert result.status == "queued"

    # Wait for the worker to process it
    await asyncio.sleep(0.05)

    assert len(driver.commands_received) == 1
    assert driver.commands_received[0] == (
        "light_device",
        "set_brightness",
        {"value": 50},
    )

    await manager.stop_async_workers()


@pytest.mark.asyncio
async def test_effect_dispatcher_async_dispatch_metadata():
    driver = DummyAsyncDriver()
    mock_config = MagicMock()
    mock_config.load_devices_config.return_value = {
        "devices": [
            {"deviceId": "vibration_device", "connectivityInterface": "dummy"}
        ]
    }

    manager = DeviceManager(drivers=[driver], config_loader=mock_config)
    await manager.start_async_workers()

    dispatcher = EffectDispatcher(device_manager=manager, managed_mode=False)

    meta = EffectMetadata(
        effect_type="vibration", intensity=75, location="center"
    )
    success = await dispatcher.async_dispatch_effect_metadata(meta)

    assert success is True

    # Wait for the worker to process it
    await asyncio.sleep(0.05)

    assert len(driver.commands_received) == 1
    assert driver.commands_received[0][0] == "vibration_device"
    assert driver.commands_received[0][1] == "set_intensity"
    assert driver.commands_received[0][2]["intensity"] == 75

    await manager.stop_async_workers()
