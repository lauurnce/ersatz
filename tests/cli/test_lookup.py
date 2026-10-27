"""ersatz lookup output, with the provider replaced by a fixture-backed fake."""

import json

import pytest
from typer.testing import CliRunner

from ersatz.cli import app
from ersatz.notice import NOTICE
from tests.providers.fakes import Router, json_response, make_digikey


@pytest.fixture(autouse=True)
def fake_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    router = Router(
        json_response(200, "productdetails_ldo.json"), json_response(404, "error_404.json")
    )
    provider, _, _ = make_digikey(router)
    monkeypatch.setattr("ersatz.cli.lookup.build_digikey", lambda *a, **k: provider)
    monkeypatch.setenv("ERSATZ_CACHE_DIR", ":memory:")


def test_text_output_shows_source_and_notice() -> None:
    result = CliRunner().invoke(app, ["lookup", "TEST-LDO33", "TEST-NOPE"])
    assert result.exit_code == 0, result.output
    assert "TEST-LDO33  (Test Semiconductor)" in result.output
    assert "source     digikey response" in result.output
    assert "TEST-NOPE (as entered)  NOT FOUND at digikey" in result.output
    assert result.output.strip().endswith(NOTICE)


def test_json_output_carries_notice() -> None:
    result = CliRunner().invoke(app, ["lookup", "TEST-LDO33", "--json"])
    data = json.loads(result.output)
    assert data["notice"] == NOTICE
    assert data["results"]["TEST-LDO33"][0]["source"]["provider"] == "digikey"
