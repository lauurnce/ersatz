"""ersatz lookup: provider records for exact part numbers, with sources."""

from typing import Annotated

import typer
from rich.markup import escape

from ersatz.cache import SqliteCache
from ersatz.cli import output
from ersatz.cli.output import EXIT_NOT_FOUND, EXIT_OK
from ersatz.cli.show import print_normalized, print_record
from ersatz.normalize import normalize
from ersatz.providers import ProviderError, ProviderRecord
from ersatz.providers.factory import build_digikey
from ersatz.settings import get_settings


def lookup(
    mpns: Annotated[list[str], typer.Argument(help="Exact manufacturer part numbers.")],
    manufacturer: Annotated[str | None, typer.Option(help="Keep only this manufacturer.")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Print JSON.")] = False,
    record: Annotated[
        bool, typer.Option(help="Save scrubbed responses under cache/recordings/.")
    ] = False,
    normalized: Annotated[
        bool, typer.Option("--normalize", help="Also show the normalized part.")
    ] = False,
) -> None:
    """Look up part numbers. Values are shown as the provider returned them."""
    settings = get_settings()
    cache = SqliteCache(settings.ersatz_cache_dir / "ersatz.sqlite")
    results: dict[str, list[ProviderRecord]] = {}
    try:
        providers = (
            [build_digikey(settings, cache, record=True)]
            if record
            else output.build_providers(settings, cache)
        )
        for mpn in mpns:
            results[mpn] = [r for p in providers for r in p.get_part(mpn, manufacturer)]
    except ProviderError as exc:
        raise output.fail(str(exc)) from exc
    names = ", ".join(p.name for p in providers)
    code = EXIT_NOT_FOUND if any(not recs for recs in results.values()) else EXIT_OK
    if as_json:
        output.emit_json(
            {
                "results": {
                    q: [
                        {
                            "record": r.model_dump(mode="json"),
                            **(
                                {"part": normalize(r).part.model_dump(mode="json")}
                                if normalized
                                else {}
                            ),
                        }
                        for r in recs
                    ]
                    for q, recs in results.items()
                },
            }
        )
        raise typer.Exit(code)
    out = output.console()
    for query, records in results.items():
        if not records:
            out.print(f"{escape(query)} (as entered)  [bold red]NOT FOUND[/] at {names}")
        for r in records:
            print_record(r, out)
            if normalized:
                print_normalized(normalize(r), out)
        out.print("")
    output.notice_line(out)
    raise typer.Exit(code)
