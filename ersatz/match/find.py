"""Find replacements for one part number: resolve, search, score, rank.

Values come from provider responses. Datasheet extractions can be passed
in by part number; they are used where they are HIGH confidence. No model
call happens here.
"""

from collections.abc import Mapping, Sequence

from pydantic import BaseModel

from ersatz.datasheets.validate import Extraction
from ersatz.match.profile import PartProfile, profile
from ersatz.match.score import CandidateScore, MatchReport, rank
from ersatz.match.search import DEFAULT_CAP, find_candidates
from ersatz.normalize import normalize
from ersatz.notice import NOTICE
from ersatz.providers.base import Provider


class FindError(Exception):
    """The original part could not be resolved to one categorized part."""


class FindResult(BaseModel, frozen=True):
    original: PartProfile
    report: MatchReport
    top: tuple[CandidateScore, ...]
    candidates_searched: int
    queries: tuple[str, ...]
    notes: tuple[str, ...]
    notice: str = NOTICE


def find(
    mpn: str,
    providers: Sequence[Provider],
    manufacturer: str | None = None,
    top: int = 5,
    cap: int = DEFAULT_CAP,
    extractions: Mapping[str, Extraction] | None = None,
) -> FindResult:
    extractions = extractions or {}
    records = [r for p in providers for r in p.get_part(mpn, manufacturer)]
    if not records:
        raise FindError(f"{mpn}: NOT FOUND at any provider")
    makers = sorted({r.manufacturer for r in records})
    if len(makers) > 1:
        raise FindError(f"{mpn}: made by {', '.join(makers)}; pass --manufacturer")
    original_part = normalize(records[0]).part
    if original_part.category is None:
        raise FindError(f"{mpn}: category is not LDO or op-amp, or could not be mapped")
    original = profile(original_part, extractions.get(original_part.mpn.value))
    search = find_candidates(original_part, providers, cap=cap)
    candidates = []
    for record in search.records:
        part = normalize(record).part
        candidates.append(profile(part, extractions.get(part.mpn.value)))
    report = rank(original, candidates)
    return FindResult(
        original=original,
        report=report,
        top=report.ranked[:top],
        candidates_searched=len(search.records),
        queries=search.queries,
        notes=search.notes,
    )
