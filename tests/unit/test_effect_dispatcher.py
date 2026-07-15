# tests/test_effect_dispatcher.py

import pytest
from unittest.mock import MagicMock, patch

from playsem.effect_dispatcher import EffectDispatcher, DispatchResult
from playsem.device_manager import DeviceManager
from playsem.effect_metadata import EffectMetadata


@pytest.fixture
def mock_device_manager():
    """Fixture for a mocked DeviceManager."""
    return MagicMock(spec=DeviceManager)


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
    dispatcher = EffectDispatcher(mock_device_manager, "dummy/path.yaml")
    dispatcher.effects_config = sample_effects_config
    dispatcher._effects_config_loaded = True
    return dispatcher


def test_dispatch_effect_simple(dispatcher, mock_device_manager):
    """Test dispatching a simple effect with no parameter mapping."""
    dispatcher.dispatch_effect("fan_on", {"speed": 100})

    mock_device_manager.send_command.assert_called_once_with(
        "fan_1", "set_speed", {"speed": 100}
    )


def test_dispatch_effect_with_parameter_mapping(dispatcher, mock_device_manager):
    """Test dispatching an effect with a mapped 'intensity' parameter."""
    dispatcher.dispatch_effect("light_on", {"intensity": "high"})

    # 'high' should be mapped to 255
    mock_device_manager.send_command.assert_called_once_with(
        "light_1", "set_brightness", {"intensity": 255}
    )


def test_dispatch_effect_with_default_parameter(dispatcher, mock_device_manager):
    """Test that a default parameter is used when none is provided."""
    # Dispatch 'light_on' without providing 'intensity'
    dispatcher.dispatch_effect("light_on", {})

    # The default value of 255 should be used
    mock_device_manager.send_command.assert_called_once_with(
        "light_1", "set_brightness", {"intensity": 255}
    )


def test_dispatch_unknown_effect(dispatcher):
    """Test that dispatching an unknown effect returns False."""
    result = dispatcher.dispatch_effect("unknown_effect", {})
    assert result is False


def test_dispatch_incomplete_effect_config(dispatcher):
    """Test that an effect with missing 'command' returns False."""
    result = dispatcher.dispatch_effect("incomplete_effect", {})
    assert result is False


def test_dispatch_effect_metadata(dispatcher, mock_device_manager):
    """Test dispatching via an EffectMetadata object."""
    effect = EffectMetadata(effect_type="light_on", intensity=100, duration=1000)
    dispatcher.dispatch_effect_metadata(effect)

    # The dispatcher should merge the intensity into the parameters
    mock_device_manager.send_command.assert_called_once_with(
        "light_1", "set_brightness", {"intensity": 100}
    )


def test_dispatch_effect_metadata_with_location(dispatcher, mock_device_manager):
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


def test_get_supported_effects(dispatcher, sample_effects_config):
    """Test that get_supported_effects returns the correct list of names."""
    supported_effects = dispatcher.get_supported_effects()
    expected_effects = list(sample_effects_config["effects"].keys())

    assert sorted(supported_effects) == sorted(expected_effects)


def test_fallback_to_default_mappings(mock_device_manager):
    """Test that the dispatcher uses default mappings if config fails to load."""
    dispatcher = EffectDispatcher(mock_device_manager, "bad/path.yaml")
    dispatcher.effects_config = None
    dispatcher._effects_config_loaded = False
    dispatcher._effects_config_path = "bad/path.yaml"
    # _load_effects_config will call open which fails, then fall back
    with patch("builtins.open") as mock_open:
        mock_open.side_effect = FileNotFoundError
        dispatcher._load_effects_config()

    # Check that a default effect can be dispatched
    dispatcher.dispatch_effect("light", {"intensity": 123})
    mock_device_manager.send_command.assert_called_once_with(
        "light_device", "set_brightness", {"intensity": 123}
    )


class TestManagedMode:
    def test_managed_mode_queues_effects(self, mock_device_manager):
        """Effects are enqueued, not dispatched immediately, in managed mode."""
        dispatcher = EffectDispatcher(mock_device_manager, managed_mode=True)
        dispatcher.dispatch_effect("light", {"intensity": 50})

        assert dispatcher.get_queue_size() == 1
        mock_device_manager.send_command.assert_not_called()

    def test_process_next_effect_dispatches_from_queue(self, mock_device_manager):
        """Calling process_next_effect() drains one item from the queue."""
        dispatcher = EffectDispatcher(mock_device_manager, managed_mode=True)
        dispatcher.dispatch_effect("light", {"intensity": 50})
        assert dispatcher.get_queue_size() == 1

        result = dispatcher.process_next_effect()
        assert result["status"] == "dispatched"
        assert dispatcher.get_queue_size() == 0
        mock_device_manager.send_command.assert_called_once()

    def test_process_all_pending_drains_queue(self, mock_device_manager):
        """process_all_pending() empties the queue and returns per-item results."""
        dispatcher = EffectDispatcher(mock_device_manager, managed_mode=True)
        dispatcher.dispatch_effect("light", {"intensity": 10})
        dispatcher.dispatch_effect("wind", {"speed": 20})
        dispatcher.dispatch_effect("vibration", {"pattern": "pulse"})

        outcomes = dispatcher.process_all_pending()
        assert len(outcomes) == 3
        assert dispatcher.get_queue_size() == 0
        assert mock_device_manager.send_command.call_count == 3

    def test_max_queue_size_rejects_when_full(self, mock_device_manager):
        """Enqueuing past max_queue_size returns a rejected DispatchResult."""
        dispatcher = EffectDispatcher(
            mock_device_manager, managed_mode=True, max_queue_size=1
        )
        result1 = dispatcher.dispatch_effect_result("light", {})
        assert result1.accepted is True

        result2 = dispatcher.dispatch_effect_result("wind", {})
        assert result2.accepted is False
        assert result2.status == "rejected"

    def test_dead_letter_on_persistent_failure(self, mock_device_manager):
        """Failed effects with dead_letter policy land in dead_letter_queue."""
        mock_device_manager.send_command.return_value = False
        dispatcher = EffectDispatcher(
            mock_device_manager,
            managed_mode=True,
            failure_policy="dead_letter",
            max_dispatch_retries=1,
        )
        dispatcher.dispatch_effect("light", {"intensity": 50})
        dispatcher.process_next_effect()

        assert len(dispatcher.dead_letter_queue) == 1
        assert dispatcher.dead_letter_queue[0]["effect"] == "light"

    def test_retry_requeues_then_dispatches(self, mock_device_manager):
        """Retry policy requeues a failed effect, then dispatches on success."""
        mock_device_manager.send_command.side_effect = [False, True]
        dispatcher = EffectDispatcher(
            mock_device_manager,
            managed_mode=True,
            failure_policy="retry",
            max_dispatch_retries=2,
        )
        dispatcher.dispatch_effect("light", {"intensity": 50})

        # First attempt fails -> requeued
        result1 = dispatcher.process_next_effect()
        assert result1["status"] == "requeued"
        assert dispatcher.get_queue_size() == 1

        # Second attempt succeeds -> dispatched
        result2 = dispatcher.process_next_effect()
        assert result2["status"] == "dispatched"
        assert dispatcher.get_queue_size() == 0


class TestDispatchResult:
    def test_to_dict_omits_none(self):
        """DispatchResult.to_dict() excludes None-valued fields."""
        result = DispatchResult(status="queued", accepted=True, effect="light")
        d = result.to_dict()
        assert "status" in d
        assert "effect" in d
        assert "error" not in d
        assert "device_id" not in d

    def test_bool_true_when_accepted(self):
        """DispatchResult is truthy when accepted and queued."""
        assert bool(DispatchResult(status="queued", accepted=True)) is True

    def test_bool_false_when_rejected(self):
        """DispatchResult is falsy when rejected."""
        assert bool(DispatchResult(status="rejected", accepted=False)) is False


class TestTtl:
    def test_ttl_expiry_rejects_stale_effect(self, mock_device_manager):
        """Dispatch with ttl_ms=0 is immediately rejected as expired."""
        dispatcher = EffectDispatcher(mock_device_manager)
        result = dispatcher.dispatch_effect_result("light", {"intensity": 50}, ttl_ms=0)
        assert result.status == "expired"
        assert result.accepted is False
        mock_device_manager.send_command.assert_not_called()
