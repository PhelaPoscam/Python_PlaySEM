#!/usr/bin/env python3
"""Shared retry policy helpers for connectivity drivers."""

from dataclasses import dataclass
from typing import List, Generator, Tuple


@dataclass
class RetryPolicy:
    """Bounded exponential backoff policy used by driver reconnect logic."""

    max_attempts: int = 3
    initial_delay: float = 0.5
    max_delay: float = 5.0
    backoff_factor: float = 2.0

    def delays(self) -> List[float]:
        """Return delay values applied after each failed attempt."""
        if self.max_attempts <= 1:
            return []

        values = []
        delay = max(0.0, self.initial_delay)
        for _ in range(self.max_attempts - 1):
            values.append(min(delay, self.max_delay))
            delay = max(delay * self.backoff_factor, delay)
        return values

    def attempts(self) -> Generator[Tuple[int, float], None, None]:
        """Yield (attempt, delay) for retry loops."""
        delays = self.delays()
        for i in range(max(1, self.max_attempts)):
            yield i + 1, delays[i] if i < len(delays) else 0.0
