"""Score candidates against an original and build the diff table.

Hard filters decide whether a candidate is listed at all. Function rules
from ersatz.match.rules then give each listed candidate a weighted score:
PASS counts 1, WARN 0.5, FAIL and UNKNOWN 0, N/A is left out. Numeric slack
is never added (D-017).
"""

import math
import re
from typing import NamedTuple

from pydantic import BaseModel

from ersatz.match import display
from ersatz.match.filters import Fit, HardFilters, hard_filters
from ersatz.match.profile import PartProfile
from ersatz.match.rules import Kind, Rule, RuleSet, Slot, Verdict, rule_set
from ersatz.model.category import Category
from ersatz.model.parameter import Parameter, ParamName
from ersatz.model.source import Source

POINTS = {Verdict.PASS: 1.0, Verdict.WARN: 0.5, Verdict.FAIL: 0.0, Verdict.UNKNOWN: 0.0}
FIT_ORDER = {Fit.DROP_IN: 0, Fit.SAME_PACKAGE_REWIRE: 1, Fit.UNKNOWN: 2, Fit.NO: 3}
CERAMIC_ESR_MAX = 0.02  # ohm; large ceramic capacitors are below 20 mOhm [R6]


class RuleResult(BaseModel, frozen=True):
    rule_id: str
    parameter: str
    better: str
    verdict: Verdict
    reason: str
    weight: float
    original: str = "-"
    candidate: str = "-"
    original_source: Source | None = None
    candidate_source: Source | None = None


class DiffRow(BaseModel, frozen=True):
    parameter: str
    original: str
    candidate: str
    verdict: str
    rule: str
    reason: str
    original_source: str
    candidate_source: str


class CandidateScore(BaseModel, frozen=True):
    mpn: str
    manufacturer: str
    filters: HardFilters
    rules: tuple[RuleResult, ...]
    score: float
    stock: int
    diff: tuple[DiffRow, ...]

    def count(self, verdict: Verdict) -> int:
        return sum(r.verdict is verdict for r in self.rules)


class Excluded(BaseModel, frozen=True):
    mpn: str
    manufacturer: str
    reasons: tuple[str, ...]


class MatchReport(BaseModel, frozen=True):
    original_mpn: str
    original_manufacturer: str
    category: Category
    ranked: tuple[CandidateScore, ...]
    excluded: tuple[Excluded, ...]


# ---------------------------------------------------------------- helpers


def _param(p: PartProfile, name: str) -> Parameter | None:
    try:
        return p.parameters.get(ParamName(name))
    except ValueError:
        return None


def _pick(o: Parameter, c: Parameter, slots: tuple[Slot, ...]) -> tuple[Slot, float, float] | None:
    for slot in slots:
        ov, cv = getattr(o, slot), getattr(c, slot)
        if ov is not None and cv is not None:
            return slot, ov, cv
    return None


_SCALE = {"": 1.0, "m": 1e-3, "u": 1e-6, "µ": 1e-6, "μ": 1e-6, "n": 1e-9, "k": 1e3, "M": 1e6}
_COND = {
    "I": re.compile(r"(\d+(?:\.\d+)?)\s*([munµμ]?)A\b"),
    "f": re.compile(r"(\d+(?:\.\d+)?)\s*([kM]?)Hz\b"),
}


def condition(p: Parameter, key: str) -> float | None:
    """A test condition in base units, from parsed conditions or the condition text."""
    stored = p.conditions.get(key)
    if stored:
        try:
            return float(stored.split()[0])
        except ValueError:
            return None
    match = _COND[key].search(p.conditions.get("text", "") + " " + p.conditions.get("note", ""))
    if match is None:
        return None
    return float(match.group(1)) * _SCALE[match.group(2)]


def _same(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-15)


def _result(
    rule: Rule,
    verdict: Verdict,
    reason: str,
    o: Parameter | None = None,
    c: Parameter | None = None,
    o_text: str | None = None,
    c_text: str | None = None,
    o_source: Source | None = None,
    c_source: Source | None = None,
) -> RuleResult:
    return RuleResult(
        rule_id=rule.id,
        parameter=rule.param,
        better=rule.better,
        verdict=verdict,
        reason=reason,
        weight=rule.weight,
        original=o_text if o_text is not None else display.parameter(o),
        candidate=c_text if c_text is not None else display.parameter(c),
        original_source=o_source or (o.source if o else None),
        candidate_source=c_source or (c.source if c else None),
    )


class _Shown(NamedTuple):
    o_text: str
    c_text: str
    o_source: Source | None
    c_source: Source | None


def _show(rule: Rule, verdict: Verdict, reason: str, shown: _Shown) -> RuleResult:
    return _result(
        rule,
        verdict,
        reason,
        o_text=shown.o_text,
        c_text=shown.c_text,
        o_source=shown.o_source,
        c_source=shown.c_source,
    )


def _cap(verdict: Verdict, ceiling: Verdict) -> Verdict:
    """Lower a PASS to WARN when the comparison is not on equal terms."""
    return ceiling if verdict is Verdict.PASS and ceiling is Verdict.WARN else verdict


# ---------------------------------------------------------------- rule kinds


def _numeric(rule: Rule, o: Parameter, c: Parameter) -> RuleResult:
    if rule.kind is Kind.CONTAINS:
        checks = []
        if o.min is not None:
            if c.min is None:
                return _result(rule, Verdict.UNKNOWN, "candidate has no minimum", o, c)
            checks.append(c.min <= o.min or _same(c.min, o.min))
        if o.max is not None:
            if c.max is None:
                return _result(rule, Verdict.UNKNOWN, "candidate has no maximum", o, c)
            checks.append(c.max >= o.max or _same(c.max, o.max))
        if not checks:
            return _result(rule, Verdict.UNKNOWN, "original has no range", o, c)
        if all(checks):
            return _result(rule, Verdict.PASS, "candidate range contains the original", o, c)
        return _result(rule, rule.broken_verdict, "candidate range is narrower", o, c)

    picked = _pick(o, c, rule.slots)
    if picked is None:
        return _result(rule, Verdict.UNKNOWN, "no common column to compare", o, c)
    slot, ov, cv = picked
    ceiling = Verdict.PASS
    notes = []
    if slot == "typ" and rule.slots[0] != "typ":
        ceiling = Verdict.WARN
        notes.append("typical values only")
    if rule.condition is not None:
        oc, cc = condition(o, rule.condition), condition(c, rule.condition)
        if rule.condition == "I" and (oc is None or cc is None):
            return _result(rule, Verdict.UNKNOWN, "no output current condition (LDO-08)", o, c)
        if rule.condition == "f" and oc is not None and cc is not None and not _same(oc, cc):
            return _result(rule, Verdict.UNKNOWN, "different test frequencies, not compared", o, c)
        if oc is None or cc is None:
            ceiling = Verdict.WARN
            notes.append("test condition not stated on both sides")
        elif not _same(oc, cc):
            ceiling = Verdict.WARN
            notes.append("different test conditions")

    if rule.kind is Kind.EQUAL:
        ok = _same(ov, cv)
        word = "equal" if ok else "different"
    elif rule.kind is Kind.HIGHER:
        ok = cv >= ov or _same(cv, ov)
        word = "equal or higher" if ok else "lower"
    else:
        ok = cv <= ov or _same(cv, ov)
        word = "equal or lower" if ok else "higher"
    reason = f"{slot}: candidate {word}"
    if notes:
        reason += "; " + ", ".join(notes)
    if not ok:
        verdict = rule.broken_verdict
        if rule.broken_verdict is Verdict.FAIL and ceiling is Verdict.WARN and rule.condition:
            verdict = Verdict.WARN  # LDO-08: WARN if conditions differ
        return _result(rule, verdict, reason, o, c)
    if rule.far_above is not None and ov > 0 and cv > rule.far_above * ov:
        return _result(rule, Verdict.WARN, f"{reason}; more than {rule.far_above:g} times", o, c)
    return _result(rule, _cap(Verdict.PASS, ceiling), reason, o, c)


def _feature(rule: Rule, original: PartProfile, candidate: PartProfile) -> RuleResult:
    of, cf = original.features.get(rule.param), candidate.features.get(rule.param)
    o_text = str(of.value) if of else "-"
    c_text = str(cf.value) if cf else "-"
    kw = _Shown(o_text, c_text, of.source if of else None, cf.source if cf else None)
    if of is None:
        return _show(rule, Verdict.UNKNOWN, "not stated for the original", kw)
    if rule.kind is Kind.FEATURE_IMPLIES and not of.value:
        return _show(rule, Verdict.PASS, "original does not have it", kw)
    if cf is None:
        return _show(rule, Verdict.UNKNOWN, "not stated for the candidate", kw)
    if cf.value == of.value:
        return _show(rule, Verdict.PASS, "same", kw)
    return _show(rule, rule.broken_verdict, "different", kw)


def _cap_class(p: PartProfile) -> tuple[str, Parameter | None]:
    ceramic = p.features.get("ceramic_cap_stable")
    esr = _param(p, "cout_esr")
    if ceramic is not None and ceramic.value:
        return "CERAMIC_STABLE", esr
    if esr is not None and esr.min is not None and esr.min > 0:
        return "ESR_WINDOW", esr
    return "UNKNOWN", esr


def _cap_stability(rule: Rule, original: PartProfile, candidate: PartProfile) -> RuleResult:
    o_cls, o_esr = _cap_class(original)
    c_cls, c_esr = _cap_class(candidate)
    o_text = f"{o_cls} {display.parameter(o_esr)}" if o_esr else o_cls
    c_text = f"{c_cls} {display.parameter(c_esr)}" if c_esr else c_cls
    o_src = o_esr.source if o_esr else _feature_source(original)
    c_src = c_esr.source if c_esr else _feature_source(candidate)
    kw = _Shown(o_text, c_text, o_src, c_src)
    if "UNKNOWN" in (o_cls, c_cls):
        return _show(rule, Verdict.UNKNOWN, "capacitor stability class unknown", kw)
    if o_cls == "ESR_WINDOW" and c_cls == "CERAMIC_STABLE":
        return _show(rule, Verdict.PASS, "board may carry an unneeded tantalum capacitor", kw)
    if o_cls == "ESR_WINDOW" and c_cls == "ESR_WINDOW":
        assert o_esr is not None  # noqa: S101 - set by _cap_class
        assert c_esr is not None  # noqa: S101 - set by _cap_class
        inside = (c_esr.min or 0) <= (o_esr.min or 0) and (
            c_esr.max is None or (o_esr.max is not None and c_esr.max >= o_esr.max)
        )
        if inside:
            return _show(rule, Verdict.PASS, "candidate ESR window contains the original", kw)
        return _show(rule, Verdict.WARN, "candidate ESR window is narrower", kw)
    if o_cls == "CERAMIC_STABLE" and c_cls == "CERAMIC_STABLE":
        o_min, c_min = _param(original, "cout_min"), _param(candidate, "cout_min")
        o_v = o_min.min if o_min else None
        c_v = c_min.min if c_min else None
        if o_v is None or c_v is None:
            return _show(rule, Verdict.WARN, "minimum capacitance not known on both", kw)
        if c_v <= o_v or _same(c_v, o_v):
            return _show(rule, Verdict.PASS, "candidate needs no more capacitance", kw)
        return _show(rule, Verdict.WARN, "candidate needs more output capacitance", kw)
    assert c_esr is not None  # noqa: S101 - ESR_WINDOW always has a parameter
    if (c_esr.min or 0) > CERAMIC_ESR_MAX:
        return _show(
            rule, rule.broken_verdict, "ceramic capacitor on the board is below the ESR window", kw
        )
    return _show(rule, Verdict.PASS, "candidate ESR window includes ceramic values", kw)


def _feature_source(p: PartProfile) -> Source | None:
    f = p.features.get("ceramic_cap_stable")
    return f.source if f else None


def _gain(p: PartProfile) -> tuple[float | None, Source | None, str]:
    unity = p.features.get("unity_gain_stable")
    if unity is not None and unity.value:
        return 1.0, unity.source, "unity-gain stable"
    g = _param(p, "min_stable_gain")
    if g is None:
        return None, None, "-"
    value = next((v for v in (g.min, g.typ, g.max) if v is not None), None)
    return value, g.source, display.parameter(g)


def _stable_gain(rule: Rule, original: PartProfile, candidate: PartProfile) -> RuleResult:
    ov, o_src, o_text = _gain(original)
    cv, c_src, c_text = _gain(candidate)
    kw = _Shown(o_text, c_text, o_src, c_src)
    if cv is not None and _same(cv, 1.0):
        return _show(rule, Verdict.PASS, "unity-gain stable is always safe", kw)
    if ov is None or cv is None:
        return _show(rule, Verdict.UNKNOWN, "minimum stable gain unknown", kw)
    if cv <= ov:
        return _show(rule, Verdict.PASS, "candidate stable at the original gain", kw)
    return _show(rule, rule.broken_verdict, "candidate needs a higher gain", kw)


def _per_channel(p: PartProfile, slots: tuple[Slot, ...]) -> tuple[float | None, Parameter | None]:
    per = _param(p, "iq_per_channel")
    if per is not None:
        return next((getattr(per, s) for s in slots if getattr(per, s) is not None), None), per
    total, channels = _param(p, "iq"), _param(p, "channels")
    if total is None or channels is None:
        return None, total
    n = next((v for v in (channels.typ, channels.min, channels.max) if v), None)
    value = next((getattr(total, s) for s in slots if getattr(total, s) is not None), None)
    if n is None or value is None:
        return None, total
    return value / n, total


def _per_channel_rule(rule: Rule, original: PartProfile, candidate: PartProfile) -> RuleResult:
    ov, o_p = _per_channel(original, rule.slots)
    cv, c_p = _per_channel(candidate, rule.slots)
    o_text = display.number(ov, "A") + " per channel" if ov is not None else "-"
    c_text = display.number(cv, "A") + " per channel" if cv is not None else "-"
    kw = _Shown(o_text, c_text, o_p.source if o_p else None, c_p.source if c_p else None)
    if ov is None or cv is None:
        return _show(rule, Verdict.UNKNOWN, "per-channel current unknown", kw)
    if cv <= ov or _same(cv, ov):
        return _show(rule, Verdict.PASS, "candidate equal or lower", kw)
    return _show(rule, rule.broken_verdict, "candidate higher", kw)


def evaluate(rule: Rule, original: PartProfile, candidate: PartProfile) -> RuleResult:
    """Apply one function rule."""
    if rule.if_original_has and _param(original, rule.if_original_has) is None:
        return _result(rule, Verdict.NA, f"original has no {rule.if_original_has}")
    if rule.unless_original_has and _param(original, rule.unless_original_has) is not None:
        return _result(rule, Verdict.NA, f"original has {rule.unless_original_has}")
    if rule.kind in (Kind.FEATURE_EQUAL, Kind.FEATURE_IMPLIES):
        return _feature(rule, original, candidate)
    if rule.kind is Kind.CAP_STABILITY:
        return _cap_stability(rule, original, candidate)
    if rule.kind is Kind.STABLE_GAIN:
        return _stable_gain(rule, original, candidate)
    if rule.kind is Kind.PER_CHANNEL:
        return _per_channel_rule(rule, original, candidate)
    o, c = _param(original, rule.param), _param(candidate, rule.param)
    if o is None or c is None:
        side = "original" if o is None else "candidate"
        return _result(rule, Verdict.UNKNOWN, f"no value for the {side}", o, c)
    return _numeric(rule, o, c)


# ---------------------------------------------------------------- scoring


def function_score(results: list[RuleResult]) -> float:
    counted = [r for r in results if r.verdict is not Verdict.NA]
    total = sum(r.weight for r in counted)
    if total == 0:
        return 0.0
    return sum(r.weight * POINTS[r.verdict] for r in counted) / total


def _diff(
    original: PartProfile, candidate: PartProfile, f: HardFilters, results: list[RuleResult]
) -> tuple[DiffRow, ...]:
    o_pkg, c_pkg = original.package, candidate.package
    rows = [
        DiffRow(
            parameter="package",
            original=f"{o_pkg.raw_name} ({o_pkg.group})" if o_pkg else "-",
            candidate=f"{c_pkg.raw_name} ({c_pkg.group})" if c_pkg else "-",
            verdict=f.form.verdict.value,
            rule="FORM",
            reason=f.form.reason,
            original_source=display.source(o_pkg.source if o_pkg else None),
            candidate_source=display.source(c_pkg.source if c_pkg else None),
        ),
        DiffRow(
            parameter="pinout",
            original=f"{len(original.pinout.pins)} pins mapped" if original.pinout else "-",
            candidate=f"{len(candidate.pinout.pins)} pins mapped" if candidate.pinout else "-",
            verdict=f.fit.fit.value,
            rule="FIT",
            reason="; ".join([f.fit.reason, *f.fit.notes]),
            original_source=display.source(original.pinout.source if original.pinout else None),
            candidate_source=display.source(candidate.pinout.source if candidate.pinout else None),
        ),
        DiffRow(
            parameter="lifecycle",
            original=original.lifecycle.value,
            candidate=candidate.lifecycle.value,
            verdict=f.lifecycle.verdict.value,
            rule="LIFECYCLE",
            reason=f.lifecycle.reason,
            original_source=display.source(
                original.part.lifecycle[0].source if original.part.lifecycle else None
            ),
            candidate_source=display.source(
                candidate.part.lifecycle[0].source if candidate.part.lifecycle else None
            ),
        ),
    ]
    rows += [
        DiffRow(
            parameter=r.parameter,
            original=r.original,
            candidate=r.candidate,
            verdict=r.verdict.value,
            rule=r.rule_id,
            reason=f"{r.reason} (better: {r.better})",
            original_source=display.source(r.original_source),
            candidate_source=display.source(r.candidate_source),
        )
        for r in results
    ]
    return tuple(rows)


def score_candidate(
    original: PartProfile, candidate: PartProfile, rules: RuleSet | None = None
) -> CandidateScore:
    category = original.category
    if rules is None:
        if category is None:
            raise ValueError("the original part has no category; nothing to score against")
        rules = rule_set(category)
    filters = hard_filters(original, candidate)
    results = [evaluate(rule, original, candidate) for rule in rules.rules]
    return CandidateScore(
        mpn=candidate.mpn,
        manufacturer=candidate.manufacturer,
        filters=filters,
        rules=tuple(results),
        score=function_score(results),
        stock=candidate.stock,
        diff=_diff(original, candidate, filters, results),
    )


def rank(original: PartProfile, candidates: list[PartProfile]) -> MatchReport:
    """Score every candidate, drop those that fail a hard filter, sort the rest."""
    if original.category is None:
        raise ValueError("the original part has no category; nothing to score against")
    rules = rule_set(original.category)
    kept: list[CandidateScore] = []
    excluded: list[Excluded] = []
    for candidate in candidates:
        if candidate.category is not original.category:
            reason = f"category {candidate.category}, original is {original.category.value}"
            excluded.append(
                Excluded(mpn=candidate.mpn, manufacturer=candidate.manufacturer, reasons=(reason,))
            )
            continue
        scored = score_candidate(original, candidate, rules)
        if scored.filters.passed:
            kept.append(scored)
        else:
            excluded.append(
                Excluded(
                    mpn=scored.mpn,
                    manufacturer=scored.manufacturer,
                    reasons=tuple(scored.filters.reasons),
                )
            )
    kept.sort(
        key=lambda s: (
            FIT_ORDER[s.filters.fit.fit],
            s.count(Verdict.FAIL),
            -s.score,
            -s.stock,
            s.mpn,
        )
    )
    return MatchReport(
        original_mpn=original.mpn,
        original_manufacturer=original.manufacturer,
        category=original.category,
        ranked=tuple(kept),
        excluded=tuple(excluded),
    )
