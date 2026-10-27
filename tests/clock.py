"""A manual clock for tests that involve time."""

from datetime import UTC, datetime, timedelta


class FakeClock:
    def __init__(self, start: datetime = datetime(2026, 11, 8, tzinfo=UTC)) -> None:
        self.now = start
        self.slept: list[float] = []

    def __call__(self) -> datetime:
        return self.now

    def monotonic(self) -> float:
        return self.now.timestamp()

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.advance(seconds)

    def advance(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)
