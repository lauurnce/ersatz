"""Source invariants."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ersatz.model import Source, SourceKind, response_id

NOW = datetime(2026, 11, 8, tzinfo=UTC)


def test_from_response_hashes_the_body() -> None:
    source = Source.from_response("digikey", b"{}", NOW)
    assert source.kind is SourceKind.PROVIDER
    assert source.response_id == response_id(b"{}")
    assert len(source.response_id) == 64


def test_provider_source_needs_response_id() -> None:
    with pytest.raises(ValidationError):
        Source(kind=SourceKind.PROVIDER, provider="digikey", retrieved_at=NOW)


def test_datasheet_source_needs_page() -> None:
    with pytest.raises(ValidationError):
        Source(
            kind=SourceKind.DATASHEET,
            url="https://example.com/a.pdf",
            sha256="ab",
            retrieved_at=NOW,
        )


def test_source_is_frozen() -> None:
    source = Source.from_response("digikey", b"{}", NOW)
    with pytest.raises(ValidationError):
        source.provider = "other"  # type: ignore[misc]
