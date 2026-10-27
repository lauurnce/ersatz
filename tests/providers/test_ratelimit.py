"""Token bucket rate limiter."""

from ersatz.providers.ratelimit import TokenBucket
from tests.clock import FakeClock


def test_burst_passes_without_sleeping() -> None:
    clock = FakeClock()
    bucket = TokenBucket(60, burst=3, monotonic=clock.monotonic, sleep=clock.sleep)
    for _ in range(3):
        bucket.acquire()
    assert clock.slept == []


def test_waits_for_next_token_after_burst() -> None:
    clock = FakeClock()
    bucket = TokenBucket(60, burst=1, monotonic=clock.monotonic, sleep=clock.sleep)
    bucket.acquire()
    bucket.acquire()
    assert clock.slept == [1.0]


def test_rate_holds_over_a_minute() -> None:
    clock = FakeClock()
    bucket = TokenBucket(120, burst=1, monotonic=clock.monotonic, sleep=clock.sleep)
    for _ in range(121):
        bucket.acquire()
    assert abs(sum(clock.slept) - 60.0) < 1e-6
