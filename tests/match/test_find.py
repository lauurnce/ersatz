"""find end to end on Digi-Key-shaped synthetic records through a fake provider."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ersatz.cli import app
from ersatz.cli.find import render, run_find
from ersatz.match.filters import Fit
from ersatz.match.find import FindError, find
from ersatz.settings import Settings
from tests.match.fakes import FakeProvider, record

LDO = {
    "Voltage - Input (Min)": "2.5V",
    "Voltage - Input (Max)": "6V",
    "Voltage - Output (Min/Fixed)": "3.3V",
    "Current - Output": "300mA",
    "Voltage Dropout (Max)": "0.35V @ 300mA",
    "Current - Quiescent (Iq)": "55 µA",
}
ORIGINAL = record("TEST-LDO-OLD", lifecycle="Obsolete", parameters=LDO)
BETTER = record(
    "TEST-LDO-A",
    manufacturer="Alpha Test",
    parameters={**LDO, "Current - Output": "500mA", "Voltage Dropout (Max)": "0.25V @ 300mA"},
    stock=10,
)
WORSE = record(
    "TEST-LDO-B",
    manufacturer="Beta Test",
    parameters={**LDO, "Voltage Dropout (Max)": "0.6V @ 300mA"},
    stock=5000,
)
OTHER_PACKAGE = record("TEST-LDO-C", package="SOT-89-3", parameters=LDO)
INACTIVE = record("TEST-LDO-D", lifecycle="Obsolete", parameters=LDO)


def provider() -> FakeProvider:
    return FakeProvider(
        "digikey",
        [ORIGINAL, BETTER, WORSE, OTHER_PACKAGE, INACTIVE],
        parametric=False,
        results=[WORSE, OTHER_PACKAGE, ORIGINAL, INACTIVE, BETTER],
    )


def test_find_ranks_and_excludes() -> None:
    result = find("TEST-LDO-OLD", [provider()])
    assert [c.mpn for c in result.top] == ["TEST-LDO-A", "TEST-LDO-B"]
    assert result.candidates_searched == 4
    assert {e.mpn for e in result.report.excluded} == {"TEST-LDO-C", "TEST-LDO-D"}
    assert result.top[0].filters.fit.fit is Fit.UNKNOWN  # provider data has no pinout
    assert "used keyword search" in result.notes[0]
    assert result.notice.startswith("Ersatz results are not engineering sign-off")


def test_top_limits_the_list() -> None:
    assert len(find("TEST-LDO-OLD", [provider()], top=1).top) == 1


def test_not_found_and_ambiguous_originals() -> None:
    with pytest.raises(FindError, match="NOT FOUND"):
        find("TEST-NOPE", [provider()])
    twin = record("TEST-LDO-OLD", manufacturer="Other Co", parameters=LDO)
    ambiguous = FakeProvider("digikey", [ORIGINAL, twin])
    with pytest.raises(FindError, match="pass --manufacturer"):
        find("TEST-LDO-OLD", [ambiguous])
    assert (
        find("TEST-LDO-OLD", [ambiguous], manufacturer="Test Semi").original.mpn == "TEST-LDO-OLD"
    )


def test_uncategorized_original_is_rejected() -> None:
    odd = record("TEST-ODD", category="Resistors")
    with pytest.raises(FindError, match="category"):
        find("TEST-ODD", [FakeProvider("digikey", [odd])])


def test_render_shows_diff_sources_and_notice() -> None:
    text = render(find("TEST-LDO-OLD", [provider()]))
    assert "1. TEST-LDO-A (Alpha Test)  fit UNKNOWN" in text
    assert "dropout" in text
    assert "LDO-08" in text
    assert "digikey " in text
    assert "Excluded:" in text
    assert "TEST-LDO-D (Test Semi): lifecycle: OBSOLETE, not ACTIVE" in text
    assert text.rstrip().endswith("Every replacement must be validated by an engineer.")


def test_run_find_prints_json(capsys: pytest.CaptureFixture[str]) -> None:
    run_find("TEST-LDO-OLD", [provider()], None, 5, 25, as_json=True)
    payload = json.loads(capsys.readouterr().out)
    assert payload["notice"].startswith("Ersatz results")
    assert payload["top"][0]["mpn"] == "TEST-LDO-A"


def test_cli_reports_missing_credentials(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = Settings(_env_file=None, ersatz_cache_dir=tmp_path)
    monkeypatch.setattr("ersatz.cli.find.get_settings", lambda: settings)
    result = CliRunner().invoke(app, ["find", "TEST-LDO-OLD"])
    assert result.exit_code == 2
    assert "error:" in result.output
