"""Fake providers for search and find tests. No network."""

from ersatz.providers.base import Capability, ParametricQuery, ProviderRecord
from ersatz.providers.errors import NotSupportedError
from tests.match.parts import source

LDO_CATEGORY = "Voltage Regulators - Linear, Low Drop Out (LDO) Regulators"
OPAMP_CATEGORY = "Instrumentation, Op Amps, Buffer Amps"


def record(
    mpn: str,
    manufacturer: str = "Test Semi",
    category: str = LDO_CATEGORY,
    package: str = "SOT-23-5",
    lifecycle: str = "Active",
    parameters: dict[str, str] | None = None,
    stock: int = 100,
    provider: str = "digikey",
) -> ProviderRecord:
    return ProviderRecord(
        provider=provider,
        mpn=mpn,
        manufacturer=manufacturer,
        raw_lifecycle=lifecycle,
        raw_last_buy=None,
        raw_category=category,
        raw_package=package,
        raw_parameters={"Supplier Device Package": package, **(parameters or {})},
        description=None,
        datasheet_url=None,
        stock=stock,
        product_url=f"https://example.invalid/{mpn}",
        source=source(mpn),
    )


class FakeProvider:
    def __init__(
        self,
        name: str,
        parts: list[ProviderRecord],
        parametric: bool = True,
        results: list[ProviderRecord] | None = None,
    ) -> None:
        self.name = name
        self.capabilities = frozenset(
            {Capability.GET_PART, Capability.SEARCH_KEYWORD}
            | ({Capability.SEARCH_PARAMETRIC} if parametric else set())
        )
        self._parts = parts
        self._parametric = parametric
        self._results = results if results is not None else parts
        self.queries: list[ParametricQuery | str] = []

    def get_part(self, mpn: str, manufacturer: str | None = None) -> list[ProviderRecord]:
        return [
            r
            for r in self._parts
            if r.mpn == mpn and (manufacturer is None or r.manufacturer == manufacturer)
        ]

    def search_keyword(self, keywords: str, limit: int = 25) -> list[ProviderRecord]:
        self.queries.append(keywords)
        return self._results[:limit]

    def search_parametric(self, query: ParametricQuery) -> list[ProviderRecord]:
        if not self._parametric:
            raise NotSupportedError(self.name, "parametric search is not mapped yet")
        self.queries.append(query)
        return self._results[: query.limit]
