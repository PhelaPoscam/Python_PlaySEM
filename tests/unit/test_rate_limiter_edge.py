import pytest
import threading
import time
from playsem.utils.rate_limiter import SlidingWindowLimiter


def test_rate_limiter_zero_capacity():
    """Verify that a capacity of 0 immediately blocks all requests."""
    limiter = SlidingWindowLimiter(max_requests=0, window_seconds=1.0)
    assert limiter.allow("client_1") is False
    assert limiter.get_remaining("client_1") == 0


def test_rate_limiter_concurrency():
    """Verify thread-safety and correctness under concurrent request contention."""
    max_requests = 50
    limiter = SlidingWindowLimiter(
        max_requests=max_requests, window_seconds=2.0
    )
    client_id = "concurrent_client"

    allowed_count = 0
    lock = threading.Lock()

    def worker():
        nonlocal allowed_count
        # Try to execute a request
        if limiter.allow(client_id):
            with lock:
                allowed_count += 1

    threads = [threading.Thread(target=worker) for _ in range(100)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # The number of allowed requests must equal max_requests exactly
    assert allowed_count == max_requests
    assert limiter.get_remaining(client_id) == 0


def test_rate_limiter_memory_cleanup():
    """Verify that resetting rate limits removes records from internal memory."""
    limiter = SlidingWindowLimiter(max_requests=5, window_seconds=1.0)
    client_1 = "client_1"
    client_2 = "client_2"

    limiter.allow(client_1)
    limiter.allow(client_2)

    # Verify keys exist in internal dictionary
    assert client_1 in limiter._requests
    assert client_2 in limiter._requests

    # Reset client_1 specifically
    limiter.reset(client_1)
    assert client_1 not in limiter._requests
    assert client_2 in limiter._requests

    # Reset all
    limiter.allow(client_1)
    limiter.reset()
    assert len(limiter._requests) == 0
