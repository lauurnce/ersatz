"""Digi-Key OAuth2 client credentials and token refresh."""

import httpx
import pytest

from ersatz.providers import AuthError, MissingCredentialsError
from ersatz.providers.digikey import TokenManager
from tests.clock import FakeClock
from tests.providers.fakes import Router, Script, make_http

URL = "https://api.test/v1/oauth2/token"


def test_fetches_token_with_client_credentials() -> None:
    clock = FakeClock()
    router = Router()
    tokens = TokenManager(make_http(router, clock), URL, "test-id", "test-secret", clock=clock)
    assert tokens.token() == "test-token-1"
    assert tokens.token() == "test-token-1"
    assert router.token_calls == 1


def test_refreshes_before_expiry() -> None:
    clock = FakeClock()
    router = Router()
    tokens = TokenManager(make_http(router, clock), URL, "test-id", "test-secret", clock=clock)
    tokens.token()
    clock.advance(599 - 61)
    assert tokens.token() == "test-token-1"
    clock.advance(2)
    assert tokens.token() == "test-token-2"


def test_sends_form_fields() -> None:
    clock = FakeClock()
    script = Script(httpx.Response(200, json={"access_token": "t", "expires_in": 599}))
    TokenManager(make_http(script, clock), URL, "test-id", "test-secret", clock=clock).token()
    body = script.requests[0].content.decode()
    assert "grant_type=client_credentials" in body
    assert "client_id=test-id" in body


def test_rejected_credentials_raise_auth_error() -> None:
    clock = FakeClock()
    script = Script(httpx.Response(401, json={"error": "invalid_client"}))
    tokens = TokenManager(make_http(script, clock), URL, "bad", "bad", clock=clock)
    with pytest.raises(AuthError, match="check DIGIKEY_CLIENT_ID"):
        tokens.token()


def test_missing_credentials_fail_before_any_request() -> None:
    clock = FakeClock()
    with pytest.raises(MissingCredentialsError, match=r"must be set in \.env"):
        TokenManager(make_http(Script(), clock), URL, "", "", clock=clock)
