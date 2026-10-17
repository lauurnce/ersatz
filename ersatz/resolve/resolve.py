"""Resolve a part number as entered to provider records.

Order (docs/DOMAIN.md section 6b):
1. The text is cleaned: surrounding whitespace, markdown and punctuation
   are removed and Unicode dashes become "-". Then it is looked up exactly.
2. A Digi-Key packaging code at the end (rules/suffixes.yaml) is removed
   and the rest is looked up exactly.
3. A keyword search may return the same part number plus a listed
   packaging suffix from the listed manufacturer.
Anything else is NOT_FOUND. A close match is never offered.
"""

import re
from collections.abc import Sequence
from enum import StrEnum
from functools import cache

from pydantic import BaseModel

from ersatz.providers.base import Provider, ProviderRecord
from ersatz.providers.errors import NotSupportedError
from ersatz.rules import load


class Status(StrEnum):
    FOUND = "FOUND"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_FOUND = "NOT_FOUND"


class SuffixRule(BaseModel, frozen=True):
    id: str
    status: str
    suffixes: tuple[str, ...]
    note: str
    provider: str | None = None
    manufacturer: str | None = None


class Resolution(BaseModel, frozen=True):
    as_entered: str
    query: str
    status: Status
    records: tuple[ProviderRecord, ...] = ()
    rule: SuffixRule | None = None
    note: str = ""

    @property
    def unverified(self) -> bool:
        return self.rule is not None and self.rule.status == "UNVERIFIED"

    @property
    def record(self) -> ProviderRecord | None:
        return self.records[0] if self.status is Status.FOUND and self.records else None


@cache
def _rules() -> tuple[tuple[SuffixRule, ...], tuple[SuffixRule, ...]]:
    data = load("suffixes")
    dist = tuple(SuffixRule.model_validate(r) for r in data["distributor_part_numbers"])
    pack = tuple(SuffixRule.model_validate(r) for r in data["packaging"])
    return dist, pack


DASHES = "".join(map(chr, [*range(0x2010, 0x2016), 0x2212]))
_EDGE = re.compile(r"^[\s*`'\"(\[{<]+|[\s*`'\")\]}>.,;:!?]+$")


def clean(text: str) -> str:
    """Remove surrounding markup and punctuation; unify dashes. Inner text is kept."""
    s = re.sub("[" + DASHES + "]", "-", text)
    previous = None
    while previous != s:
        previous = s
        s = _EDGE.sub("", s)
    return s


def _same(a: str, b: str) -> bool:
    return a.casefold() == b.casefold()


def _status(records: list[ProviderRecord], manufacturer: str | None) -> Status:
    if manufacturer is None and len({r.manufacturer.casefold() for r in records}) > 1:
        return Status.AMBIGUOUS
    return Status.FOUND


def _lookup(
    mpn: str, providers: Sequence[Provider], manufacturer: str | None
) -> list[ProviderRecord]:
    return [r for p in providers for r in p.get_part(mpn, manufacturer)]


def resolve(
    as_entered: str,
    providers: Sequence[Provider],
    manufacturer: str | None = None,
    distributor_rules: Sequence[SuffixRule] | None = None,
    packaging_rules: Sequence[SuffixRule] | None = None,
) -> Resolution:
    dist_default, pack_default = _rules()
    dist = dist_default if distributor_rules is None else tuple(distributor_rules)
    pack = pack_default if packaging_rules is None else tuple(packaging_rules)
    query = clean(as_entered)
    if not query:
        return Resolution(as_entered=as_entered, query=query, status=Status.NOT_FOUND, note="empty")

    records = _lookup(query, providers, manufacturer)
    if records:
        return Resolution(
            as_entered=as_entered,
            query=query,
            status=_status(records, manufacturer),
            records=tuple(records),
            note="exact match" if query == as_entered else "exact match after cleaning",
        )

    for rule in dist:
        for suffix in rule.suffixes:
            if len(query) > len(suffix) and query.upper().endswith(suffix.upper()):
                base = query[: -len(suffix)]
                found = [
                    r
                    for p in providers
                    if rule.provider in (None, p.name)
                    for r in p.get_part(base, manufacturer)
                ]
                if found:
                    return Resolution(
                        as_entered=as_entered,
                        query=base,
                        status=_status(found, manufacturer),
                        records=tuple(found),
                        rule=rule,
                        note=f"{rule.id}: removed {suffix}",
                    )
                break  # the longest matching code decides; shorter ones are not tried

    variants: list[tuple[ProviderRecord, SuffixRule, str]] = []
    for provider in providers:
        try:
            hits = provider.search_keyword(query, 25)
        except NotSupportedError:
            continue
        for record in hits:
            for rule in pack:
                if rule.manufacturer is None or not _same(rule.manufacturer, record.manufacturer):
                    continue
                if manufacturer is not None and not _same(manufacturer, record.manufacturer):
                    continue
                for suffix in rule.suffixes:
                    if _same(record.mpn, query + suffix):
                        variants.append((record, rule, suffix))
    if variants:
        records_found = [v[0] for v in variants]
        rule = variants[0][1]
        listed = ", ".join(r.mpn for r in records_found)
        return Resolution(
            as_entered=as_entered,
            query=query,
            status=_status(records_found, manufacturer),
            records=tuple(records_found),
            rule=rule,
            note=f"{rule.id}: orderable variants {listed}",
        )
    return Resolution(as_entered=as_entered, query=query, status=Status.NOT_FOUND)
