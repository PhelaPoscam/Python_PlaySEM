"""
Unit tests for CommandEnvelope

Tests the command envelope creation and management:
- Basic construction with required parameters
- Optional parameters handling
- Default values
- Created_at auto-generation
- Delivery modes
"""

import pytest
import time

from playsem.command_envelope import CommandEnvelope
from playsem.effect_metadata import EffectMetadata


class TestCommandEnvelope:
    """Test CommandEnvelope construction and properties."""

    def test_basic_construction(self):
        """Test creating a CommandEnvelope with required parameters."""
        effect = EffectMetadata(effect_type="vibration", intensity=75)
        envelope = CommandEnvelope(
            effect=effect,
            device_id="device_123",
            command="set_intensity",
            params={"intensity": 75},
        )

        assert envelope.effect == effect
        assert envelope.device_id == "device_123"
        assert envelope.command == "set_intensity"
        assert envelope.params == {"intensity": 75}
        assert envelope.effect_id is None
        assert envelope.deadline_ms is None
        assert envelope.idempotency_key is None
        assert envelope.priority == 5
        assert envelope.delivery_mode == "best_effort"
        assert envelope.created_at is not None

    def test_optional_parameters(self):
        """Test creating a CommandEnvelope with all optional parameters."""
        effect = EffectMetadata(effect_type="light", intensity=100)
        created_time = time.monotonic()

        envelope = CommandEnvelope(
            effect=effect,
            device_id="device_456",
            command="turn_off",
            params={},
            effect_id="eff_789",
            deadline_ms=5000,
            idempotency_key="key_abc",
            priority=10,
            delivery_mode="at_least_once",
            created_at=created_time,
        )

        assert envelope.effect == effect
        assert envelope.device_id == "device_456"
        assert envelope.command == "turn_off"
        assert envelope.params == {}
        assert envelope.effect_id == "eff_789"
        assert envelope.deadline_ms == 5000
        assert envelope.idempotency_key == "key_abc"
        assert envelope.priority == 10
        assert envelope.delivery_mode == "at_least_once"
        assert envelope.created_at == created_time

    def test_created_at_default(self):
        """Test that created_at is automatically set if not provided."""
        effect = EffectMetadata(effect_type="wind")
        before = time.monotonic()
        envelope = CommandEnvelope(
            effect=effect, device_id="device_789", command="test", params={}
        )
        after = time.monotonic()

        assert before <= envelope.created_at <= after

    def test_empty_params(self):
        """Test that empty params dict is handled correctly."""
        effect = EffectMetadata(effect_type="scent")
        envelope = CommandEnvelope(
            effect=effect, device_id="device_empty", command="noop", params={}
        )

        assert envelope.params == {}
        assert isinstance(envelope.params, dict)

    def test_complex_params(self):
        """Test CommandEnvelope with complex parameter structures."""
        effect = EffectMetadata(effect_type="light", intensity=80)
        complex_params = {
            "intensity": 80,
            "color": {"r": 255, "g": 128, "b": 0},
            "effects": ["fade", "pulse"],
            "metadata": {"user": "test_user", "session": "abc123"},
        }

        envelope = CommandEnvelope(
            effect=effect,
            device_id="device_complex",
            command="set_complex",
            params=complex_params,
        )

        assert envelope.params == complex_params
        assert envelope.params["color"]["r"] == 255
        assert envelope.params["effects"][0] == "fade"

    def test_priority_ordering(self):
        """Test that priority values are preserved correctly."""
        effect = EffectMetadata(effect_type="vibration")
        low_priority = CommandEnvelope(
            effect=effect,
            device_id="device_low",
            command="cmd_low",
            params={},
            priority=1,
        )
        high_priority = CommandEnvelope(
            effect=effect,
            device_id="device_high",
            command="cmd_high",
            params={},
            priority=10,
        )

        assert low_priority.priority == 1
        assert high_priority.priority == 10
        assert high_priority.priority > low_priority.priority

    def test_delivery_modes(self):
        """Test that delivery_mode is tracked correctly."""
        effect = EffectMetadata(effect_type="light")
        modes = ["best_effort", "at_least_once"]

        for mode in modes:
            envelope = CommandEnvelope(
                effect=effect,
                device_id=f"device_{mode}",
                command="test",
                params={},
                delivery_mode=mode,
            )
            assert envelope.delivery_mode == mode

    def test_deadline_ms(self):
        """Test deadline_ms parameter handling."""
        effect = EffectMetadata(effect_type="vibration")

        # No deadline
        envelope_no_deadline = CommandEnvelope(
            effect=effect,
            device_id="device_no_deadline",
            command="test",
            params={},
        )
        assert envelope_no_deadline.deadline_ms is None

        # With deadline
        envelope_with_deadline = CommandEnvelope(
            effect=effect,
            device_id="device_with_deadline",
            command="test",
            params={},
            deadline_ms=10000,
        )
        assert envelope_with_deadline.deadline_ms == 10000

    def test_idempotency_key(self):
        """Test idempotency_key for tracking duplicate commands."""
        effect = EffectMetadata(effect_type="light")
        idempotency_key = "unique_key_abc_123"

        envelope1 = CommandEnvelope(
            effect=effect,
            device_id="device_corr_1",
            command="cmd1",
            params={},
            idempotency_key=idempotency_key,
        )
        envelope2 = CommandEnvelope(
            effect=effect,
            device_id="device_corr_2",
            command="cmd2",
            params={},
            idempotency_key=idempotency_key,
        )

        assert envelope1.idempotency_key == idempotency_key
        assert envelope2.idempotency_key == idempotency_key
        assert envelope1.idempotency_key == envelope2.idempotency_key

    def test_frozen_dataclass(self):
        """Test that CommandEnvelope is immutable (frozen dataclass)."""
        effect = EffectMetadata(effect_type="vibration")
        envelope = CommandEnvelope(
            effect=effect,
            device_id="device_test",
            command="test",
            params={"value": 1},
        )

        # Should not be able to modify attributes
        with pytest.raises(Exception):  # FrozenInstanceError
            envelope.device_id = "new_device"

        with pytest.raises(Exception):
            envelope.command = "new_command"

        with pytest.raises(Exception):
            envelope.priority = 999
