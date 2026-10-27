"""Digi-Key adapter against synthetic fixtures. No test touches the network."""

import json
from datetime import timedelta
from pathlib import Path

import httpx
import pytest

from ersatz.budget import BudgetExhaustedError
from ersatz.model import Category, SourceKind, response_id
from ersatz.providers import (
    AuthError,
    Capability,
    NotSupportedError,
    ParametricQuery,
    QuotaExceededError,
)
from tests.clock import FakeClock
from tests.providers.fakes import Router, fixture, json_response, make_digikey


def test_parses_product_details() -> None:
    provider, _, _ = make_digikey(Router(json_response(200, "productdetails_ldo.json")))
    [record] = provider.get_part("TEST-LDO33")
    assert record.mpn == "TEST-LDO33"
    assert record.manufacturer == "Test Semiconductor"
    assert record.raw_lifecycle == "Active"
    assert record.raw_category == "Voltage Regulators - Linear, Low Drop Out (LDO) Regulators"
    assert record.raw_package == "SOT-223-3"
    assert record.raw_parameters["Voltage - Output (Min/Fixed)"] == "3.3V"
    assert record.datasheet_url == "https://example.com/datasheets/test-ldo33.pdf"
    assert record.stock == 1520


def test_source_traces_to_the_response_body() -> None:
    provider, _, _ = make_digikey(Router(json_response(200, "productdetails_ldo.json")))
    [record] = provider.get_part("TEST-LDO33")
    assert record.source.kind is SourceKind.PROVIDER
    assert record.source.provider == "digikey"
    assert record.source.response_id == response_id(fixture("productdetails_ldo.json"))
    assert record.source.url == record.product_url


def test_obsolete_part_keeps_status_and_last_buy() -> None:
    provider, _, _ = make_digikey(Router(json_response(200, "productdetails_obsolete.json")))
    [record] = provider.get_part("test-opa2")
    assert record.raw_lifecycle == "Obsolete"
    assert record.raw_last_buy == "2025-06-30T00:00:00Z"
    assert record.raw_package is not None
    assert record.raw_package.startswith("8-SOIC")


def test_unknown_mpn_returns_empty() -> None:
    provider, _, _ = make_digikey(Router(json_response(404, "error_404.json")))
    assert provider.get_part("TEST-NOPE") == []


def test_non_exact_match_is_dropped() -> None:
    provider, _, _ = make_digikey(Router(json_response(200, "productdetails_ldo.json")))
    assert provider.get_part("TEST-LDO3") == []


def test_manufacturer_filter() -> None:
    router = Router(json_response(200, "productdetails_ldo.json"))
    provider, _, _ = make_digikey(router)
    assert provider.get_part("TEST-LDO33", manufacturer="Other Co") == []
    assert provider.get_part("TEST-LDO33", manufacturer="test semiconductor") != []


def test_cache_hit_makes_no_request_and_keeps_source() -> None:
    clock = FakeClock()
    router = Router(json_response(200, "productdetails_ldo.json"))
    provider, _, budget = make_digikey(router, clock)
    [first] = provider.get_part("TEST-LDO33")
    clock.advance(3600)
    [second] = provider.get_part("TEST-LDO33")
    assert len(router.api.requests) == 1
    assert budget.used() == 1
    assert second.source == first.source


def test_cache_expiry_refetches() -> None:
    clock = FakeClock()
    router = Router(
        json_response(200, "productdetails_ldo.json"),
        json_response(200, "productdetails_ldo.json"),
    )
    provider, _, _ = make_digikey(router, clock)
    provider.get_part("TEST-LDO33")
    clock.advance(timedelta(hours=24).total_seconds())
    provider.get_part("TEST-LDO33")
    assert len(router.api.requests) == 2


def test_sends_auth_and_locale_headers() -> None:
    router = Router(json_response(200, "productdetails_ldo.json"))
    provider, _, _ = make_digikey(router)
    provider.get_part("TEST-LDO33")
    headers = router.api.requests[0].headers
    assert headers["Authorization"] == "Bearer test-token-1"
    assert headers["X-DIGIKEY-Client-Id"] == "test-id"
    assert headers["X-DIGIKEY-Locale-Site"] == "US"


def test_401_refreshes_token_once() -> None:
    router = Router(httpx.Response(401), json_response(200, "productdetails_ldo.json"))
    provider, _, _ = make_digikey(router)
    assert provider.get_part("TEST-LDO33") != []
    assert router.token_calls == 2
    assert router.api.requests[1].headers["Authorization"] == "Bearer test-token-2"


def test_401_twice_raises_auth_error() -> None:
    provider, _, _ = make_digikey(Router(httpx.Response(401), httpx.Response(401)))
    with pytest.raises(AuthError, match="twice"):
        provider.get_part("TEST-LDO33")


def test_403_raises_auth_error() -> None:
    provider, _, _ = make_digikey(Router(httpx.Response(403)))
    with pytest.raises(AuthError, match="403"):
        provider.get_part("TEST-LDO33")


def test_rate_limited_after_retries_raises_quota_error() -> None:
    provider, _, _ = make_digikey(Router(*[httpx.Response(429) for _ in range(4)]))
    with pytest.raises(QuotaExceededError):
        provider.get_part("TEST-LDO33")


def test_budget_exhaustion_stops_before_sending() -> None:
    router = Router(json_response(200, "productdetails_ldo.json"))
    provider, _, _ = make_digikey(router, daily_limit=0)
    with pytest.raises(BudgetExhaustedError):
        provider.get_part("TEST-LDO33")
    assert router.api.requests == []


def test_keyword_search_parses_products() -> None:
    router = Router(json_response(200, "keyword_search.json"))
    provider, _, _ = make_digikey(router)
    records = provider.search_keyword("TEST-LDO33")
    assert [r.mpn for r in records] == ["TEST-LDO33", "TEST-LDO33-B"]
    assert records[1].raw_lifecycle == "Not For New Designs"
    assert json.loads(router.api.requests[0].content)["Keywords"] == "TEST-LDO33"


def test_parametric_search_is_not_supported_yet() -> None:
    provider, _, _ = make_digikey(Router())
    assert Capability.SEARCH_PARAMETRIC not in provider.capabilities
    with pytest.raises(NotSupportedError):
        provider.search_parametric(ParametricQuery(category=Category.LDO))


def test_recordings_are_scrubbed(tmp_path: Path) -> None:
    router = Router(json_response(200, "productdetails_ldo.json"))
    provider, _, _ = make_digikey(router, record_dir=tmp_path)
    provider.get_part("TEST-LDO33")
    [path] = list((tmp_path / "digikey").iterdir())
    text = path.read_text()
    assert "test-secret" not in text
    assert "test-token" not in text
    assert "TEST-LDO33" in text
