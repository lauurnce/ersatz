"""Map provider lifecycle strings to the Ersatz enum (rules/lifecycle.yaml)."""

from datetime import date
from typing import Any

from ersatz.model import Lifecycle
from ersatz.rules import load


def map_lifecycle(
    provider: str, raw: str | None, last_buy: date | None = None, today: date | None = None
) -> Lifecycle:
    """Return the Ersatz status. Unlisted or missing strings are UNKNOWN."""
    if raw is None or not raw.strip():
        return Lifecycle.UNKNOWN
    rules: dict[str, Any] = load("lifecycle")["providers"].get(provider, {})
    wanted = raw.strip().casefold()
    for text, value in (rules.get("map") or {}).items():
        if text.casefold() == wanted:
            return Lifecycle(value)
    eol = any(wanted == t.casefold() for t in rules.get("eol_with_future_last_buy", []))
    if eol and last_buy is not None and last_buy > (today or date.today()):
        return Lifecycle.LAST_TIME_BUY
    return Lifecycle.UNKNOWN
