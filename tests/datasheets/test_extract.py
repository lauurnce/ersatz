import pytest

from ersatz.budget.spend import SpendCapError, SpendLedger
from ersatz.cache import SqliteCache
from ersatz.datasheets.extract import extractor_version, run_extraction
from ersatz.datasheets.pages import PageText
from ersatz.llm.base import LLMError
from ersatz.model import Category
from tests.datasheets.test_schema import EXAMPLE
from tests.llm.fakes import FakeLLM

PAGES = [PageText(page=n, text=f"page {n} text", chars=500) for n in range(1, 4)]


def ledger(cap: float = 5.0) -> SpendLedger:
    return SpendLedger(SqliteCache(":memory:"), run_cap_usd=cap)


def test_extraction_parses_reply_and_records_spend() -> None:
    llm = FakeLLM(EXAMPLE)
    book = ledger()
    raw, run = run_extraction(PAGES, [1, 3], Category.LDO, "TEST-LDO1", llm, book)
    assert raw.parameters[0].name == "dropout"
    assert run.pages == (1, 3)
    assert run.request_id == "req_fake"
    assert run.call.cost_usd > 0
    assert book.run_spent == pytest.approx(run.call.cost_usd)
    sent = llm.requests[0]
    assert "=== PAGE 3 ===" in sent["user"]
    assert "=== PAGE 2 ===" not in sent["user"]
    assert sent["schema"]["type"] == "object"


def test_schema_mismatch_raises_after_recording_spend() -> None:
    book = ledger()
    with pytest.raises(LLMError, match="does not match"):
        run_extraction(PAGES, [1], Category.LDO, None, FakeLLM({"parameters": "x"}), book)
    assert book.run_spent > 0


def test_cap_refuses_before_the_call() -> None:
    llm = FakeLLM(EXAMPLE)
    with pytest.raises(SpendCapError):
        run_extraction(PAGES, [1], Category.LDO, None, llm, ledger(cap=0.01))
    assert llm.requests == []


def test_extractor_version_names_model_schema_and_prompt() -> None:
    assert extractor_version("claude-opus-5-5") == "claude-opus-5-5/s1/p1"
