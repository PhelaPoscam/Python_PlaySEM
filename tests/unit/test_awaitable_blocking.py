import pytest
import asyncio
import threading
import time
from playsem import DeviceManager
from unittest.mock import MagicMock


async def dummy_coro(val):
    await asyncio.sleep(0.01)
    return val


async def failing_coro():
    await asyncio.sleep(0.01)
    raise ValueError("Coroutine exception")


async def slow_coro():
    await asyncio.sleep(1.0)
    return "done"


def test_awaitable_blocking_no_running_loop():
    """Verify execution of awaitable when no event loop is running (standard thread)."""
    manager = DeviceManager(client=MagicMock())
    result = manager._run_awaitable_blocking(dummy_coro("hello"))
    assert result == "hello"


def test_awaitable_blocking_exception_propagation():
    """Verify that exceptions from the coroutine are correctly raised in calling thread."""
    manager = DeviceManager(client=MagicMock())
    with pytest.raises(ValueError, match="Coroutine exception"):
        manager._run_awaitable_blocking(failing_coro())


@pytest.mark.asyncio
async def test_awaitable_blocking_from_running_loop():
    """Verify execution of awaitable from inside a running event loop (nested prevention)."""
    # This test is decorated with pytest.mark.asyncio, meaning it runs inside an active event loop.
    manager = DeviceManager(client=MagicMock())

    # Normally, calling asyncio.run() here would raise RuntimeError.
    # _run_awaitable_blocking should delegate to an isolated loop thread and complete successfully.
    result = manager._run_awaitable_blocking(dummy_coro("nested_world"))
    assert result == "nested_world"


@pytest.mark.asyncio
async def test_awaitable_blocking_timeout():
    """Verify that timed-out bridge joins to completion rather than abandoning thread."""
    manager = DeviceManager(client=MagicMock(), async_bridge_timeout=0.05)

    start = time.monotonic()
    result = manager._run_awaitable_blocking(slow_coro())
    elapsed = time.monotonic() - start

    assert result == "done"
    assert (
        elapsed >= 1.0
    )  # Thread was allowed to complete rather than being abandoned
