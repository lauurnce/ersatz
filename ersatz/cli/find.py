"""ersatz find: ranked replacement candidates with diffs and sources."""

from collections.abc import Sequence
from typing import Annotated

import typer

from ersatz.cache import SqliteCache
from ersatz.cli import output
from ersatz.cli.output import EXIT_ERROR, EXIT_NOT_FOUND, styled
from ersatz.cli.tables import diff_table
from ersatz.match import display
from ersatz.match.find import FindError, FindResult, find
from ersatz.match.rules import Verdict
from ersatz.providers import ProviderError
from ersatz.providers.base import Provider
from ersatz.settings import get_settings

_VERDICTS = (Verdict.FAIL, Verdict.WARN, Verdict.UNKNOWN, Verdict.PASS, Verdict.NA)


def show(result: FindResult) -> None:
    out = output.console()
    o = result.original
    lifecycle = o.part.lifecycle[0].source if o.part.lifecycle else None
    out.print(
        f"Original: {o.mpn} ({o.manufacturer}), {o.category.value if o.category else '-'}, "
        f"{styled(o.lifecycle.value)} [dim][{display.source(lifecycle)}][/]"
    )
    pkg = o.package
    out.print(f"Package: {pkg.raw_name if pkg else '-'} ({pkg.group if pkg else '-'})")
    out.print(
        f"Searched {result.candidates_searched} candidates; "
        f"{len(result.report.ranked)} passed the hard filters, "
        f"{len(result.report.excluded)} excluded."
    )
    for query in result.queries:
        out.print(f"[dim]Query: {query}[/]")
    for note in result.notes:
        out.print(f"[dim]Note: {note}[/]")
    for n, c in enumerate(result.top, start=1):
        counts = ", ".join(f"{c.count(v)} {styled(v.value)}" for v in _VERDICTS if c.count(v))
        out.print(
            f"\n[bold]{n}. {c.mpn}[/] ({c.manufacturer})  fit {styled(c.filters.fit.fit.value)}  "
            f"function score {c.score:.2f}  stock {c.stock}"
        )
        out.print(f"   {counts}")
        out.print(diff_table(c))
    if result.report.excluded:
        out.print("\nExcluded:")
        for e in result.report.excluded:
            out.print(f"  {e.mpn} ({e.manufacturer}): {'; '.join(e.reasons)}")
    output.notice_line(out)


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
    except FindError as exc:
        code = EXIT_NOT_FOUND if "NOT FOUND" in str(exc) else EXIT_ERROR
        raise output.fail(str(exc), code) from exc
    except ProviderError as exc:
        raise output.fail(str(exc)) from exc
    if as_json:
        output.emit_json(result)
    else:
        show(result)


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
        providers = output.build_providers(settings, cache)
    except ProviderError as exc:
        raise output.fail(str(exc)) from exc
    run_find(mpn, providers, manufacturer, top, cap, as_json)
