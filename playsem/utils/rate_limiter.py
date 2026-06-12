"""
Rate limiting utilities for protocol servers.

Provides simple sliding window rate limiters
to prevent DoS attacks and resource exhaustion.
"""

import time
import threading
from typing import Dict
from collections import defaultdict


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
