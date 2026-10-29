"""Package aliases and footprint-equivalence groups from rules/packages.yaml.

Unknown, ambiguous and no-lead names are flagged UNKNOWN with a reason.
A group is never guessed.
"""

import re
import unicodedata
from dataclasses import dataclass
from functools import cache
from typing import Literal

from ersatz.rules import load

Status = Literal["MATCHED", "UNKNOWN"]


@dataclass(frozen=True)
class PackageGroup:
    name: str
    status: str
    sources: tuple[str, ...]
    pin_counts: tuple[int, ...]
    body_width_mm: float | None
    height_max_mm: float | None
    land_pattern: str


@dataclass(frozen=True)
class PackageMatch:
    raw: str
    status: Status
    reason: str
    group: PackageGroup | None = None
    pin_count: int | None = None
    body_width_mm: float | None = None


def key(name: str) -> str:
    """Uppercase and keep only letters and digits."""
    return re.sub(r"[^0-9A-Z]", "", unicodedata.normalize("NFKC", name).upper())


@dataclass(frozen=True)
class _Tables:
    groups: dict[str, PackageGroup]
    aliases: dict[str, str]
    ambiguous: dict[str, dict[float, str]]
    no_lead: tuple[str, ...]
    width_tolerance: float


@cache
def tables() -> _Tables:
    data = load("packages")
    groups: dict[str, PackageGroup] = {}
    aliases: dict[str, str] = {}
    for name, g in data["groups"].items():
        group = PackageGroup(
            name=name,
            status=str(g["status"]),
            sources=tuple(g["sources"]),
            pin_counts=tuple(g["pin_counts"]),
            body_width_mm=g.get("body_width_mm"),
            height_max_mm=g.get("height_max_mm"),
            land_pattern=g.get("land_pattern", name),
        )
        groups[name] = group
        for alias in g["aliases"]:
            k = key(alias)
            if k in aliases and aliases[k] != name:
                raise ValueError(f"alias {alias} is in {aliases[k]} and {name}")
            aliases[k] = name
    ambiguous: dict[str, dict[float, str]] = {
        key(n): {float(w): str(grp) for w, grp in widths.items()}
        for n, widths in data["ambiguous"].items()
    }
    return _Tables(
        groups=groups,
        aliases=aliases,
        ambiguous=ambiguous,
        no_lead=tuple(data["no_lead"]),
        width_tolerance=float(data["width_tolerance_mm"]),
    )


_WIDTH = re.compile(r"(\d+(?:\.\d+)?)\s*mm\s*width", re.IGNORECASE)
_PIN_PREFIX = re.compile(r"^(\d+)-(\D.*)$")


def _body_width(text: str) -> float | None:
    match = _WIDTH.search(text)
    return float(match.group(1)) if match else None


def _candidates(piece: str) -> tuple[list[str], int | None]:
    """Keys to look up for one comma-separated piece, and a lead count from a prefix."""
    name = re.sub(r"\([^)]*\)", "", piece).strip()
    prefix = _PIN_PREFIX.match(name)
    if prefix:
        pins, family = int(prefix.group(1)), prefix.group(2)
        return [key(f"{family}-{pins}"), key(family)], pins
    return [key(name)], None


def _split(raw: str) -> list[str]:
    """Split on commas that are not inside parentheses."""
    pieces, depth, current = [], 0, ""
    for char in raw:
        depth += {"(": 1, ")": -1}.get(char, 0)
        if char == "," and depth == 0:
            pieces.append(current)
            current = ""
        else:
            current += char
    pieces.append(current)
    return [p.strip() for p in pieces if p.strip()]


def _same_width(a: float, b: float) -> bool:
    return abs(a - b) <= tables().width_tolerance + 1e-9


def _match_piece(
    piece: str, pin_count: int | None, width: float | None
) -> tuple[str | None, str, int | None]:
    t = tables()
    keys, prefix_pins = _candidates(piece)
    pins = prefix_pins if prefix_pins is not None else pin_count
    for k in keys:
        if any(tag in k for tag in t.no_lead):
            return None, f"{piece.strip()}: no-lead package, compared by outline drawing only", pins
        if k in t.ambiguous:
            if width is None:
                return None, f"{piece.strip()}: ambiguous name without a body width", pins
            for w, group in t.ambiguous[k].items():
                if _same_width(w, width):
                    return group, "matched by name and body width", pins
            return None, f"{piece.strip()}: body width {width} mm fits no group", pins
        if k in t.aliases:
            return t.aliases[k], "matched by alias", pins
    return None, f"{piece.strip()}: unknown package name", pins


def package_group(
    raw: str, pin_count: int | None = None, body_width_mm: float | None = None
) -> PackageMatch:
    """Match a provider or datasheet package string to a footprint group.

    Comma-separated names are alternatives for the same package. They must
    not point to different groups. A known pin count or body width that
    disagrees with the group makes the result UNKNOWN.
    """
    if not raw or not raw.strip():
        return PackageMatch(raw=raw, status="UNKNOWN", reason="no package name")
    width = body_width_mm if body_width_mm is not None else _body_width(raw)
    found: dict[str, int | None] = {}
    skipped: list[str] = []
    for piece in _split(raw):
        matched, reason, pins = _match_piece(piece, pin_count, width)
        if matched is None:
            skipped.append(reason)
        else:
            found.setdefault(matched, pins)

    def unknown(reason: str, pins: int | None = None) -> PackageMatch:
        return PackageMatch(
            raw=raw, status="UNKNOWN", reason=reason, pin_count=pins, body_width_mm=width
        )

    if not found:
        return unknown("; ".join(skipped))
    if len(found) > 1:
        return unknown("names point to different groups: " + ", ".join(sorted(found)))
    name, pins = next(iter(found.items()))
    group = tables().groups[name]
    if pin_count is not None:
        pins = pin_count
    if pins is not None and pins not in group.pin_counts:
        return unknown(f"{pins} pins do not fit {name}", pins)
    if (
        width is not None
        and group.body_width_mm is not None
        and not _same_width(width, group.body_width_mm)
    ):
        return unknown(f"body width {width} mm does not fit {name}", pins)
    if pins is None and len(group.pin_counts) == 1:
        pins = group.pin_counts[0]
    reason = "matched" if not skipped else "matched; ignored " + "; ".join(skipped)
    return PackageMatch(
        raw=raw,
        status="MATCHED",
        reason=reason,
        group=group,
        pin_count=pins,
        body_width_mm=width if width is not None else group.body_width_mm,
    )
