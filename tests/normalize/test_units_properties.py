"""Property-based round trips for the unit parser."""

import math
from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from ersatz.normalize.units import UnitParseError, parse_value

MICRO = st.sampled_from(["u", "µ", "μ"])
SPACE = st.sampled_from(["", " "])
DECIMALS = st.decimals(min_value=Decimal("0.001"), max_value=Decimal("9999"), places=3)

PREFIXES: dict[str, list[tuple[str, float]]] = {
    "V": [("", 1.0), ("m", 1e-3), ("u", 1e-6), ("n", 1e-9), ("k", 1e3)],
    "A": [("", 1.0), ("m", 1e-3), ("u", 1e-6), ("n", 1e-9), ("p", 1e-12)],
    "Hz": [("", 1.0), ("k", 1e3), ("M", 1e6), ("G", 1e9)],
}
UNITS = st.sampled_from(sorted(PREFIXES))


def _close(a: float | None, b: float) -> bool:
    return a is not None and math.isclose(a, b, rel_tol=1e-9)


@st.composite
def quantity_text(draw: st.DrawFn) -> tuple[str, str, float]:
    unit = draw(UNITS)
    prefix, factor = draw(st.sampled_from(PREFIXES[unit]))
    if prefix == "u":
        prefix = draw(MICRO)
    number = draw(DECIMALS)
    text = f"{number}{draw(SPACE)}{prefix}{unit}"
    return text, unit, float(number) * factor


@given(quantity_text())
def test_single_value_round_trip(case: tuple[str, str, float]) -> None:
    text, unit, expected = case
    assert _close(parse_value(text, unit).typ, expected)


@given(quantity_text(), st.sampled_from(["min", "typ", "max"]))
def test_qualifier_sets_the_slot(case: tuple[str, str, float], slot: str) -> None:
    text, unit, expected = case
    word = {"min": "min", "typ": "typ", "max": "max"}[slot]
    parsed = parse_value(f"{text} {word}", unit)
    assert _close(getattr(parsed, slot), expected)
    assert [getattr(parsed, s) is None for s in ("min", "typ", "max")].count(False) == 1


@given(
    DECIMALS,
    DECIMALS,
    st.sampled_from(["~", " ~ ", " to ", "-", " - ", "..."]),
    st.sampled_from(["V", "mV", "A", "mA", "Hz", "kHz"]),
    st.booleans(),
)
def test_range_round_trip(
    a: Decimal, b: Decimal, sep: str, unit_text: str, unit_on_both: bool
) -> None:
    low, high = sorted((a, b))
    canonical = unit_text.lstrip("mk")
    factor = {"m": 1e-3, "k": 1e3}.get(unit_text[0], 1.0) if unit_text != canonical else 1.0
    left = f"{low}{unit_text}" if unit_on_both else f"{low}"
    parsed = parse_value(f"{left}{sep}{high}{unit_text}", canonical)
    assert _close(parsed.min, float(low) * factor)
    assert _close(parsed.max, float(high) * factor)
    assert parsed.typ is None


@given(quantity_text(), DECIMALS)
def test_current_condition_round_trip(case: tuple[str, str, float], ma: Decimal) -> None:
    text, unit, expected = case
    if unit == "A":
        return
    parsed = parse_value(f"{text} @ {ma}mA", unit)
    assert _close(parsed.typ, expected)
    value, canonical = parsed.conditions["I"].split()
    assert canonical == "A"
    assert math.isclose(float(value), float(ma) * 1e-3, rel_tol=1e-9)


@given(DECIMALS)
def test_tolerance_is_symmetric(number: Decimal) -> None:
    parsed = parse_value(f"±{number}%", "percent")
    assert parsed.min is not None
    assert parsed.max is not None
    assert parsed.min == -parsed.max
    assert _close(parsed.max, float(number))


@given(quantity_text(), UNITS)
def test_wrong_dimension_is_rejected(case: tuple[str, str, float], other: str) -> None:
    text, unit, _ = case
    if other == unit:
        return
    try:
        parse_value(text, other)
    except UnitParseError:
        return
    raise AssertionError(f"{text!r} parsed as {other}")
