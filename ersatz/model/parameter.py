"""Numeric parameters with min, typ and max in SI base units."""

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from ersatz.model.category import Category
from ersatz.model.source import Source


class ParamName(StrEnum):
    # LDO (DOMAIN.md section 3)
    VIN = "vin"
    VIN_ABS_MAX = "vin_abs_max"
    VOUT = "vout"
    VREF = "vref"
    VOUT_ACCURACY = "vout_accuracy"
    IOUT = "iout"
    DROPOUT = "dropout"
    IQ = "iq"
    ISHDN = "ishdn"
    PSRR = "psrr"
    COUT_MIN = "cout_min"  # LDO-13: minimum stable output capacitance
    COUT_ESR = "cout_esr"  # LDO-13: stable output capacitor ESR window
    # Op-amp (DOMAIN.md section 4)
    CHANNELS = "channels"
    VSUPPLY = "vsupply"
    GBW = "gbw"
    SLEW_RATE = "slew_rate"
    VOS = "vos"
    IBIAS = "ibias"
    VNOISE = "vnoise"
    IQ_PER_CHANNEL = "iq_per_channel"
    MIN_STABLE_GAIN = "min_stable_gain"
    # Both
    TJ = "tj"


# Canonical unit per parameter, as a pint unit string. "" means dimensionless.
UNITS: dict[ParamName, str] = {
    ParamName.VIN: "V",
    ParamName.VIN_ABS_MAX: "V",
    ParamName.VOUT: "V",
    ParamName.VREF: "V",
    ParamName.VOUT_ACCURACY: "percent",
    ParamName.IOUT: "A",
    ParamName.DROPOUT: "V",
    ParamName.IQ: "A",
    ParamName.ISHDN: "A",
    ParamName.PSRR: "dB",
    ParamName.COUT_MIN: "F",
    ParamName.COUT_ESR: "ohm",
    ParamName.CHANNELS: "",
    ParamName.VSUPPLY: "V",
    ParamName.GBW: "Hz",
    ParamName.SLEW_RATE: "V/s",
    ParamName.VOS: "V",
    ParamName.IBIAS: "A",
    ParamName.VNOISE: "V/Hz**0.5",
    ParamName.IQ_PER_CHANNEL: "A",
    ParamName.MIN_STABLE_GAIN: "",
    ParamName.TJ: "degC",
}

CATEGORY_PARAMS: dict[Category, frozenset[ParamName]] = {
    Category.LDO: frozenset(
        {
            ParamName.VIN,
            ParamName.VIN_ABS_MAX,
            ParamName.VOUT,
            ParamName.VREF,
            ParamName.VOUT_ACCURACY,
            ParamName.IOUT,
            ParamName.DROPOUT,
            ParamName.IQ,
            ParamName.ISHDN,
            ParamName.PSRR,
            ParamName.COUT_MIN,
            ParamName.COUT_ESR,
            ParamName.TJ,
        }
    ),
    Category.OPAMP: frozenset(
        {
            ParamName.CHANNELS,
            ParamName.VSUPPLY,
            ParamName.GBW,
            ParamName.SLEW_RATE,
            ParamName.VOS,
            ParamName.IBIAS,
            ParamName.VNOISE,
            ParamName.IQ,
            ParamName.IQ_PER_CHANNEL,
            ParamName.MIN_STABLE_GAIN,
            ParamName.TJ,
        }
    ),
}


class Parameter(BaseModel, frozen=True):
    name: ParamName
    min: float | None = None
    typ: float | None = None
    max: float | None = None
    unit: str
    conditions: dict[str, str] = Field(default_factory=dict)
    source: Source

    @model_validator(mode="after")
    def _check(self) -> "Parameter":
        if self.min is None and self.typ is None and self.max is None:
            raise ValueError(f"{self.name}: a parameter needs min, typ or max")
        if self.unit != UNITS[self.name]:
            raise ValueError(f"{self.name}: unit must be {UNITS[self.name]!r}, got {self.unit!r}")
        values = [v for v in (self.min, self.typ, self.max) if v is not None]
        if values != sorted(values):
            raise ValueError(f"{self.name}: min <= typ <= max does not hold")
        return self
