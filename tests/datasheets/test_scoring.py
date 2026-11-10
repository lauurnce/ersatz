from pathlib import Path
from typing import Any

import pytest

from ersatz.datasheets.schema import RawFeature, RawPackage, RawParameter, RawPin
from ersatz.datasheets.scoring import (
    GoldFile,
    GoldLabel,
    Outcome,
    load_gold,
    score,
    summarize,
)
from ersatz.datasheets.validate import Extraction, validate
from ersatz.datasheets.verify import VerifiedExtraction, VerifiedPinout
from ersatz.model import Category
from tests.datasheets.test_validate import REF

GOLD_DIR = Path(__file__).parent.parent.parent / "eval" / "extraction" / "gold"


def param(name: str, unit: str, page: int = 5, **cols: str) -> RawParameter:
    values: dict[str, Any] = {"min": None, "typ": None, "max": None, **cols}
    return RawParameter(
        name=name, unit=unit, conditions="", variant=None, page=page, quote="q", **values
    )


def extraction() -> Extraction:
    pins = (
        RawPin(number="1", name="OUTA", function="OUT", channel=1, page=3, quote="1"),
        RawPin(number="2", name="-INA", function="INP", channel=1, page=3, quote="2"),
    )
    verified = VerifiedExtraction(
        parameters=(
            param("gbw", "MHz", typ="1"),
            param("slew_rate", "V/us", page=9, typ="0.6"),
            param("vos", "mV", typ="0.5", max="5"),
            param("iq", "uA", typ="100", max="150"),
            param("channels", "", typ="2"),
        ),
        packages=(RawPackage(name="SOIC-8", pin_count=8, page=1, quote="SOIC-8"),),
        pinouts=(VerifiedPinout(package="SOIC-8", pins=pins, complete=True),),
        features=(RawFeature(name="rail_to_rail_output", value=True, page=1, quote="RRO"),),
        dropped=(),
    )
    return validate(verified, Category.OPAMP, REF)


def gold(*labels: dict[str, Any]) -> GoldFile:
    return GoldFile(
        id="test",
        category=Category.OPAMP,
        device="TEST-OPA2",
        manufacturer="Test",
        url="https://example.invalid/a.pdf",
        sha256="ab" * 32,
        revision=None,
        status="DRAFT",
        labels=tuple(GoldLabel.model_validate(label) for label in labels),
    )


def outcomes(*labels: dict[str, Any]) -> list[tuple[Outcome, bool]]:
    return [(s.outcome, s.cited_ok) for s in score(gold(*labels), extraction())]


def test_parameter_outcomes() -> None:
    assert outcomes(
        {"kind": "parameter", "name": "gbw", "typ": 1.0e6, "pages": [5]},
        {"kind": "parameter", "name": "slew_rate", "typ": 0.6e6, "pages": [4]},
        {"kind": "parameter", "name": "vos", "typ": 0.5e-3, "max": 6e-3, "pages": [5]},
        {"kind": "parameter", "name": "ibias", "typ": 1e-12, "pages": [5]},
    ) == [
        (Outcome.CORRECT, True),
        (Outcome.CORRECT, False),
        (Outcome.WRONG, False),
        (Outcome.MISSING, False),
    ]


def test_alt_names_and_any_slot() -> None:
    assert outcomes(
        {
            "kind": "parameter",
            "name": "iq_per_channel",
            "alt_names": ["iq"],
            "typ": 1e-4,
            "max": 1.5e-4,
            "pages": [5],
        },
        {"kind": "parameter", "name": "channels", "max": 2, "any_slot": True, "pages": [5]},
    ) == [(Outcome.CORRECT, True), (Outcome.CORRECT, True)]


def test_values_within_one_percent_match() -> None:
    assert outcomes({"kind": "parameter", "name": "gbw", "typ": 1.009e6, "pages": [5]}) == [
        (Outcome.CORRECT, True)
    ]
    assert outcomes({"kind": "parameter", "name": "gbw", "typ": 1.02e6, "pages": [5]}) == [
        (Outcome.WRONG, False)
    ]


def test_package_pin_and_feature_outcomes() -> None:
    assert outcomes(
        {"kind": "package", "name": "SOIC", "pin_count": 8, "pages": [1]},
        {"kind": "package", "name": "SOIC", "pin_count": 14, "pages": [1]},
        {"kind": "package", "name": "MSOP", "pin_count": 8, "pages": [1]},
        {"kind": "pin", "package": ["SOIC"], "number": "1", "function": "OUT", "pages": [3]},
        {"kind": "pin", "package": "SOIC", "number": "2", "function": "INN", "pages": [3]},
        {"kind": "pin", "package": ["MSOP"], "number": "1", "function": "OUT", "pages": [3]},
        {"kind": "feature", "name": "rail_to_rail_output", "value": True, "pages": [1]},
        {"kind": "feature", "name": "rail_to_rail_input", "value": True, "pages": [1]},
    ) == [
        (Outcome.CORRECT, True),
        (Outcome.WRONG, False),
        (Outcome.MISSING, False),
        (Outcome.CORRECT, True),
        (Outcome.WRONG, False),
        (Outcome.MISSING, False),
        (Outcome.CORRECT, True),
        (Outcome.MISSING, False),
    ]


def test_summary_counts_per_field_type() -> None:
    scores = score(
        gold(
            {"kind": "parameter", "name": "gbw", "typ": 1.0e6, "pages": [5]},
            {"kind": "pin", "package": "SOIC", "number": "1", "function": "OUT", "pages": [9]},
            {"kind": "pin", "package": "SOIC", "number": "2", "function": "INN", "pages": [3]},
        ),
        extraction(),
    )
    by_type = {s.field_type: s for s in summarize(scores)}
    pins = by_type["pin"]
    assert (pins.labels, pins.correct, pins.wrong, pins.cited) == (2, 1, 1, 0)
    assert pins.field_accuracy == 0.5
    assert pins.citation_accuracy == 0.0
    assert by_type["parameter:gbw"].citation_accuracy == 1.0


def test_unknown_label_fields_are_rejected() -> None:
    with pytest.raises(ValueError, match="extra"):
        GoldLabel.model_validate({"kind": "feature", "pages": [1], "colour": "red"})


def test_committed_gold_set_loads() -> None:
    files = load_gold(GOLD_DIR)
    assert len(files) == 10
    assert {f.category for f in files} == {Category.LDO, Category.OPAMP}
    assert sum(f.category is Category.LDO for f in files) == 5
    assert len({f.manufacturer for f in files}) >= 5
