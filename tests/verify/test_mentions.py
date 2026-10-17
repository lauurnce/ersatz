import pytest

from ersatz.verify.mentions import extract_mpns, is_part_number

MESSY = """Sure! Here are some options for replacing the **TEST-LDO50-OLD** (3.3V, 500mA, SOT-23-5):

| Part | Notes |
|---|---|
| TEST-LDO50-A | AEC-Q100, PSRR 70 dB @ 1kHz |
| `TEST-LDO50-X` | pin-compatible, -40 to 125 C |

- TEST-LDO50-Z9: also a drop-in (datasheet rev 2024-05-01).
- Or try TEST-LDO50-A again, or TEST-OPA/TT1 for the amplifier stage.
I2C, SPI and USB are not needed. Use a 1uF ceramic cap, 10-uF works too.
"""


def test_extracts_from_markdown_tables_lists_and_code() -> None:
    assert extract_mpns(MESSY) == [
        "TEST-LDO50-OLD",
        "TEST-LDO50-A",
        "TEST-LDO50-X",
        "TEST-LDO50-Z9",
        "TEST-OPA/TT1",
    ]


@pytest.mark.parametrize(
    "token",
    [
        "3.3V",
        "500MA",
        "1KHZ",
        "100NF",
        "10-UF",
        "AEC-Q100",
        "I2C",
        "SOT-23-5",
        "SOIC-8",
        "2024-05-01",
        "R2D2"[:3],
    ],
)
def test_values_packages_and_spec_words_are_not_part_numbers(token: str) -> None:
    assert not is_part_number(token)


@pytest.mark.parametrize("token", ["TEST-A1", "TEST-OPA/TT1", "TEST1#PBF", "TEST2+"])
def test_part_number_shapes(token: str) -> None:
    assert is_part_number(token)


def test_lowercase_words_are_ignored() -> None:
    assert extract_mpns("use the test-ldo50 or the Abc123 part") == []


def test_trailing_period_is_not_part_of_the_token() -> None:
    assert extract_mpns("Pick TEST-LDO50-A.") == ["TEST-LDO50-A"]


def test_empty_text() -> None:
    assert extract_mpns("") == []
