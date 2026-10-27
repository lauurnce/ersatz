"""Build configured providers from settings."""

from pathlib import Path

from ersatz.budget import RequestBudget
from ersatz.cache import Cache
from ersatz.providers.digikey import (
    PRODUCTION_URL,
    SANDBOX_URL,
    DigiKeyProvider,
    TokenManager,
)
from ersatz.providers.http import HttpClient
from ersatz.providers.ratelimit import TokenBucket
from ersatz.settings import Settings

# 900 of Digi-Key's 1,000 daily calls, and under its 120 per minute limit.
DIGIKEY_DAILY_BUDGET = 900
DIGIKEY_PER_MINUTE = 100


def build_digikey(settings: Settings, cache: Cache, record: bool = False) -> DigiKeyProvider:
    secret = settings.digikey_client_secret.get_secret_value()
    base = SANDBOX_URL if settings.digikey_use_sandbox else PRODUCTION_URL
    http = HttpClient("digikey", TokenBucket(DIGIKEY_PER_MINUTE))
    tokens = TokenManager(http, f"{base}/v1/oauth2/token", settings.digikey_client_id, secret)
    return DigiKeyProvider(
        http=http,
        tokens=tokens,
        client_id=settings.digikey_client_id,
        cache=cache,
        budget=RequestBudget(cache, "digikey", DIGIKEY_DAILY_BUDGET),
        base_url=base,
        record_dir=Path(settings.ersatz_cache_dir) / "recordings" if record else None,
        secrets=(settings.digikey_client_id, secret),
    )
