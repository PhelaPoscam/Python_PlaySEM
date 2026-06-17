import sys
import pytest
import asyncio
import time
from pathlib import Path
from unittest.mock import patch

# Add project root to sys.path if not present
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class MockMonotonic:
    def __init__(self):
        self.val = 1000.0

    def __call__(self):
        # Slightly advance on each call to prevent infinite loops in check conditions
        self.val += 0.002
        return self.val

    def advance(self, secs):
        self.val += secs


original_sleep = asyncio.sleep
clock = MockMonotonic()


async def mock_asyncio_sleep(delay, *args, **kwargs):
    """Bypasses asyncio.sleep delays in demos for instant testing by advancing the mock clock."""
    clock.advance(delay)
    # Yield control to the event loop so other async tasks (like timeline player) can run
    await original_sleep(0.0001)


@pytest.mark.asyncio
async def test_timeline_demo_runs_successfully():
    """Verify that tools/timeline/demo.py runs to completion without errors."""
    global clock
    clock = MockMonotonic()  # Reset clock

    # Patch time.monotonic globally so playsem.timeline and demo check the same mock clock
    with (
        patch("time.monotonic", clock),
        patch("asyncio.sleep", mock_asyncio_sleep),
        patch("time.sleep", return_value=None),
    ):

        from tools.timeline.demo import main as timeline_main

        await timeline_main()


def test_device_registry_demo_runs_successfully():
    """Verify that examples/device_registry_demo.py runs to completion without errors."""
    with patch("time.sleep", return_value=None):
        from examples.device_registry_demo import main as registry_demo_main

        registry_demo_main()
