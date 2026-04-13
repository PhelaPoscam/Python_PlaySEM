from unittest.mock import MagicMock

from playsem.device_manager import DeviceManager
from playsem.drivers.rgb_light_driver import RGBLightDriver
from playsem.effect_dispatcher import EffectDispatcher


def test_abstract_effect_to_reference_rgb_driver_flow():
    """E2E path: abstract light effect -> concrete RGBLightDriver command."""
    config_loader = MagicMock()
    config_loader.load_devices_config.return_value = {
        "devices": [
            {
                "deviceId": "light_device",
                "connectivityInterface": "rgb_light_if",
            }
        ]
    }

    rgb_driver = RGBLightDriver(interface_name="rgb_light_if")
    manager = DeviceManager(drivers=[rgb_driver], config_loader=config_loader)

    dispatcher = EffectDispatcher(
        manager,
        managed_mode=False,
        validate_capabilities=True,
    )

    result = dispatcher.dispatch_effect("light", {"intensity": 80})

    assert result is True
    assert len(rgb_driver.command_log) == 1

    sent = rgb_driver.command_log[0]
    assert sent["device_id"] == "light_device"
    assert sent["command"] == "set_brightness"
    assert sent["params"]["brightness"] == 204
