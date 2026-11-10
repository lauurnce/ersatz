"""Extraction on stored synthetic page text with a fake model reply."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ersatz.budget.spend import SpendLedger
from ersatz.cache import SqliteCache
from ersatz.datasheets.fetch import DatasheetFile
from ersatz.datasheets.pages import PageText
from ersatz.datasheets.pipeline import extract_datasheet
from ersatz.datasheets.validate import Confidence
from ersatz.model import Category, ParamName, PinFunction
from tests.llm.fakes import FakeLLM

FIXTURE = Path(__file__).parent.parent / "fixtures" / "datasheets" / "test_opa2_pages.json"


def load() -> tuple[str, list[PageText]]:
    data = json.loads(FIXTURE.read_text())
    assert data["synthetic"] is True
    pages = [PageText(page=p["page"], text=p["text"], chars=len(p["text"])) for p in data["pages"]]
    return data["device"], pages


def param(name: str, quote: str, unit: str, **cols: str) -> dict[str, Any]:
    values = {"min": None, "typ": None, "max": None, **cols}
    return {
        "name": name,
        "unit": unit,
        "conditions": "",
        "variant": None,
        "page": 5,
        "quote": quote,
        **values,
    }


def pin(number: str, name: str, function: str, channel: int | None) -> dict[str, Any]:
    line = {
        "1": "1 OUTA O Output, channel A",
        "2": "2 -INA I Inverting input, channel A",
        "3": "3 +INA I Noninverting input, channel A",
        "4": "4 V- - Negative supply",
        "8": "8 V+ - Positive supply",
    }[number]
    return {
        "number": number,
        "name": name,
        "function": function,
        "channel": channel,
        "page": 3,
        "quote": line,
    }


REPLY = {
    "parameters": [
        param(
            "vos", "VOS Input offset voltage VCM = VS / 2 0.5 4.5 mV", "mV", typ="0.5", max="4.5"
        ),
        param("ibias", "IB Input bias current 1 10 pA", "pA", typ="1", max="10"),
        param("gbw", "GBW Gain-bandwidth product CL = 100 pF 1 MHz", "MHz", typ="1"),
        param("slew_rate", "SR Slew rate G = +1 0.6 V/us", "V/us", typ="0.6"),
        param("iq_per_channel", "per amplifier IO = 0 mA 100 150 uA", "uA", typ="100", max="150"),
        param("gbw", "GBW Gain-bandwidth product 10 MHz", "MHz", typ="10"),
    ],
    "packages": [{"name": "SOIC", "pin_count": 8, "page": 1, "quote": "TEST-OPA2 SOIC (8)"}],
    "pinouts": [
        {
            "package": "SOIC",
            "pins": [
                pin("1", "OUTA", "OUT", 1),
                pin("2", "-INA", "INN", 1),
                pin("3", "+INA", "INP", 1),
                pin("4", "V-", "VEE", None),
                pin("8", "V+", "VCC", None),
            ],
        }
    ],
    "features": [
        {"name": "rail_to_rail_output", "value": True, "page": 1, "quote": "Rail-to-rail output"},
        {"name": "unity_gain_stable", "value": True, "page": 1, "quote": "Unity-gain stable"},
    ],
}


class Responder:
    def __call__(self, system: str, user: str) -> dict[str, Any]:
        return REPLY


def test_stored_page_text_extracts_and_drops_the_invented_row(tmp_path: Path) -> None:
    device, pages = load()
    file = DatasheetFile(
        url="https://example.invalid/test-opa2.pdf",
        sha256="cd" * 32,
        path=tmp_path / "missing.pdf",
        size=0,
        fetched_at=datetime(2026, 11, 10, tzinfo=UTC),
    )
    cache = SqliteCache(":memory:")
    llm = FakeLLM(responder=Responder())
    result = extract_datasheet(
        file, Category.OPAMP, llm, SpendLedger(cache, 5.0), cache, device=device, pages=pages
    )
    ex = result.extraction
    assert ex.datasheet.revision is None
    gbw = ex.values(ParamName.GBW)
    assert [g.parameter.typ for g in gbw] == [1e6]
    assert ex.values(ParamName.SLEW_RATE)[0].parameter.typ == pytest.approx(6e5)
    assert ex.values(ParamName.IBIAS)[0].parameter.max == pytest.approx(1e-11)
    assert [d.reason for d in ex.dropped] == ["quote not found on page 5"]
    assert all(p.confidence is Confidence.HIGH for p in ex.parameters)
    functions = [p.function for p in ex.pinouts[0].pinout.pins]
    assert functions[:3] == [PinFunction.OUT, PinFunction.INN, PinFunction.INP]
    assert {f.name for f in ex.features} == {"rail_to_rail_output", "unity_gain_stable"}
    assert "=== PAGE 5 ===" in llm.requests[0]["user"]
