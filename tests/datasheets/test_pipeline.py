from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ersatz.budget.spend import SpendLedger
from ersatz.cache import SqliteCache
from ersatz.datasheets.fetch import load_local
from ersatz.datasheets.pages import PageText
from ersatz.datasheets.pipeline import UnextractedError, extract_datasheet
from ersatz.model import Category, ParamName
from tests.datasheets.pdfgen import write_pdf
from tests.llm.fakes import FakeLLM

FILLER = "Typical characteristics and application notes for this regulator family." * 2

PDF_PAGES = [
    ["TEST-LDO1 300 mA LDO regulator", "TESTDOC1A - JANUARY 2026", FILLER],
    ["Pin Configuration", "1 VIN Input", "2 GND Ground", "3 VOUT Output", FILLER],
    [
        "Electrical Characteristics",
        "Dropout voltage IOUT = 150 mA 250 350 mV",
        "Quiescent current IOUT = 0 mA 1.6 4 uA",
        FILLER,
    ],
]


def cited(page: int, quote: str, **fields: Any) -> dict[str, Any]:
    return {"page": page, "quote": quote, **fields}


def reply() -> dict[str, Any]:
    def param(name: str, page: int, quote: str, **cols: str) -> dict[str, Any]:
        values = {"min": None, "typ": None, "max": None, **cols}
        unit = "mV" if name == "dropout" else "uA"
        return cited(page, quote, name=name, unit=unit, conditions="", variant=None, **values)

    return {
        "parameters": [
            param("dropout", 3, "Dropout voltage IOUT = 150 mA 250 350 mV", typ="250", max="350"),
            param("iq", 3, "Quiescent current IOUT = 0 mA 1.6 4 uA", typ="1.6", max="4"),
            param("iq", 3, "Quiescent current 0.9 uA", typ="0.9"),
        ],
        "packages": [],
        "pinouts": [
            {
                "package": "SOT-23",
                "pins": [
                    cited(2, "1 VIN Input", number="1", name="VIN", function="IN", channel=None),
                    cited(2, "2 GND Ground", number="2", name="GND", function="GND", channel=None),
                ],
            }
        ],
        "features": [],
    }


@pytest.fixture
def datasheet(tmp_path: Path) -> Any:
    pdf = write_pdf(tmp_path / "ds.pdf", PDF_PAGES)
    clock = datetime(2026, 11, 10, tzinfo=UTC)
    return load_local(pdf, "https://example.invalid/ds.pdf", tmp_path / "cache", lambda: clock)


def test_end_to_end_keeps_verified_values_and_drops_the_rest(datasheet: Any) -> None:
    cache = SqliteCache(":memory:")
    llm = FakeLLM(reply())
    ledger = SpendLedger(cache, run_cap_usd=5.0)
    result = extract_datasheet(datasheet, Category.LDO, llm, ledger, cache, device="TEST-LDO1")
    ex = result.extraction
    assert result.cached is False
    assert len(ex.values(ParamName.DROPOUT)) == 1
    assert len(ex.values(ParamName.IQ)) == 1
    assert ex.dropped[0].reason == "quote not found on page 3"
    dropout = ex.values(ParamName.DROPOUT)[0].parameter
    assert dropout.max == pytest.approx(0.35)
    assert dropout.source.sha256 == datasheet.sha256
    assert dropout.source.page == 3
    assert ex.pinouts[0].pinout.pins[0].number == "1"
    assert "Target device: TEST-LDO1." in llm.requests[0]["user"]


def test_second_run_uses_the_cached_reply(datasheet: Any) -> None:
    cache = SqliteCache(":memory:")
    ledger = SpendLedger(cache, run_cap_usd=5.0)
    first = extract_datasheet(datasheet, Category.LDO, FakeLLM(reply()), ledger, cache)
    llm = FakeLLM()
    second = extract_datasheet(datasheet, Category.LDO, llm, ledger, cache)
    assert second.cached is True
    assert llm.requests == []
    assert second.extraction == first.extraction


def test_image_only_pdf_is_unextracted(datasheet: Any) -> None:
    blank = [PageText(page=n, text="", chars=0) for n in (1, 2, 3)]
    cache = SqliteCache(":memory:")
    llm = FakeLLM()
    with pytest.raises(UnextractedError):
        extract_datasheet(datasheet, Category.LDO, llm, SpendLedger(cache, 5.0), cache, pages=blank)
    assert llm.requests == []
