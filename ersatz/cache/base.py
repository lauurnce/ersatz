"""Cache protocol and time-to-live per data kind."""

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Literal, Protocol

from pydantic import BaseModel


class DataKind(StrEnum):
    PROVIDER_RECORD = "provider_record"
    SEARCH_RESULT = "search_result"
    DATASHEET_FILE = "datasheet_file"
    EXTRACTION = "extraction"
    BUDGET = "budget"
    LLM_SPEND = "llm_spend"


# None means the entry never expires. Provider data uses the shortest provider
# limit (24 hours). Datasheets and extractions are keyed by file hash.
DEFAULT_TTL: dict[DataKind, timedelta | None] = {
    DataKind.PROVIDER_RECORD: timedelta(hours=24),
    DataKind.SEARCH_RESULT: timedelta(hours=24),
    DataKind.DATASHEET_FILE: None,
    DataKind.EXTRACTION: None,
    DataKind.BUDGET: timedelta(days=2),
    DataKind.LLM_SPEND: None,
}


class CacheEntry(BaseModel, frozen=True):
    kind: DataKind
    key: str
    payload: bytes
    created_at: datetime
    expires_at: datetime | None


class Cache(Protocol):
    def get(self, kind: DataKind, key: str) -> CacheEntry | None: ...

    def put(
        self,
        kind: DataKind,
        key: str,
        payload: bytes,
        ttl: timedelta | Literal["default"] | None = "default",
    ) -> None: ...

    def purge_expired(self) -> int: ...
