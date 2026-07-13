"""
Unit tests for sliding window rate limiting utility.
"""

import time
import pytest
from playsem.utils.rate_limiter import SlidingWindowLimiter


def test_sliding_window_limiter():
    # Max 2 requests in a 0.1-second window
    limiter = SlidingWindowLimiter(max_requests=2, window_seconds=0.1)
    client = "client_1"

    # Initial remaining count
    assert limiter.get_remaining(client) == 2

    # Allow first request
    assert limiter.allow(client) is True
    assert limiter.get_remaining(client) == 1

    # Allow second request
    assert limiter.allow(client) is True
    assert limiter.get_remaining(client) == 0

    # Third request should be blocked
    assert limiter.allow(client) is False
    assert limiter.get_remaining(client) == 0

    # Different client should not be affected
    assert limiter.allow("client_2") is True

    # Wait for window to slide (0.12 seconds)
    time.sleep(0.12)

    # Should allow requests again
    assert limiter.get_remaining(client) == 2
    assert limiter.allow(client) is True

    # Reset specific client
    limiter.reset(client)
    assert limiter.get_remaining(client) == 2

    # Reset all
    limiter.allow(client)
    limiter.reset()
    assert limiter.get_remaining(client) == 2
