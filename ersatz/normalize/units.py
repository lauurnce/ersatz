"""Parse messy parameter strings into values in SI base units.

Examples: "1.5 µA", "1.5uA typ", "200mV @ 150mA", "2.5V ~ 5.5V", "±2%",
"60dB (120Hz)". Ranges, tolerances, qualifiers and conditions are split by
regular expressions before pint sees the text (DOMAIN.md section 6). Unit
spellings are checked against an allow-list, because case matters: "MV" is
megavolt and "a" is a year.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal

import pint

Slot = Literal["min", "typ", "max"]


class UnitParseError(ValueError):
    """The text is not a value in the expected unit."""


@lru_cache(maxsize=1)
def registry() -> pint.UnitRegistry:
    return pint.UnitRegistry()


# Allowed spellings per canonical unit, after cleaning (micro is "u").
ALLOWED: dict[str, frozenset[str]] = {
    "V": frozenset({"V", "mV", "uV", "nV", "kV"}),
    "A": frozenset({"A", "mA", "uA", "nA", "pA", "fA"}),
    "Hz": frozenset({"Hz", "kHz", "MHz", "GHz"}),
    "V/s": frozenset({"V/s", "V/ms", "V/us", "V/ns", "mV/us", "kV/us"}),
    "V/Hz**0.5": frozenset({"V/Hz**0.5", "uV/Hz**0.5", "nV/Hz**0.5"}),
    "percent": frozenset({"percent"}),
    "dB": frozenset({"dB"}),
    "degC": frozenset({"degC"}),
    "F": frozenset({"F", "mF", "uF", "nF", "pF"}),
    "ohm": frozenset({"ohm", "mohm", "kohm", "Mohm"}),
    "W": frozenset({"W", "mW", "uW"}),
    "": frozenset({""}),
}

_SLOTS: dict[str, Slot] = {"typ": "typ", "max": "max", "min": "min"}

# Units pint does not handle linearly. They are kept as plain numbers.
_PLAIN = frozenset({"dB", "percent", ""})

# Condition keys by canonical unit.
_CONDITION_KEY = {
    "V": "V",
    "A": "I",
    "Hz": "f",
    "degC": "T",
    "F": "C",
    "ohm": "R",
    "W": "P",
}

_NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_VALUE = re.compile(rf"^(?P<pm>±)?\s*(?P<num>{_NUMBER})\s*(?P<unit>.*?)$")
_QUALIFIER = re.compile(
    r"\(?\b(?P<q>typ(?:ical)?|max(?:imum)?|min(?:imum)?)\b\.?\)?", re.IGNORECASE
)
_PAREN = re.compile(r"\(([^()]*)\)\s*$")
_RANGE = re.compile(
    r"^(?P<a>.+?)\s*(?:~|\bto\b|\.\.\.?|…|(?<![\d.][eE])(?<=[\w%])\s*-\s*(?=[±+]?\d|\.\d))\s*(?P<b>.+)$"
)


@dataclass(frozen=True)
class ParsedValue:
    """A parsed value. Numbers are floats in the canonical unit."""

    unit: str
    min: float | None = None
    typ: float | None = None
    max: float | None = None
    conditions: dict[str, str] = field(default_factory=dict)

    def quantity(self, slot: Slot) -> pint.Quantity | None:
        """Return one slot as a pint quantity, or None if it is empty."""
        value: float | None = getattr(self, slot)
        if value is None:
            return None
        return registry().Quantity(value, self.unit or "dimensionless")


def clean(text: str) -> str:
    """Unify code points: micro signs, ohm signs, degree, minus and dashes."""
    s = unicodedata.normalize("NFKC", text).strip()
    s = s.replace("μ", "u").replace("µ", "u")
    s = s.replace("Ω", "ohm").replace("Ω", "ohm")
    s = re.sub(r"[°º]\s*C\b|℃", "degC", s)
    s = re.sub("[\u2010\u2011\u2012\u2013\u2014\u2212]", "-", s)
    s = re.sub(r"/\s*(?:√|sqrt)\s*\(?\s*Hz\s*\)?|/\s*rtHz\b|/\s*Hz\s*\^\s*0?\.5", "/Hz**0.5", s)
    s = re.sub(r"\s*%", " percent", s)
    s = re.sub(r"\s+/\s+", "/", s)
    return re.sub(r"\s+", " ", s).strip()


def _round(value: float) -> float:
    return float(f"{value:.12g}")


def _to_canonical(number: float, unit: str, canonical: str) -> float:
    if unit not in ALLOWED.get(canonical, frozenset()):
        raise UnitParseError(f"unit {unit!r} is not an allowed spelling for {canonical!r}")
    if canonical in _PLAIN:
        return _round(number)
    ureg = registry()
    try:
        magnitude = ureg.Quantity(number, unit).to(canonical).magnitude
    except pint.errors.PintError as exc:
        raise UnitParseError(f"cannot convert {unit!r} to {canonical!r}") from exc
    return _round(float(magnitude))


def _split_value(text: str) -> tuple[bool, float, str]:
    match = _VALUE.match(text.strip())
    if match is None:
        raise UnitParseError(f"no number in {text!r}")
    return bool(match["pm"]), float(match["num"]), match["unit"].strip()


def _canonical_for(unit: str) -> str | None:
    for canonical, spellings in ALLOWED.items():
        if unit in spellings:
            return canonical
    return None


def _condition(text: str, conditions: dict[str, str]) -> None:
    for piece in (p.strip() for p in text.split(",")):
        if not piece:
            continue
        try:
            _, number, unit = _split_value(piece)
            canonical = _canonical_for(unit)
            if canonical is None or canonical in _PLAIN:
                raise UnitParseError(piece)
            key = _CONDITION_KEY.get(canonical, canonical)
            value = _to_canonical(number, unit, canonical)
            conditions[key] = f"{value:.12g} {canonical}"
        except UnitParseError:
            note = conditions.get("note")
            conditions["note"] = f"{note}, {piece}" if note else piece


def parse_value(text: str, unit: str, slot: Slot = "typ") -> ParsedValue:
    """Parse `text` as a value in canonical `unit`.

    `slot` says where a single value goes, for example "max" for a provider
    field named "Voltage - Input (Max)". A qualifier in the text overrides it.
    Raises UnitParseError when the text has no number or the wrong dimension.
    """
    if unit not in ALLOWED:
        raise UnitParseError(f"unknown canonical unit {unit!r}")
    s = clean(text)
    conditions: dict[str, str] = {}

    main, _, cond = s.partition("@")
    if cond:
        _condition(cond, conditions)
    main = main.strip()

    # Alternatives after a comma, such as a split-supply form, are kept as a note.
    if "," in main:
        main, rest = (p.strip() for p in main.split(",", 1))
        conditions["alternative"] = rest

    paren = _PAREN.search(main)
    if paren and not _QUALIFIER.fullmatch(paren.group(0).strip()):
        _condition(paren.group(1), conditions)
        main = main[: paren.start()].strip()

    qualifiers = [m["q"].lower()[:3] for m in _QUALIFIER.finditer(main)]
    main = _QUALIFIER.sub("", main).strip()
    if len(set(qualifiers)) > 1:
        raise UnitParseError(f"conflicting qualifiers in {text!r}")
    if qualifiers:
        slot = _SLOTS[qualifiers[0]]

    if not main:
        raise UnitParseError(f"no value in {text!r}")

    ranged = _RANGE.match(main)
    if ranged:
        pm_a, a, unit_a = _split_value(ranged["a"])
        pm_b, b, unit_b = _split_value(ranged["b"])
        unit_a = unit_a or unit_b
        if pm_a and pm_b:
            conditions["supply"] = "split"
        elif pm_a or pm_b:
            raise UnitParseError(f"mixed tolerance and range in {text!r}")
        low = _to_canonical(a, unit_a, unit)
        high = _to_canonical(b, unit_b, unit)
        if low > high:
            raise UnitParseError(f"range runs backwards in {text!r}")
        return ParsedValue(unit=unit, min=low, max=high, conditions=conditions)

    pm, number, unit_text = _split_value(main)
    value = _to_canonical(number, unit_text, unit)
    if pm:
        return ParsedValue(unit=unit, min=-abs(value), max=abs(value), conditions=conditions)
    return ParsedValue(unit=unit, conditions=conditions, **{slot: value})
