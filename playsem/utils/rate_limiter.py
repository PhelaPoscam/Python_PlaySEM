"""
Rate limiting utilities for protocol servers.

Provides simple token bucket and sliding window rate limiters
to prevent DoS attacks and resource exhaustion.
"""

import time
import threading
from typing import Dict, Tuple
from collections import defaultdict


class TokenBucketLimiter:
    """
    Token bucket rate limiter for controlling request rates.

    Allows burst traffic up to bucket capacity while maintaining
    an average rate limit over time.
    """

    def __init__(self, rate: float, capacity: int):
        """
        Initialize token bucket limiter.

        Args:
            rate: Tokens added per second (average rate)
            capacity: Maximum burst capacity
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()
        self._lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if rate limited
        """
        with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update

            # Add tokens based on elapsed time
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now

            # Try to consume
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def reset(self):
        """Reset the bucket to full capacity."""
        with self._lock:
            self.tokens = self.capacity
            self.last_update = time.monotonic()


class SlidingWindowLimiter:
    """
    Sliding window rate limiter for per-client rate limiting.

    Tracks request timestamps within a sliding window to enforce
    rate limits per client identifier.
    """

    def __init__(self, max_requests: int, window_seconds: float):
        """
        Initialize sliding window limiter.

        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Window size in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()

    def allow(self, client_id: str) -> bool:
        """
        Check if a request from client_id is allowed.

        Args:
            client_id: Unique client identifier

        Returns:
            True if request is allowed, False if rate limited
        """
        now = time.monotonic()
        window_start = now - self.window_seconds

        with self._lock:
            # Remove old requests outside the window
            self._requests[client_id] = [
                ts for ts in self._requests[client_id] if ts > window_start
            ]

            # Check if under limit
            if len(self._requests[client_id]) < self.max_requests:
                self._requests[client_id].append(now)
                return True
            return False

    def get_remaining(self, client_id: str) -> int:
        """
        Get remaining requests for a client in current window.

        Args:
            client_id: Unique client identifier

        Returns:
            Number of remaining requests allowed
        """
        now = time.monotonic()
        window_start = now - self.window_seconds

        with self._lock:
            # Remove old requests
            self._requests[client_id] = [
                ts for ts in self._requests[client_id] if ts > window_start
            ]
            return max(0, self.max_requests - len(self._requests[client_id]))

    def reset(self, client_id: str = None):
        """
        Reset rate limiter for a client or all clients.

        Args:
            client_id: Optional client ID to reset (None resets all)
        """
        with self._lock:
            if client_id:
                self._requests.pop(client_id, None)
            else:
                self._requests.clear()


def validate_payload_size(payload: bytes, max_size: int) -> Tuple[bool, str]:
    """
    Validate that a payload doesn't exceed the maximum size.

    Args:
        payload: Payload bytes to validate
        max_size: Maximum allowed size in bytes

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(payload) > max_size:
        return (
            False,
            f"Payload size {len(payload)} exceeds maximum {max_size} bytes",
        )
    return True, ""
