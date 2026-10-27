"""Where a value came from."""

import hashlib
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, model_validator


class SourceKind(StrEnum):
    PROVIDER = "provider"
    DATASHEET = "datasheet"


class Source(BaseModel, frozen=True):
    """The provider response or datasheet page behind a value."""

    kind: SourceKind
    retrieved_at: datetime
    provider: str | None = None
    response_id: str | None = None
    url: str | None = None
    sha256: str | None = None
    revision: str | None = None
    page: int | None = None
    quote: str | None = None

    @model_validator(mode="after")
    def _check_kind_fields(self) -> "Source":
        if self.kind is SourceKind.PROVIDER and not (self.provider and self.response_id):
            raise ValueError("a provider source needs provider and response_id")
        if self.kind is SourceKind.DATASHEET and not (self.url and self.sha256 and self.page):
            raise ValueError("a datasheet source needs url, sha256 and page")
        return self

    @classmethod
    def from_response(
        cls, provider: str, body: bytes, retrieved_at: datetime, url: str | None = None
    ) -> "Source":
        """Build a provider source whose response_id is the SHA-256 of the raw body."""
        return cls(
            kind=SourceKind.PROVIDER,
            provider=provider,
            response_id=response_id(body),
            retrieved_at=retrieved_at,
            url=url,
        )


def response_id(body: bytes) -> str:
    """Return the SHA-256 hex digest of a raw response body."""
    return hashlib.sha256(body).hexdigest()
