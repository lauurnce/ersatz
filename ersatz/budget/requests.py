"""Daily request budget per provider, stored in the cache.

The count is checked and increased before every provider call. It is not
safe across processes that share one cache file; v0.1 runs one process.
"""

from collections.abc import Callable
from datetime import UTC, datetime

from ersatz.cache.base import Cache, DataKind


class BudgetExhaustedError(Exception):
    def __init__(self, provider: str, limit: int) -> None:
        super().__init__(f"{provider}: daily request budget of {limit} is spent")
        self.provider = provider
        self.limit = limit


def _utcnow() -> datetime:
    return datetime.now(UTC)


class RequestBudget:
    def __init__(
        self,
        cache: Cache,
        provider: str,
        daily_limit: int,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._cache = cache
        self._provider = provider
        self._limit = daily_limit
        self._clock = clock

    def _key(self) -> str:
        return f"{self._provider}:{self._clock().date().isoformat()}"

    def used(self) -> int:
        entry = self._cache.get(DataKind.BUDGET, self._key())
        return int(entry.payload) if entry else 0

    def remaining(self) -> int:
        return max(self._limit - self.used(), 0)

    def spend(self) -> None:
        """Count one request, or raise if the day's budget is spent."""
        used = self.used()
        if used >= self._limit:
            raise BudgetExhaustedError(self._provider, self._limit)
        self._cache.put(DataKind.BUDGET, self._key(), str(used + 1).encode())
