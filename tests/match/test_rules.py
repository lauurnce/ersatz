"""One test or more per function rule ID in rules/match_*.yaml."""

from typing import Any

import pytest

from ersatz.match.rules import Kind, Verdict, rule_set
from ersatz.match.score import evaluate
from ersatz.model import Category
from tests.match.parts import ldo, opamp


def verdict(rule_id: str, original: Any, candidate: Any) -> Verdict:
    category = original.category
    rule = next(r for r in rule_set(category).rules if r.id == rule_id)
    return evaluate(rule, original, candidate).verdict


def reason(rule_id: str, original: Any, candidate: Any) -> str:
    rule = next(r for r in rule_set(original.category).rules if r.id == rule_id)
    return evaluate(rule, original, candidate).reason


O_LDO = ldo("TEST-LDO-OLD")
O_OPA = opamp("TEST-OPA-OLD")

LDO_CASES = [
    # id, candidate params, candidate features, expected
    ("LDO-01", {}, {}, Verdict.PASS),
    ("LDO-01", {}, {"adjustable_output": True}, Verdict.FAIL),
    ("LDO-02", {}, {}, Verdict.PASS),
    ("LDO-02", {"vout": {"typ": 3.0}}, {}, Verdict.FAIL),
    ("LDO-04", {"vin": {"min": 1.8, "max": 6.5}}, {}, Verdict.PASS),
    ("LDO-04", {"vin": {"min": 2.7, "max": 6.0}}, {}, Verdict.FAIL),
    ("LDO-04", {"vin": {"max": 6.0}}, {}, Verdict.UNKNOWN),
    ("LDO-05", {"vin_abs_max": {"max": 7.0}}, {}, Verdict.PASS),
    ("LDO-05", {"vin_abs_max": {"max": 6.0}}, {}, Verdict.FAIL),
    ("LDO-06", {"vout_accuracy": {"max": 1}}, {}, Verdict.PASS),
    ("LDO-06", {"vout_accuracy": {"max": 3}}, {}, Verdict.WARN),
    ("LDO-07", {"iout": {"max": 0.5}}, {}, Verdict.PASS),
    ("LDO-07", {"iout": {"max": 0.2}}, {}, Verdict.FAIL),
    ("LDO-08", {"dropout": {"max": 0.3, "conditions": {"I": "0.3 A"}}}, {}, Verdict.PASS),
    ("LDO-08", {"dropout": {"max": 0.5, "conditions": {"I": "0.3 A"}}}, {}, Verdict.FAIL),
    ("LDO-08", {"dropout": {"max": 0.5, "conditions": {"I": "0.15 A"}}}, {}, Verdict.WARN),
    ("LDO-08", {"dropout": {"max": 0.3, "conditions": {"I": "0.15 A"}}}, {}, Verdict.WARN),
    ("LDO-08", {"dropout": {"max": 0.3}}, {}, Verdict.UNKNOWN),
    (
        "LDO-08",
        {"dropout": {"max": 0.3, "conditions": {"text": "IOUT = 300 mA"}}},
        {},
        Verdict.PASS,
    ),
    ("LDO-09", {"iq": {"max": 60e-6}}, {}, Verdict.PASS),
    ("LDO-09", {"iq": {"max": 1e-4}}, {}, Verdict.WARN),
    ("LDO-10", {"ishdn": {"max": 0.1e-6}}, {}, Verdict.PASS),
    ("LDO-10", {"ishdn": {"max": 5e-6}}, {}, Verdict.WARN),
    ("LDO-11", {"psrr": {"typ": 70, "conditions": {"f": "1000 Hz"}}}, {}, Verdict.WARN),
    ("LDO-11", {"psrr": {"typ": 50, "conditions": {"f": "1000 Hz"}}}, {}, Verdict.WARN),
    ("LDO-11", {"psrr": {"typ": 70, "conditions": {"f": "120 Hz"}}}, {}, Verdict.UNKNOWN),
]


@pytest.mark.parametrize(("rule_id", "params", "features", "expected"), LDO_CASES)
def test_ldo_rules(
    rule_id: str, params: dict[str, Any], features: dict[str, bool], expected: Verdict
) -> None:
    candidate = ldo("TEST-LDO-C", params=params, features=features)
    assert verdict(rule_id, O_LDO, candidate) is expected


def test_ldo_02_and_03_follow_the_output_type() -> None:
    adjustable = ldo("TEST-LDO-ADJ", params={"vref": {"typ": 1.25}})
    assert verdict("LDO-02", adjustable, adjustable) is Verdict.NA
    assert (
        verdict("LDO-03", adjustable, ldo("TEST-LDO-ADJ2", params={"vref": {"typ": 1.25}}))
        is Verdict.PASS
    )
    assert (
        verdict("LDO-03", adjustable, ldo("TEST-LDO-ADJ3", params={"vref": {"typ": 0.8}}))
        is Verdict.WARN
    )
    assert verdict("LDO-03", O_LDO, O_LDO) is Verdict.NA


def test_typical_only_comparison_is_warn_at_best() -> None:
    original = ldo("TEST-LDO-T1", params={"iq": {"typ": 50e-6}})
    candidate = ldo("TEST-LDO-T2", params={"iq": {"typ": 40e-6}})
    assert verdict("LDO-09", original, candidate) is Verdict.WARN
    assert "typical values only" in reason("LDO-09", original, candidate)


def test_guaranteed_columns_can_pass() -> None:
    original = opamp("TEST-OPA-M1", params={"slew_rate": {"min": 0.3e6, "typ": 0.5e6}})
    candidate = opamp("TEST-OPA-M2", params={"slew_rate": {"min": 0.4e6, "typ": 0.6e6}})
    assert verdict("OPA-04", original, candidate) is Verdict.PASS
    assert reason("OPA-04", original, candidate) == "min: candidate equal or higher"


def test_missing_value_on_either_side_is_unknown() -> None:
    no_iq = ldo("TEST-LDO-N")
    no_iq.parameters.pop(next(k for k in no_iq.parameters if k.value == "iq"))
    assert verdict("LDO-09", O_LDO, no_iq) is Verdict.UNKNOWN
    assert verdict("LDO-09", no_iq, O_LDO) is Verdict.UNKNOWN


def cap(
    mpn: str, ceramic: bool | None, esr: dict[str, float] | None, cout: float | None = None
) -> Any:
    params: dict[str, Any] = {}
    if esr is not None:
        params["cout_esr"] = esr
    if cout is not None:
        params["cout_min"] = {"min": cout}
    features = {} if ceramic is None else {"ceramic_cap_stable": ceramic}
    profile = ldo(mpn, params=params, features=features)
    if ceramic is None:
        profile.features.pop("ceramic_cap_stable")
    return profile


@pytest.mark.parametrize(
    ("original", "candidate", "expected"),
    [
        (cap("O", False, {"min": 0.3, "max": 22}), cap("C", True, None), Verdict.PASS),
        (
            cap("O", False, {"min": 0.3, "max": 22}),
            cap("C", False, {"min": 0.1, "max": 30}),
            Verdict.PASS,
        ),
        (
            cap("O", False, {"min": 0.3, "max": 22}),
            cap("C", False, {"min": 0.5, "max": 10}),
            Verdict.WARN,
        ),
        (cap("O", True, None, 1e-6), cap("C", True, None, 0.47e-6), Verdict.PASS),
        (cap("O", True, None, 1e-6), cap("C", True, None, 2.2e-6), Verdict.WARN),
        (cap("O", True, None), cap("C", True, None), Verdict.WARN),
        (cap("O", True, None), cap("C", False, {"min": 0.3, "max": 22}), Verdict.FAIL),
        (cap("O", True, None), cap("C", False, {"min": 0.01, "max": 10}), Verdict.PASS),
        (cap("O", True, None), cap("C", None, None), Verdict.UNKNOWN),
    ],
)
def test_ldo_13_capacitor_stability_table(original: Any, candidate: Any, expected: Verdict) -> None:
    assert verdict("LDO-13", original, candidate) is expected


OPA_CASES = [
    ("OPA-01", {"channels": {"typ": 2}}, {}, Verdict.PASS),
    ("OPA-01", {"channels": {"typ": 1}}, {}, Verdict.FAIL),
    ("OPA-02", {"vsupply": {"min": 2.7, "max": 36}}, {}, Verdict.PASS),
    ("OPA-02", {"vsupply": {"min": 1.8, "max": 5.5}}, {}, Verdict.FAIL),
    ("OPA-03", {"gbw": {"typ": 3e6}}, {}, Verdict.WARN),
    ("OPA-03", {"gbw": {"typ": 0.7e6}}, {}, Verdict.FAIL),
    ("OPA-03", {"gbw": {"typ": 20e6}}, {}, Verdict.WARN),
    ("OPA-04", {"slew_rate": {"typ": 1e6}}, {}, Verdict.WARN),
    ("OPA-04", {"slew_rate": {"typ": 0.3e6}}, {}, Verdict.FAIL),
    ("OPA-05", {"vos": {"max": 3e-3}}, {}, Verdict.PASS),
    ("OPA-05", {"vos": {"max": 9e-3}}, {}, Verdict.WARN),
    ("OPA-06", {"ibias": {"max": 1e-12}}, {}, Verdict.PASS),
    ("OPA-06", {"ibias": {"max": 500e-9}}, {}, Verdict.WARN),
    ("OPA-07", {}, {"rail_to_rail_input": True}, Verdict.PASS),
    ("OPA-08", {}, {"rail_to_rail_output": True}, Verdict.PASS),
    ("OPA-10", {"vnoise": {"typ": 20e-9, "conditions": {"f": "1000 Hz"}}}, {}, Verdict.WARN),
    ("OPA-10", {"vnoise": {"typ": 60e-9, "conditions": {"f": "1000 Hz"}}}, {}, Verdict.WARN),
    ("OPA-10", {"vnoise": {"typ": 20e-9, "conditions": {"f": "10000 Hz"}}}, {}, Verdict.UNKNOWN),
    ("OPA-11", {}, {}, Verdict.PASS),
    ("OPA-12", {"iq_per_channel": {"max": 500e-6}}, {}, Verdict.PASS),
    ("OPA-12", {"iq_per_channel": {"max": 900e-6}}, {}, Verdict.WARN),
]


@pytest.mark.parametrize(("rule_id", "params", "features", "expected"), OPA_CASES)
def test_opamp_rules(
    rule_id: str, params: dict[str, Any], features: dict[str, bool], expected: Verdict
) -> None:
    candidate = opamp("TEST-OPA-C", params=params, features=features)
    assert verdict(rule_id, O_OPA, candidate) is expected


@pytest.mark.parametrize("rule_id", ["OPA-07", "OPA-08"])
def test_rail_to_rail_must_be_kept(rule_id: str) -> None:
    feature = "rail_to_rail_input" if rule_id == "OPA-07" else "rail_to_rail_output"
    original = opamp("TEST-OPA-RR", features={feature: True})
    assert (
        verdict(rule_id, original, opamp("TEST-OPA-C", features={feature: False})) is Verdict.FAIL
    )
    assert verdict(rule_id, original, opamp("TEST-OPA-C", features={feature: True})) is Verdict.PASS
    unknown = opamp("TEST-OPA-U")
    unknown.features.pop(feature)
    assert verdict(rule_id, original, unknown) is Verdict.UNKNOWN


def test_opa_11_minimum_stable_gain() -> None:
    gain5 = opamp(
        "TEST-OPA-G5", params={"min_stable_gain": {"min": 5}}, features={"unity_gain_stable": False}
    )
    gain2 = opamp(
        "TEST-OPA-G2", params={"min_stable_gain": {"min": 2}}, features={"unity_gain_stable": False}
    )
    assert verdict("OPA-11", O_OPA, gain5) is Verdict.FAIL
    assert verdict("OPA-11", gain5, gain2) is Verdict.PASS
    assert verdict("OPA-11", gain2, gain5) is Verdict.FAIL
    assert verdict("OPA-11", gain5, O_OPA) is Verdict.PASS


def test_opa_12_derives_per_channel_from_package_total() -> None:
    total = opamp("TEST-OPA-T", params={"iq": {"max": 1.0e-3}})
    total.parameters.pop(next(k for k in total.parameters if k.value == "iq_per_channel"))
    assert verdict("OPA-12", O_OPA, total) is Verdict.PASS  # 0.5 mA per channel <= 0.6 mA
    heavy = opamp("TEST-OPA-H", params={"iq": {"max": 1.6e-3}})
    heavy.parameters.pop(next(k for k in heavy.parameters if k.value == "iq_per_channel"))
    assert verdict("OPA-12", O_OPA, heavy) is Verdict.WARN


def test_every_rule_id_has_a_test() -> None:
    covered = {c[0] for c in LDO_CASES + OPA_CASES} | {
        "LDO-03",
        "LDO-13",
        "OPA-07",
        "OPA-08",
        "OPA-11",
    }
    declared = {r.id for c in Category for r in rule_set(c).rules}
    assert declared <= covered


def test_rule_files_mirror_domain_ids() -> None:
    from pathlib import Path

    domain = (Path(__file__).parents[2] / "docs" / "DOMAIN.md").read_text()
    for category in Category:
        for rule in rule_set(category).rules:
            assert f"| {rule.id} |" in domain
            assert rule.kind in Kind
