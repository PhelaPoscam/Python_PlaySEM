# tests/test_effect_dispatcher.py

import pytest
from unittest.mock import MagicMock, patch

from playsem.effect_dispatcher import EffectDispatcher
from playsem.device_manager import DeviceManager
from playsem.effect_metadata import EffectMetadata


@pytest.fixture
def mock_device_manager():
    """Fixture for a mocked DeviceManager."""
    manager = MagicMock(spec=DeviceManager)
    # Add a reconfigure method to the mock spec
    manager.reconfigure = MagicMock(return_value=True)
    return manager


@pytest.fixture
def sample_effects_config():
    """Fixture for a sample effects configuration dictionary."""
    return {
        "effects": {
            "light_on": {
                "device": "light_1",
                "command": "set_brightness",
                "parameters": [
                    {
                        "name": "intensity",
                        "mapping": {"low": 64, "medium": 128, "high": 255},
                        "default": 255,
                    }
                ],
            },
            "fan_on": {"device": "fan_1", "command": "set_speed"},
            "incomplete_effect": {"device": "some_device"},
        }
    }


@pytest.fixture
def dispatcher(mock_device_manager, sample_effects_config):
    """Fixture for an EffectDispatcher initialized with mock config."""
    # Patch load_effects_yaml to avoid file system access
    with patch("playsem.effect_dispatcher.load_effects_yaml") as mock_load:
        mock_load.return_value = sample_effects_config
        # Initialize with a dummy path to trigger loading
        dispatcher = EffectDispatcher(mock_device_manager, "dummy/path.yaml")
        return dispatcher


def test_dispatch_effect_simple(dispatcher, mock_device_manager):
    """Test dispatching a simple effect with no parameter mapping."""
    dispatcher.dispatch_effect("fan_on", {"speed": 100})

    mock_device_manager.send_command.assert_called_once_with(
        "fan_1", "set_speed", {"speed": 100}
    )


def test_dispatch_effect_with_parameter_mapping(
    dispatcher, mock_device_manager
):
    """Test dispatching an effect with a mapped 'intensity' parameter."""
    dispatcher.dispatch_effect("light_on", {"intensity": "high"})

    # 'high' should be mapped to 255
    mock_device_manager.send_command.assert_called_once_with(
        "light_1", "set_brightness", {"intensity": 255}
    )


def test_dispatch_effect_with_default_parameter(
    dispatcher, mock_device_manager
):
    """Test that a default parameter is used when none is provided."""
    # Dispatch 'light_on' without providing 'intensity'
    dispatcher.dispatch_effect("light_on", {})

    # The default value of 255 should be used
    mock_device_manager.send_command.assert_called_once_with(
        "light_1", "set_brightness", {"intensity": 255}
    )


def test_dispatch_unknown_effect(dispatcher):
    """Test that dispatching an unknown effect raises a ValueError."""
    with pytest.raises(ValueError, match="Unknown effect: unknown_effect"):
        dispatcher.dispatch_effect("unknown_effect", {})


def test_dispatch_incomplete_effect_config(dispatcher):
    """Test that an effect with missing 'command' raises a ValueError."""
    with pytest.raises(
        ValueError,
        match="Effect 'incomplete_effect' missing device or command",
    ):
        dispatcher.dispatch_effect("incomplete_effect", {})


def test_dispatch_effect_metadata(dispatcher, mock_device_manager):
    """Test dispatching via an EffectMetadata object."""
    effect = EffectMetadata(
        effect_type="light_on", intensity=100, duration=1000
    )
    dispatcher.dispatch_effect_metadata(effect)

    # The dispatcher should merge the intensity into the parameters
    mock_device_manager.send_command.assert_called_once_with(
        "light_1", "set_brightness", {"intensity": 100}
    )


def test_dispatch_effect_metadata_with_location(
    dispatcher, mock_device_manager
):
    """Test that location from EffectMetadata is passed as a parameter."""
    effect = EffectMetadata(
        effect_type="fan_on",
        parameters={"speed": 50},
        location="zone_A",
    )
    dispatcher.dispatch_effect_metadata(effect)

    mock_device_manager.send_command.assert_called_once_with(
        "fan_1", "set_speed", {"speed": 50, "location": "zone_A"}
    )


def test_dispatch_reconfigure_command(dispatcher, mock_device_manager):
    """Test the special 'reconfigure' effect type."""
    reconfig_data = {"device_manager": {"some_setting": "some_value"}}
    effect = EffectMetadata(
        effect_type="reconfigure", parameters=reconfig_data
    )

    dispatcher.dispatch_effect_metadata(effect)

    # Verify that the device manager's reconfigure method was called
    mock_device_manager.reconfigure.assert_called_once_with(
        reconfig_data["device_manager"]
    )
    # Verify that send_command was NOT called for a reconfigure effect
    mock_device_manager.send_command.assert_not_called()


def test_get_supported_effects(dispatcher, sample_effects_config):
    """Test that get_supported_effects returns the correct list of names."""
    supported_effects = dispatcher.get_supported_effects()
    expected_effects = list(sample_effects_config["effects"].keys())

    assert sorted(supported_effects) == sorted(expected_effects)


def test_fallback_to_default_mappings(mock_device_manager):
    """Test that the dispatcher uses default mappings if config fails to load."""
    # Patch load_effects_yaml to simulate it failing
    with patch("playsem.effect_dispatcher.load_effects_yaml") as mock_load:
        mock_load.side_effect = FileNotFoundError
        dispatcher = EffectDispatcher(mock_device_manager, "bad/path.yaml")

    # Check that a default effect can be dispatched
    dispatcher.dispatch_effect("light", {"intensity": 123})
    mock_device_manager.send_command.assert_called_once_with(
        "light_device", "set_brightness", {"intensity": 123}
    )
