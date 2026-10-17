import pytest

from ersatz.resolve import Status, SuffixRule, clean, resolve
from tests.match.fakes import FakeProvider, record

TI = "Texas Instruments"
PACKAGING = [
    SuffixRule(id="SFX-T", manufacturer=TI, status="UNVERIFIED", suffixes=("R", "T"), note="reel")
]
DIST = [
    SuffixRule(
        id="SFX-DK",
        provider="digikey",
        status="UNVERIFIED",
        suffixes=("DKR-ND", "CT-ND", "TR-ND", "-ND"),
        note="codes",
    )
]


def run(text: str, provider: FakeProvider, manufacturer: str | None = None):  # type: ignore[no-untyped-def]
    return resolve(text, [provider], manufacturer, DIST, PACKAGING)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("TEST-A1", "TEST-A1"),
        ("  **TEST-A1**, ", "TEST-A1"),
        ("`TEST-A1`.", "TEST-A1"),
        ("(TEST-A1)", "TEST-A1"),
        ("TEST" + chr(0x2013) + "A1", "TEST-A1"),
        ("MCP-TEST/TT", "MCP-TEST/TT"),
    ],
)
def test_clean_removes_only_surrounding_markup(text: str, expected: str) -> None:
    assert clean(text) == expected


def test_exact_match_is_found() -> None:
    result = run("TEST-A1", FakeProvider("digikey", [record("TEST-A1")]))
    assert result.status is Status.FOUND
    assert result.note == "exact match"
    assert result.rule is None
    assert result.record is not None


def test_cleaned_match_says_so() -> None:
    result = run("**TEST-A1**", FakeProvider("digikey", [record("TEST-A1")]))
    assert result.status is Status.FOUND
    assert result.note == "exact match after cleaning"


def test_two_manufacturers_are_ambiguous_unless_one_is_named() -> None:
    provider = FakeProvider(
        "digikey", [record("TEST-A1"), record("TEST-A1", manufacturer="Other Co")]
    )
    assert run("TEST-A1", provider).status is Status.AMBIGUOUS
    assert run("TEST-A1", provider, manufacturer="Other Co").status is Status.FOUND


@pytest.mark.parametrize("code", ["CT-ND", "TR-ND", "DKR-ND", "-ND"])
def test_digikey_codes_are_removed(code: str) -> None:
    result = run(f"TEST-A1{code}", FakeProvider("digikey", [record("TEST-A1")]))
    assert result.status is Status.FOUND
    assert result.query == "TEST-A1"
    assert result.unverified
    assert result.note == f"SFX-DK: removed {code}"


def test_digikey_code_rule_only_applies_to_digikey() -> None:
    result = run("TEST-A1CT-ND", FakeProvider("mouser", [record("TEST-A1")]))
    assert result.status is Status.NOT_FOUND


def test_packaging_variant_from_the_listed_manufacturer_is_found() -> None:
    provider = FakeProvider("digikey", [], results=[record("TEST-A1R", manufacturer=TI)])
    result = run("TEST-A1", provider)
    assert result.status is Status.FOUND
    assert result.records[0].mpn == "TEST-A1R"
    assert "orderable variants TEST-A1R" in result.note


def test_packaging_variant_from_another_manufacturer_is_not_used() -> None:
    provider = FakeProvider("digikey", [], results=[record("TEST-A1R", manufacturer="Other Co")])
    assert run("TEST-A1", provider).status is Status.NOT_FOUND


@pytest.mark.parametrize("near", ["TEST-A1X", "TEST-A12", "TEST-A", "TEST-A1RR"])
def test_close_matches_are_never_offered(near: str) -> None:
    provider = FakeProvider(
        "digikey", [record(near, manufacturer=TI)], results=[record(near, manufacturer=TI)]
    )
    result = run("TEST-A1", provider)
    assert result.status is Status.NOT_FOUND
    assert result.records == ()


def test_inner_characters_are_never_stripped() -> None:
    provider = FakeProvider("digikey", [record("TESTA1")])
    assert run("TEST-A1", provider).status is Status.NOT_FOUND


def test_empty_text_is_not_found() -> None:
    assert run(" ** ", FakeProvider("digikey", [])).status is Status.NOT_FOUND


def test_default_rules_load_from_the_rules_file() -> None:
    provider = FakeProvider("digikey", [record("TEST-A1")])
    assert resolve("TEST-A1CT-ND", [provider]).rule is not None
