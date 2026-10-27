"""Live check against Digi-Key with keys from .env. Run with make smoke, never in CI."""

import os

import pytest

from ersatz.cache import SqliteCache
from ersatz.providers.factory import build_digikey
from ersatz.settings import Settings

pytestmark = [pytest.mark.live, pytest.mark.enable_socket]


@pytest.fixture
def settings() -> Settings:
    if os.environ.get("CI"):
        pytest.skip("live checks never run in CI")
    settings = Settings()
    if not settings.digikey_client_id or not settings.digikey_client_secret.get_secret_value():
        pytest.skip("DIGIKEY_CLIENT_ID and DIGIKEY_CLIENT_SECRET are not set in .env")
    return settings


def test_lookup_returns_sourced_records(settings: Settings) -> None:
    parts = os.environ.get("ERSATZ_SMOKE_PARTS", "").split()
    if not parts:
        pytest.skip("set ERSATZ_SMOKE_PARTS to one or more exact part numbers")
    provider = build_digikey(settings, SqliteCache(settings.ersatz_cache_dir / "ersatz.sqlite"))
    for mpn in parts:
        records = provider.get_part(mpn)
        assert records, f"{mpn} not found"
        assert all(r.source.response_id for r in records)
