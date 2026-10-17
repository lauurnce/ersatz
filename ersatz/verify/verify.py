"""Verify one suggested replacement against an original part.

Verdicts follow decision 9 of the project brief:
- VERIFIED: form PASS, fit DROP_IN, every applicable function rule PASS,
  lifecycle ACTIVE, stock at one provider or more, and no UNVERIFIED rule
  was needed to find the part.
- PARTIAL: any WARN or UNKNOWN, a rewire fit, NRND or last time buy, no stock,
  or a part found only through an UNVERIFIED suffix rule.
- MISMATCH: any FAIL, a fit of NO, a different category, or OBSOLETE.
- NOT FOUND: no provider returned the part number, after the documented
  normalization in ersatz.resolve. The text is kept exactly as entered.
"""

from collections.abc import Mapping, Sequence
from enum import StrEnum

from pydantic import BaseModel

from ersatz.datasheets.validate import Extraction
from ersatz.match.filters import Fit
from ersatz.match.profile import PartProfile, profile
from ersatz.match.rules import Verdict as RuleVerdict
from ersatz.match.score import CandidateScore, score_candidate
from ersatz.model.lifecycle import Lifecycle
from ersatz.normalize import normalize
from ersatz.notice import NOTICE
from ersatz.providers.base import Provider
from ersatz.resolve import Resolution, Status, resolve


class Verdict(StrEnum):
    VERIFIED = "VERIFIED"
    PARTIAL = "PARTIAL"
    MISMATCH = "MISMATCH"
    NOT_FOUND = "NOT FOUND"


class VerifyError(Exception):
    """The original part could not be resolved to one categorized part."""


class VerifyResult(BaseModel, frozen=True):
    original: Resolution
    candidate: Resolution
    candidate_as_entered: str
    verdict: Verdict
    reasons: tuple[str, ...]
    score: CandidateScore | None = None
    notice: str = NOTICE


def decide(
    score: CandidateScore, candidate: PartProfile, resolution: Resolution
) -> tuple[Verdict, tuple[str, ...]]:
    """Apply decision 9 to one scored candidate."""
    mismatch: list[str] = []
    partial: list[str] = []
    f = score.filters
    if f.form.verdict is RuleVerdict.FAIL:
        mismatch.append(f"form: {f.form.reason}")
    elif f.form.verdict is not RuleVerdict.PASS:
        partial.append(f"form {f.form.verdict.value}: {f.form.reason}")
    if f.fit.fit is Fit.NO:
        mismatch.append(f"fit: {f.fit.reason}")
    elif f.fit.fit is not Fit.DROP_IN:
        partial.append(f"fit {f.fit.fit.value}: {f.fit.reason}")
    status = candidate.lifecycle
    if status is Lifecycle.OBSOLETE:
        mismatch.append("lifecycle: OBSOLETE")
    elif status is not Lifecycle.ACTIVE:
        partial.append(f"lifecycle: {status.value}")
    for r in score.rules:
        if r.verdict is RuleVerdict.FAIL:
            mismatch.append(f"{r.rule_id} {r.parameter}: {r.reason}")
        elif r.verdict in (RuleVerdict.WARN, RuleVerdict.UNKNOWN):
            partial.append(f"{r.rule_id} {r.parameter} {r.verdict.value}: {r.reason}")
    if candidate.stock <= 0:
        partial.append("no stock at any provider")
    if resolution.unverified and resolution.rule is not None:
        partial.append(f"found only through {resolution.rule.id}, an UNVERIFIED rule")
    if mismatch:
        return Verdict.MISMATCH, tuple(mismatch + partial)
    if partial:
        return Verdict.PARTIAL, tuple(partial)
    return Verdict.VERIFIED, ("every check passed",)


def resolve_original(
    original_mpn: str, providers: Sequence[Provider], manufacturer: str | None = None
) -> tuple[Resolution, PartProfile]:
    original = resolve(original_mpn, providers, manufacturer)
    if original.status is not Status.FOUND or original.record is None:
        raise VerifyError(f"original {original_mpn!r} (as entered): {original.status.value}")
    part = normalize(original.record).part
    if part.category is None:
        raise VerifyError(f"original {part.mpn.value}: category is not LDO or op-amp")
    return original, profile(part)


def verify_against(
    original: Resolution,
    original_profile: PartProfile,
    candidate_mpn: str,
    providers: Sequence[Provider],
    candidate_manufacturer: str | None = None,
    extractions: Mapping[str, Extraction] | None = None,
) -> VerifyResult:
    extractions = extractions or {}
    candidate = resolve(candidate_mpn, providers, candidate_manufacturer)
    base = {
        "original": original,
        "candidate": candidate,
        "candidate_as_entered": candidate_mpn,
    }
    if candidate.status is Status.NOT_FOUND:
        reason = f"no provider returned {candidate_mpn!r} (as entered)"
        return VerifyResult(**base, verdict=Verdict.NOT_FOUND, reasons=(reason,))
    if candidate.status is Status.AMBIGUOUS:
        makers = ", ".join(sorted({r.manufacturer for r in candidate.records}))
        reason = f"made by {makers}; name the manufacturer to verify"
        return VerifyResult(**base, verdict=Verdict.PARTIAL, reasons=(reason,))
    assert candidate.record is not None  # noqa: S101 - FOUND always has a record
    part = normalize(candidate.record).part
    if part.category is None or part.category.value is not original_profile.category:
        got = part.category.value.value if part.category else "unknown"
        reason = f"category {got}, original is {original_profile.category}"
        return VerifyResult(**base, verdict=Verdict.MISMATCH, reasons=(reason,))
    o_profile = profile(original_profile.part, extractions.get(original_profile.mpn))
    c_profile = profile(part, extractions.get(part.mpn.value))
    scored = score_candidate(o_profile, c_profile)
    verdict, reasons = decide(scored, c_profile, candidate)
    return VerifyResult(**base, verdict=verdict, reasons=reasons, score=scored)


def verify(
    original_mpn: str,
    candidate_mpn: str,
    providers: Sequence[Provider],
    original_manufacturer: str | None = None,
    candidate_manufacturer: str | None = None,
    extractions: Mapping[str, Extraction] | None = None,
) -> VerifyResult:
    """Verify one candidate. Raises VerifyError if the original cannot be resolved."""
    original, original_profile = resolve_original(original_mpn, providers, original_manufacturer)
    return verify_against(
        original, original_profile, candidate_mpn, providers, candidate_manufacturer, extractions
    )
