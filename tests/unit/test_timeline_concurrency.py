import pytest
import asyncio
import threading
import time
from playsem.effect_metadata import create_effect, create_timeline
from playsem.effect_dispatcher import EffectDispatcher
from playsem.device_manager import DeviceManager
from playsem.timeline import Timeline
from unittest.mock import MagicMock


def run_loop_in_thread(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


def test_timeline_threading_and_async_interaction():
    # Set up event loop running in a background thread
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=run_loop_in_thread, args=(loop,), daemon=True)
    thread.start()

    try:
        # Create components
        device_manager = DeviceManager(client=MagicMock())
        dispatcher = EffectDispatcher(device_manager)

        # Configure mock effects mapping
        dispatcher.effects_config = {
            "effects": {"light": {"device": "mock_light", "command": "set_color"}}
        }

        # Set tick interval to 10ms for fast testing
        timeline = Timeline(dispatcher, tick_interval=0.01)

        # Create a timeline
        effect_timeline = create_timeline(
            create_effect("light", timestamp=0, duration=1000, intensity=100),
            title="Test Concurrency",
        )
        timeline.load_timeline(effect_timeline)

        # Start timeline in the background loop thread
        future_start = asyncio.run_coroutine_threadsafe(timeline.start(), loop)
        future_start.result(timeout=1.0)

        # Wait briefly for scheduler to start running
        time.sleep(0.05)
        assert timeline.is_running is True
        assert timeline.is_paused is False

        # Read position from main thread (thread-safe check)
        pos_initial = timeline.get_position()
        assert pos_initial >= 0

        # Pause from main thread (synchronous method)
        timeline.pause()
        assert timeline.is_paused is True

        # Capture position at pause
        pos_paused = timeline.get_position()
        time.sleep(0.05)

        # Position should not advance when paused
        assert timeline.get_position() == pos_paused

        # Resume from main thread (synchronous method)
        timeline.resume()
        assert timeline.is_paused is False
        time.sleep(0.05)

        # Position should now advance again
        assert timeline.get_position() > pos_paused

        # Stop timeline in the background loop thread
        future_stop = asyncio.run_coroutine_threadsafe(timeline.stop(), loop)
        future_stop.result(timeout=1.0)

        assert timeline.is_running is False
        assert timeline.current_position == 0

    finally:
        # Stop loop and clean up thread
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=1.0)
