import json
from typing import Any

import pytest

from ersatz.datasheets.schema import RawExtraction, json_schema
from ersatz.model import Category

EXAMPLE = {
    "parameters": [
        {
            "name": "dropout",
            "min": None,
            "typ": "250",
            "max": "350",
            "unit": "mV",
            "conditions": "IOUT = 150 mA",
            "variant": None,
            "page": 5,
            "quote": "Dropout voltage IOUT = 150 mA 250 350 mV",
        }
    ],
    "packages": [{"name": "SOT-23-5", "pin_count": 5, "page": 1, "quote": "SOT-23-5"}],
    "pinouts": [
        {
            "package": "SOT-23-5",
            "pins": [
                {
                    "number": "1",
                    "name": "VIN",
                    "function": "IN",
                    "channel": None,
                    "page": 3,
                    "quote": "1 VIN Input",
                }
            ],
        }
    ],
    "features": [{"name": "ceramic_cap_stable", "value": True, "page": 1, "quote": "ceramic"}],
}


def _objects(node: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(node, dict):
        if node.get("type") == "object":
            found.append(node)
        for child in node.values():
            found.extend(_objects(child))
    elif isinstance(node, list):
        for child in node:
            found.extend(_objects(child))
    return found


@pytest.mark.parametrize("category", list(Category))
def test_every_object_is_closed_and_fully_required(category: Category) -> None:
    for obj in _objects(json_schema(category)):
        assert obj["additionalProperties"] is False
        assert set(obj["required"]) == set(obj["properties"])


@pytest.mark.parametrize("category", list(Category))
def test_schema_has_no_numeric_constraints(category: Category) -> None:
    text = json.dumps(json_schema(category))
    for keyword in ("minimum", "maximum", "multipleOf"):
        assert f'"{keyword}"' not in text


def test_parameter_names_follow_the_category() -> None:
    def names(category: Category) -> list[str]:
        schema = json_schema(category)
        items = schema["properties"]["parameters"]["items"]
        enum: list[str] = items["properties"]["name"]["enum"]
        return enum

    assert "dropout" in names(Category.LDO)
    assert "slew_rate" not in names(Category.LDO)
    assert "slew_rate" in names(Category.OPAMP)


def test_pin_functions_include_other() -> None:
    schema = json_schema(Category.OPAMP)
    pin = schema["properties"]["pinouts"]["items"]["properties"]["pins"]["items"]
    assert "OTHER" in pin["properties"]["function"]["enum"]
    assert "INP" in pin["properties"]["function"]["enum"]


def test_example_payload_parses() -> None:
    raw = RawExtraction.model_validate(EXAMPLE)
    assert raw.parameters[0].max == "350"
    assert raw.pinouts[0].pins[0].function == "IN"


def test_unknown_fields_are_rejected() -> None:
    bad = {**EXAMPLE, "extra": 1}
    with pytest.raises(ValueError, match="extra"):
        RawExtraction.model_validate(bad)
