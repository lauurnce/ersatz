"""Shared HTTP client: rate limit, retries with backoff and jitter."""

import random
import time
from collections.abc import Callable, Mapping
from typing import Any

import httpx

from ersatz.providers.errors import ProviderUnavailableError, QuotaExceededError
from ersatz.providers.ratelimit import TokenBucket

RETRY_STATUS = frozenset({429, 500, 502, 503, 504})


class RetryPolicy:
    def __init__(
        self,
        attempts: int = 4,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        rng: random.Random | None = None,
    ) -> None:
        self.attempts = attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._rng = rng or random.Random()  # noqa: S311 - jitter, not security

    def delay(self, attempt: int, retry_after: float | None) -> float:
        """Full jitter backoff. A Retry-After header sets the minimum."""
        cap = min(self.max_delay, self.base_delay * 2**attempt)
        jittered = self._rng.uniform(0, cap)
        return max(jittered, retry_after or 0.0)


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None


class HttpClient:
    def __init__(
        self,
        provider: str,
        limiter: TokenBucket,
        retry: RetryPolicy | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        timeout: float = 20.0,
    ) -> None:
        self.provider = provider
        self._limiter = limiter
        self._retry = retry or RetryPolicy()
        self._sleep = sleep
        self._client = httpx.Client(
            transport=transport,
            timeout=timeout,
            headers={"User-Agent": "ersatz-parts"},
        )

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        json: Any = None,
        data: Mapping[str, str] | None = None,
        before_send: Callable[[], None] | None = None,
    ) -> httpx.Response:
        """Send a request. Retries 429, 5xx and network errors, then raises.

        Other status codes are returned to the caller. `before_send` runs
        before every attempt, so request budgets count each retry.
        """
        last_error: str = ""
        for attempt in range(self._retry.attempts):
            self._limiter.acquire()
            if before_send is not None:
                before_send()
            try:
                response = self._client.request(method, url, headers=headers, json=json, data=data)
            except httpx.TransportError as exc:
                last_error = f"network error: {type(exc).__name__}"
                retry_after = None
            else:
                if response.status_code not in RETRY_STATUS:
                    return response
                retry_after = _retry_after(response)
                if response.status_code == 429 and attempt == self._retry.attempts - 1:
                    raise QuotaExceededError(
                        self.provider,
                        "rate limit still exceeded after retries; wait and try again",
                        retry_after=retry_after,
                    )
                last_error = f"HTTP {response.status_code}"
            if attempt < self._retry.attempts - 1:
                self._sleep(self._retry.delay(attempt, retry_after))
        raise ProviderUnavailableError(
            self.provider, f"{last_error} after {self._retry.attempts} attempts"
        )

    def close(self) -> None:
        self._client.close()
