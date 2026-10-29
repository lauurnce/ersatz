"""Lifecycle mapping per provider (DOMAIN.md section 1)."""

from datetime import date

import pytest

from ersatz.model import Lifecycle
from ersatz.normalize.lifecycle import map_lifecycle


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Active", Lifecycle.ACTIVE),
        ("active", Lifecycle.ACTIVE),
        ("Not Recommended for New Design", Lifecycle.NRND),
        ("Not For New Designs", Lifecycle.NRND),
        ("Last Time Buy", Lifecycle.LAST_TIME_BUY),
        ("Obsolete", Lifecycle.OBSOLETE),
        ("Discontinued at Digi-Key", Lifecycle.UNKNOWN),
        ("Preview", Lifecycle.UNKNOWN),
        ("Something unseen", Lifecycle.UNKNOWN),
        (None, Lifecycle.UNKNOWN),
        ("", Lifecycle.UNKNOWN),
    ],
)
def test_digikey(raw: str | None, expected: Lifecycle) -> None:
    assert map_lifecycle("digikey", raw) is expected


def test_nexar_eol_depends_on_last_buy_date() -> None:
    today = date(2026, 11, 9)
    assert map_lifecycle("nexar", "EOL", date(2027, 1, 1), today) is Lifecycle.LAST_TIME_BUY
    assert map_lifecycle("nexar", "EOL", date(2026, 1, 1), today) is Lifecycle.UNKNOWN
    assert map_lifecycle("nexar", "EOL", None, today) is Lifecycle.UNKNOWN
    assert map_lifecycle("nexar", "Production") is Lifecycle.ACTIVE


def test_mouser_values_are_unknown_until_documented() -> None:
    assert map_lifecycle("mouser", "Active") is Lifecycle.UNKNOWN
