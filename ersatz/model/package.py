"""Package outline and pinout."""

from enum import StrEnum

from pydantic import BaseModel

from ersatz.model.source import Source


class Package(BaseModel, frozen=True):
    raw_name: str
    group: str | None  # None means UNKNOWN: unknown or ambiguous names are never guessed
    pin_count: int | None = None
    body_width_mm: float | None = None
    height_max_mm: float | None = None
    source: Source


class PinFunction(StrEnum):
    # LDO
    IN = "IN"
    OUT = "OUT"
    GND = "GND"
    EN = "EN"
    NR = "NR"
    PG = "PG"
    ADJ = "ADJ"
    # Op-amp, per channel
    INP = "INP"
    INN = "INN"
    # Op-amp, shared
    VCC = "VCC"
    VEE = "VEE"
    NULL = "NULL"
    SHDN = "SHDN"
    # Both
    NC = "NC"


class Pin(BaseModel, frozen=True):
    number: str  # "1", "TAB", "EP": the tab or exposed pad is a pin
    function: PinFunction
    channel: int | None = None


class Pinout(BaseModel, frozen=True):
    pins: tuple[Pin, ...]
    source: Source
