# tests/test_effect_dispatcher.py

import pytest
from unittest.mock import MagicMock
from src.effect_dispatcher import EffectDispatcher
from src.device_manager import DeviceManager


@pytest.fixture
def mock_device_manager():
    return MagicMock(spec=DeviceManager)


@pytest.fixture
def effect_dispatcher(mock_device_manager):
    return EffectDispatcher(device_manager=mock_device_manager)


def test_dispatch_effect(effect_dispatcher, mock_device_manager):
    effect_dispatcher.dispatch_effect(
        "light",
        {"intensity": "high"}
    )
    mock_device_manager.send_command.assert_called_with(
        "light_device",
        "set_brightness",
        {"intensity": "high"}
    )
    mock_device_manager.send_command.assert_called_with(
        "light_device",
        "set_brightness",
        {"intensity": "low"}
    )
