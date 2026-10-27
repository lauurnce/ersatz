"""Daily request budget."""

from datetime import timedelta

import pytest

from ersatz.budget import BudgetExhaustedError, RequestBudget
from ersatz.cache import SqliteCache
from tests.clock import FakeClock


def test_spend_counts_until_limit() -> None:
    clock = FakeClock()
    budget = RequestBudget(SqliteCache(":memory:", clock=clock), "digikey", 2, clock=clock)
    budget.spend()
    budget.spend()
    assert budget.remaining() == 0
    with pytest.raises(BudgetExhaustedError, match="digikey"):
        budget.spend()


def test_budget_resets_next_day() -> None:
    clock = FakeClock()
    budget = RequestBudget(SqliteCache(":memory:", clock=clock), "digikey", 1, clock=clock)
    budget.spend()
    clock.advance(timedelta(days=1).total_seconds())
    assert budget.remaining() == 1
    budget.spend()
