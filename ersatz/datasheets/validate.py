"""Deterministic checks after quote verification (DOMAIN.md section 6).

1. Units: every value is parsed with ersatz.normalize.units. A value that
   does not parse in the parameter's unit is dropped.
2. Ranges: a value outside the plausible window for its parameter is kept
   but marked LOW confidence (EXT-02).
3. Cross-field rules: a field that breaks a rule is marked LOW (EXT-03 to
   EXT-09). Nothing here raises a value to HIGH that verification dropped.
"""

import math
import re
from collections.abc import Iterable
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ValidationError

from ersatz.datasheets.schema import OTHER_PIN, Cited, RawFeature, RawParameter
from ersatz.datasheets.verify import Dropped, VerifiedExtraction, VerifiedPinout
from ersatz.model.category import Category
from ersatz.model.package import Package, Pin, PinFunction, Pinout
from ersatz.model.parameter import UNITS, Parameter, ParamName
from ersatz.model.source import Source, SourceKind
from ersatz.normalize.packages import package_group
from ersatz.normalize.units import UnitParseError, parse_value


class Confidence(StrEnum):
    HIGH = "HIGH"
    LOW = "LOW"


class DatasheetRef(BaseModel, frozen=True):
    url: str
    sha256: str
    revision: str | None
    fetched_at: datetime

    def source(self, page: int, quote: str | None) -> Source:
        return Source(
            kind=SourceKind.DATASHEET,
            retrieved_at=self.fetched_at,
            url=self.url,
            sha256=self.sha256,
            revision=self.revision,
            page=page,
            quote=quote,
        )


class ExtractedParameter(BaseModel, frozen=True):
    parameter: Parameter
    variant: str | None
    confidence: Confidence
    issues: tuple[str, ...]


class ExtractedFeature(BaseModel, frozen=True):
    name: str
    value: bool
    source: Source


class ExtractedPinout(BaseModel, frozen=True):
    package: str
    pinout: Pinout
    confidence: Confidence
    issues: tuple[str, ...]


class Extraction(BaseModel, frozen=True):
    category: Category
    datasheet: DatasheetRef
    parameters: tuple[ExtractedParameter, ...]
    packages: tuple[Package, ...]
    pinouts: tuple[ExtractedPinout, ...]
    features: tuple[ExtractedFeature, ...]
    dropped: tuple[Dropped, ...]

    def values(self, name: ParamName) -> list[ExtractedParameter]:
        return [p for p in self.parameters if p.parameter.name is name]


# EXT-02 plausible windows in canonical units, compared on magnitude.
# PROPOSED sanity bounds for v0.1 LDOs and op-amps, not limits from a source.
RANGES: dict[ParamName, tuple[float, float]] = {
    ParamName.VIN: (0.5, 100),
    ParamName.VIN_ABS_MAX: (1, 120),
    ParamName.VOUT: (0.5, 60),
    ParamName.VREF: (0.2, 5),
    ParamName.VOUT_ACCURACY: (0, 10),
    ParamName.IOUT: (1e-3, 10),
    ParamName.DROPOUT: (0, 5),
    ParamName.IQ: (0, 0.05),
    ParamName.ISHDN: (0, 1e-3),
    ParamName.PSRR: (0, 120),
    ParamName.COUT_MIN: (0, 1e-3),
    ParamName.COUT_ESR: (0, 100),
    ParamName.CHANNELS: (1, 4),
    ParamName.VSUPPLY: (0.5, 60),
    ParamName.GBW: (1e3, 1e10),
    ParamName.SLEW_RATE: (1e3, 1e10),
    ParamName.VOS: (0, 0.1),
    ParamName.IBIAS: (0, 1e-5),
    ParamName.VNOISE: (1e-10, 1e-5),
    ParamName.IQ_PER_CHANNEL: (0, 0.05),
    ParamName.MIN_STABLE_GAIN: (1, 100),
    ParamName.TJ: (-65, 200),
}

_CURRENT = re.compile(r"\d\s*[munpf\u00b5\u03bc]?A\b")

_DIMENSIONLESS = {ParamName.CHANNELS, ParamName.MIN_STABLE_GAIN}


def _page(item: Cited) -> int:
    """Verification keeps cited values only; a missing page is a bug."""
    if item.page is None:
        raise ValueError("value reached validation without a page")
    return item.page


def _parse(raw: RawParameter) -> tuple[float | None, float | None, float | None, dict[str, str]]:
    """Parse each column into the canonical unit. Raises UnitParseError."""
    name = ParamName(raw.name)
    unit = UNITS[name]
    slots: dict[str, float | None] = {"min": None, "typ": None, "max": None}
    conditions: dict[str, str] = {}
    for slot in ("min", "typ", "max"):
        text = getattr(raw, slot)
        if text is None or not text.strip():
            continue
        printed_unit = "" if name in _DIMENSIONLESS else raw.unit
        parsed = parse_value(f"{text} {printed_unit}".strip(), unit, slot)
        conditions.update(parsed.conditions)
        if parsed.min is not None and parsed.max is not None and parsed.typ is None:
            if parsed.min == -parsed.max:  # a tolerance such as "±3": keep the magnitude
                slots[slot] = parsed.max
            else:  # a range printed in one column
                slots["min"] = parsed.min if slots["min"] is None else slots["min"]
                slots["max"] = parsed.max
            continue
        value = next(v for v in (parsed.min, parsed.typ, parsed.max) if v is not None)
        slots[slot] = value
    if conditions.get("supply") == "split" and name is ParamName.VSUPPLY:
        slots = {k: (2 * v if v is not None else None) for k, v in slots.items()}
        conditions["supply"] = "split, converted to total span"
    return slots["min"], slots["typ"], slots["max"], conditions


def _out_of_range(p: Parameter) -> str | None:
    low, high = RANGES[p.name]
    for value in (p.min, p.typ, p.max):
        if value is None:
            continue
        magnitude = value if p.name is ParamName.TJ else abs(value)
        if not low <= magnitude <= high or math.isnan(magnitude):
            return f"EXT-02: {value:g} {p.unit} is outside the plausible range {low:g} to {high:g}"
    return None


def _parameters(
    raws: Iterable[RawParameter], ref: DatasheetRef, dropped: list[Dropped]
) -> list[tuple[Parameter, str | None, list[str]]]:
    out: list[tuple[Parameter, str | None, list[str]]] = []
    for raw in raws:
        try:
            low, typ, high, parsed = _parse(raw)
            conditions = {**parsed, "text": raw.conditions} if raw.conditions else parsed
            parameter = Parameter(
                name=ParamName(raw.name),
                min=low,
                typ=typ,
                max=high,
                unit=UNITS[ParamName(raw.name)],
                conditions=conditions,
                source=ref.source(_page(raw), raw.quote),
            )
        except (UnitParseError, ValidationError, ValueError) as exc:
            reason = exc.errors()[0]["msg"] if isinstance(exc, ValidationError) else str(exc)
            dropped.append(Dropped(kind="parameter", name=raw.name, page=raw.page, reason=reason))
            continue
        issues = [issue] if (issue := _out_of_range(parameter)) else []
        out.append((parameter, raw.variant, issues))
    return out


def _single(items: list[tuple[Parameter, str | None, list[str]]], name: ParamName) -> list[int]:
    return [i for i, (p, _, _) in enumerate(items) if p.name is name]


def _value(p: Parameter, *order: str) -> float | None:
    for slot in order:
        value: float | None = getattr(p, slot)
        if value is not None:
            return value
    return None


def _cross_field(items: list[tuple[Parameter, str | None, list[str]]], category: Category) -> None:
    def flag(indices: list[int], message: str) -> None:
        for i in indices:
            items[i][2].append(message)

    def one(name: ParamName) -> int | None:
        found = _single(items, name)
        return found[0] if len(found) == 1 else None

    for i, (p, _, _) in enumerate(items):
        if p.name is ParamName.DROPOUT and "I" not in p.conditions:
            text = p.conditions.get("text", "") + " " + p.conditions.get("note", "")
            if not _CURRENT.search(text):
                flag([i], "EXT-05: dropout has no output current condition (LDO-08)")

    if category is Category.LDO:
        vin, vout, drop, iq, ishdn, iout = (
            one(n)
            for n in (
                ParamName.VIN,
                ParamName.VOUT,
                ParamName.DROPOUT,
                ParamName.IQ,
                ParamName.ISHDN,
                ParamName.IOUT,
            )
        )
        get = {k: items[k][0] for k in (vin, vout, drop, iq, ishdn, iout) if k is not None}
        if vin is not None and vout is not None:
            vin_max = _value(get[vin], "max")
            v_out = _value(get[vout], "typ", "max", "min")
            if vin_max is not None and v_out is not None and v_out >= vin_max:
                flag([vin, vout], "EXT-04: output voltage is not below maximum input voltage")
            vin_min = _value(get[vin], "min")
            if drop is not None and vin_min is not None and v_out is not None:
                d = _value(get[drop], "max", "typ")
                if d is not None and vin_min + 1e-9 < v_out + d and vin_min > v_out:
                    flag([vin], "EXT-03: minimum input voltage is below output plus dropout")
        if drop is not None and vout is not None:
            d = _value(get[drop], "max", "typ")
            v_out = _value(get[vout], "typ", "max", "min")
            if d is not None and v_out is not None and not 0 < d < v_out:
                flag([drop], "EXT-05: dropout is not between 0 and the output voltage")
        if iq is not None and iout is not None:
            q = _value(get[iq], "max", "typ")
            rated = _value(get[iout], "max", "typ", "min")
            if q is not None and rated is not None and q >= rated:
                flag([iq, iout], "EXT-06: quiescent current is not below rated output current")
        if ishdn is not None and iq is not None:
            s = _value(get[ishdn], "max", "typ")
            q = _value(get[iq], "max", "typ")
            if s is not None and q is not None and s > q:
                flag([ishdn], "EXT-06: shutdown current is above quiescent current")
    else:
        supply = one(ParamName.VSUPPLY)
        if supply is not None:
            p = items[supply][0]
            if p.min is not None and p.max is not None and not p.min < p.max:
                flag([supply], "EXT-08: supply minimum is not below supply maximum")


def _pinout(vp: VerifiedPinout, ref: DatasheetRef) -> ExtractedPinout:
    issues: list[str] = []
    if not vp.complete:
        issues.append("EXT-09: one or more pins failed quote verification")
    pins: list[Pin] = []
    for raw in vp.pins:
        if raw.function == OTHER_PIN:
            issues.append(f"EXT-09: pin {raw.number} ({raw.name}) has no Ersatz function")
            continue
        pins.append(Pin(number=raw.number, function=PinFunction(raw.function), channel=raw.channel))
    first = vp.pins[0]
    pinout = Pinout(pins=tuple(pins), source=ref.source(_page(first), first.quote))
    confidence = Confidence.LOW if issues else Confidence.HIGH
    return ExtractedPinout(
        package=vp.package, pinout=pinout, confidence=confidence, issues=tuple(issues)
    )


def _feature(raw: RawFeature, ref: DatasheetRef) -> ExtractedFeature:
    return ExtractedFeature(
        name=raw.name, value=raw.value, source=ref.source(_page(raw), raw.quote)
    )


def validate(verified: VerifiedExtraction, category: Category, ref: DatasheetRef) -> Extraction:
    """Parse units, run range and cross-field checks, mark confidence."""
    dropped = list(verified.dropped)
    items = _parameters(verified.parameters, ref, dropped)
    _cross_field(items, category)
    parameters = tuple(
        ExtractedParameter(
            parameter=p,
            variant=variant,
            confidence=Confidence.LOW if issues else Confidence.HIGH,
            issues=tuple(issues),
        )
        for p, variant, issues in items
    )
    packages = []
    for raw in verified.packages:
        match = package_group(raw.name, raw.pin_count)
        packages.append(
            Package(
                raw_name=raw.name,
                group=match.group.name if match.group else None,
                pin_count=match.pin_count if match.pin_count is not None else raw.pin_count,
                body_width_mm=match.body_width_mm,
                source=ref.source(_page(raw), raw.quote),
            )
        )
    return Extraction(
        category=category,
        datasheet=ref,
        parameters=parameters,
        packages=tuple(packages),
        pinouts=tuple(_pinout(p, ref) for p in verified.pinouts),
        features=tuple(_feature(f, ref) for f in verified.features),
        dropped=tuple(dropped),
    )
