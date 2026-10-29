"""Lifecycle status, mapped from provider strings in ersatz.normalize.lifecycle."""

from enum import StrEnum


class Lifecycle(StrEnum):
    ACTIVE = "ACTIVE"
    NRND = "NRND"
    LAST_TIME_BUY = "LAST_TIME_BUY"
    OBSOLETE = "OBSOLETE"
    UNKNOWN = "UNKNOWN"


# Order used when providers disagree: the status furthest along wins
# (DOMAIN.md section 1). UNKNOWN never overrides a known status.
PROGRESSION: tuple[Lifecycle, ...] = (
    Lifecycle.ACTIVE,
    Lifecycle.NRND,
    Lifecycle.LAST_TIME_BUY,
    Lifecycle.OBSOLETE,
)


def furthest(statuses: list[Lifecycle]) -> Lifecycle:
    """Return the status furthest along the progression, or UNKNOWN if none is known."""
    known = [s for s in statuses if s in PROGRESSION]
    if not known:
        return Lifecycle.UNKNOWN
    return max(known, key=PROGRESSION.index)
