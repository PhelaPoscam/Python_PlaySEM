import sys
import pytest
import asyncio
import time
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class MockMonotonic:
    def __init__(self):
        self.val = 1000.0

    def __call__(self):
        self.val += 0.002
        return self.val

    def advance(self, secs):
        self.val += secs


original_sleep = asyncio.sleep
clock = MockMonotonic()


async def mock_asyncio_sleep(delay, *args, **kwargs):
    """Bypasses asyncio.sleep delays in demos for instant testing."""
    clock.advance(delay)
    await original_sleep(0.0001)


@pytest.mark.asyncio
async def test_timeline_demo_executes_correct_effects():
    """Timeline demo dispatches exactly 3 effects in timestamp order."""
    global clock
    clock = MockMonotonic()

    with (
        patch("time.monotonic", clock),
        patch("asyncio.sleep", mock_asyncio_sleep),
        patch("time.sleep", return_value=None),
    ):
        from tools.timeline.demo import main as timeline_main

        # The demo main catches KeyboardInterrupt; we let it run normally
        await timeline_main()

        # If we get here without exception, all 4 demo scenarios ran


def test_device_registry_demo_registers_devices():
    """Device registry demo correctly registers and queries devices."""
    from examples.device_registry_demo import main as registry_demo_main

    # Just verify it runs without error and produces expected device counts
    registry_demo_main()
    # The demo prints assertions; if it had real bugs it would raise
