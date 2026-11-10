import pytest

from ersatz.budget.spend import (
    SpendCapError,
    SpendLedger,
    cost,
    estimate_tokens,
    price,
)
from ersatz.cache import SqliteCache
from ersatz.llm.base import Usage
from tests.clock import FakeClock

MODEL = "claude-opus-5-5"


def test_cost_uses_per_million_prices() -> None:
    usage = Usage(input_tokens=1_000_000, output_tokens=100_000)
    assert cost(MODEL, usage) == pytest.approx(4.0 + 2.0)


def test_cache_tokens_are_priced() -> None:
    usage = Usage(
        input_tokens=0,
        output_tokens=0,
        cache_read_input_tokens=1_000_000,
        cache_creation_input_tokens=1_000_000,
    )
    assert cost(MODEL, usage) == pytest.approx(0.20 + 5.00)


def test_unknown_model_is_refused() -> None:
    with pytest.raises(SpendCapError, match="no price"):
        price("some-model")


def test_estimate_rounds_up() -> None:
    assert estimate_tokens("abcd") == 2
    assert estimate_tokens("ab", "c") == 1


def test_record_adds_to_run_and_total() -> None:
    cache = SqliteCache(":memory:")
    ledger = SpendLedger(cache, run_cap_usd=5.0, clock=FakeClock())
    record = ledger.record(MODEL, Usage(input_tokens=10_000, output_tokens=1_000), "extract")
    assert record.cost_usd == pytest.approx(0.06)
    assert ledger.run_spent == pytest.approx(0.06)
    assert SpendLedger(cache, run_cap_usd=5.0).total_spent() == pytest.approx(0.06)


def test_run_cap_refuses_a_call_that_could_cross_it() -> None:
    ledger = SpendLedger(SqliteCache(":memory:"), run_cap_usd=0.10)
    ledger.check(MODEL, input_tokens=5_000, max_tokens=2_000)
    with pytest.raises(SpendCapError, match="run cap"):
        ledger.check(MODEL, input_tokens=5_000, max_tokens=16_000)


def test_total_cap_counts_earlier_runs() -> None:
    cache = SqliteCache(":memory:")
    first = SpendLedger(cache, run_cap_usd=100.0, total_cap_usd=1.0)
    first.record(MODEL, Usage(input_tokens=200_000, output_tokens=0), "extract")
    second = SpendLedger(cache, run_cap_usd=100.0, total_cap_usd=1.0)
    with pytest.raises(SpendCapError, match="total cap"):
        second.check(MODEL, input_tokens=10_000, max_tokens=16_000)
