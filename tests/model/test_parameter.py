"""Parameter invariants."""

import pytest
from pydantic import ValidationError

from ersatz.model import UNITS, Parameter, ParamName
from tests.model.helpers import DATASHEET


def test_accepts_ordered_values() -> None:
    p = Parameter(name=ParamName.VIN, min=2.5, max=5.5, unit="V", source=DATASHEET)
    assert p.typ is None


def test_rejects_min_above_max() -> None:
    with pytest.raises(ValidationError, match="min <= typ <= max"):
        Parameter(name=ParamName.VIN, min=6, max=5.5, unit="V", source=DATASHEET)


def test_rejects_typ_above_max() -> None:
    with pytest.raises(ValidationError):
        Parameter(name=ParamName.IQ, typ=2e-6, max=1e-6, unit="A", source=DATASHEET)


def test_rejects_wrong_unit() -> None:
    with pytest.raises(ValidationError, match="unit must be 'A'"):
        Parameter(name=ParamName.IQ, typ=1e-6, unit="mA", source=DATASHEET)


def test_rejects_empty_value() -> None:
    with pytest.raises(ValidationError, match="needs min, typ or max"):
        Parameter(name=ParamName.IQ, unit="A", source=DATASHEET)


def test_every_parameter_has_a_unit() -> None:
    assert set(UNITS) == set(ParamName)


def test_ldo_output_capacitor_window_uses_farad_and_ohm() -> None:
    esr = Parameter(name=ParamName.COUT_ESR, min=0.3, max=22, unit="ohm", source=DATASHEET)
    cap = Parameter(name=ParamName.COUT_MIN, min=1e-6, unit="F", source=DATASHEET)
    assert (esr.unit, cap.unit) == ("ohm", "F")
