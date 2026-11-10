"""Local citation check (D-021).

A value is kept only when its quote appears on the cited page and every
number it reports appears inside the quote. Comparison runs after Unicode
normalization, dash and micro sign unification, whitespace collapsing and
case folding. Everything dropped is listed with a reason; nothing dropped
is ever shown.
"""

import re
import unicodedata
from typing import Literal

from pydantic import BaseModel

from ersatz.datasheets.pages import PageText
from ersatz.datasheets.schema import (
    CATEGORY_FEATURES,
    MAX_QUOTE_CHARS,
    Cited,
    RawExtraction,
    RawFeature,
    RawPackage,
    RawParameter,
    RawPin,
    RawPinout,
)
from ersatz.model.category import Category
from ersatz.model.parameter import CATEGORY_PARAMS

Kind = Literal["parameter", "package", "pin", "feature"]


class Dropped(BaseModel, frozen=True):
    kind: Kind
    name: str
    page: int | None
    reason: str


class VerifiedPinout(BaseModel, frozen=True):
    package: str
    pins: tuple[RawPin, ...]
    complete: bool  # False when one or more pins were dropped


class VerifiedExtraction(BaseModel, frozen=True):
    parameters: tuple[RawParameter, ...]
    packages: tuple[RawPackage, ...]
    pinouts: tuple[VerifiedPinout, ...]
    features: tuple[RawFeature, ...]
    dropped: tuple[Dropped, ...]


def normalize(text: str) -> str:
    s = unicodedata.normalize("NFKC", text)
    s = re.sub(r"[\u00b5\u03bc]", "u", s)
    s = re.sub(r"[\u2010-\u2014\u2212]", "-", s)
    return re.sub(r"\s+", " ", s).strip().casefold()


def number_in(value: str, quote: str) -> bool:
    """True when `value` appears in the normalized quote as a whole number."""
    candidates = {normalize(value)}
    candidates.add(re.sub(r"^[+\u00b1]", "", normalize(value)))
    for candidate in candidates:
        if candidate and re.search(rf"(?<![\d.]){re.escape(candidate)}(?!\d)", quote):
            return True
    return False


def _compact(text: str) -> str:
    return re.sub(r"[^0-9a-z]", "", normalize(text))


class _Checker:
    def __init__(self, pages: list[PageText], sent: list[int] | None) -> None:
        self.text = {p.page: normalize(p.text) for p in pages}
        self.sent = set(sent) if sent is not None else set(self.text)
        self.dropped: list[Dropped] = []

    def drop(self, kind: Kind, name: str, page: int | None, reason: str) -> None:
        self.dropped.append(Dropped(kind=kind, name=name, page=page, reason=reason))

    def cited(self, kind: Kind, name: str, item: Cited) -> str | None:
        """Return the normalized quote if the citation holds, else drop."""
        if item.page is None or not item.quote or not item.quote.strip():
            self.drop(kind, name, item.page, "no citation")
            return None
        if item.page not in self.sent:
            self.drop(kind, name, item.page, f"page {item.page} was not sent")
            return None
        quote = normalize(item.quote)
        if len(quote) > MAX_QUOTE_CHARS:
            self.drop(kind, name, item.page, f"quote longer than {MAX_QUOTE_CHARS} characters")
            return None
        if quote not in self.text[item.page]:
            self.drop(kind, name, item.page, f"quote not found on page {item.page}")
            return None
        return quote

    def parameter(self, p: RawParameter, allowed: set[str]) -> bool:
        if p.name not in allowed:
            self.drop("parameter", p.name, p.page, "not a parameter of this category")
            return False
        values = [v for v in (p.min, p.typ, p.max) if v is not None and v.strip()]
        if not values:
            self.drop("parameter", p.name, p.page, "no value")
            return False
        quote = self.cited("parameter", p.name, p)
        if quote is None:
            return False
        for value in values:
            if not number_in(value, quote):
                self.drop("parameter", p.name, p.page, f"value {value!r} not in quote")
                return False
        return True

    def package(self, p: RawPackage) -> bool:
        quote = self.cited("package", p.name, p)
        if quote is None:
            return False
        if _compact(p.name) not in _compact(quote):
            self.drop("package", p.name, p.page, "package name not in quote")
            return False
        return True

    def pin(self, package: str, pin: RawPin) -> bool:
        name = f"{package} pin {pin.number}"
        quote = self.cited("pin", name, pin)
        if quote is None:
            return False
        if not number_in(pin.number, quote) and normalize(pin.number) not in quote:
            self.drop("pin", name, pin.page, "pin number not in quote")
            return False
        return True

    def pinout(self, pinout: RawPinout) -> VerifiedPinout | None:
        kept = tuple(pin for pin in pinout.pins if self.pin(pinout.package, pin))
        if not kept:
            return None
        return VerifiedPinout(
            package=pinout.package, pins=kept, complete=len(kept) == len(pinout.pins)
        )

    def feature(self, f: RawFeature, allowed: set[str]) -> bool:
        if f.name not in allowed:
            self.drop("feature", f.name, f.page, "not a feature of this category")
            return False
        return self.cited("feature", f.name, f) is not None


def verify_quotes(
    raw: RawExtraction,
    pages: list[PageText],
    category: Category,
    sent: list[int] | None = None,
) -> VerifiedExtraction:
    """Keep only values whose citation checks out against the page text."""
    check = _Checker(pages, sent)
    params = {p.value for p in CATEGORY_PARAMS[category]}
    features = {f.value for f in CATEGORY_FEATURES[category]}
    pinouts = (check.pinout(p) for p in raw.pinouts)
    return VerifiedExtraction(
        parameters=tuple(p for p in raw.parameters if check.parameter(p, params)),
        packages=tuple(p for p in raw.packages if check.package(p)),
        pinouts=tuple(p for p in pinouts if p is not None),
        features=tuple(f for f in raw.features if check.feature(f, features)),
        dropped=tuple(check.dropped),
    )
