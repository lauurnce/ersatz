"""Map provider taxonomies to the two v0.1 categories.

Everything that is not an LDO or an op-amp is OUT_OF_SCOPE. A category that
needs a parameter to decide, and lacks it or has an unlisted value, is
UNKNOWN. Nothing is guessed.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from ersatz.model import Category
from ersatz.rules import load

Scope = Literal["IN_SCOPE", "OUT_OF_SCOPE", "UNKNOWN"]


@dataclass(frozen=True)
class CategoryMatch:
    status: Scope
    reason: str
    category: Category | None = None


def _same(a: str, b: str) -> bool:
    return a.strip().casefold() == b.strip().casefold()


def map_category(
    provider: str, raw: str | None, parameters: Mapping[str, str] | None = None
) -> CategoryMatch:
    """Map a provider category string, and parameters where the rules need one."""
    if not raw or not raw.strip():
        return CategoryMatch("UNKNOWN", "no category in the provider record")
    rules: dict[str, Any] = load("categories")["providers"].get(provider, {})
    if not rules:
        return CategoryMatch("UNKNOWN", f"no category rules for provider {provider!r}")
    for name, rule in rules.items():
        if not any(_same(raw, c) for c in rule["categories"]):
            continue
        category = Category(name)
        field = rule.get("parameter")
        if field is None:
            return CategoryMatch("IN_SCOPE", f"{provider} category {raw!r}", category)
        value = (parameters or {}).get(field)
        if value is None:
            return CategoryMatch("UNKNOWN", f"{raw!r} needs {field!r} to decide")
        if any(_same(value, v) for v in rule.get("in_scope", [])):
            return CategoryMatch("IN_SCOPE", f"{raw!r} with {field} {value!r}", category)
        if any(_same(value, v) for v in rule.get("out_of_scope", [])):
            return CategoryMatch("OUT_OF_SCOPE", f"{field} {value!r} is not an op-amp")
        return CategoryMatch("UNKNOWN", f"{field} {value!r} is not in the rules")
    return CategoryMatch("OUT_OF_SCOPE", f"{provider} category {raw!r} is not covered in v0.1")
