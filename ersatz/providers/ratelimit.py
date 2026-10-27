"""Token bucket rate limiter, one per provider."""

import time
from collections.abc import Callable


class TokenBucket:
    """Allows `rate_per_minute` calls per minute with bursts up to `burst`."""

    def __init__(
        self,
        rate_per_minute: float,
        burst: int | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._rate = rate_per_minute / 60.0
        self._capacity = float(burst if burst is not None else max(int(rate_per_minute // 6), 1))
        self._tokens = self._capacity
        self._monotonic = monotonic
        self._sleep = sleep
        self._updated = monotonic()

    def _refill(self) -> None:
        now = self._monotonic()
        self._tokens = min(self._capacity, self._tokens + (now - self._updated) * self._rate)
        self._updated = now

    def acquire(self) -> None:
        """Take one token, sleeping until one is available."""
        self._refill()
        if self._tokens < 1:
            self._sleep((1 - self._tokens) / self._rate)
            self._refill()
        self._tokens -= 1
