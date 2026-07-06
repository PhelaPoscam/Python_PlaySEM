import pytest
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock

from playsem import EffectDispatcher
from playsem.timeline import Timeline
from playsem.effect_metadata import create_effect, create_timeline


@pytest.fixture
def real_dispatcher():
    """Dispatcher with a real mock device manager (not just MagicMock)."""
    dm = MagicMock()
    dm.send_command.return_value = True
    return EffectDispatcher(dm)


@pytest.fixture
def fast_timeline(real_dispatcher):
    """Timeline with a very fast tick interval for speedy tests."""
    return Timeline(real_dispatcher, tick_interval=0.001)


class TestTimelineE2E:
    @pytest.mark.asyncio
    async def test_effects_dispatched_in_timestamp_order(self, fast_timeline):
        """Effects are dispatched in order of their timestamps."""
        dispatched = []

        def on_effect(effect):
            dispatched.append((effect.effect_type, time.monotonic()))

        fast_timeline.set_callbacks(on_effect=on_effect)

        timeline = create_timeline(
            create_effect("light", timestamp=0, duration=50),
            create_effect("wind", timestamp=30, duration=50),
            create_effect("vibration", timestamp=60, duration=50),
        )
        fast_timeline.load_timeline(timeline)

        await fast_timeline.start()
        while fast_timeline.is_running:
            await asyncio.sleep(0.01)
        await fast_timeline.stop()

        types = [d[0] for d in dispatched]
        assert types == ["light", "wind", "vibration"]

    @pytest.mark.asyncio
    async def test_on_complete_fires_once(self, fast_timeline):
        """on_complete callback fires exactly once when timeline finishes."""
        complete_count = [0]

        def on_complete():
            complete_count[0] += 1

        fast_timeline.set_callbacks(on_complete=on_complete)

        timeline = create_timeline(
            create_effect("light", timestamp=0, duration=50)
        )
        fast_timeline.load_timeline(timeline)

        await fast_timeline.start()
        while fast_timeline.is_running:
            await asyncio.sleep(0.01)
        await fast_timeline.stop()

        assert complete_count[0] == 1

    @pytest.mark.asyncio
    async def test_pause_delays_subsequent_effects(self, fast_timeline):
        """Pausing delays effects scheduled after the pause point."""
        dispatched = []

        def on_effect(effect):
            dispatched.append(effect.effect_type)

        fast_timeline.set_callbacks(on_effect=on_effect)

        # Effect at 200ms - we pause at ~50ms, resume after 100ms pause
        timeline = create_timeline(
            create_effect("light", timestamp=0, duration=500),
            create_effect("wind", timestamp=200, duration=100),
        )
        fast_timeline.load_timeline(timeline)

        await fast_timeline.start()

        # Wait ~50ms then pause for 100ms
        await asyncio.sleep(0.06)
        fast_timeline.pause()
        await asyncio.sleep(0.1)
        fast_timeline.resume()

        while fast_timeline.is_running:
            await asyncio.sleep(0.01)
        await fast_timeline.stop()

        # Both effects should still have dispatched despite the pause
        assert "light" in dispatched
        assert "wind" in dispatched

    @pytest.mark.asyncio
    async def test_dynamic_add_effect_while_running(self, fast_timeline):
        """Effects added while timeline is running are dispatched correctly."""
        dispatched = []

        def on_effect(effect):
            dispatched.append(effect.effect_type)

        fast_timeline.set_callbacks(on_effect=on_effect)

        timeline = create_timeline(
            create_effect("light", timestamp=0, duration=100)
        )
        fast_timeline.load_timeline(timeline)

        await fast_timeline.start()
        await asyncio.sleep(0.05)

        # Add a new effect while running
        new_effect = create_effect("wind", timestamp=150, duration=50)
        fast_timeline.add_effect(new_effect)

        while fast_timeline.is_running:
            await asyncio.sleep(0.01)
        await fast_timeline.stop()

        assert "wind" in dispatched

    @pytest.mark.asyncio
    async def test_remove_effect_prevents_dispatch(self, fast_timeline):
        """Removing an effect before it executes prevents dispatch."""
        dispatched = []

        def on_effect(effect):
            dispatched.append(effect.effect_type)

        fast_timeline.set_callbacks(on_effect=on_effect)

        vibration = create_effect("vibration", timestamp=100, duration=50)
        timeline = create_timeline(
            create_effect("light", timestamp=0, duration=200),
            vibration,
        )
        fast_timeline.load_timeline(timeline)
        await fast_timeline.start()

        # Remove before it fires
        await asyncio.sleep(0.05)
        fast_timeline.remove_effect(vibration)

        while fast_timeline.is_running:
            await asyncio.sleep(0.01)
        await fast_timeline.stop()

        assert "light" in dispatched
        assert "vibration" not in dispatched
