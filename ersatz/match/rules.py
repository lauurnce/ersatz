"""Function rule sets per category, loaded from rules/match_*.yaml.

Each rule keeps its docs/DOMAIN.md ID. Hard filters (form, fit, lifecycle)
are code in ersatz.match.filters; soft function rules are data here.
"""

from enum import StrEnum
from functools import cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ersatz.model.category import Category
from ersatz.rules import load

Slot = Literal["min", "typ", "max"]


class Verdict(StrEnum):
    PASS = "PASS"  # noqa: S105 - a verdict, not a secret
    WARN = "WARN"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NA = "N/A"  # the rule does not apply to this original


class Kind(StrEnum):
    EQUAL = "equal"
    CONTAINS = "contains"
    HIGHER = "higher"
    LOWER = "lower"
    FEATURE_EQUAL = "feature_equal"
    FEATURE_IMPLIES = "feature_implies"
    CAP_STABILITY = "cap_stability"
    STABLE_GAIN = "stable_gain"
    PER_CHANNEL = "per_channel"


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    param: str
    kind: Kind
    broken: Literal["FAIL", "WARN"]
    weight: float = Field(gt=0)
    slots: tuple[Slot, ...] = ()
    condition: str | None = None
    far_above: float | None = None
    if_original_has: str | None = None
    unless_original_has: str | None = None
    sources: tuple[str, ...] = ()

    @property
    def broken_verdict(self) -> Verdict:
        return Verdict(self.broken)

    @property
    def better(self) -> str:
        """The direction that counts as better, for the diff table."""
        return {
            Kind.EQUAL: "equal",
            Kind.CONTAINS: "wider range",
            Kind.HIGHER: "higher",
            Kind.LOWER: "lower",
            Kind.FEATURE_EQUAL: "same",
            Kind.FEATURE_IMPLIES: "present if original has it",
            Kind.CAP_STABILITY: "stable with the original capacitor",
            Kind.STABLE_GAIN: "lower",
            Kind.PER_CHANNEL: "lower",
        }[self.kind]


class RuleSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: int
    category: Category
    rules: tuple[Rule, ...]


@cache
def rule_set(category: Category) -> RuleSet:
    rules = RuleSet.model_validate(load(f"match_{category.value}"))
    if rules.category is not category:
        raise ValueError(f"match_{category.value}.yaml declares {rules.category}")
    return rules
