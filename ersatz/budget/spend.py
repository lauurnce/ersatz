"""LLM spend ledger with hard caps, checked before every call.

The worst-case cost of a call (estimated input plus max_tokens of output)
must fit under both the v0.1 total cap and the per-run cap, or the call is
refused. After the call, the real cost from the reported usage is added.
Not safe across processes that share one cache file; v0.1 runs one process.
"""

import json
import math
from collections.abc import Callable
from datetime import UTC, datetime

from pydantic import BaseModel

from ersatz.cache.base import Cache, DataKind
from ersatz.llm.base import Usage

TOTAL_CAP_USD = 150.0

# USD per million tokens: input, output, cache read, cache write (5 minute,
# 1.25 times input). Models without a listed price are refused.
# Source: https://platform.claude.com/docs/en/about-claude/pricing
PRICES: dict[str, tuple[float, float, float, float]] = {
    "claude-opus-5-5": (4.00, 20.00, 0.20, 5.00),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20, 2.50),
}

# A conservative token estimate: about 3 characters per token for datasheet
# text with many numbers and symbols, so the estimate runs high, not low.
CHARS_PER_TOKEN = 3.0

_TOTAL_KEY = "total"


class SpendCapError(Exception):
    """The call could cross the total or per-run spend cap."""


class CallRecord(BaseModel, frozen=True):
    at: datetime
    model: str
    purpose: str
    usage: Usage
    cost_usd: float


def _utcnow() -> datetime:
    return datetime.now(UTC)


def price(model: str) -> tuple[float, float, float, float]:
    try:
        return PRICES[model]
    except KeyError:
        raise SpendCapError(f"no price for model {model!r}; add it to PRICES first") from None


def estimate_tokens(*texts: str) -> int:
    return math.ceil(sum(len(t) for t in texts) / CHARS_PER_TOKEN)


def cost(model: str, usage: Usage) -> float:
    p_in, p_out, p_read, p_write = price(model)
    total = (
        usage.input_tokens * p_in
        + usage.output_tokens * p_out
        + usage.cache_read_input_tokens * p_read
        + usage.cache_creation_input_tokens * p_write
    )
    return total / 1_000_000


class SpendLedger:
    def __init__(
        self,
        cache: Cache,
        run_cap_usd: float,
        total_cap_usd: float = TOTAL_CAP_USD,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._cache = cache
        self._run_cap = run_cap_usd
        self._total_cap = total_cap_usd
        self._clock = clock
        self.run_spent = 0.0
        self.records: list[CallRecord] = []

    def total_spent(self) -> float:
        entry = self._cache.get(DataKind.LLM_SPEND, _TOTAL_KEY)
        return float(entry.payload) if entry else 0.0

    def worst_case(self, model: str, input_tokens: int, max_tokens: int) -> float:
        p_in, p_out, _, p_write = price(model)
        return (input_tokens * max(p_in, p_write) + max_tokens * p_out) / 1_000_000

    def check(self, model: str, input_tokens: int, max_tokens: int) -> None:
        """Raise SpendCapError if the worst case could cross a cap."""
        worst = self.worst_case(model, input_tokens, max_tokens)
        if self.run_spent + worst > self._run_cap:
            raise SpendCapError(
                f"run cap {self._run_cap:.2f} USD: spent {self.run_spent:.4f}, "
                f"next call could cost {worst:.4f}"
            )
        total = self.total_spent()
        if total + worst > self._total_cap:
            raise SpendCapError(
                f"total cap {self._total_cap:.2f} USD: spent {total:.4f}, "
                f"next call could cost {worst:.4f}"
            )

    def record(self, model: str, usage: Usage, purpose: str) -> CallRecord:
        amount = cost(model, usage)
        now = self._clock()
        record = CallRecord(at=now, model=model, purpose=purpose, usage=usage, cost_usd=amount)
        self.run_spent += amount
        self.records.append(record)
        total = self.total_spent() + amount
        self._cache.put(DataKind.LLM_SPEND, _TOTAL_KEY, f"{total:.6f}".encode())
        key = f"call:{now.isoformat()}:{len(self.records)}"
        self._cache.put(
            DataKind.LLM_SPEND, key, json.dumps(record.model_dump(mode="json")).encode()
        )
        return record
