"""normalize(record) -> Part on the synthetic Digi-Key fixtures."""

import json
from datetime import UTC, date, datetime

import pytest

from ersatz.model import Category, Lifecycle, ParamName, Source, SourceKind
from ersatz.normalize.part import Normalized, normalize
from ersatz.providers.digikey import parse_product
from tests.providers.fakes import fixture

TODAY = date(2026, 11, 9)


def run(name: str, **changes: object) -> Normalized:
    raw = fixture(name)
    product = json.loads(raw)["Product"]
    product.update(changes)
    source = Source.from_response("digikey", raw, datetime(2026, 11, 9, tzinfo=UTC))
    return normalize(parse_product(product, source), today=TODAY)


def test_ldo_parameters_in_si_units() -> None:
    part = run("productdetails_ldo.json").part
    p = part.parameters
    assert p[ParamName.VOUT].typ == 3.3
    assert p[ParamName.VIN].max == 15.0
    assert p[ParamName.IOUT].max == 0.5
    assert p[ParamName.DROPOUT].max == 1.2
    assert p[ParamName.DROPOUT].conditions == {"I": "0.5 A"}
    assert p[ParamName.IQ].typ == pytest.approx(5e-3)
    assert p[ParamName.PSRR].conditions == {"f": "120 Hz"}


def test_every_value_keeps_the_provider_source() -> None:
    part = run("productdetails_ldo.json").part
    sources = [
        part.mpn.source,
        part.manufacturer.source,
        *(p.source for p in part.parameters.values()),
        *(s.source for s in part.lifecycle),
    ]
    assert part.package is not None
    sources.append(part.package.source)
    assert all(s.kind is SourceKind.PROVIDER and s.provider == "digikey" for s in sources)
    assert len({s.response_id for s in sources}) == 1


def test_ldo_category_lifecycle_and_package() -> None:
    result = run("productdetails_ldo.json")
    part = result.part
    assert part.category is not None
    assert part.category.value is Category.LDO
    assert part.lifecycle[0].value is Lifecycle.ACTIVE
    assert part.package is not None
    assert part.package.group == "SOT223"
    assert part.package.height_max_mm == 1.8
    assert part.stock[0].value == 1520


def test_input_range_merges_min_and_max_fields() -> None:
    part = run("productdetails_ldo_nrnd.json").part
    vin = part.parameters[ParamName.VIN]
    assert (vin.min, vin.max) == (2.5, 6.0)
    assert part.lifecycle[0].value is Lifecycle.NRND
    assert part.package is not None
    assert part.package.group == "SOT23-5"


def test_empty_placeholder_is_absent_not_unparsed() -> None:
    part = run("productdetails_ldo_nrnd.json").part
    assert ParamName.PSRR not in part.parameters
    assert "PSRR" not in part.unparsed


def test_op_amp() -> None:
    result = run("productdetails_obsolete.json")
    part = result.part
    assert part.category is not None
    assert part.category.value is Category.OPAMP
    assert part.lifecycle[0].value is Lifecycle.OBSOLETE
    p = part.parameters
    assert p[ParamName.CHANNELS].typ == 2
    assert p[ParamName.GBW].typ == 1e6
    assert p[ParamName.SLEW_RATE].typ == 5e5
    vs = p[ParamName.VSUPPLY]
    assert (vs.min, vs.max) == (3.0, 32.0)
    assert part.package is not None
    assert part.package.group == "SOIC8N"


def test_unparseable_value_is_kept_verbatim() -> None:
    result = run(
        "productdetails_ldo.json",
        Parameters=[{"ParameterText": "Voltage - Output (Min/Fixed)", "ValueText": "Adjustable"}],
    )
    part = result.part
    assert ParamName.VOUT not in part.parameters
    assert part.unparsed["Voltage - Output (Min/Fixed)"].value == "Adjustable"
    assert any("Voltage - Output" in note for note in result.notes)


def test_out_of_scope_category_has_no_parameters() -> None:
    result = run("productdetails_ldo.json", Category={"Name": "Comparators"})
    assert result.part.category is None
    assert result.category.status == "OUT_OF_SCOPE"
    assert result.part.parameters == {}


def test_unknown_package_is_not_guessed() -> None:
    result = run(
        "productdetails_ldo.json",
        Parameters=[{"ParameterText": "Supplier Device Package", "ValueText": "8-WSON (2x2)"}],
    )
    assert result.part.package is not None
    assert result.part.package.group is None
    assert "no-lead" in result.package.reason


def test_unknown_lifecycle_string() -> None:
    part = run("productdetails_ldo.json", ProductStatus={"Status": "Discontinued at Digi-Key"}).part
    assert part.lifecycle[0].value is Lifecycle.UNKNOWN
