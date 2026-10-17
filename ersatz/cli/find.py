"""ersatz find: ranked replacement candidates with diffs and sources."""

import json
from collections.abc import Sequence
from typing import Annotated

import typer

from ersatz.cache import SqliteCache
from ersatz.match import display
from ersatz.match.find import FindError, FindResult, find
from ersatz.match.rules import Verdict
from ersatz.providers import ProviderError
from ersatz.providers.base import Provider
from ersatz.providers.factory import build_digikey
from ersatz.settings import get_settings

_VERDICTS = (Verdict.FAIL, Verdict.WARN, Verdict.UNKNOWN, Verdict.PASS, Verdict.NA)
COLUMNS = ("parameter", "original", "candidate", "verdict", "rule", "source O", "source C")


def _table(rows: list[tuple[str, ...]]) -> list[str]:
    widths = [min(max(len(r[i]) for r in rows), 44) for i in range(len(rows[0]))]

    def cell(text: str, width: int) -> str:
        return (text if len(text) <= width else text[: width - 1] + "~").ljust(width)

    return ["  " + " | ".join(cell(c, w) for c, w in zip(r, widths, strict=True)) for r in rows]


def render(result: FindResult) -> str:
    o = result.original
    lifecycle = o.part.lifecycle[0].source if o.part.lifecycle else None
    lines = [
        f"Original: {o.mpn} ({o.manufacturer}), {o.category.value if o.category else '-'}, "
        f"{o.lifecycle.value} [{display.source(lifecycle)}]",
        f"Package: {o.package.raw_name if o.package else '-'} "
        f"({o.package.group if o.package else '-'})",
        f"Searched {result.candidates_searched} candidates; "
        f"{len(result.report.ranked)} passed the hard filters, "
        f"{len(result.report.excluded)} excluded.",
    ]
    lines += [f"Query: {q}" for q in result.queries]
    lines += [f"Note: {n}" for n in result.notes]
    for n, c in enumerate(result.top, start=1):
        counts = ", ".join(f"{c.count(v)} {v.value}" for v in _VERDICTS if c.count(v))
        lines += [
            "",
            f"{n}. {c.mpn} ({c.manufacturer})  fit {c.filters.fit.fit.value}  "
            f"function score {c.score:.2f}  stock {c.stock}",
            f"   {counts}",
        ]
        rows: list[tuple[str, ...]] = [
            COLUMNS,
            *[
                (
                    r.parameter,
                    r.original,
                    r.candidate,
                    r.verdict,
                    r.rule,
                    r.original_source,
                    r.candidate_source,
                )
                for r in c.diff
            ],
        ]
        lines += _table(rows)
    if result.report.excluded:
        lines += ["", "Excluded:"]
        lines += [
            f"  {e.mpn} ({e.manufacturer}): {'; '.join(e.reasons)}" for e in result.report.excluded
        ]
    lines += ["", f"Notice: {result.notice}"]
    return "\n".join(lines)


def run_find(
    mpn: str,
    providers: Sequence[Provider],
    manufacturer: str | None,
    top: int,
    cap: int,
    as_json: bool,
) -> None:
    try:
        result = find(mpn, providers, manufacturer=manufacturer, top=top, cap=cap)
    except (FindError, ProviderError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(2) from exc
    if as_json:
        typer.echo(json.dumps(result.model_dump(mode="json"), indent=2))
    else:
        typer.echo(render(result))


def find_command(
    mpn: Annotated[str, typer.Argument(help="Exact part number of the original part.")],
    manufacturer: Annotated[
        str | None, typer.Option(help="Manufacturer, when several make it.")
    ] = None,
    top: Annotated[int, typer.Option(help="How many candidates to show.")] = 5,
    cap: Annotated[int, typer.Option(help="Most candidates to score.")] = 25,
    as_json: Annotated[bool, typer.Option("--json", help="Print JSON.")] = False,
) -> None:
    """Rank replacement candidates for a part, with a diff and a source for every value."""
    settings = get_settings()
    cache = SqliteCache(settings.ersatz_cache_dir / "ersatz.sqlite")
    try:
        providers: list[Provider] = [build_digikey(settings, cache)]
    except ProviderError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(2) from exc
    run_find(mpn, providers, manufacturer, top, cap, as_json)
