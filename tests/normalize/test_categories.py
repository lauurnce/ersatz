"""Category mapping per provider."""

import pytest

from ersatz.model import Category
from ersatz.normalize.categories import map_category

LDO = "Voltage Regulators - Linear, Low Drop Out (LDO) Regulators"
AMPS = "Instrumentation, Op Amps, Buffer Amps"


def test_digikey_ldo() -> None:
    match = map_category("digikey", LDO)
    assert match.status == "IN_SCOPE"
    assert match.category is Category.LDO


def test_case_and_spacing_do_not_matter() -> None:
    assert map_category("digikey", f"  {LDO.upper()} ").category is Category.LDO


@pytest.mark.parametrize("kind", ["General Purpose", "CMOS", "J-FET", "Chopper (Zero-Drift)"])
def test_digikey_op_amp_types(kind: str) -> None:
    match = map_category("digikey", AMPS, {"Amplifier Type": kind})
    assert match.status == "IN_SCOPE"
    assert match.category is Category.OPAMP


@pytest.mark.parametrize("kind", ["Instrumentation", "Buffer", "Current Sense", "Differential"])
def test_other_amplifiers_are_out_of_scope(kind: str) -> None:
    match = map_category("digikey", AMPS, {"Amplifier Type": kind})
    assert match.status == "OUT_OF_SCOPE"
    assert match.category is None


def test_amplifier_without_type_is_unknown() -> None:
    assert map_category("digikey", AMPS, {}).status == "UNKNOWN"
    assert map_category("digikey", AMPS, {"Amplifier Type": "Something New"}).status == "UNKNOWN"


@pytest.mark.parametrize(
    "raw",
    [
        "Voltage Regulators - DC DC Switching Regulators",
        "Comparators",
        "Voltage Reference",
        "Resistors",
    ],
)
def test_everything_else_is_out_of_scope(raw: str) -> None:
    match = map_category("digikey", raw)
    assert match.status == "OUT_OF_SCOPE"
    assert "not covered in v0.1" in match.reason


def test_mouser_taxonomy() -> None:
    assert map_category("mouser", "LDO Voltage Regulators").category is Category.LDO
    assert map_category("mouser", "Operational Amplifiers - Op Amps").category is Category.OPAMP
    assert map_category("mouser", "Audio Amplifiers").status == "OUT_OF_SCOPE"


def test_missing_category_or_provider_is_unknown() -> None:
    assert map_category("digikey", None).status == "UNKNOWN"
    assert map_category("other", LDO).status == "UNKNOWN"
