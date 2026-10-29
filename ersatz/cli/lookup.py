"""ersatz lookup: provider records for exact part numbers, with sources."""

import json
from typing import Annotated

import typer

from ersatz.cache import SqliteCache
from ersatz.cli.show import print_normalized, print_record
from ersatz.normalize import normalize
from ersatz.notice import NOTICE
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
    """Look up part numbers at Digi-Key. Values are shown as the provider returned them."""
    settings = get_settings()
    cache = SqliteCache(settings.ersatz_cache_dir / "ersatz.sqlite")
    results: dict[str, list[ProviderRecord]] = {}
    try:
        provider = build_digikey(settings, cache, record=record)
        for mpn in mpns:
            results[mpn] = provider.get_part(mpn, manufacturer)
    except ProviderError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(2) from exc
    if as_json:
        payload = {
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
            "notice": NOTICE,
        }
        typer.echo(json.dumps(payload, indent=2))
        return
    for query, records in results.items():
        if not records:
            typer.echo(f"{query} (as entered)  NOT FOUND at digikey")
        for r in records:
            print_record(r)
            if normalized:
                print_normalized(normalize(r))
        typer.echo("")
    typer.echo(NOTICE)
