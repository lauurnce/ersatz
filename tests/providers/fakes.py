"""Scripted HTTP transport and helpers for provider tests."""

import json
from collections.abc import Callable
from pathlib import Path

import httpx

from ersatz.budget import RequestBudget
from ersatz.cache import SqliteCache
from ersatz.providers.digikey import DigiKeyProvider, TokenManager
from ersatz.providers.http import HttpClient, RetryPolicy
from ersatz.providers.ratelimit import TokenBucket
from tests.clock import FakeClock

FIXTURES = Path(__file__).parent.parent / "fixtures" / "digikey"

Handler = Callable[[httpx.Request], httpx.Response]


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def json_response(status: int, name: str | None = None, **headers: str) -> httpx.Response:
    content = fixture(name) if name else b"{}"
    return httpx.Response(status, content=content, headers=headers)


class Script:
    """Answers requests in order and remembers what was sent."""

    def __init__(self, *responses: httpx.Response | Exception) -> None:
        self.responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class Router:
    """Answers token requests with the token fixture and API calls from a script."""

    def __init__(self, *api: httpx.Response | Exception) -> None:
        self.api = Script(*api)
        self.token_calls = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/oauth2/token":
            self.token_calls += 1
            body = json.loads(fixture("token.json"))
            body["access_token"] = f"test-token-{self.token_calls}"
            return httpx.Response(200, json=body)
        return self.api(request)


def make_http(handler: Handler, clock: FakeClock, attempts: int = 4) -> HttpClient:
    return HttpClient(
        "digikey",
        TokenBucket(6000, monotonic=clock.monotonic, sleep=clock.sleep),
        retry=RetryPolicy(attempts=attempts, base_delay=1.0),
        transport=httpx.MockTransport(handler),
        sleep=clock.sleep,
    )


def make_digikey(
    handler: Handler,
    clock: FakeClock | None = None,
    daily_limit: int = 100,
    record_dir: Path | None = None,
) -> tuple[DigiKeyProvider, SqliteCache, RequestBudget]:
    clock = clock or FakeClock()
    http = make_http(handler, clock)
    cache = SqliteCache(":memory:", clock=clock)
    budget = RequestBudget(cache, "digikey", daily_limit, clock=clock)
    tokens = TokenManager(
        http, "https://api.test/v1/oauth2/token", "test-id", "test-secret", clock=clock
    )
    provider = DigiKeyProvider(
        http=http,
        tokens=tokens,
        client_id="test-id",
        cache=cache,
        budget=budget,
        base_url="https://api.test",
        clock=clock,
        record_dir=record_dir,
        secrets=("test-id", "test-secret"),
    )
    return provider, cache, budget
