"""Score extractions against hand-labeled ground truth.

Field accuracy: share of labels whose value was extracted correctly.
Citation accuracy: share of correct values whose cited page is one of the
pages the label lists. Labels live in eval/extraction/gold/*.yaml.
"""

import math
import re
from collections import defaultdict
from enum import StrEnum
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from ersatz.datasheets.validate import Extraction
from ersatz.model.category import Category

REL_TOL = 0.01
SLOTS = ("min", "typ", "max")


class GoldLabel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["parameter", "package", "pin", "feature"]
    pages: tuple[int, ...]
    name: str | None = None
    alt_names: tuple[str, ...] = ()
    min: float | None = None
    typ: float | None = None
    max: float | None = None
    any_slot: bool = False
    pin_count: int | None = None
    package: str | tuple[str, ...] | None = None
    number: str | None = None
    function: str | None = None
    value: bool | None = None
    note: str | None = None

    @property
    def field_type(self) -> str:
        return f"parameter:{self.name}" if self.kind == "parameter" else self.kind

    @property
    def label(self) -> str:
        if self.kind == "pin":
            return f"pin {self.number}"
        return str(self.name)


class GoldFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    category: Category
    device: str
    manufacturer: str
    url: str
    sha256: str
    revision: str | None
    status: Literal["DRAFT", "REVIEWED"]
    labels: tuple[GoldLabel, ...] = Field(min_length=1)


def load_gold(folder: Path) -> list[GoldFile]:
    return [
        GoldFile.model_validate(yaml.safe_load(path.read_text()))
        for path in sorted(folder.glob("*.yaml"))
    ]


class Outcome(StrEnum):
    CORRECT = "CORRECT"
    WRONG = "WRONG"
    MISSING = "MISSING"


class LabelScore(BaseModel, frozen=True):
    datasheet: str
    field_type: str
    label: str
    outcome: Outcome
    cited_ok: bool
    expected: str
    got: str


def close(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return False
    return math.isclose(a, b, rel_tol=REL_TOL, abs_tol=1e-15)


def _compact(text: str) -> str:
    return re.sub(r"[^0-9a-z]", "", text.lower())


def _fmt(values: dict[str, float | None]) -> str:
    shown = [f"{k}={v:g}" for k, v in values.items() if v is not None]
    return ", ".join(shown) or "-"


def _score_parameter(label: GoldLabel, ex: Extraction) -> tuple[Outcome, bool, str]:
    names = {label.name, *label.alt_names}
    found = [p.parameter for p in ex.parameters if p.parameter.name.value in names]
    if not found:
        return Outcome.MISSING, False, "-"
    expected = {s: getattr(label, s) for s in SLOTS if getattr(label, s) is not None}
    matches = []
    for p in found:
        if label.any_slot:
            target = next(iter(expected.values()))
            ok = any(close(getattr(p, s), target) for s in SLOTS)
        else:
            ok = all(close(getattr(p, s), v) for s, v in expected.items())
        if ok:
            matches.append(p)
    got = "; ".join(f"{_fmt({s: getattr(p, s) for s in SLOTS})} p{p.source.page}" for p in found)
    if not matches:
        return Outcome.WRONG, False, got
    cited = any(p.source.page in label.pages for p in matches)
    return Outcome.CORRECT, cited, got


def _score_package(label: GoldLabel, ex: Extraction) -> tuple[Outcome, bool, str]:
    want = _compact(str(label.name))
    found = [p for p in ex.packages if want in _compact(p.raw_name)]
    if not found:
        return Outcome.MISSING, False, "-"
    got = "; ".join(f"{p.raw_name} ({p.pin_count} pins) p{p.source.page}" for p in found)
    matches = [
        p for p in found if label.pin_count is None or p.pin_count in (None, label.pin_count)
    ]
    if not matches:
        return Outcome.WRONG, False, got
    return Outcome.CORRECT, any(p.source.page in label.pages for p in matches), got


def _score_pin(label: GoldLabel, ex: Extraction) -> tuple[Outcome, bool, str]:
    hints = label.package if isinstance(label.package, tuple) else (str(label.package),)
    wanted = [_compact(h) for h in hints]
    pinouts = [p for p in ex.pinouts if any(w in _compact(p.package) for w in wanted)]
    pins = [
        (pin, po.pinout.source.page)
        for po in pinouts
        for pin in po.pinout.pins
        if pin.number.upper() == str(label.number).upper()
    ]
    if not pins:
        return Outcome.MISSING, False, "-"
    got = "; ".join(f"{pin.function.value} p{page}" for pin, page in pins)
    matches = [(pin, page) for pin, page in pins if pin.function.value == label.function]
    if not matches:
        return Outcome.WRONG, False, got
    return Outcome.CORRECT, any(page in label.pages for _, page in matches), got


def _score_feature(label: GoldLabel, ex: Extraction) -> tuple[Outcome, bool, str]:
    found = [f for f in ex.features if f.name == label.name]
    if not found:
        return Outcome.MISSING, False, "-"
    got = "; ".join(f"{f.value} p{f.source.page}" for f in found)
    matches = [f for f in found if f.value == label.value]
    if not matches:
        return Outcome.WRONG, False, got
    return Outcome.CORRECT, any(f.source.page in label.pages for f in matches), got


_SCORERS = {
    "parameter": _score_parameter,
    "package": _score_package,
    "pin": _score_pin,
    "feature": _score_feature,
}


def _expected(label: GoldLabel) -> str:
    if label.kind == "parameter":
        return _fmt({s: getattr(label, s) for s in SLOTS}) + (
            " (any column)" if label.any_slot else ""
        )
    if label.kind == "package":
        return f"{label.name} ({label.pin_count} pins)"
    if label.kind == "pin":
        return str(label.function)
    return str(label.value)


def score(gold: GoldFile, ex: Extraction) -> list[LabelScore]:
    out = []
    for label in gold.labels:
        outcome, cited, got = _SCORERS[label.kind](label, ex)
        out.append(
            LabelScore(
                datasheet=gold.id,
                field_type=label.field_type,
                label=label.label,
                outcome=outcome,
                cited_ok=cited,
                expected=_expected(label) + f" p{','.join(map(str, label.pages))}",
                got=got,
            )
        )
    return out


class TypeSummary(BaseModel, frozen=True):
    field_type: str
    labels: int
    correct: int
    wrong: int
    missing: int
    cited: int

    @property
    def field_accuracy(self) -> float:
        return self.correct / self.labels if self.labels else 0.0

    @property
    def citation_accuracy(self) -> float | None:
        return self.cited / self.correct if self.correct else None


def summarize(scores: list[LabelScore]) -> list[TypeSummary]:
    groups: dict[str, list[LabelScore]] = defaultdict(list)
    for s in scores:
        groups[s.field_type].append(s)
    return [
        TypeSummary(
            field_type=key,
            labels=len(items),
            correct=sum(s.outcome is Outcome.CORRECT for s in items),
            wrong=sum(s.outcome is Outcome.WRONG for s in items),
            missing=sum(s.outcome is Outcome.MISSING for s in items),
            cited=sum(s.cited_ok for s in items),
        )
        for key, items in sorted(groups.items())
    ]
