"""Serve a synthetic Digi-Key catalog through the real adapter. No network."""

import json
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import unquote

import httpx
import pytest

from ersatz.settings import get_settings
from tests.providers.fakes import FIXTURES, fixture, make_digikey


class CatalogRouter:
    """Product details by part number, keyword search over the whole catalog."""

    def __init__(self, name: str = "catalog_ldo50.json") -> None:
        products = json.loads((FIXTURES / name).read_text())["Products"]
        self.products = {p["ManufacturerProductNumber"].casefold(): p for p in products}
        self.calls: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.calls.append(f"{request.method} {path}")
        if path == "/v1/oauth2/token":
            return httpx.Response(200, content=fixture("token.json"))
        if path.endswith("/productdetails"):
            mpn = unquote(path.split("/")[-2]).casefold()
            product = self.products.get(mpn)
            if product is None:
                return httpx.Response(404, content=fixture("error_404.json"))
            return httpx.Response(200, json={"Product": product})
        if path.endswith("/search/keyword"):
            products = list(self.products.values())
            return httpx.Response(200, json={"ProductsCount": len(products), "Products": products})
        return httpx.Response(404, content=fixture("error_404.json"))


@pytest.fixture
def catalog(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[CatalogRouter]:
    router = CatalogRouter()
    provider, _, _ = make_digikey(router)
    monkeypatch.setattr("ersatz.cli.output.build_providers", lambda *a, **k: [provider])
    monkeypatch.setenv("ERSATZ_CACHE_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield router
    get_settings.cache_clear()
