"""Digi-Key Product Information API v4 adapter."""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from ersatz.budget import RequestBudget
from ersatz.cache import Cache, DataKind
from ersatz.model import Source, response_id
from ersatz.providers.base import Capability, ParametricQuery, ProviderRecord
from ersatz.providers.digikey.auth import TokenManager
from ersatz.providers.errors import (
    AuthError,
    NotSupportedError,
    ProviderResponseError,
    QuotaExceededError,
)
from ersatz.providers.http import HttpClient
from ersatz.providers.scrub import scrub_body, scrub_headers

PRODUCTION_URL = "https://api.digikey.com"
SANDBOX_URL = "https://sandbox-api.digikey.com"
NAME = "digikey"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _same(a: str, b: str) -> bool:
    return a.strip().casefold() == b.strip().casefold()


def _deepest_category(category: dict[str, Any] | None) -> str | None:
    name = None
    while category:
        name = category.get("Name") or name
        children = category.get("ChildCategories") or []
        category = children[0] if children else None
    return name


def _absolute(url: str | None) -> str | None:
    if not url:
        return None
    return f"https:{url}" if url.startswith("//") else url


def parse_product(product: dict[str, Any], source: Source) -> ProviderRecord:
    """Map one v4 Product object to a ProviderRecord."""
    try:
        mpn = product["ManufacturerProductNumber"]
        manufacturer = product["Manufacturer"]["Name"]
    except (KeyError, TypeError) as exc:
        raise ProviderResponseError(NAME, "product without part number or manufacturer") from exc
    parameters = {
        str(p["ParameterText"]): str(p["ValueText"])
        for p in product.get("Parameters") or []
        if p.get("ParameterText") and p.get("ValueText") is not None
    }
    status = product.get("ProductStatus") or {}
    description = product.get("Description") or {}
    return ProviderRecord(
        provider=NAME,
        mpn=str(mpn),
        manufacturer=str(manufacturer),
        raw_lifecycle=status.get("Status"),
        raw_last_buy=product.get("DateLastBuyChance"),
        raw_category=_deepest_category(product.get("Category")),
        raw_package=parameters.get("Supplier Device Package") or parameters.get("Package / Case"),
        raw_parameters=parameters,
        description=description.get("ProductDescription"),
        datasheet_url=_absolute(product.get("DatasheetUrl")),
        stock=product.get("QuantityAvailable"),
        product_url=product.get("ProductUrl"),
        source=source.model_copy(update={"url": product.get("ProductUrl")}),
    )


class DigiKeyProvider:
    name = NAME
    # Parametric search needs Digi-Key filter IDs that are only visible in live
    # responses. It is enabled once those IDs are mapped from recordings.
    capabilities = frozenset({Capability.GET_PART, Capability.SEARCH_KEYWORD})

    def __init__(
        self,
        http: HttpClient,
        tokens: TokenManager,
        client_id: str,
        cache: Cache,
        budget: RequestBudget,
        base_url: str = PRODUCTION_URL,
        clock: Callable[[], datetime] = _utcnow,
        record_dir: Path | None = None,
        secrets: tuple[str, ...] = (),
    ) -> None:
        self._http = http
        self._tokens = tokens
        self._client_id = client_id
        self._cache = cache
        self._budget = budget
        self._base = base_url.rstrip("/")
        self._clock = clock
        self._record_dir = record_dir
        self._secrets = secrets

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._tokens.token()}",
            "X-DIGIKEY-Client-Id": self._client_id,
            "X-DIGIKEY-Locale-Site": "US",
            "X-DIGIKEY-Locale-Language": "en",
            "X-DIGIKEY-Locale-Currency": "USD",
            "Accept": "application/json",
        }

    def _send(self, method: str, path: str, body: Any = None) -> httpx.Response:
        url = f"{self._base}{path}"
        response = self._http.request(
            method, url, headers=self._headers(), json=body, before_send=self._budget.spend
        )
        if response.status_code == 401:
            self._tokens.invalidate()
            response = self._http.request(
                method, url, headers=self._headers(), json=body, before_send=self._budget.spend
            )
            if response.status_code == 401:
                raise AuthError(NAME, "API rejected the access token twice; check the app keys")
        self._record(method, path, response)
        return response

    def _record(self, method: str, path: str, response: httpx.Response) -> None:
        if self._record_dir is None:
            return
        body = scrub_body(response.content, self._secrets)
        entry = {
            "method": method,
            "path": path,
            "status": response.status_code,
            "headers": scrub_headers(dict(response.headers)),
            "body": json.loads(body) if response.status_code < 300 else body.decode(),
        }
        folder = self._record_dir / NAME
        folder.mkdir(parents=True, exist_ok=True)
        name = f"{self._clock():%Y%m%dT%H%M%S}-{method}-{response_id(path.encode())[:12]}.json"
        (folder / name).write_text(json.dumps(entry, indent=2, sort_keys=True))

    def _check(self, response: httpx.Response) -> None:
        if response.status_code == 403:
            raise AuthError(NAME, "access denied (HTTP 403); the app may lack this API product")
        if response.status_code == 429:
            raise QuotaExceededError(NAME, "daily or burst limit reached")
        if response.status_code >= 400:
            raise ProviderResponseError(NAME, f"HTTP {response.status_code} from the API")

    def _cached_or_fetch(
        self, kind: DataKind, key: str, method: str, path: str, body: Any = None
    ) -> tuple[bytes, datetime] | None:
        entry = self._cache.get(kind, key)
        if entry is not None:
            return entry.payload, entry.created_at
        response = self._send(method, path, body)
        if response.status_code == 404:
            return None
        self._check(response)
        self._cache.put(kind, key, response.content)
        return response.content, self._clock()

    def get_part(self, mpn: str, manufacturer: str | None = None) -> list[ProviderRecord]:
        """Product details for one part number. Only exact part number matches return."""
        query = mpn.strip()
        if not query:
            return []
        found = self._cached_or_fetch(
            DataKind.PROVIDER_RECORD,
            f"{NAME}:details:{query.casefold()}",
            "GET",
            f"/products/v4/search/{quote(query, safe='')}/productdetails",
        )
        if found is None:
            return []
        raw, retrieved = found
        product = self._load(raw).get("Product")
        if not product:
            return []
        record = parse_product(product, Source.from_response(NAME, raw, retrieved))
        if not _same(record.mpn, query):
            return []
        if manufacturer is not None and not _same(record.manufacturer, manufacturer):
            return []
        return [record]

    def search_keyword(self, keywords: str, limit: int = 25) -> list[ProviderRecord]:
        body = {"Keywords": keywords, "Limit": limit, "Offset": 0}
        found = self._cached_or_fetch(
            DataKind.SEARCH_RESULT,
            f"{NAME}:keyword:{limit}:{keywords.casefold()}",
            "POST",
            "/products/v4/search/keyword",
            body,
        )
        if found is None:
            return []
        raw, retrieved = found
        source = Source.from_response(NAME, raw, retrieved)
        return [parse_product(p, source) for p in self._load(raw).get("Products") or []]

    def search_parametric(self, query: ParametricQuery) -> list[ProviderRecord]:
        raise NotSupportedError(NAME, "parametric search is not mapped yet")

    @staticmethod
    def _load(raw: bytes) -> dict[str, Any]:
        try:
            data = json.loads(raw)
        except ValueError as exc:
            raise ProviderResponseError(NAME, "response is not JSON") from exc
        if not isinstance(data, dict):
            raise ProviderResponseError(NAME, "response is not a JSON object")
        return data
