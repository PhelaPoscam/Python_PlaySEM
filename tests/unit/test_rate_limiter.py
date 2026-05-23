"""
Unit tests for rate limiting and payload validation utilities.
"""

import time
import pytest
from playsem.utils.rate_limiter import (
    TokenBucketLimiter,
    SlidingWindowLimiter,
    validate_payload_size,
)


def test_token_bucket_limiter():
    # Capacity 2, refilling 10 tokens per second
    limiter = TokenBucketLimiter(rate=10.0, capacity=2)

    # Initial capacity should be full
    assert limiter.tokens == 2

    # Consume 1 token - success
    assert limiter.consume(1) is True
    assert (
        limiter.tokens <= 1.0
    )  # slightly more than 1 due to tiny time elapsed

    # Consume another token - success
    assert limiter.consume(1) is True

    # Consume third token - should fail (exhausted)
    assert limiter.consume(1) is False

    # Wait for refill (0.1 seconds should refill 1 token)
    time.sleep(0.12)
    assert limiter.consume(1) is True
    assert limiter.consume(1) is False  # empty again

    # Reset
    limiter.reset()
    assert limiter.tokens == 2
    assert limiter.consume(2) is True


def test_sliding_window_limiter():
    # Max 2 requests in a 1-second window
    limiter = SlidingWindowLimiter(max_requests=2, window_seconds=1.0)
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

    # Wait for window to slide (1.1 seconds)
    time.sleep(1.1)

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


def test_validate_payload_size():
    payload = b"hello world"

    # Valid payload size
    is_valid, err = validate_payload_size(payload, 20)
    assert is_valid is True
    assert err == ""

    # Invalid payload size
    is_valid, err = validate_payload_size(payload, 5)
    assert is_valid is False
    assert "exceeds maximum" in err
