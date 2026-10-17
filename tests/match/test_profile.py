from datetime import UTC, datetime

from ersatz.datasheets.schema import RawFeature, RawParameter, RawPin
from ersatz.datasheets.validate import DatasheetRef, validate
from ersatz.datasheets.verify import VerifiedExtraction, VerifiedPinout
from ersatz.match.profile import profile
from ersatz.model import Category, Lifecycle, ParamName, SourceKind
from tests.match.parts import ldo

REF = DatasheetRef(
    url="https://example.invalid/test.pdf",
    sha256="ef" * 32,
    revision="TEST-A",
    fetched_at=datetime(2026, 10, 17, tzinfo=UTC),
)


def raw(name: str, unit: str, **cols: str) -> RawParameter:
    values = {"min": None, "typ": None, "max": None, **cols}
    return RawParameter(
        name=name, unit=unit, conditions="IOUT = 300 mA", variant=None, page=5, quote="q", **values
    )


def test_datasheet_values_win_and_low_values_are_ignored() -> None:
    base = ldo("TEST-LDO-P", lifecycle=Lifecycle.NRND)
    verified = VerifiedExtraction(
        parameters=(raw("dropout", "mV", max="300"), raw("iout", "A", max="300")),
        packages=(),
        pinouts=(
            VerifiedPinout(
                package="SOT-23-5",
                pins=(
                    RawPin(number="1", name="VIN", function="IN", channel=None, page=3, quote="1"),
                ),
                complete=True,
            ),
        ),
        features=(RawFeature(name="ceramic_cap_stable", value=True, page=1, quote="ceramic"),),
        dropped=(),
    )
    extraction = validate(verified, Category.LDO, REF)
    merged = profile(base.part, extraction)
    dropout = merged.parameters[ParamName.DROPOUT]
    assert dropout.source.kind is SourceKind.DATASHEET
    assert dropout.max == 0.3
    # iout of 300 A is out of range, so LOW, and the provider value stays.
    assert merged.parameters[ParamName.IOUT].source.kind is SourceKind.PROVIDER
    assert merged.features["ceramic_cap_stable"].source.page == 1
    assert merged.pinout is not None
    assert merged.pinout.source.kind is SourceKind.DATASHEET
    assert merged.lifecycle is Lifecycle.NRND
    assert merged.stock == 1000


def test_profile_without_extraction_uses_provider_values() -> None:
    base = ldo("TEST-LDO-Q")
    merged = profile(base.part)
    assert merged.parameters == base.part.parameters
    assert merged.features == {}
