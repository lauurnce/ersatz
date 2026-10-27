"""Retries with backoff and clear errors when they run out."""

import random

import httpx
import pytest

from ersatz.providers import ProviderUnavailableError, QuotaExceededError
from ersatz.providers.http import RetryPolicy
from tests.clock import FakeClock
from tests.providers.fakes import Script, make_http


def test_retries_5xx_then_succeeds() -> None:
    clock = FakeClock()
    script = Script(httpx.Response(503), httpx.Response(502), httpx.Response(200))
    response = make_http(script, clock).request("GET", "https://api.test/x")
    assert response.status_code == 200
    assert len(script.requests) == 3
    assert len(clock.slept) == 2


def test_honours_retry_after_on_429() -> None:
    clock = FakeClock()
    script = Script(httpx.Response(429, headers={"Retry-After": "7"}), httpx.Response(200))
    make_http(script, clock).request("GET", "https://api.test/x")
    assert clock.slept[0] >= 7


def test_429_after_all_attempts_raises_quota_error() -> None:
    clock = FakeClock()
    script = Script(*[httpx.Response(429, headers={"Retry-After": "2"}) for _ in range(3)])
    with pytest.raises(QuotaExceededError) as info:
        make_http(script, clock, attempts=3).request("GET", "https://api.test/x")
    assert info.value.retry_after == 2


def test_network_errors_retry_then_raise() -> None:
    clock = FakeClock()
    script = Script(*[httpx.ConnectError("down") for _ in range(4)])
    with pytest.raises(ProviderUnavailableError, match="ConnectError after 4 attempts"):
        make_http(script, clock).request("GET", "https://api.test/x")


def test_client_errors_are_returned_without_retry() -> None:
    clock = FakeClock()
    script = Script(httpx.Response(404))
    assert make_http(script, clock).request("GET", "https://api.test/x").status_code == 404
    assert clock.slept == []


def test_backoff_grows_and_is_capped() -> None:
    policy = RetryPolicy(base_delay=1, max_delay=5, rng=random.Random(1))
    for attempt in range(6):
        assert 0 <= policy.delay(attempt, None) <= min(5, 2**attempt)
