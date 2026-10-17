"""Check every part number in a pasted chatbot answer.

With an original part, each mention is verified against it. Without one,
each mention is only resolved: found or not, by whom, and its lifecycle.
The original is never guessed from the text.
"""

from collections.abc import Sequence

from pydantic import BaseModel

from ersatz.model.lifecycle import furthest
from ersatz.normalize import normalize
from ersatz.notice import NOTICE
from ersatz.providers.base import Provider
from ersatz.resolve import Status, clean, resolve
from ersatz.verify.mentions import extract_mpns
from ersatz.verify.verify import Verdict, VerifyResult, resolve_original, verify_against


class CheckItem(BaseModel, frozen=True):
    as_entered: str
    status: str  # a Verdict value with an original, else FOUND, AMBIGUOUS or NOT FOUND
    manufacturer: str | None = None
    lifecycle: str | None = None
    reasons: tuple[str, ...] = ()
    result: VerifyResult | None = None


class CheckReport(BaseModel, frozen=True):
    original: str | None
    mentions: tuple[str, ...]
    items: tuple[CheckItem, ...]
    notice: str = NOTICE


def _lookup_only(mpn: str, providers: Sequence[Provider]) -> CheckItem:
    resolution = resolve(mpn, providers)
    if resolution.status is Status.NOT_FOUND:
        return CheckItem(
            as_entered=mpn,
            status=Verdict.NOT_FOUND.value,
            reasons=(f"no provider returned {mpn!r} (as entered)",),
        )
    if resolution.status is Status.AMBIGUOUS:
        makers = sorted({r.manufacturer for r in resolution.records})
        return CheckItem(
            as_entered=mpn, status="AMBIGUOUS", reasons=(f"made by {', '.join(makers)}",)
        )
    record = resolution.records[0]
    part = normalize(record).part
    lifecycle = furthest([s.value for s in part.lifecycle]).value
    reasons = (resolution.note,) if resolution.note else ()
    return CheckItem(
        as_entered=mpn,
        status="FOUND",
        manufacturer=record.manufacturer,
        lifecycle=lifecycle,
        reasons=reasons,
    )


def check_text(
    text: str,
    providers: Sequence[Provider],
    original: str | None = None,
    original_manufacturer: str | None = None,
) -> CheckReport:
    """Extract part numbers from `text` and check each one."""
    mentions = extract_mpns(text)
    if original is None:
        items = tuple(_lookup_only(m, providers) for m in mentions)
        return CheckReport(original=None, mentions=tuple(mentions), items=items)
    resolution, original_profile = resolve_original(original, providers, original_manufacturer)
    same = {clean(original).casefold(), original_profile.mpn.casefold()}
    items_list: list[CheckItem] = []
    for mpn in mentions:
        if clean(mpn).casefold() in same:
            continue
        result = verify_against(resolution, original_profile, mpn, providers)
        record = result.candidate.record
        lifecycle = None
        if record is not None:
            lifecycle = furthest([s.value for s in normalize(record).part.lifecycle]).value
        items_list.append(
            CheckItem(
                as_entered=mpn,
                status=result.verdict.value,
                manufacturer=record.manufacturer if record else None,
                lifecycle=lifecycle,
                reasons=result.reasons,
                result=result,
            )
        )
    return CheckReport(original=original, mentions=tuple(mentions), items=tuple(items_list))
