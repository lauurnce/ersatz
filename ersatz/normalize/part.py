"""Turn a ProviderRecord into a Part.

Every value keeps the provider source it came from. Strings that cannot be
parsed are kept verbatim in Part.unparsed, and nothing is filled in.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from ersatz.model import (
    UNITS,
    Category,
    Package,
    Parameter,
    ParamName,
    Part,
    Source,
    Sourced,
)
from ersatz.normalize.categories import CategoryMatch, map_category
from ersatz.normalize.lifecycle import map_lifecycle
from ersatz.normalize.packages import PackageMatch, package_group
from ersatz.normalize.units import ParsedValue, Slot, UnitParseError, parse_value
from ersatz.providers.base import ProviderRecord
from ersatz.rules import load

# Placeholders providers print when a field has no value.
EMPTY = frozenset({"", "-", "--", "N/A", "*"})

# Provider fields that hold the package name, most specific first.
PACKAGE_FIELDS = {"digikey": ("Supplier Device Package", "Package / Case")}


@dataclass(frozen=True)
class Normalized:
    """The part plus the reasons behind its category and package."""

    part: Part
    category: CategoryMatch
    package: PackageMatch
    notes: tuple[str, ...] = field(default_factory=tuple)


def _date(text: str | None) -> date | None:
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _merge(a: ParsedValue, b: ParsedValue) -> ParsedValue | None:
    """Combine two partial values, or None if they overlap or disagree on conditions."""
    slots: dict[str, float | None] = {}
    for slot in ("min", "typ", "max"):
        x, y = getattr(a, slot), getattr(b, slot)
        if x is not None and y is not None:
            return None
        slots[slot] = x if x is not None else y
    if a.conditions and b.conditions and a.conditions != b.conditions:
        return None
    return ParsedValue(unit=a.unit, conditions=a.conditions or b.conditions, **slots)


def _parameters(
    record: ProviderRecord, category: Category, source: Source
) -> tuple[dict[ParamName, Parameter], dict[str, Sourced[str]], list[str]]:
    rules: dict[str, Any] = (
        load("parameters")["providers"].get(record.provider, {}).get(category.value, {})
    )
    parsed: dict[ParamName, ParsedValue] = {}
    unparsed: dict[str, Sourced[str]] = {}
    notes: list[str] = []
    for field_name, rule in rules.items():
        raw = record.raw_parameters.get(field_name)
        if raw is None or raw.strip() in EMPTY:
            continue
        name = ParamName(rule["param"])
        slot: Slot = rule["slot"]
        try:
            value = parse_value(raw, UNITS[name], slot)
        except UnitParseError as exc:
            unparsed[field_name] = Sourced(value=raw, source=source)
            notes.append(f"{field_name}: {exc}")
            continue
        if name in parsed:
            merged = _merge(parsed[name], value)
            if merged is None:
                unparsed[field_name] = Sourced(value=raw, source=source)
                notes.append(f"{field_name}: overlaps another field for {name}")
                continue
            value = merged
        parsed[name] = value
    parameters: dict[ParamName, Parameter] = {}
    for name, value in parsed.items():
        try:
            parameters[name] = Parameter(
                name=name,
                min=value.min,
                typ=value.typ,
                max=value.max,
                unit=value.unit,
                conditions=value.conditions,
                source=source,
            )
        except ValueError as exc:
            notes.append(f"{name}: {exc}")
    return parameters, unparsed, notes


def normalize(record: ProviderRecord, today: date | None = None) -> Normalized:
    """Normalize one provider record."""
    source = record.source
    cat = map_category(record.provider, record.raw_category, record.raw_parameters)

    names = [
        record.raw_parameters[f]
        for f in PACKAGE_FIELDS.get(record.provider, ())
        if record.raw_parameters.get(f)
    ]
    if not names and record.raw_package:
        names = [record.raw_package]
    raw_package = ", ".join(names)
    pkg = package_group(raw_package)
    package = (
        Package(
            raw_name=raw_package,
            group=pkg.group.name if pkg.group else None,
            pin_count=pkg.pin_count,
            body_width_mm=pkg.body_width_mm,
            height_max_mm=pkg.group.height_max_mm if pkg.group else None,
            source=source,
        )
        if raw_package
        else None
    )

    lifecycle = map_lifecycle(
        record.provider, record.raw_lifecycle, _date(record.raw_last_buy), today
    )
    parameters: dict[ParamName, Parameter] = {}
    unparsed: dict[str, Sourced[str]] = {}
    notes: list[str] = []
    if cat.category is not None:
        parameters, unparsed, notes = _parameters(record, cat.category, source)

    part = Part(
        mpn=Sourced(value=record.mpn, source=source),
        manufacturer=Sourced(value=record.manufacturer, source=source),
        category=Sourced(value=cat.category, source=source) if cat.category else None,
        lifecycle=(Sourced(value=lifecycle, source=source),),
        package=package,
        parameters=parameters,
        datasheet_url=Sourced(value=record.datasheet_url, source=source)
        if record.datasheet_url
        else None,
        stock=(Sourced(value=record.stock, source=source),) if record.stock is not None else (),
        unparsed=unparsed,
    )
    return Normalized(part=part, category=cat, package=pkg, notes=tuple(notes))


__all__ = ["Normalized", "normalize"]
