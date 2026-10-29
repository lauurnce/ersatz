"""Fetch datasheet PDFs into the local cache, keyed by content hash.

Files live under <cache_dir>/datasheets/<sha256>.pdf and are never
committed. The cache index maps a URL to the file metadata, so a second
fetch of the same URL does not touch the network.
"""

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx
from pydantic import BaseModel

from ersatz.cache.base import Cache, DataKind

MAX_BYTES = 50 * 1024 * 1024
USER_AGENT = "ersatz-parts"


class DatasheetFetchError(Exception):
    """The URL did not return a PDF."""


class DatasheetFile(BaseModel, frozen=True):
    url: str
    sha256: str
    path: Path
    size: int
    fetched_at: datetime


def _utcnow() -> datetime:
    return datetime.now(UTC)


def store(content: bytes, url: str, cache_dir: Path, fetched_at: datetime) -> DatasheetFile:
    """Write PDF bytes under their SHA-256 and return the file record."""
    if not content.startswith(b"%PDF"):
        raise DatasheetFetchError(f"{url}: content is not a PDF")
    digest = hashlib.sha256(content).hexdigest()
    folder = cache_dir / "datasheets"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{digest}.pdf"
    if not path.exists():
        path.write_bytes(content)
    return DatasheetFile(
        url=url, sha256=digest, path=path, size=len(content), fetched_at=fetched_at
    )


def fetch(
    url: str,
    cache: Cache,
    cache_dir: Path,
    transport: httpx.BaseTransport | None = None,
    clock: Callable[[], datetime] = _utcnow,
) -> DatasheetFile:
    """Return the cached file for `url`, downloading it on the first call."""
    entry = cache.get(DataKind.DATASHEET_FILE, url)
    if entry is not None:
        cached = DatasheetFile.model_validate_json(entry.payload)
        if cached.path.exists():
            return cached
    with httpx.Client(
        transport=transport,
        timeout=60.0,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        try:
            response = client.get(url)
        except httpx.TransportError as exc:
            raise DatasheetFetchError(f"{url}: network error {type(exc).__name__}") from exc
    if response.status_code != 200:
        raise DatasheetFetchError(f"{url}: HTTP {response.status_code}")
    if len(response.content) > MAX_BYTES:
        raise DatasheetFetchError(f"{url}: file is larger than {MAX_BYTES} bytes")
    file = store(response.content, url, cache_dir, clock())
    cache.put(DataKind.DATASHEET_FILE, url, file.model_dump_json().encode())
    return file


def load_local(
    path: Path, url: str, cache_dir: Path, clock: Callable[[], datetime] = _utcnow
) -> DatasheetFile:
    """Register a PDF already on disk, for example one saved by hand."""
    return store(path.read_bytes(), url, cache_dir, clock())
