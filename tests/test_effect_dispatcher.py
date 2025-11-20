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
    effect_dispatcher.dispatch_effect("light", {"intensity": "high"})
    # Verify that send_command was called at least once
    assert mock_device_manager.send_command.called
    # Check the first call
    call_args = mock_device_manager.send_command.call_args_list[0]
    assert call_args[0][0] == "light_device"  # device_id
    assert call_args[0][1] == "set_brightness"  # command
