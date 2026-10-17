"""Each verdict, through decide() on full synthetic profiles and through verify()."""

import pytest

from ersatz.match.profile import PartProfile
from ersatz.match.score import score_candidate
from ersatz.model import Lifecycle
from ersatz.resolve import Resolution, Status, SuffixRule
from ersatz.verify import Verdict, VerifyError, decide, verify
from tests.match.fakes import OPAMP_CATEGORY, FakeProvider, record
from tests.match.parts import DUAL_PINS, ldo, opamp

FOUND = Resolution(as_entered="X", query="X", status=Status.FOUND)
VIA_RULE = Resolution(
    as_entered="XCT-ND",
    query="X",
    status=Status.FOUND,
    rule=SuffixRule(id="SFX-DK", status="UNVERIFIED", suffixes=("CT-ND",), note="n"),
)
ORIGINAL = ldo("TEST-LDO-OLD", lifecycle=Lifecycle.OBSOLETE)


def judge(
    candidate: PartProfile, resolution: Resolution = FOUND
) -> tuple[Verdict, tuple[str, ...]]:
    return decide(score_candidate(ORIGINAL, candidate), candidate, resolution)


# full psrr, cap and accuracy data so every LDO rule can PASS
FULL = {
    "psrr": {"min": 55, "typ": 60, "conditions": {"f": "1000 Hz"}},
    "iq": {"max": 80e-6},
    "cout_min": {"min": 1e-6},
}


def full_original() -> PartProfile:
    return ldo("TEST-LDO-OLD", lifecycle=Lifecycle.OBSOLETE, params=FULL)


def test_verified_needs_every_check_to_pass() -> None:
    original = full_original()
    candidate = ldo("TEST-LDO-A", params=FULL)
    verdict, reasons = decide(score_candidate(original, candidate), candidate, FOUND)
    assert verdict is Verdict.VERIFIED, reasons
    assert reasons == ("every check passed",)


def test_unverified_suffix_rule_caps_at_partial() -> None:
    original = full_original()
    candidate = ldo("TEST-LDO-A", params=FULL)
    verdict, reasons = decide(score_candidate(original, candidate), candidate, VIA_RULE)
    assert verdict is Verdict.PARTIAL
    assert "UNVERIFIED rule" in reasons[-1]


@pytest.mark.parametrize(
    ("candidate", "reason"),
    [
        (ldo("TEST-LDO-W", params={"iq": {"max": 1e-4}}), "LDO-09 iq WARN"),
        (ldo("TEST-LDO-N", lifecycle=Lifecycle.NRND), "lifecycle: NRND"),
        (ldo("TEST-LDO-L", lifecycle=Lifecycle.LAST_TIME_BUY), "lifecycle: LAST_TIME_BUY"),
        (ldo("TEST-LDO-S", stock=0), "no stock at any provider"),
        (ldo("TEST-LDO-U", pins=None), "fit UNKNOWN"),
        (
            ldo(
                "TEST-LDO-R",
                pins=(
                    ("1", "OUT", None),
                    ("2", "GND", None),
                    ("3", "EN", None),
                    ("4", "NC", None),
                    ("5", "IN", None),
                ),
            ),
            "fit SAME_PACKAGE_REWIRE",
        ),
    ],
)
def test_partial_reasons(candidate: PartProfile, reason: str) -> None:
    verdict, reasons = judge(candidate)
    assert verdict is Verdict.PARTIAL
    assert any(r.startswith(reason) for r in reasons), reasons


@pytest.mark.parametrize(
    ("candidate", "reason"),
    [
        (ldo("TEST-LDO-F", params={"iout": {"max": 0.1}}), "LDO-07 iout"),
        (ldo("TEST-LDO-O", lifecycle=Lifecycle.OBSOLETE), "lifecycle: OBSOLETE"),
        (ldo("TEST-LDO-P", package="SOT-89", pins=None), "form:"),
        (ldo("TEST-LDO-6", package="SOT-23-6", pins=None), "fit:"),
    ],
)
def test_mismatch_reasons(candidate: PartProfile, reason: str) -> None:
    verdict, reasons = judge(candidate)
    assert verdict is Verdict.MISMATCH
    assert any(r.startswith(reason) for r in reasons), reasons


def test_dual_opamp_with_swapped_channels_can_verify() -> None:
    original = opamp(
        "TEST-OPA-OLD",
        lifecycle=Lifecycle.OBSOLETE,
        params={
            "gbw": {"min": 0.8e6, "typ": 1e6},
            "slew_rate": {"min": 0.3e6},
            "vnoise": {"max": 50e-9, "conditions": {"f": "1000 Hz"}},
        },
    )
    swapped = tuple((n, f, {1: 2, 2: 1}[ch] if ch else None) for n, f, ch in DUAL_PINS)
    candidate = opamp(
        "TEST-OPA-A",
        pins=swapped,
        params={
            "gbw": {"min": 0.9e6, "typ": 1.2e6},
            "slew_rate": {"min": 0.4e6},
            "vnoise": {"max": 40e-9, "conditions": {"f": "1000 Hz"}},
        },
    )
    verdict, reasons = decide(score_candidate(original, candidate), candidate, FOUND)
    assert verdict is Verdict.VERIFIED, reasons


# ---------------------------------------------------------------- verify()

LDO = {
    "Voltage - Input (Min)": "2.5V",
    "Voltage - Input (Max)": "6V",
    "Voltage - Output (Min/Fixed)": "3.3V",
    "Current - Output": "300mA",
    "Voltage Dropout (Max)": "0.35V @ 300mA",
}


def provider() -> FakeProvider:
    return FakeProvider(
        "digikey",
        [
            record("TEST-LDO-OLD", lifecycle="Obsolete", parameters=LDO),
            record("TEST-LDO-A", parameters=LDO),
            record("TEST-LDO-X", lifecycle="Obsolete", parameters=LDO),
            record(
                "TEST-OPA-A",
                category=OPAMP_CATEGORY,
                package="8-SOIC",
                parameters={"Amplifier Type": "General Purpose"},
            ),
        ],
        parametric=False,
        results=[],
    )


def test_verify_not_found_keeps_text_as_entered() -> None:
    result = verify("TEST-LDO-OLD", " TEST-LDO-ZZ9 ", [provider()])
    assert result.verdict is Verdict.NOT_FOUND
    assert result.candidate_as_entered == " TEST-LDO-ZZ9 "
    assert result.reasons == ("no provider returned ' TEST-LDO-ZZ9 ' (as entered)",)
    assert result.score is None
    assert result.notice.startswith("Ersatz results")


def test_verify_provider_only_data_is_partial() -> None:
    result = verify("TEST-LDO-OLD", "TEST-LDO-A", [provider()])
    assert result.verdict is Verdict.PARTIAL
    assert any(r.startswith("fit UNKNOWN") for r in result.reasons)
    assert result.score is not None
    assert result.score.diff[0].original_source.startswith("digikey")


def test_verify_obsolete_candidate_is_mismatch() -> None:
    assert verify("TEST-LDO-OLD", "TEST-LDO-X", [provider()]).verdict is Verdict.MISMATCH


def test_verify_other_category_is_mismatch() -> None:
    result = verify("TEST-LDO-OLD", "TEST-OPA-A", [provider()])
    assert result.verdict is Verdict.MISMATCH
    assert result.reasons[0].startswith("category opamp")


def test_verify_ambiguous_candidate_is_partial() -> None:
    p = FakeProvider(
        "digikey",
        [
            record("TEST-LDO-OLD", lifecycle="Obsolete", parameters=LDO),
            record("TEST-LDO-A", parameters=LDO),
            record("TEST-LDO-A", manufacturer="Other Co", parameters=LDO),
        ],
    )
    result = verify("TEST-LDO-OLD", "TEST-LDO-A", [p])
    assert result.verdict is Verdict.PARTIAL
    assert "name the manufacturer" in result.reasons[0]


def test_verify_suffix_normalization_is_reported() -> None:
    result = verify("TEST-LDO-OLD", "TEST-LDO-ACT-ND", [provider()])
    assert result.candidate.query == "TEST-LDO-A"
    assert any("UNVERIFIED rule" in r for r in result.reasons)


def test_unresolvable_original_raises() -> None:
    with pytest.raises(VerifyError, match="NOT_FOUND"):
        verify("TEST-NOPE", "TEST-LDO-A", [provider()])
    odd = FakeProvider("digikey", [record("TEST-R1", category="Resistors")])
    with pytest.raises(VerifyError, match="category"):
        verify("TEST-R1", "TEST-LDO-A", [odd])
