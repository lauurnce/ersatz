from datetime import UTC, datetime
from pathlib import Path

import pytest

from ersatz.budget.spend import SpendLedger
from ersatz.cache import SqliteCache
from ersatz.datasheets.fetch import DatasheetFile, load_local
from ersatz.datasheets.report import render
from ersatz.datasheets.scoring import GoldFile, GoldLabel
from ersatz.llm.base import LLMError
from ersatz.model import Category
from scripts.eval_extraction import _reason_group, evaluate, file_getter
from tests.datasheets.test_pipeline import PDF_PAGES, reply
from tests.llm.fakes import FakeLLM

CLOCK = datetime(2026, 11, 10, tzinfo=UTC)


def make_gold(sha256: str, gid: str = "test-ldo") -> GoldFile:
    labels = [
        {"kind": "parameter", "name": "dropout", "typ": 0.25, "max": 0.35, "pages": [3]},
        {"kind": "parameter", "name": "iq", "typ": 1.6e-6, "max": 4e-6, "pages": [2]},
        {"kind": "parameter", "name": "psrr", "typ": 60, "pages": [3]},
        {"kind": "pin", "package": "SOT-23", "number": "1", "function": "IN", "pages": [2]},
    ]
    return GoldFile(
        id=gid,
        category=Category.LDO,
        device="TEST-LDO1",
        manufacturer="Test",
        url="https://example.invalid/ds.pdf",
        sha256=sha256,
        revision=None,
        status="DRAFT",
        labels=tuple(GoldLabel.model_validate(label) for label in labels),
    )


@pytest.fixture
def datasheet(tmp_path: Path) -> DatasheetFile:
    from tests.datasheets.pdfgen import write_pdf

    pdf = write_pdf(tmp_path / "test-ldo.pdf", PDF_PAGES)
    return load_local(pdf, "https://example.invalid/ds.pdf", tmp_path / "cache", lambda: CLOCK)


def test_evaluate_scores_and_renders_failures(datasheet: DatasheetFile) -> None:
    cache = SqliteCache(":memory:")
    gold = make_gold(datasheet.sha256)
    run = evaluate(
        [gold],
        lambda g: datasheet,
        FakeLLM(reply()),
        SpendLedger(cache, 5.0),
        cache,
        clock=lambda: CLOCK,
    )
    outcomes = [s.outcome.value for s in run.scores]
    assert outcomes == ["CORRECT", "CORRECT", "MISSING", "CORRECT"]
    assert [s.cited_ok for s in run.scores] == [True, False, False, True]
    sheet = run.datasheets[0]
    assert (sheet.dropped, sheet.error, sheet.cached) == (1, None, False)
    assert sheet.cost_usd > 0
    text = render(run)
    assert "| parameter | 3 | 2 | 0 | 1 | 67% | 50% |" in text
    assert "| test-ldo | parameter:psrr psrr | MISSING |" in text
    assert "quote not found on page N" in text
    assert "Labels are drafts" in text
    assert "Notice: Ersatz results are not engineering sign-off." in text


def test_hash_mismatch_is_reported_without_a_call(datasheet: DatasheetFile) -> None:
    cache = SqliteCache(":memory:")
    llm = FakeLLM()
    run = evaluate([make_gold("00" * 32)], lambda g: datasheet, llm, SpendLedger(cache, 5.0), cache)
    assert "differs from the label file" in str(run.datasheets[0].error)
    assert llm.requests == []
    assert run.scores == ()


def test_cached_only_skips_datasheets_without_a_reply(datasheet: DatasheetFile) -> None:
    cache = SqliteCache(":memory:")
    llm = FakeLLM()
    gold = make_gold(datasheet.sha256)
    run = evaluate(
        [gold], lambda g: datasheet, llm, SpendLedger(cache, 5.0), cache, cached_only=True
    )
    assert "--cached-only" in str(run.datasheets[0].error)
    assert llm.requests == []


def test_model_errors_are_recorded(datasheet: DatasheetFile) -> None:
    cache = SqliteCache(":memory:")
    llm = FakeLLM(LLMError("anthropic: stopped with max_tokens"))
    run = evaluate(
        [make_gold(datasheet.sha256)], lambda g: datasheet, llm, SpendLedger(cache, 5.0), cache
    )
    assert "max_tokens" in str(run.datasheets[0].error)


def test_file_getter_prefers_a_local_copy(datasheet: DatasheetFile, tmp_path: Path) -> None:
    get = file_getter(SqliteCache(":memory:"), tmp_path / "cache", tmp_path)
    file = get(make_gold(datasheet.sha256))
    assert file.sha256 == datasheet.sha256


def test_reason_groups_hide_numbers_and_values() -> None:
    assert _reason_group("value '35' not in quote") == "value 'X' not in quote"
    assert _reason_group("quote not found on page 12") == "quote not found on page N"
