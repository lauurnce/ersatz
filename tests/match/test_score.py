"""The five synthetic scenarios from the matching phase, ranked end to end."""

import pytest

from ersatz.match.filters import Fit
from ersatz.match.rules import Verdict
from ersatz.match.score import function_score, rank, score_candidate
from ersatz.model import Category, Lifecycle
from tests.match.parts import DUAL_PINS, ldo, opamp, part

ORIGINAL = ldo("TEST-LDO-OLD", lifecycle=Lifecycle.OBSOLETE)
PERFECT = ldo(
    "TEST-LDO-A",
    params={"iout": {"max": 0.5}, "dropout": {"max": 0.2, "conditions": {"I": "0.3 A"}}},
    stock=50,
)
WORSE = ldo(
    "TEST-LDO-B",
    params={"iout": {"max": 0.2}, "dropout": {"max": 0.6, "conditions": {"I": "0.3 A"}}},
    stock=90000,
)
OTHER_PACKAGE = ldo("TEST-LDO-C", package="SOT-89", pins=None)
INACTIVE = ldo("TEST-LDO-D", lifecycle=Lifecycle.OBSOLETE)


def test_ldo_scenarios_rank_and_exclude() -> None:
    report = rank(ORIGINAL, [WORSE, OTHER_PACKAGE, INACTIVE, PERFECT])
    assert [c.mpn for c in report.ranked] == ["TEST-LDO-A", "TEST-LDO-B"]
    best, worse = report.ranked
    assert best.filters.fit.fit is Fit.DROP_IN
    assert best.count(Verdict.FAIL) == 0
    assert worse.count(Verdict.FAIL) == 2
    assert {r.rule_id for r in worse.rules if r.verdict is Verdict.FAIL} == {"LDO-07", "LDO-08"}
    assert best.score > worse.score
    excluded = {e.mpn: e.reasons for e in report.excluded}
    assert excluded["TEST-LDO-C"][0].startswith("form:")
    assert excluded["TEST-LDO-D"] == ("lifecycle: OBSOLETE, not ACTIVE",)


def test_more_stock_never_beats_fewer_failures() -> None:
    report = rank(ORIGINAL, [WORSE, PERFECT])
    assert report.ranked[0].mpn == "TEST-LDO-A"


def test_dual_opamp_with_nonstandard_pinout_ranks_after_drop_in() -> None:
    original = opamp("TEST-OPA-OLD", lifecycle=Lifecycle.OBSOLETE)
    swapped_supply = tuple(
        (n, {"VEE": "VCC", "VCC": "VEE"}.get(f, f), ch) for n, f, ch in DUAL_PINS
    )
    nonstandard = opamp("TEST-OPA-X", pins=swapped_supply, params={"gbw": {"typ": 3e6}})
    standard = opamp("TEST-OPA-A")
    report = rank(original, [nonstandard, standard])
    assert [c.mpn for c in report.ranked] == ["TEST-OPA-A", "TEST-OPA-X"]
    assert report.ranked[1].filters.fit.fit is Fit.SAME_PACKAGE_REWIRE


def test_other_category_is_excluded() -> None:
    report = rank(ORIGINAL, [opamp("TEST-OPA-A")])
    assert report.ranked == ()
    assert "category opamp" in report.excluded[0].reasons[0]


def test_diff_table_has_values_verdicts_and_sources() -> None:
    scored = score_candidate(ORIGINAL, WORSE)
    rows = {row.rule: row for row in scored.diff}
    assert [r.rule for r in scored.diff[:3]] == ["FORM", "FIT", "LIFECYCLE"]
    dropout = rows["LDO-08"]
    assert dropout.parameter == "dropout"
    assert dropout.original.startswith("typ 250 mV, max 350 mV")
    assert dropout.candidate.startswith("max 600 mV")
    assert dropout.verdict == "FAIL"
    assert "better: lower" in dropout.reason
    assert dropout.original_source.startswith("digikey ")
    assert dropout.candidate_source.startswith("digikey ")
    assert rows["LIFECYCLE"].original == "OBSOLETE"
    assert rows["FORM"].original == "SOT-23-5 (SOT23-5)"


def test_function_score_weights_and_skips_na() -> None:
    scored = score_candidate(ORIGINAL, PERFECT)
    counted = [r for r in scored.rules if r.verdict is not Verdict.NA]
    assert len(counted) < len(scored.rules)  # LDO-03 is N/A for a fixed output
    assert 0 < scored.score <= 1
    assert function_score([]) == 0.0


def test_original_without_category_is_rejected() -> None:
    bare = part("TEST-X", Category.LDO, "SOT-23-5")
    no_cat = bare.model_copy(update={"part": bare.part.model_copy(update={"category": None})})
    with pytest.raises(ValueError, match="no category"):
        rank(no_cat, [PERFECT])
    with pytest.raises(ValueError, match="no category"):
        score_candidate(no_cat, PERFECT)
