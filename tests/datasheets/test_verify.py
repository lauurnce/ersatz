from typing import Any

import pytest

from ersatz.datasheets.pages import PageText
from ersatz.datasheets.schema import RawExtraction
from ersatz.datasheets.verify import normalize, number_in, verify_quotes
from ersatz.model import Category

MU = chr(0x00B5)
MINUS = chr(0x2212)

PAGES = [
    PageText(page=1, text="TEST-LDO1 300 mA LDO\nPackage: SOT-23-5", chars=500),
    PageText(
        page=5,
        text=(
            "Electrical Characteristics\n"
            "Dropout Voltage  IOUT = 150 mA   250   350   mV\n"
            f"Quiescent Current  IOUT = 0 mA  1.6  4  {MU}A\n"
            f"Operating temperature {MINUS}40 to 125 C\n"
            "1 VIN Input supply\n2 GND Ground\n"
            "Stable with ceramic output capacitors"
        ),
        chars=500,
    ),
]


def param(**overrides: Any) -> dict[str, Any]:
    base = {
        "name": "dropout",
        "min": None,
        "typ": "250",
        "max": "350",
        "unit": "mV",
        "conditions": "IOUT = 150 mA",
        "variant": None,
        "page": 5,
        "quote": "Dropout Voltage IOUT = 150 mA 250 350 mV",
    }
    return {**base, **overrides}


def run(**fields: Any) -> Any:
    raw = RawExtraction.model_validate(fields)
    return verify_quotes(raw, PAGES, Category.LDO, sent=[1, 5])


def test_matching_quote_with_extra_spaces_is_kept() -> None:
    result = run(parameters=[param()])
    assert len(result.parameters) == 1
    assert result.dropped == ()


def test_micro_sign_and_minus_sign_are_unified() -> None:
    result = run(
        parameters=[
            param(name="iq", typ="1.6", max="4", unit="uA", quote="1.6 4 uA"),
            param(name="tj", min="-40", typ=None, max="125", unit="C", quote="-40 to 125 C"),
        ]
    )
    assert [p.name for p in result.parameters] == ["iq", "tj"]


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"page": None}, "no citation"),
        ({"quote": " "}, "no citation"),
        ({"page": 2}, "page 2 was not sent"),
        ({"page": 1}, "quote not found on page 1"),
        ({"quote": "Dropout Voltage IOUT = 150 mA 250 360 mV"}, "quote not found"),
        ({"max": "35"}, "value '35' not in quote"),
        ({"typ": None, "max": None}, "no value"),
        ({"name": "slew_rate"}, "not a parameter of this category"),
        ({"quote": "x" * 201}, "quote longer than 200"),
    ],
)
def test_bad_citations_are_dropped_with_a_reason(overrides: dict[str, Any], reason: str) -> None:
    result = run(parameters=[param(**overrides)])
    assert result.parameters == ()
    assert reason in result.dropped[0].reason


def test_number_match_needs_whole_numbers() -> None:
    quote = normalize("Dropout 11.2 V and 0.35 V")
    assert number_in("11.2", quote)
    assert not number_in("1.2", quote)
    assert not number_in("0.3", quote)
    assert number_in("+0.35", quote)


def test_packages_need_their_name_in_the_quote() -> None:
    result = run(
        packages=[
            {"name": "SOT-23-5", "pin_count": 5, "page": 1, "quote": "Package: SOT-23-5"},
            {"name": "SOT-89", "pin_count": 3, "page": 1, "quote": "Package: SOT-23-5"},
        ]
    )
    assert [p.name for p in result.packages] == ["SOT-23-5"]
    assert result.dropped[0].reason == "package name not in quote"


def pin(number: str, quote: str) -> dict[str, Any]:
    return {
        "number": number,
        "name": "X",
        "function": "IN",
        "channel": None,
        "page": 5,
        "quote": quote,
    }


def test_pinout_with_a_dropped_pin_is_incomplete() -> None:
    pins = [pin("1", "1 VIN Input supply"), pin("2", "2 GND Ground"), pin("3", "3 VOUT")]
    result = run(pinouts=[{"package": "SOT-23-5", "pins": pins}])
    assert len(result.pinouts[0].pins) == 2
    assert result.pinouts[0].complete is False


def test_pinout_with_no_verified_pin_is_dropped() -> None:
    result = run(pinouts=[{"package": "SOT-23-5", "pins": [pin("4", "1 VIN Input supply")]}])
    assert result.pinouts == ()
    assert result.dropped[0].reason == "pin number not in quote"


def test_features_are_checked() -> None:
    good = {"name": "ceramic_cap_stable", "value": True, "page": 5, "quote": "ceramic output"}
    wrong_kind = {**good, "name": "rail_to_rail_input"}
    result = run(features=[good, wrong_kind])
    assert [f.name for f in result.features] == ["ceramic_cap_stable"]
    assert result.dropped[0].reason == "not a feature of this category"


def test_all_pages_count_as_sent_by_default() -> None:
    raw = RawExtraction.model_validate({"parameters": [param()]})
    assert len(verify_quotes(raw, PAGES, Category.LDO).parameters) == 1


def test_private_use_glyphs_are_ignored() -> None:
    ge = chr(0xF0B3)
    page = PageText(page=3, text=f"Maximum Output I 250 mA For V {ge}2.5V", chars=500)
    p = param(page=3, name="iout", typ=None, max=None, min="250", unit="mA")
    raw = RawExtraction.model_validate(
        {"parameters": [{**p, "quote": "Maximum Output I 250 mA For V 2.5V"}]}
    )
    assert len(verify_quotes(raw, [page], Category.LDO).parameters) == 1
