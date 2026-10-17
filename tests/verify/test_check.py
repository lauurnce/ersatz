import pytest

from ersatz.verify import VerifyError, check_text
from tests.match.fakes import FakeProvider, record

LDO = {
    "Voltage - Input (Min)": "2.5V",
    "Voltage - Input (Max)": "6V",
    "Voltage - Output (Min/Fixed)": "3.3V",
    "Current - Output": "300mA",
    "Voltage Dropout (Max)": "0.35V @ 300mA",
}
TEXT = """For TEST-LDO50-OLD (3.3V, SOT-23-5) try **TEST-LDO50-A**, TEST-LDO50-X or TEST-LDO50-Z9.
TEST-LDO50-A is the best pick."""


def provider() -> FakeProvider:
    return FakeProvider(
        "digikey",
        [
            record("TEST-LDO50-OLD", lifecycle="Obsolete", parameters=LDO),
            record("TEST-LDO50-A", parameters=LDO),
            record("TEST-LDO50-X", lifecycle="Obsolete", parameters=LDO),
        ],
        parametric=False,
        results=[],
    )


def test_with_original_each_mention_gets_a_verdict() -> None:
    report = check_text(TEXT, [provider()], original="TEST-LDO50-OLD")
    assert report.mentions == ("TEST-LDO50-OLD", "TEST-LDO50-A", "TEST-LDO50-X", "TEST-LDO50-Z9")
    assert [(i.as_entered, i.status) for i in report.items] == [
        ("TEST-LDO50-A", "PARTIAL"),
        ("TEST-LDO50-X", "MISMATCH"),
        ("TEST-LDO50-Z9", "NOT FOUND"),
    ]
    assert report.items[1].lifecycle == "OBSOLETE"
    assert report.items[2].manufacturer is None
    assert report.notice.startswith("Ersatz results")


def test_without_original_mentions_are_only_resolved() -> None:
    report = check_text(TEXT, [provider()])
    statuses = {i.as_entered: (i.status, i.lifecycle) for i in report.items}
    assert statuses == {
        "TEST-LDO50-OLD": ("FOUND", "OBSOLETE"),
        "TEST-LDO50-A": ("FOUND", "ACTIVE"),
        "TEST-LDO50-X": ("FOUND", "OBSOLETE"),
        "TEST-LDO50-Z9": ("NOT FOUND", None),
    }


def test_ambiguous_mention_without_original() -> None:
    p = FakeProvider("digikey", [record("TEST-A1"), record("TEST-A1", manufacturer="Other Co")])
    item = check_text("TEST-A1", [p]).items[0]
    assert item.status == "AMBIGUOUS"


def test_unknown_original_raises() -> None:
    with pytest.raises(VerifyError):
        check_text(TEXT, [provider()], original="TEST-NOPE")
