# tests/test_timeline.py

import pytest
import time
from unittest.mock import MagicMock
from src.timeline import Timeline
from src.effect_metadata import create_effect, create_timeline
from src.effect_dispatcher import EffectDispatcher


@pytest.fixture
def mock_dispatcher():
    return MagicMock(spec=EffectDispatcher)


@pytest.fixture
def timeline_scheduler(mock_dispatcher):
    return Timeline(mock_dispatcher, tick_interval=0.01)


def test_timeline_load(timeline_scheduler):
    """Test loading a timeline."""
    effect_timeline = create_timeline(
        create_effect("light", timestamp=0, duration=1000),
        create_effect("wind", timestamp=500, duration=1000),
        title="Test Timeline",
    )

    timeline_scheduler.load_timeline(effect_timeline)
    assert timeline_scheduler.timeline is not None
    assert len(timeline_scheduler.timeline.effects) == 2


def test_timeline_start_stop(timeline_scheduler, mock_dispatcher):
    """Test starting and stopping timeline."""
    effect_timeline = create_timeline(
        create_effect("light", timestamp=0, duration=100)
    )

    timeline_scheduler.load_timeline(effect_timeline)
    timeline_scheduler.start()

    assert timeline_scheduler.is_running
    time.sleep(0.15)  # Wait for effect to execute

    timeline_scheduler.stop()
    assert not timeline_scheduler.is_running
    assert mock_dispatcher.dispatch_effect_metadata.called


def test_timeline_pause_resume(timeline_scheduler):
    """Test pausing and resuming timeline."""
    effect_timeline = create_timeline(
        create_effect("light", timestamp=0, duration=1000)
    )

    timeline_scheduler.load_timeline(effect_timeline)
    timeline_scheduler.start()
    assert timeline_scheduler.is_running

    timeline_scheduler.pause()
    assert timeline_scheduler.is_paused

    timeline_scheduler.resume()
    assert not timeline_scheduler.is_paused
    assert timeline_scheduler.is_running

    timeline_scheduler.stop()


def test_timeline_get_position(timeline_scheduler):
    """Test getting timeline position."""
    effect_timeline = create_timeline(
        create_effect("light", timestamp=0, duration=200)
    )

    timeline_scheduler.load_timeline(effect_timeline)
    initial_pos = timeline_scheduler.get_position()
    assert initial_pos == 0

    timeline_scheduler.start()
    time.sleep(0.1)

    current_pos = timeline_scheduler.get_position()
    assert current_pos >= 90  # Allow some timing variance

    timeline_scheduler.stop()


def test_event_effect(timeline_scheduler, mock_dispatcher):
    """Test event-based effect triggering."""
    effect = create_effect(
        "vibration", timestamp=0, duration=100, event_id=123
    )

    timeline_scheduler.add_event_effect(effect)
    assert mock_dispatcher.dispatch_effect_metadata.called
