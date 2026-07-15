# tests/test_timeline.py

import pytest
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, AsyncMock
from playsem.timeline import Timeline
from playsem.effect_metadata import create_effect, create_timeline
from playsem import EffectDispatcher


@pytest.fixture
def mock_dispatcher():
    dispatcher = MagicMock(spec=EffectDispatcher)
    dispatcher.async_dispatch_effect_metadata = AsyncMock(return_value=True)
    return dispatcher


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


@pytest.mark.asyncio
async def test_timeline_start_stop(timeline_scheduler, mock_dispatcher):
    """Test starting and stopping timeline."""
    effect_timeline = create_timeline(create_effect("light", timestamp=0, duration=100))

    timeline_scheduler.load_timeline(effect_timeline)
    await timeline_scheduler.start()

    assert timeline_scheduler.is_running
    await asyncio.sleep(0.15)  # Wait for effect to execute

    await timeline_scheduler.stop()
    assert not timeline_scheduler.is_running
    assert mock_dispatcher.async_dispatch_effect_metadata.called


@pytest.mark.asyncio
async def test_timeline_pause_resume(timeline_scheduler):
    """Test pausing and resuming timeline."""
    effect_timeline = create_timeline(
        create_effect("light", timestamp=0, duration=1000)
    )

    timeline_scheduler.load_timeline(effect_timeline)
    await timeline_scheduler.start()
    assert timeline_scheduler.is_running

    timeline_scheduler.pause()
    assert timeline_scheduler.is_paused

    timeline_scheduler.resume()
    assert not timeline_scheduler.is_paused
    assert timeline_scheduler.is_running

    await timeline_scheduler.stop()


@pytest.mark.asyncio
async def test_timeline_get_position(timeline_scheduler):
    """Test getting timeline position."""
    effect_timeline = create_timeline(create_effect("light", timestamp=0, duration=200))

    timeline_scheduler.load_timeline(effect_timeline)
    initial_pos = timeline_scheduler.get_position()
    assert initial_pos == 0

    await timeline_scheduler.start()
    await asyncio.sleep(0.1)

    current_pos = timeline_scheduler.get_position()
    assert current_pos >= 90  # Allow some timing variance

    await timeline_scheduler.stop()


def test_timeline_get_status_does_not_deadlock(timeline_scheduler):
    """get_status can safely call get_position while holding the timeline lock."""
    effect_timeline = create_timeline(create_effect("light", timestamp=0, duration=200))

    timeline_scheduler.load_timeline(effect_timeline)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(timeline_scheduler.get_status)
        status = future.result(timeout=1.0)

    assert status["current_position"] == 0
    assert status["pending_effects"] == 0


@pytest.mark.asyncio
async def test_event_effect(timeline_scheduler, mock_dispatcher):
    """Test event-based effect triggering."""
    effect = create_effect("vibration", timestamp=0, duration=100, event_id=123)

    await timeline_scheduler.add_event_effect(effect)
    assert mock_dispatcher.async_dispatch_effect_metadata.called


@pytest.mark.asyncio
async def test_timeline_managed_mode_without_auto_processing():
    """Managed dispatcher does not send commands without queue processing."""
    device_manager = MagicMock()
    device_manager.send_command.return_value = True
    dispatcher = EffectDispatcher(device_manager, managed_mode=True)
    timeline = Timeline(
        dispatcher,
        tick_interval=0.01,
        process_managed_queue=False,
    )

    effect_timeline = create_timeline(create_effect("light", timestamp=0, duration=100))
    timeline.load_timeline(effect_timeline)
    await timeline.start()
    await asyncio.sleep(0.15)
    await timeline.stop()

    device_manager.send_command.assert_not_called()
    assert dispatcher.get_queue_size() >= 1


@pytest.mark.asyncio
async def test_timeline_managed_mode_with_auto_processing():
    """Managed dispatcher sends commands when queue processing is enabled."""
    device_manager = MagicMock()
    device_manager.send_command.return_value = True
    dispatcher = EffectDispatcher(device_manager, managed_mode=True)
    timeline = Timeline(
        dispatcher,
        tick_interval=0.01,
        process_managed_queue=True,
    )

    effect_timeline = create_timeline(create_effect("light", timestamp=0, duration=100))
    timeline.load_timeline(effect_timeline)
    await timeline.start()
    await asyncio.sleep(0.15)
    await timeline.stop()

    device_manager.send_command.assert_called()
    assert dispatcher.get_queue_size() == 0


@pytest.mark.asyncio
async def test_timeline_dynamic_add_remove(timeline_scheduler, mock_dispatcher):
    """Test dynamically adding and removing effects while the timeline is running."""
    effect_timeline = create_timeline(
        create_effect("light", timestamp=100, duration=100)
    )
    timeline_scheduler.load_timeline(effect_timeline)
    await timeline_scheduler.start()

    # Dynamically add an effect that should execute shortly
    new_effect = create_effect("wind", timestamp=150, duration=100)
    timeline_scheduler.add_effect(new_effect)

    # Dynamically add and then remove an effect to ensure it doesn't get executed
    cancel_effect = create_effect("vibration", timestamp=200, duration=100)
    timeline_scheduler.add_effect(cancel_effect)
    timeline_scheduler.remove_effect(cancel_effect)

    await asyncio.sleep(0.3)
    await timeline_scheduler.stop()

    # verify "light" and "wind" executed, but not "vibration"
    calls = mock_dispatcher.async_dispatch_effect_metadata.call_args_list
    executed_types = [call[0][0].effect_type for call in calls]

    assert "light" in executed_types
    assert "wind" in executed_types
    assert "vibration" not in executed_types


@pytest.mark.asyncio
async def test_timeline_concurrent_mutation_safety(timeline_scheduler, mock_dispatcher):
    """Test that concurrent edits to the timeline effects do not cause iteration crashes."""
    effect_timeline = create_timeline(create_effect("light", timestamp=10, duration=50))
    timeline_scheduler.load_timeline(effect_timeline)
    await timeline_scheduler.start()

    import random
    from threading import Thread

    stop_mutator = False

    def mutator():
        while not stop_mutator:
            # Randomly add/remove/clear effects to stress-test locks and iteration
            eff = create_effect("light", timestamp=random.randint(0, 1000), duration=50)
            timeline_scheduler.add_effect(eff)
            time.sleep(0.005)
            timeline_scheduler.remove_effect(eff)
            time.sleep(0.005)
            if random.random() < 0.1:
                timeline_scheduler.clear_effects()

    t = Thread(target=mutator)
    t.start()

    # Let timeline scheduler and mutator run concurrently for a short period
    await asyncio.sleep(0.2)
    stop_mutator = True
    t.join(timeout=1.0)

    await timeline_scheduler.stop()
    # Test succeeds if no RuntimeError (list changed size during iteration) or deadlocks occurred
