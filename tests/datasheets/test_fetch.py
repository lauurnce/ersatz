import hashlib
from pathlib import Path

import httpx
import pytest

from ersatz.cache import SqliteCache
from ersatz.datasheets.fetch import DatasheetFetchError, fetch, load_local
from tests.clock import FakeClock
from tests.datasheets.pdfgen import make_pdf

URL = "https://example.invalid/ds.pdf"
PDF = make_pdf([["TEST-LDO1 datasheet"]])


class Counter:
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.calls = 0
        self.headers: list[httpx.Headers] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        self.headers.append(request.headers)
        return self.response


def test_fetch_stores_file_under_its_hash(tmp_path: Path) -> None:
    handler = Counter(httpx.Response(200, content=PDF))
    cache = SqliteCache(":memory:")
    file = fetch(URL, cache, tmp_path, transport=httpx.MockTransport(handler), clock=FakeClock())
    digest = hashlib.sha256(PDF).hexdigest()
    assert file.sha256 == digest
    assert file.path == tmp_path / "datasheets" / f"{digest}.pdf"
    assert file.path.read_bytes() == PDF
    assert file.size == len(PDF)
    assert handler.headers[0]["User-Agent"] == "ersatz-parts"


def test_second_fetch_uses_the_cache(tmp_path: Path) -> None:
    handler = Counter(httpx.Response(200, content=PDF))
    cache = SqliteCache(":memory:")
    transport = httpx.MockTransport(handler)
    first = fetch(URL, cache, tmp_path, transport=transport)
    second = fetch(URL, cache, tmp_path, transport=transport)
    assert first == second
    assert handler.calls == 1


def test_fetch_again_when_the_cached_file_is_gone(tmp_path: Path) -> None:
    handler = Counter(httpx.Response(200, content=PDF))
    cache = SqliteCache(":memory:")
    transport = httpx.MockTransport(handler)
    fetch(URL, cache, tmp_path, transport=transport).path.unlink()
    fetch(URL, cache, tmp_path, transport=transport)
    assert handler.calls == 2


def test_html_is_rejected(tmp_path: Path) -> None:
    handler = Counter(httpx.Response(200, content=b"<html>login</html>"))
    with pytest.raises(DatasheetFetchError, match="not a PDF"):
        fetch(URL, SqliteCache(":memory:"), tmp_path, transport=httpx.MockTransport(handler))


def test_http_error_is_reported(tmp_path: Path) -> None:
    handler = Counter(httpx.Response(403))
    with pytest.raises(DatasheetFetchError, match="HTTP 403"):
        fetch(URL, SqliteCache(":memory:"), tmp_path, transport=httpx.MockTransport(handler))


def test_network_error_is_reported(tmp_path: Path) -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    with pytest.raises(DatasheetFetchError, match="network error"):
        fetch(URL, SqliteCache(":memory:"), tmp_path, transport=httpx.MockTransport(fail))


def test_load_local_registers_a_file(tmp_path: Path) -> None:
    source = tmp_path / "saved.pdf"
    source.write_bytes(PDF)
    file = load_local(source, URL, tmp_path / "cache")
    assert file.path.read_bytes() == PDF
    assert file.url == URL
