"""A Part can only be built from provider data."""

import pytest
from pydantic import ValidationError

from ersatz.model import (
    Category,
    Lifecycle,
    Parameter,
    ParamName,
    Part,
    Pin,
    PinFunction,
    Pinout,
    Sourced,
)
from tests.model.helpers import DATASHEET, PROVIDER


def make(mpn_source: object = PROVIDER, **kwargs: object) -> Part:
    return Part.model_validate(
        {
            "mpn": {"value": "TEST-LDO33", "source": mpn_source},
            "manufacturer": Sourced(value="Test Semiconductor", source=PROVIDER),
            "category": Sourced(value=Category.LDO, source=PROVIDER),
            "lifecycle": (Sourced(value=Lifecycle.ACTIVE, source=PROVIDER),),
            "package": None,
            **kwargs,
        }
    )


def test_part_from_provider_source() -> None:
    part = make()
    assert part.mpn.value == "TEST-LDO33"
    assert part.mpn.source.provider == "digikey"


def test_part_number_from_a_datasheet_is_rejected() -> None:
    with pytest.raises(ValidationError, match="must come from a provider response"):
        make(mpn_source=DATASHEET)


def test_bare_string_part_number_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Part.model_validate({"mpn": "TEST-LDO33"})


def test_parameter_key_must_match_name() -> None:
    vout = Parameter(name=ParamName.VOUT, typ=3.3, unit="V", source=DATASHEET)
    assert make(parameters={ParamName.VOUT: vout}).parameters[ParamName.VOUT].typ == 3.3
    with pytest.raises(ValidationError, match="stored under"):
        make(parameters={ParamName.VIN: vout})


def test_tab_is_a_pin() -> None:
    pinout = Pinout(
        pins=(
            Pin(number="1", function=PinFunction.GND),
            Pin(number="2", function=PinFunction.OUT),
            Pin(number="3", function=PinFunction.IN),
            Pin(number="TAB", function=PinFunction.OUT),
        ),
        source=DATASHEET,
    )
    assert make(pinout=pinout).pinout == pinout


def test_part_is_frozen() -> None:
    part = make()
    with pytest.raises(ValidationError):
        part.package = None  # type: ignore[misc]
