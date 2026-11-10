from datetime import UTC, datetime
from typing import Any

import pytest

from ersatz.datasheets.schema import RawFeature, RawPackage, RawParameter, RawPin
from ersatz.datasheets.validate import Confidence, DatasheetRef, Extraction, validate
from ersatz.datasheets.verify import VerifiedExtraction, VerifiedPinout
from ersatz.model import Category, ParamName, SourceKind

MU = chr(0x00B5)
REF = DatasheetRef(
    url="https://example.invalid/ds.pdf",
    sha256="ab" * 32,
    revision="TEST-REV-A",
    fetched_at=datetime(2026, 11, 10, tzinfo=UTC),
)


def raw(name: str, unit: str, conditions: str = "", **cols: str | None) -> RawParameter:
    values: dict[str, Any] = {"min": None, "typ": None, "max": None, **cols}
    return RawParameter(
        name=name,
        unit=unit,
        conditions=conditions,
        variant=None,
        page=4,
        quote="quoted text",
        **values,
    )


def run(category: Category = Category.LDO, *params: RawParameter, **rest: Any) -> Extraction:
    verified = VerifiedExtraction(
        parameters=params,
        packages=rest.get("packages", ()),
        pinouts=rest.get("pinouts", ()),
        features=rest.get("features", ()),
        dropped=(),
    )
    return validate(verified, category, REF)


def only(ex: Extraction, name: ParamName) -> Any:
    found = ex.values(name)
    assert len(found) == 1
    return found[0]


def test_values_are_parsed_into_canonical_units_with_a_datasheet_source() -> None:
    ex = run(Category.LDO, raw("iq", f"{MU}A", "IOUT = 0 mA", typ="1.6", max="4"))
    item = only(ex, ParamName.IQ)
    assert item.parameter.typ == pytest.approx(1.6e-6)
    assert item.parameter.max == pytest.approx(4e-6)
    assert item.parameter.conditions["text"] == "IOUT = 0 mA"
    source = item.parameter.source
    assert (source.kind, source.page, source.revision) == (SourceKind.DATASHEET, 4, "TEST-REV-A")
    assert item.confidence is Confidence.HIGH


def test_unparseable_unit_is_dropped() -> None:
    ex = run(Category.LDO, raw("iq", "V", typ="1.6"))
    assert ex.parameters == ()
    assert "not an allowed spelling" in ex.dropped[0].reason


def test_min_above_max_is_dropped() -> None:
    ex = run(Category.LDO, raw("vin", "V", min="6", max="2.5"))
    assert ex.parameters == ()
    assert "min <= typ <= max" in ex.dropped[0].reason


def test_tolerance_keeps_its_magnitude() -> None:
    ex = run(Category.LDO, raw("vout_accuracy", "%", max="±2"))
    assert only(ex, ParamName.VOUT_ACCURACY).parameter.max == 2


def test_range_in_one_column_fills_min_and_max() -> None:
    ex = run(Category.LDO, raw("vin", "V", typ="2.5 to 6"))
    p = only(ex, ParamName.VIN).parameter
    assert (p.min, p.max) == (2.5, 6)


def test_split_supply_becomes_total_span() -> None:
    ex = run(Category.OPAMP, raw("vsupply", "V", min="±1.5", max="±16"))
    p = only(ex, ParamName.VSUPPLY).parameter
    assert (p.min, p.max) == (1.5, 16)
    ex = run(Category.OPAMP, raw("vsupply", "V", typ="±1.5 to ±16"))
    p = only(ex, ParamName.VSUPPLY).parameter
    assert (p.min, p.max) == (3, 32)


def test_dimensionless_parameters_ignore_the_printed_unit() -> None:
    ex = run(Category.OPAMP, raw("min_stable_gain", "V/V", min="5"))
    assert only(ex, ParamName.MIN_STABLE_GAIN).parameter.min == 5


def test_out_of_range_value_is_low_confidence() -> None:
    ex = run(Category.LDO, raw("iout", "A", max="300"))
    item = only(ex, ParamName.IOUT)
    assert item.confidence is Confidence.LOW
    assert item.issues[0].startswith("EXT-02")


def test_dropout_without_current_is_low() -> None:
    ex = run(Category.LDO, raw("dropout", "mV", "VIN = 5 V", max="350"))
    assert "EXT-05" in only(ex, ParamName.DROPOUT).issues[0]
    ex = run(Category.LDO, raw("dropout", "mV", "IOUT = 150mA", max="350"))
    assert only(ex, ParamName.DROPOUT).confidence is Confidence.HIGH


def test_ldo_cross_field_rules() -> None:
    ex = run(
        Category.LDO,
        raw("vin", "V", max="3.3"),
        raw("vout", "V", typ="3.3"),
        raw("dropout", "mV", "IOUT = 300 mA", max="5000"),
        raw("iq", "mA", max="400"),
        raw("iout", "mA", max="300"),
    )
    issues = {i for p in ex.parameters for i in p.issues}
    assert any(i.startswith("EXT-04") for i in issues)
    assert any("dropout is not between" in i for i in issues)
    assert any(i.startswith("EXT-06") for i in issues)


def test_input_below_output_plus_dropout_is_low() -> None:
    ex = run(
        Category.LDO,
        raw("vin", "V", min="3.5", max="6"),
        raw("vout", "V", typ="3.3"),
        raw("dropout", "mV", "IOUT = 300 mA", max="250"),
    )
    assert "EXT-03" in only(ex, ParamName.VIN).issues[0]


def test_shutdown_above_quiescent_is_low() -> None:
    ex = run(Category.LDO, raw("iq", "uA", max="1"), raw("ishdn", "uA", max="5"))
    assert "shutdown current" in only(ex, ParamName.ISHDN).issues[0]


def test_rules_skip_when_a_parameter_has_several_rows() -> None:
    ex = run(
        Category.LDO,
        raw("vin", "V", max="3"),
        raw("vout", "V", typ="3.3"),
        raw("vout", "V", typ="1.8"),
    )
    assert all(p.confidence is Confidence.HIGH for p in ex.parameters)


def pin(number: str, function: str) -> RawPin:
    return RawPin(number=number, name="P", function=function, channel=None, page=3, quote=number)


def test_pinout_with_other_pin_is_low() -> None:
    pinout = VerifiedPinout(
        package="SOT-23-5", pins=(pin("1", "IN"), pin("2", "OTHER")), complete=True
    )
    ex = run(Category.LDO, pinouts=(pinout,))
    out = ex.pinouts[0]
    assert [p.number for p in out.pinout.pins] == ["1"]
    assert out.confidence is Confidence.LOW


def test_incomplete_pinout_is_low() -> None:
    pinout = VerifiedPinout(package="SOT-23-5", pins=(pin("1", "IN"),), complete=False)
    assert run(Category.LDO, pinouts=(pinout,)).pinouts[0].confidence is Confidence.LOW


def test_packages_get_a_group_and_features_a_source() -> None:
    package = RawPackage(name="SOT-23-5", pin_count=5, page=1, quote="SOT-23-5")
    feature = RawFeature(name="ceramic_cap_stable", value=True, page=2, quote="ceramic")
    ex = run(Category.LDO, packages=(package,), features=(feature,))
    assert ex.packages[0].group is not None
    assert ex.packages[0].source.page == 1
    assert ex.features[0].source.page == 2


def test_negative_bias_current_keeps_its_magnitude() -> None:
    ex = run(Category.OPAMP, raw("ibias", "nA", typ="-20", max="-250"))
    p = only(ex, ParamName.IBIAS).parameter
    assert (p.typ, p.max) == (pytest.approx(2e-8), pytest.approx(2.5e-7))
    assert p.conditions["direction"] == "out of the input pins"
