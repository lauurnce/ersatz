"""Table of real-world parameter strings, in the forms distributors and datasheets print."""

import math

import pytest

from ersatz.normalize.units import ParsedValue, Slot, UnitParseError, parse_value

N = None

# text, canonical unit, default slot, expected (min, typ, max), expected conditions
CASES: list[
    tuple[str, str, Slot, tuple[float | None, float | None, float | None], dict[str, str]]
] = [
    # Prompt examples
    ("1.5 µA", "A", "typ", (N, 1.5e-6, N), {}),
    ("1.5uA typ", "A", "max", (N, 1.5e-6, N), {}),
    ("200mV @ 150mA", "V", "max", (N, N, 0.2), {"I": "0.15 A"}),
    ("2.5V ~ 5.5V", "V", "typ", (2.5, N, 5.5), {}),
    # Micro sign variants: U+00B5, U+03BC and u
    ("1.5\u00b5A", "A", "typ", (N, 1.5e-6, N), {}),
    ("1.5 μA", "A", "typ", (N, 1.5e-6, N), {}),
    ("75uA", "A", "typ", (N, 75e-6, N), {}),
    # Distributor style, unit glued to the number
    ("15V", "V", "max", (N, N, 15.0), {}),
    ("3.3V", "V", "typ", (N, 3.3, N), {}),
    ("500mA", "A", "max", (N, N, 0.5), {}),
    ("1.2V @ 500mA", "V", "max", (N, N, 1.2), {"I": "0.5 A"}),
    ("0.35V @ 300mA", "V", "max", (N, N, 0.35), {"I": "0.3 A"}),
    ("60dB (120Hz)", "dB", "typ", (N, 60.0, N), {"f": "120 Hz"}),
    ("-40°C ~ 125°C (TJ)", "degC", "typ", (-40.0, N, 125.0), {"note": "TJ"}),
    ("1 MHz", "Hz", "typ", (N, 1e6, N), {}),
    ("4.5MHz", "Hz", "typ", (N, 4.5e6, N), {}),
    ("0.6V/µs", "V/s", "typ", (N, 6e5, N), {}),
    ("20 V/us", "V/s", "typ", (N, 2e7, N), {}),
    ("45 pA", "A", "typ", (N, 45e-12, N), {}),
    ("2 nA", "A", "typ", (N, 2e-9, N), {}),
    ("3 mV", "V", "typ", (N, 3e-3, N), {}),
    ("250 µV", "V", "typ", (N, 250e-6, N), {}),
    ("2", "", "typ", (N, 2.0, N), {}),
    ("2.7V ~ 36V, ±1.35V ~ ±18V", "V", "typ", (2.7, N, 36.0), {"alternative": "±1.35V ~ ±18V"}),
    ("±1.35V ~ ±18V", "V", "typ", (1.35, N, 18.0), {"supply": "split"}),
    ("1.8 V ~ 5.5 V", "V", "typ", (1.8, N, 5.5), {}),
    # Datasheet style
    ("1.2 to 3.3 V", "V", "typ", (1.2, N, 3.3), {}),
    ("1.2-3.3 V", "V", "typ", (1.2, N, 3.3), {}),
    ("1.2 \u2013 3.3 V", "V", "typ", (1.2, N, 3.3), {}),
    ("-40 to 125 °C", "degC", "typ", (-40.0, N, 125.0), {}),
    ("±2%", "percent", "typ", (-2.0, N, 2.0), {}),
    ("± 1.5 %", "percent", "typ", (-1.5, N, 1.5), {}),
    ("±0.5 mV", "V", "max", (-5e-4, N, 5e-4), {}),
    ("10 nV/√Hz", "V/Hz**0.5", "typ", (N, 1e-8, N), {}),
    ("12 nV/rtHz", "V/Hz**0.5", "typ", (N, 12e-9, N), {}),
    ("8 nV/sqrt(Hz)", "V/Hz**0.5", "typ", (N, 8e-9, N), {}),
    ("max 2 mA", "A", "typ", (N, N, 2e-3), {}),
    ("2 mA (max)", "A", "typ", (N, N, 2e-3), {}),
    ("2.7 V min", "V", "typ", (2.7, N, N), {}),
    ("150 mV typ @ 100 mA, 25 °C", "V", "max", (N, 0.15, N), {"I": "0.1 A", "T": "25 degC"}),
    ("1 µA @ VIN = 5 V", "A", "typ", (N, 1e-6, N), {"note": "VIN = 5 V"}),
    ("0.1 µF", "F", "typ", (N, 1e-7, N), {}),
    ("1 Ω", "ohm", "typ", (N, 1.0, N), {}),
    ("2.2 kΩ", "ohm", "typ", (N, 2200.0, N), {}),
    ("5e-3 A", "A", "typ", (N, 5e-3, N), {}),
    (".5 mA", "A", "typ", (N, 5e-4, N), {}),
]

REJECTED = [
    ("2 MV", "V"),  # megavolt, not millivolt
    ("5 mA", "V"),  # wrong dimension
    ("1 a", "A"),  # "a" is a year in pint
    ("15", "V"),  # no unit for a dimensional parameter
    ("Adjustable", "V"),
    ("-", "V"),
    ("", "A"),
    ("1.5 typ max uA", "A"),  # conflicting qualifiers
    ("5V ~ 2V", "V"),  # backwards range
    ("75dB ~ 45dB (100Hz ~ 1MHz)", "dB"),  # backwards range with conditions
    ("1.25 V ±1%", "V"),  # value with tolerance: rejected, not guessed
]


def _close(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return a is b
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-18)


def test_table_has_at_least_40_strings() -> None:
    assert len(CASES) + len(REJECTED) >= 40
    assert len({c[0] for c in CASES}) == len(CASES)


@pytest.mark.parametrize(("text", "unit", "slot", "expected", "conditions"), CASES)
def test_parses(
    text: str,
    unit: str,
    slot: Slot,
    expected: tuple[float | None, float | None, float | None],
    conditions: dict[str, str],
) -> None:
    parsed: ParsedValue = parse_value(text, unit, slot)
    assert all(
        _close(a, b) for a, b in zip((parsed.min, parsed.typ, parsed.max), expected, strict=True)
    ), parsed
    assert parsed.conditions == conditions
    assert parsed.unit == unit


@pytest.mark.parametrize(("text", "unit"), REJECTED)
def test_rejects(text: str, unit: str) -> None:
    with pytest.raises(UnitParseError):
        parse_value(text, unit)


def test_quantity_returns_pint_value() -> None:
    q = parse_value("200mV @ 150mA", "V").quantity("typ")
    assert q is not None
    assert str(q.units) == "volt"
    assert q.magnitude == pytest.approx(0.2)
    assert parse_value("200mV", "V").quantity("max") is None
