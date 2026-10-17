"""ersatz lookup output, with the provider replaced by a fixture-backed fake."""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ersatz.cli import app
from ersatz.notice import NOTICE
from ersatz.settings import get_settings
from tests.providers.fakes import Router, json_response, make_digikey


@pytest.fixture(autouse=True)
def fake_provider(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    router = Router(
        json_response(200, "productdetails_ldo.json"), json_response(404, "error_404.json")
    )
    provider, _, _ = make_digikey(router)
    monkeypatch.setattr("ersatz.cli.output.build_providers", lambda *a, **k: [provider])
    monkeypatch.setenv("ERSATZ_CACHE_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_text_output_shows_source_and_notice() -> None:
    result = CliRunner().invoke(app, ["lookup", "TEST-LDO33", "TEST-NOPE"])
    assert result.exit_code == 4, result.output
    assert "TEST-LDO33  (Test Semiconductor)" in result.output
    assert "source     digikey response" in result.output
    assert "TEST-NOPE (as entered)  NOT FOUND at digikey" in result.output
    assert result.output.strip().endswith(NOTICE)
    assert "Notice:" in result.output


def test_json_output_carries_notice() -> None:
    result = CliRunner().invoke(app, ["lookup", "TEST-LDO33", "--json"])
    data = json.loads(result.output)
    assert data["notice"] == NOTICE
    assert data["results"]["TEST-LDO33"][0]["record"]["source"]["provider"] == "digikey"


def test_normalize_shows_before_and_after() -> None:
    result = CliRunner().invoke(app, ["lookup", "TEST-LDO33", "--normalize"])
    assert result.exit_code == 0, result.output
    assert "  - Voltage - Output (Min/Fixed): 3.3V" in result.output
    assert "    package    SOT223 (matched)" in result.output
    assert "vout            min        -  typ      3.3  max        -  V" in result.output
    assert "@ I=0.5 A" in result.output


def test_normalize_json_has_part() -> None:
    result = CliRunner().invoke(app, ["lookup", "TEST-LDO33", "--json", "--normalize"])
    part = json.loads(result.output)["results"]["TEST-LDO33"][0]["part"]
    assert part["parameters"]["vout"]["typ"] == 3.3
    assert part["mpn"]["source"]["provider"] == "digikey"
