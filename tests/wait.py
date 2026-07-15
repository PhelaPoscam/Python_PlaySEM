"""Wait helpers that replace arbitrary time.sleep() with condition-based polling.

Two main functions:
- ``wait_for(predicate, timeout=5.0, interval=0.01)``: poll until predicate returns
  truthy. Raises AssertionError on timeout. Works for both sync and async
  predicates (async ones are detected via inspect.iscoroutinefunction).
- ``wait_until(predicate, timeout=5.0)``: sugar around wait_for when you just
  need a single condition.

The default timeout is generous (5s) but the polling interval is short (10ms),
so a passing test typically returns within ~30ms once the condition is met.
"""

from __future__ import annotations

import asyncio
import inspect
import time
from typing import Any, Awaitable, Callable, TypeVar

T = TypeVar("T")


async def _await_async_predicate(predicate: Callable[[], Any]) -> Any:
    """Run an async predicate and return its result."""
    result = predicate()
    if inspect.isawaitable(result):
        return await result
    return result


def wait_for(
    predicate: Callable[[], Any | Awaitable[Any]],
    timeout: float = 5.0,
    interval: float = 0.01,
    message: str = "condition not met within timeout",
) -> Any:
    """Block until predicate() is truthy or raise AssertionError on timeout.

    Args:
        predicate: Zero-arg callable. May be sync or async (coroutine).
        timeout: Maximum seconds to wait.
        interval: Seconds between polls.
        message: Error message on timeout.

    Returns:
        The truthy value returned by the predicate.
    """
    if inspect.iscoroutinefunction(predicate):
        # Defer to async variant when called from a sync context.
        raise TypeError(
            "wait_for received an async predicate in a sync context; "
            "use await wait_for_async(...) instead"
        )

    deadline = time.monotonic() + timeout
    while True:
        result = predicate()
        if result:
            return result
        if time.monotonic() >= deadline:
            raise AssertionError(
                f"{message} (waited {timeout}s, last result={result!r})"
            )
        time.sleep(interval)


async def wait_for_async(
    predicate: Callable[[], Any | Awaitable[Any]],
    timeout: float = 5.0,
    interval: float = 0.01,
    message: str = "async condition not met within timeout",
) -> Any:
    """Async version of wait_for. Polls an async predicate."""
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        result = await _await_async_predicate(predicate)
        if result:
            return result
        if asyncio.get_event_loop().time() >= deadline:
            raise AssertionError(
                f"{message} (waited {timeout}s, last result={result!r})"
            )
        await asyncio.sleep(interval)


def wait_until(
    predicate: Callable[[], bool],
    timeout: float = 5.0,
    interval: float = 0.01,
) -> None:
    """Convenience: assert that predicate becomes truthy within timeout."""
    wait_for(predicate, timeout=timeout, interval=interval)


async def wait_until_async(
    predicate: Callable[[], Any | Awaitable[Any]],
    timeout: float = 5.0,
    interval: float = 0.01,
    message: str = "async condition not met within timeout",
) -> None:
    """Convenience: async version of wait_until."""
    await wait_for_async(predicate, timeout=timeout, interval=interval, message=message)
