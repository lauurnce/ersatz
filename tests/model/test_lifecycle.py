"""Combining lifecycle values from several providers."""

from ersatz.model import Lifecycle, furthest


def test_furthest_status_wins() -> None:
    assert furthest([Lifecycle.ACTIVE, Lifecycle.OBSOLETE, Lifecycle.NRND]) is Lifecycle.OBSOLETE


def test_unknown_never_overrides_known() -> None:
    assert furthest([Lifecycle.UNKNOWN, Lifecycle.ACTIVE]) is Lifecycle.ACTIVE


def test_nothing_known_is_unknown() -> None:
    assert furthest([]) is Lifecycle.UNKNOWN
    assert furthest([Lifecycle.UNKNOWN]) is Lifecycle.UNKNOWN
