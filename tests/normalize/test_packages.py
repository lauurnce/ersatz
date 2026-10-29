"""Package aliases and equivalence groups."""

import re
from pathlib import Path

import pytest

from ersatz.normalize.packages import key, package_group, tables
from ersatz.rules import load

EN_DASH = chr(0x2013)
DOMAIN = (Path(__file__).parents[2] / "docs" / "DOMAIN.md").read_text(encoding="utf-8")


def _domain_groups() -> dict[str, str]:
    section = DOMAIN.split("### Package equivalence groups", 1)[1].split("###", 1)[0]
    rows = re.findall(r"^\| ([A-Z0-9-]+) \| ([^|]+) \|", section, flags=re.M)
    return {group: names for group, names in rows if group != "Group"}


def test_rules_file_has_every_domain_group() -> None:
    assert set(load("packages")["groups"]) == set(_domain_groups())


def test_every_group_cites_sources_listed_in_domain() -> None:
    for group in tables().groups.values():
        assert group.sources, group.name
        for source in group.sources:
            assert f"- [{source}]" in DOMAIN, (group.name, source)


@pytest.mark.parametrize(
    "alias", [a for g in load("packages")["groups"].values() for a in g["aliases"]]
)
def test_every_alias_matches_its_group(alias: str) -> None:
    expected = next(n for n, g in load("packages")["groups"].items() if alias in g["aliases"])
    match = package_group(alias)
    assert match.status == "MATCHED", match.reason
    assert match.group is not None
    assert match.group.name == expected


DISTRIBUTOR_STRINGS = [
    ("SOT-223-3", "SOT223"),
    ("TO-261-4, TO-261AA", "SOT223"),
    ('8-SOIC (0.154", 3.90mm Width)', "SOIC8N"),
    ("TO-236-3, SC-59, SOT-23-3", "SOT23-3"),
    ("SC-74A, SOT-753", "SOT23-5"),
    ("SOT-23-5 Thin, TSOT-23-5", "TSOT23-5"),
    ('8-TSSOP, 8-MSOP (0.118", 3.00mm Width)', "MSOP8"),
    ('8-TSSOP (0.173", 4.40mm Width)', "TSSOP8W"),
    ("TO-252-3, DPak (2 Leads + Tab), SC-63", "DPAK"),
    ("TO-263-3, D²Pak (2 Leads + Tab), TO-263AB", "D2PAK3"),
    ("TO-220-3", "TO220"),
    ("TO-92-3", "TO92"),
    ("SOT-89-3", "SOT89"),
    ("sot 23-5", "SOT23-5"),
    (f"SOT{EN_DASH}23{EN_DASH}5", "SOT23-5"),
]


@pytest.mark.parametrize(("raw", "group"), DISTRIBUTOR_STRINGS)
def test_distributor_strings(raw: str, group: str) -> None:
    match = package_group(raw)
    assert match.status == "MATCHED", match.reason
    assert match.group is not None
    assert match.group.name == group


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        ("SOP-8", "ambiguous name without a body width"),
        ("8-TSSOP", "ambiguous name without a body width"),
        ("8-WSON (2x2)", "no-lead package"),
        ("6-UDFN Exposed Pad", "no-lead package"),
        ("16-VQFN (3x3)", "no-lead package"),
        ("XYZ-7", "unknown package name"),
        ("", "no package name"),
        ("SOT-23, SOT-23-5", "different groups"),
        ('8-SOIC (0.209", 5.30mm Width)', "does not fit SOIC8N"),
        ('SOP-8 (0.209", 5.30mm Width)', "fits no group"),
    ],
)
def test_unknown_is_flagged_not_guessed(raw: str, reason: str) -> None:
    match = package_group(raw)
    assert match.status == "UNKNOWN"
    assert match.group is None
    assert reason in match.reason


def test_ambiguous_name_resolves_with_body_width() -> None:
    match = package_group("SOP-8", body_width_mm=3.9)
    assert match.group is not None
    assert match.group.name == "SOIC8N"


def test_pin_count_mismatch_is_unknown() -> None:
    match = package_group("SOT-23-5", pin_count=6)
    assert match.status == "UNKNOWN"
    assert "6 pins do not fit SOT23-5" in match.reason


def test_thin_variant_shares_land_pattern_with_lower_height() -> None:
    thin = tables().groups["TSOT23-5"]
    regular = tables().groups["SOT23-5"]
    assert thin.land_pattern == regular.name
    assert thin.height_max_mm is not None
    assert regular.height_max_mm is not None
    assert thin.height_max_mm < regular.height_max_mm


def test_sot23_5_and_6_stay_separate() -> None:
    a, b = package_group("SOT-23-5").group, package_group("SOT-23-6").group
    assert a is not None
    assert b is not None
    assert a.name != b.name


def test_key_ignores_case_spaces_and_dashes() -> None:
    assert key("sot-23 - 5") == key(f"SOT23{EN_DASH}5") == "SOT235"
