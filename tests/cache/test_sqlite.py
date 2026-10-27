"""SQLite cache hits, expiry and time-to-live per kind."""

from datetime import timedelta
from pathlib import Path

from ersatz.cache import DataKind, SqliteCache
from tests.clock import FakeClock


def make(clock: FakeClock) -> SqliteCache:
    return SqliteCache(":memory:", clock=clock)


def test_hit_returns_payload_and_created_at() -> None:
    clock = FakeClock()
    cache = make(clock)
    cache.put(DataKind.PROVIDER_RECORD, "digikey:TEST-1", b"body")
    entry = cache.get(DataKind.PROVIDER_RECORD, "digikey:TEST-1")
    assert entry is not None
    assert entry.payload == b"body"
    assert entry.created_at == clock.now


def test_miss_for_unknown_key_and_other_kind() -> None:
    cache = make(FakeClock())
    cache.put(DataKind.PROVIDER_RECORD, "k", b"x")
    assert cache.get(DataKind.PROVIDER_RECORD, "other") is None
    assert cache.get(DataKind.SEARCH_RESULT, "k") is None


def test_provider_records_expire_after_24_hours() -> None:
    clock = FakeClock()
    cache = make(clock)
    cache.put(DataKind.PROVIDER_RECORD, "k", b"x")
    clock.advance(timedelta(hours=23, minutes=59).total_seconds())
    assert cache.get(DataKind.PROVIDER_RECORD, "k") is not None
    clock.advance(60)
    assert cache.get(DataKind.PROVIDER_RECORD, "k") is None


def test_search_results_expire_after_24_hours() -> None:
    clock = FakeClock()
    cache = make(clock)
    cache.put(DataKind.SEARCH_RESULT, "q", b"x")
    clock.advance(timedelta(hours=24).total_seconds())
    assert cache.get(DataKind.SEARCH_RESULT, "q") is None


def test_datasheets_never_expire() -> None:
    clock = FakeClock()
    cache = make(clock)
    cache.put(DataKind.DATASHEET_FILE, "sha", b"%PDF")
    clock.advance(timedelta(days=3650).total_seconds())
    entry = cache.get(DataKind.DATASHEET_FILE, "sha")
    assert entry is not None
    assert entry.expires_at is None


def test_explicit_ttl_overrides_default() -> None:
    clock = FakeClock()
    cache = make(clock)
    cache.put(DataKind.DATASHEET_FILE, "sha", b"x", ttl=timedelta(seconds=10))
    clock.advance(10)
    assert cache.get(DataKind.DATASHEET_FILE, "sha") is None


def test_put_replaces_and_purge_removes_expired() -> None:
    clock = FakeClock()
    cache = make(clock)
    cache.put(DataKind.PROVIDER_RECORD, "a", b"1")
    cache.put(DataKind.PROVIDER_RECORD, "a", b"2")
    cache.put(DataKind.DATASHEET_FILE, "b", b"3")
    entry = cache.get(DataKind.PROVIDER_RECORD, "a")
    assert entry is not None
    assert entry.payload == b"2"
    clock.advance(timedelta(days=2).total_seconds())
    assert cache.purge_expired() == 1
    assert cache.get(DataKind.DATASHEET_FILE, "b") is not None


def test_file_cache_persists(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "ersatz.sqlite"
    first = SqliteCache(path)
    first.put(DataKind.DATASHEET_FILE, "sha", b"x")
    first.close()
    assert SqliteCache(path).get(DataKind.DATASHEET_FILE, "sha") is not None
