"""Candidate generation through provider search.

Parametric search is asked first: same category, same footprint group and
the original's key values. A provider that does not offer it (Digi-Key
until its filter IDs are mapped, D-029) is asked by keyword instead, and
the hard filters do the narrowing. Results from all providers are merged,
deduplicated by manufacturer and part number, and capped. They are never
filtered by manufacturer (decision 15).
"""

from collections.abc import Sequence

from pydantic import BaseModel

from ersatz.model.category import Category
from ersatz.model.parameter import Parameter, ParamName
from ersatz.model.part import Part
from ersatz.providers.base import ParametricQuery, Provider, ProviderRecord
from ersatz.providers.errors import NotSupportedError

DEFAULT_CAP = 25
PROVIDER_LIMIT = 50

# Words a distributor's keyword search understands for each category.
CATEGORY_WORDS = {Category.LDO: "LDO voltage regulator", Category.OPAMP: "operational amplifier"}
CHANNEL_WORDS = {1: "single", 2: "dual", 4: "quad"}


class SearchResult(BaseModel, frozen=True):
    records: tuple[ProviderRecord, ...]
    queries: tuple[str, ...]
    notes: tuple[str, ...]
    found: int  # before deduplication and the cap


def _first(p: Parameter | None, *slots: str) -> float | None:
    if p is None:
        return None
    return next((getattr(p, s) for s in slots if getattr(p, s) is not None), None)


def parametric_query(
    original: Part, category: Category, limit: int = PROVIDER_LIMIT
) -> ParametricQuery:
    """Same category and footprint group, with the original's key values as bounds."""
    params = original.parameters
    ranges: dict[str, tuple[float | None, float | None]] = {}
    if category is Category.LDO:
        vout = _first(params.get(ParamName.VOUT), "typ", "min", "max")
        iout = _first(params.get(ParamName.IOUT), "max", "min", "typ")
        if vout is not None:
            ranges[ParamName.VOUT.value] = (vout, vout)
        if iout is not None:
            ranges[ParamName.IOUT.value] = (iout, None)
    else:
        channels = _first(params.get(ParamName.CHANNELS), "typ", "min", "max")
        if channels is not None:
            ranges[ParamName.CHANNELS.value] = (channels, channels)
    groups = (original.package.group,) if original.package and original.package.group else ()
    return ParametricQuery(category=category, package_groups=groups, ranges=ranges, limit=limit)


def keywords(original: Part, category: Category) -> str:
    """A keyword query built only from the original's own values."""
    words: list[str] = []
    params = original.parameters
    if category is Category.LDO:
        vout = _first(params.get(ParamName.VOUT), "typ", "min", "max")
        if vout is not None:
            words.append(f"{vout:g}V")
    else:
        channels = _first(params.get(ParamName.CHANNELS), "typ", "min", "max")
        if channels is not None and int(channels) in CHANNEL_WORDS:
            words.append(CHANNEL_WORDS[int(channels)])
    words.append(CATEGORY_WORDS[category])
    if original.package is not None:
        words.append(original.package.group or original.package.raw_name)
    return " ".join(words)


def _key(record: ProviderRecord) -> tuple[str, str]:
    return record.manufacturer.casefold().strip(), record.mpn.casefold().strip()


def find_candidates(
    original: Part,
    providers: Sequence[Provider],
    cap: int = DEFAULT_CAP,
    limit: int = PROVIDER_LIMIT,
) -> SearchResult:
    """Ask every provider, merge, drop the original and duplicates, cap."""
    if original.category is None:
        raise ValueError("the original part has no category; cannot search")
    category = original.category.value
    query = parametric_query(original, category, limit)
    text = keywords(original, category)
    records: list[ProviderRecord] = []
    queries: list[str] = []
    notes: list[str] = []
    for provider in providers:
        try:
            found = provider.search_parametric(query)
            queries.append(f"{provider.name} parametric: {query.model_dump_json()}")
        except NotSupportedError:
            found = provider.search_keyword(text, limit)
            queries.append(f"{provider.name} keyword: {text}")
            notes.append(f"{provider.name}: parametric search not available, used keyword search")
        records.extend(found)
    seen = {_key_of(original)}
    unique: list[ProviderRecord] = []
    for record in records:
        key = _key(record)
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    if len(unique) > cap:
        notes.append(f"{len(unique)} unique candidates, kept the first {cap}")
    return SearchResult(
        records=tuple(unique[:cap]),
        queries=tuple(queries),
        notes=tuple(notes),
        found=len(records),
    )


def _key_of(part: Part) -> tuple[str, str]:
    return part.manufacturer.value.casefold().strip(), part.mpn.value.casefold().strip()
