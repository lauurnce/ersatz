"""ersatz extract with a fake model and a generated PDF. No network, no cost."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from ersatz.cli import app
from ersatz.datasheets.fetch import DatasheetFetchError, DatasheetFile, load_local
from ersatz.llm.base import LLMError
from ersatz.notice import NOTICE
from ersatz.settings import get_settings
from tests.datasheets.pdfgen import write_pdf
from tests.datasheets.test_pipeline import PDF_PAGES, reply
from tests.llm.fakes import FakeLLM


@pytest.fixture
def setup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Any:
    pdf = write_pdf(tmp_path / "ds.pdf", PDF_PAGES)
    clock = datetime(2026, 10, 17, tzinfo=UTC)

    def fake_fetch(url: str, cache: Any, cache_dir: Path) -> DatasheetFile:
        return load_local(pdf, url, cache_dir, lambda: clock)

    monkeypatch.setattr("ersatz.cli.extract.fetch", fake_fetch)
    monkeypatch.setattr("ersatz.cli.extract.factory.make_llm", lambda s: FakeLLM(reply()))
    monkeypatch.setenv("ERSATZ_CACHE_DIR", str(tmp_path / "cache"))
    get_settings.cache_clear()
    yield monkeypatch
    get_settings.cache_clear()


URL = "https://example.invalid/test-ldo1.pdf"


def test_extract_prints_cited_values(setup: Any) -> None:
    result = CliRunner().invoke(app, ["extract", URL, "--category", "ldo", "--device", "TEST-LDO1"])
    assert result.exit_code == 0, result.output
    assert "dropout" in result.output
    assert "HIGH" in result.output
    assert "Dropped by quote verification or validation: 1" in result.output
    assert "quote not found on page 3" in result.output
    assert NOTICE in result.output


def test_extract_json(setup: Any) -> None:
    result = CliRunner().invoke(app, ["extract", URL, "--category", "ldo", "--json"])
    data = json.loads(result.output)
    assert data["extraction"]["parameters"][0]["parameter"]["source"]["page"] == 3
    assert data["notice"] == NOTICE


def test_extract_without_a_key_exits_2(setup: Any) -> None:
    def no_key(settings: Any) -> Any:
        raise LLMError("ANTHROPIC_API_KEY is empty; set it in .env to run extraction")

    setup.setattr("ersatz.cli.extract.factory.make_llm", no_key)
    result = CliRunner().invoke(app, ["extract", URL, "--category", "ldo"])
    assert result.exit_code == 2
    assert "ANTHROPIC_API_KEY is empty" in result.output


def test_extract_fetch_error_exits_2(setup: Any) -> None:
    def blocked(url: str, cache: Any, cache_dir: Path) -> DatasheetFile:
        raise DatasheetFetchError(f"{url}: HTTP 403")

    setup.setattr("ersatz.cli.extract.fetch", blocked)
    result = CliRunner().invoke(app, ["extract", URL, "--category", "opamp"])
    assert result.exit_code == 2
    assert "HTTP 403" in result.output


def test_extract_rejects_unknown_category(setup: Any) -> None:
    assert CliRunner().invoke(app, ["extract", URL, "--category", "mosfet"]).exit_code == 2
