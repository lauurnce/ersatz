"""Sources for model tests."""

from datetime import UTC, datetime

from ersatz.model import Source, SourceKind

NOW = datetime(2026, 11, 9, tzinfo=UTC)
PROVIDER = Source.from_response("digikey", b"{}", NOW)
DATASHEET = Source(
    kind=SourceKind.DATASHEET,
    url="https://example.com/test.pdf",
    sha256="ab" * 32,
    page=4,
    quote="3.3 V",
    retrieved_at=NOW,
)
