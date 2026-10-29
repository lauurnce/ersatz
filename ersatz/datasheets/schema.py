"""The typed extraction schema, versioned.

The model returns raw strings exactly as printed, each with a 1-indexed
page and a verbatim quote. Ersatz parses units and checks the quotes
itself (D-021). Change SCHEMA_VERSION whenever a field changes, so cached
extractions made with an older schema are not reused.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ersatz.model.category import Category
from ersatz.model.package import PinFunction
from ersatz.model.parameter import CATEGORY_PARAMS

SCHEMA_VERSION = "1"
MAX_QUOTE_CHARS = 200


class Feature(StrEnum):
    # LDO
    ADJUSTABLE_OUTPUT = "adjustable_output"
    CERAMIC_CAP_STABLE = "ceramic_cap_stable"
    ENABLE_PIN = "enable_pin"
    # Op-amp
    RAIL_TO_RAIL_INPUT = "rail_to_rail_input"
    RAIL_TO_RAIL_OUTPUT = "rail_to_rail_output"
    UNITY_GAIN_STABLE = "unity_gain_stable"


CATEGORY_FEATURES: dict[Category, tuple[Feature, ...]] = {
    Category.LDO: (Feature.ADJUSTABLE_OUTPUT, Feature.CERAMIC_CAP_STABLE, Feature.ENABLE_PIN),
    Category.OPAMP: (
        Feature.RAIL_TO_RAIL_INPUT,
        Feature.RAIL_TO_RAIL_OUTPUT,
        Feature.UNITY_GAIN_STABLE,
    ),
}

CATEGORY_PINS: dict[Category, tuple[PinFunction, ...]] = {
    Category.LDO: (
        PinFunction.IN,
        PinFunction.OUT,
        PinFunction.GND,
        PinFunction.EN,
        PinFunction.NR,
        PinFunction.PG,
        PinFunction.ADJ,
        PinFunction.NC,
    ),
    Category.OPAMP: (
        PinFunction.INP,
        PinFunction.INN,
        PinFunction.OUT,
        PinFunction.VCC,
        PinFunction.VEE,
        PinFunction.NULL,
        PinFunction.SHDN,
        PinFunction.NC,
    ),
}

OTHER_PIN = "OTHER"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Cited(_Strict):
    page: int | None
    quote: str | None


class RawParameter(Cited):
    name: str
    min: str | None
    typ: str | None
    max: str | None
    unit: str
    conditions: str
    variant: str | None


class RawPackage(Cited):
    name: str
    pin_count: int | None


class RawPin(Cited):
    number: str
    name: str
    function: str
    channel: int | None


class RawPinout(_Strict):
    package: str
    pins: tuple[RawPin, ...]


class RawFeature(Cited):
    name: str
    value: bool


class RawExtraction(_Strict):
    parameters: tuple[RawParameter, ...] = Field(default=())
    packages: tuple[RawPackage, ...] = Field(default=())
    pinouts: tuple[RawPinout, ...] = Field(default=())
    features: tuple[RawFeature, ...] = Field(default=())


def _nullable(kind: str) -> dict[str, Any]:
    return {"type": [kind, "null"]}


def _object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def _cited(properties: dict[str, Any]) -> dict[str, Any]:
    return _object(
        {
            **properties,
            "page": {**_nullable("integer"), "description": "1-indexed PDF page"},
            "quote": {
                **_nullable("string"),
                "description": f"verbatim text from that page, at most {MAX_QUOTE_CHARS} chars",
            },
        }
    )


def json_schema(category: Category) -> dict[str, Any]:
    """JSON schema for structured outputs, with enums for this category."""
    params = sorted(p.value for p in CATEGORY_PARAMS[category])
    features = [f.value for f in CATEGORY_FEATURES[category]]
    pins = [p.value for p in CATEGORY_PINS[category]] + [OTHER_PIN]
    value = {**_nullable("string"), "description": "number as printed, without the unit"}
    parameter = _cited(
        {
            "name": {"type": "string", "enum": params},
            "min": value,
            "typ": value,
            "max": value,
            "unit": {"type": "string", "description": "unit as printed, for example mV"},
            "conditions": {"type": "string", "description": "test conditions as printed"},
            "variant": {
                **_nullable("string"),
                "description": "device or package variant the row applies to, if any",
            },
        }
    )
    package = _cited({"name": {"type": "string"}, "pin_count": _nullable("integer")})
    pin = _cited(
        {
            "number": {"type": "string", "description": "pin number, or TAB or EP"},
            "name": {"type": "string", "description": "pin name as printed"},
            "function": {"type": "string", "enum": pins},
            "channel": _nullable("integer"),
        }
    )
    pinout = _object({"package": {"type": "string"}, "pins": {"type": "array", "items": pin}})
    feature = _cited({"name": {"type": "string", "enum": features}, "value": {"type": "boolean"}})
    return _object(
        {
            "parameters": {"type": "array", "items": parameter},
            "packages": {"type": "array", "items": package},
            "pinouts": {"type": "array", "items": pinout},
            "features": {"type": "array", "items": feature},
        }
    )
