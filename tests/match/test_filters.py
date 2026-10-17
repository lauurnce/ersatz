"""Every hard filter outcome: form, fit and lifecycle."""

import pytest

from ersatz.match.filters import Fit, check_fit, check_form, check_lifecycle, hard_filters
from ersatz.match.rules import Verdict
from ersatz.model import Lifecycle
from tests.match.parts import DUAL_PINS, LDO_PINS, ldo, opamp

ORIGINAL = ldo("TEST-LDO-OLD", lifecycle=Lifecycle.OBSOLETE)


# ---------------------------------------------------------------- form


def test_form_same_group_passes() -> None:
    assert check_form(ORIGINAL, ldo("TEST-LDO-A")).verdict is Verdict.PASS


def test_form_alias_of_the_same_group_passes() -> None:
    assert check_form(ORIGINAL, ldo("TEST-LDO-A", package="SOT-25")).verdict is Verdict.PASS


def test_form_other_group_fails() -> None:
    result = check_form(ORIGINAL, ldo("TEST-LDO-C", package="SOT-89"))
    assert result.verdict is Verdict.FAIL
    assert "is not SOT23-5" in result.reason


def test_form_taller_part_warns() -> None:
    result = check_form(ORIGINAL, ldo("TEST-LDO-T", height=1.6))
    assert result.verdict is Verdict.WARN
    assert "taller" in result.reason


@pytest.mark.parametrize("package", [None, "QQQ-99"])
def test_form_unknown_group_is_unknown(package: str | None) -> None:
    assert check_form(ORIGINAL, ldo("TEST-LDO-U", package=package)).verdict is Verdict.UNKNOWN


# ---------------------------------------------------------------- fit


def test_fit_same_map_is_drop_in() -> None:
    assert check_fit(ORIGINAL, ldo("TEST-LDO-A")).fit is Fit.DROP_IN


def test_fit_moved_pins_are_a_rewire() -> None:
    pins = (
        ("1", "OUT", None),
        ("2", "GND", None),
        ("3", "EN", None),
        ("4", "NC", None),
        ("5", "IN", None),
    )
    result = check_fit(ORIGINAL, ldo("TEST-LDO-R", pins=pins))
    assert result.fit is Fit.SAME_PACKAGE_REWIRE
    assert "pin 1: IN -> OUT" in result.reason


def test_fit_different_functions_is_no() -> None:
    pins = (*LDO_PINS[:3], ("4", "PG", None), LDO_PINS[4])
    result = check_fit(ORIGINAL, ldo("TEST-LDO-P", pins=pins))
    assert result.fit is Fit.NO
    assert "pin 4: NC -> PG" in result.reason


def test_fit_different_pin_count_is_no() -> None:
    result = check_fit(ORIGINAL, ldo("TEST-LDO-6", package="SOT-23-6", pins=None))
    assert result.fit is Fit.NO
    assert "6 pins, original has 5" in result.reason


def test_fit_missing_pinout_is_unknown_and_never_assumed() -> None:
    result = check_fit(ORIGINAL, ldo("TEST-LDO-N", pins=None))
    assert result.fit is Fit.UNKNOWN
    assert "never assumed" in result.reason


def test_fit_tab_mismatch_is_no() -> None:
    original = ldo(
        "TEST-REG-OLD",
        package="SOT-223",
        pins=(("1", "GND", None), ("2", "OUT", None), ("3", "IN", None), ("TAB", "OUT", None)),
    )
    candidate = ldo(
        "TEST-REG-B",
        package="SOT-223",
        pins=(("1", "GND", None), ("2", "OUT", None), ("3", "IN", None), ("TAB", "GND", None)),
    )
    result = check_fit(original, candidate)
    assert result.fit is Fit.NO
    assert result.reason.startswith("LDO-16")


def test_fit_dual_with_swapped_channels_is_drop_in() -> None:
    swapped = tuple((n, f, {1: 2, 2: 1}[ch] if ch else None) for n, f, ch in DUAL_PINS)
    assert check_fit(opamp("TEST-OPA-OLD"), opamp("TEST-OPA-S", pins=swapped)).fit is Fit.DROP_IN


def test_fit_dual_with_nonstandard_supply_pins_is_a_rewire() -> None:
    pins = tuple((n, {"VEE": "VCC", "VCC": "VEE"}.get(f, f), ch) for n, f, ch in DUAL_PINS)
    result = check_fit(opamp("TEST-OPA-OLD"), opamp("TEST-OPA-X", pins=pins))
    assert result.fit is Fit.SAME_PACKAGE_REWIRE
    assert "pin 4: VEE -> VCC" in result.reason


def test_fit_offset_null_counts_as_nc_with_a_note() -> None:
    single = (
        ("1", "NULL", None),
        ("2", "INN", 1),
        ("3", "INP", 1),
        ("4", "VEE", None),
        ("5", "NULL", None),
        ("6", "OUT", 1),
        ("7", "VCC", None),
        ("8", "NC", None),
    )
    nc = tuple((n, "NC" if f == "NULL" else f, ch) for n, f, ch in single)
    result = check_fit(opamp("TEST-OPS-OLD", pins=single), opamp("TEST-OPS-A", pins=nc))
    assert result.fit is Fit.DROP_IN
    assert "NC-compatible" in result.notes[0]


# ---------------------------------------------------------------- lifecycle


@pytest.mark.parametrize(
    ("status", "verdict"),
    [
        (Lifecycle.ACTIVE, Verdict.PASS),
        (Lifecycle.NRND, Verdict.FAIL),
        (Lifecycle.LAST_TIME_BUY, Verdict.FAIL),
        (Lifecycle.OBSOLETE, Verdict.FAIL),
        (Lifecycle.UNKNOWN, Verdict.FAIL),
    ],
)
def test_lifecycle_only_active_passes(status: Lifecycle, verdict: Verdict) -> None:
    assert check_lifecycle(ldo("TEST-LDO-L", lifecycle=status)).verdict is verdict


# ---------------------------------------------------------------- combined


def test_unknown_form_and_fit_do_not_exclude() -> None:
    filters = hard_filters(ORIGINAL, ldo("TEST-LDO-U", package=None, pins=None))
    assert filters.passed
    assert filters.reasons == []


def test_failed_filters_list_their_reasons() -> None:
    filters = hard_filters(
        ORIGINAL, ldo("TEST-LDO-C", package="SOIC-8", pins=None, lifecycle=Lifecycle.OBSOLETE)
    )
    assert not filters.passed
    assert [r.split(":")[0] for r in filters.reasons] == ["form", "fit", "lifecycle"]
