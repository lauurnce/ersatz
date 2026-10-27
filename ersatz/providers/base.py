"""Provider protocol and the record every adapter returns."""

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel

from ersatz.model import Category, Source


class Capability(StrEnum):
    GET_PART = "get_part"
    SEARCH_PARAMETRIC = "search_parametric"
    SEARCH_KEYWORD = "search_keyword"


class ProviderRecord(BaseModel, frozen=True):
    """One product as a provider returned it. Strings are kept as received."""

    provider: str
    mpn: str
    manufacturer: str
    raw_lifecycle: str | None
    raw_last_buy: str | None
    raw_category: str | None
    raw_package: str | None
    raw_parameters: dict[str, str]
    description: str | None
    datasheet_url: str | None
    stock: int | None
    product_url: str | None
    source: Source


class ParametricQuery(BaseModel, frozen=True):
    category: Category
    package_groups: tuple[str, ...] = ()
    ranges: dict[str, tuple[float | None, float | None]] = {}
    in_stock_only: bool = False
    limit: int = 50


class Provider(Protocol):
    name: str
    capabilities: frozenset[Capability]

    def get_part(self, mpn: str, manufacturer: str | None = None) -> list[ProviderRecord]:
        """Return records whose part number matches exactly. Empty means not found."""
        ...

    def search_keyword(self, keywords: str, limit: int = 25) -> list[ProviderRecord]: ...

    def search_parametric(self, query: ParametricQuery) -> list[ProviderRecord]: ...
