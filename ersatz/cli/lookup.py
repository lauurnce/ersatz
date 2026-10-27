"""ersatz lookup: provider records for exact part numbers, with sources."""

import json
from typing import Annotated

import typer

from ersatz.cache import SqliteCache
from ersatz.notice import NOTICE
from ersatz.providers import ProviderError, ProviderRecord
from ersatz.providers.factory import build_digikey
from ersatz.settings import get_settings


def _print_record(record: ProviderRecord) -> None:
    s = record.source
    typer.echo(f"{record.mpn}  ({record.manufacturer})")
    rows = [
        ("lifecycle", record.raw_lifecycle),
        ("last buy", record.raw_last_buy),
        ("category", record.raw_category),
        ("package", record.raw_package),
        ("stock", None if record.stock is None else str(record.stock)),
        ("datasheet", record.datasheet_url),
    ]
    for label, value in rows:
        if value is not None:
            typer.echo(f"  {label:<10} {value}")
    for name, value in record.raw_parameters.items():
        typer.echo(f"  - {name}: {value}")
    typer.echo(
        f"  source     {s.provider} response {(s.response_id or '')[:12]} "
        f"retrieved {s.retrieved_at:%Y-%m-%d %H:%M} UTC"
    )
    if s.url:
        typer.echo(f"             {s.url}")


def lookup(
    mpns: Annotated[list[str], typer.Argument(help="Exact manufacturer part numbers.")],
    manufacturer: Annotated[str | None, typer.Option(help="Keep only this manufacturer.")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Print JSON.")] = False,
    record: Annotated[
        bool, typer.Option(help="Save scrubbed responses under cache/recordings/.")
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
                q: [r.model_dump(mode="json") for r in recs] for q, recs in results.items()
            },
            "notice": NOTICE,
        }
        typer.echo(json.dumps(payload, indent=2))
        return
    for query, records in results.items():
        if not records:
            typer.echo(f"{query} (as entered)  NOT FOUND at digikey")
        for r in records:
            _print_record(r)
        typer.echo("")
    typer.echo(NOTICE)
