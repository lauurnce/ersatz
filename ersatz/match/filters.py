"""Hard filters: form, fit and lifecycle.

A candidate that fails one of them is excluded and listed with the reason.
UNKNOWN form or fit does not exclude a candidate, but it never passes:
the candidate is kept and flagged (decision 9 in the project brief).
"""

from collections import Counter
from enum import StrEnum
from itertools import permutations

from pydantic import BaseModel

from ersatz.match.profile import PartProfile
from ersatz.match.rules import Verdict
from ersatz.model.lifecycle import Lifecycle
from ersatz.model.package import Pin, PinFunction, Pinout


class Fit(StrEnum):
    DROP_IN = "DROP_IN"
    SAME_PACKAGE_REWIRE = "SAME_PACKAGE_REWIRE"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class FilterResult(BaseModel, frozen=True):
    verdict: Verdict
    reason: str


class FitResult(BaseModel, frozen=True):
    fit: Fit
    reason: str
    notes: tuple[str, ...] = ()


class HardFilters(BaseModel, frozen=True):
    form: FilterResult
    fit: FitResult
    lifecycle: FilterResult

    @property
    def passed(self) -> bool:
        return (
            self.form.verdict is not Verdict.FAIL
            and self.fit.fit is not Fit.NO
            and self.lifecycle.verdict is Verdict.PASS
        )

    @property
    def reasons(self) -> list[str]:
        out = []
        if self.form.verdict is Verdict.FAIL:
            out.append(f"form: {self.form.reason}")
        if self.fit.fit is Fit.NO:
            out.append(f"fit: {self.fit.reason}")
        if self.lifecycle.verdict is not Verdict.PASS:
            out.append(f"lifecycle: {self.lifecycle.reason}")
        return out


def check_form(original: PartProfile, candidate: PartProfile) -> FilterResult:
    """Same footprint-equivalence group (DOMAIN.md section 2)."""
    o, c = original.package, candidate.package
    if o is None or c is None or o.group is None or c.group is None:
        return FilterResult(verdict=Verdict.UNKNOWN, reason="package group unknown on one side")
    if o.group != c.group:
        return FilterResult(verdict=Verdict.FAIL, reason=f"{c.group} is not {o.group}")
    taller = (
        o.height_max_mm is not None
        and c.height_max_mm is not None
        and c.height_max_mm > o.height_max_mm
    )
    if taller:
        return FilterResult(
            verdict=Verdict.WARN,
            reason=f"same group {o.group}, but taller ({c.height_max_mm} mm > "
            f"{o.height_max_mm} mm)",
        )
    return FilterResult(verdict=Verdict.PASS, reason=f"same group {o.group}")


def _pin_count(p: PartProfile) -> int | None:
    if p.package is not None and p.package.pin_count is not None:
        return p.package.pin_count
    if p.pinout is not None:
        return len([pin for pin in p.pinout.pins if pin.number.upper() not in ("TAB", "EP")])
    return None


_NC_LIKE = {PinFunction.NC, PinFunction.NULL}


def _key(pin: Pin, channels: dict[int, int]) -> tuple[str, int | None]:
    function = PinFunction.NC if pin.function in _NC_LIKE else pin.function
    channel = channels.get(pin.channel, pin.channel) if pin.channel is not None else None
    return function.value, channel


def _same_map(o: Pinout, c: Pinout) -> bool:
    """Equal pin maps, allowing identical channels to be swapped."""
    o_map = {pin.number.upper(): _key(pin, {}) for pin in o.pins}
    c_channels = sorted({pin.channel for pin in c.pins if pin.channel is not None})
    for order in permutations(c_channels):
        mapping = dict(zip(c_channels, order, strict=True))
        if {pin.number.upper(): _key(pin, mapping) for pin in c.pins} == o_map:
            return True
    return False


def check_fit(original: PartProfile, candidate: PartProfile) -> FitResult:
    """Pin count and pin function map (decision 14, LDO-16, OPA-13)."""
    o_count, c_count = _pin_count(original), _pin_count(candidate)
    if o_count is not None and c_count is not None and o_count != c_count:
        return FitResult(fit=Fit.NO, reason=f"{c_count} pins, original has {o_count}")
    o, c = original.pinout, candidate.pinout
    if o is None or c is None:
        return FitResult(fit=Fit.UNKNOWN, reason="pinout unknown on one side; never assumed")
    o_tab = {p.number.upper(): p.function for p in o.pins if p.number.upper() in ("TAB", "EP")}
    c_tab = {p.number.upper(): p.function for p in c.pins if p.number.upper() in ("TAB", "EP")}
    for number, function in o_tab.items():
        if number in c_tab and c_tab[number] is not function:
            return FitResult(
                fit=Fit.NO,
                reason=f"LDO-16: {number} is {c_tab[number].value}, original is {function.value}",
            )
    notes = []
    if any(p.function is PinFunction.NULL for p in [*o.pins, *c.pins]):
        notes.append("offset null pins treated as NC-compatible; check the board (WARN)")
    if _same_map(o, c):
        return FitResult(fit=Fit.DROP_IN, reason="same pin function map", notes=tuple(notes))
    o_functions = Counter(_key(p, {})[0] for p in o.pins)
    c_functions = Counter(_key(p, {})[0] for p in c.pins)
    by_number = {p.number.upper(): p.function.value for p in c.pins}
    moved = [
        f"pin {p.number}: {p.function.value} -> {by_number.get(p.number.upper(), 'none')}"
        for p in o.pins
        if by_number.get(p.number.upper()) != p.function.value
    ]
    if o_functions == c_functions:
        return FitResult(
            fit=Fit.SAME_PACKAGE_REWIRE,
            reason="same pin functions on different pins: " + "; ".join(moved),
            notes=tuple(notes),
        )
    return FitResult(fit=Fit.NO, reason="pin functions differ: " + "; ".join(moved))


def check_lifecycle(candidate: PartProfile) -> FilterResult:
    """Only ACTIVE candidates pass. UNKNOWN never passes."""
    status = candidate.lifecycle
    if status is Lifecycle.ACTIVE:
        return FilterResult(verdict=Verdict.PASS, reason="ACTIVE")
    return FilterResult(verdict=Verdict.FAIL, reason=f"{status.value}, not ACTIVE")


def hard_filters(original: PartProfile, candidate: PartProfile) -> HardFilters:
    return HardFilters(
        form=check_form(original, candidate),
        fit=check_fit(original, candidate),
        lifecycle=check_lifecycle(candidate),
    )
