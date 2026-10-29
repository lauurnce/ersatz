"""Plain text output for provider records and normalized parts."""

import typer

from ersatz.model import Parameter
from ersatz.normalize import Normalized
from ersatz.providers import ProviderRecord


def _fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:.6g}"


def parameter_line(p: Parameter) -> str:
    unit = p.unit or "count"
    values = f"min {_fmt(p.min):>8}  typ {_fmt(p.typ):>8}  max {_fmt(p.max):>8}"
    text = f"{p.name.value:<15} {values}  {unit}"
    if p.conditions:
        text += "  @ " + ", ".join(f"{k}={v}" for k, v in p.conditions.items())
    return text


def print_record(record: ProviderRecord) -> None:
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


def print_normalized(result: Normalized) -> None:
    part = result.part
    category = part.category.value.value if part.category else result.category.status
    typer.echo("  normalized")
    typer.echo(f"    category   {category} ({result.category.reason})")
    typer.echo(f"    lifecycle  {', '.join(s.value.value for s in part.lifecycle)}")
    if part.package is not None:
        group = part.package.group or "UNKNOWN"
        typer.echo(f"    package    {group} ({result.package.reason})")
    for p in part.parameters.values():
        typer.echo(f"    {parameter_line(p)}")
    for name, raw in part.unparsed.items():
        typer.echo(f"    unparsed   {name}: {raw.value}")
    for note in result.notes:
        typer.echo(f"    note       {note}")
    typer.echo(
        f"    source     every value above: {part.mpn.source.provider} response "
        f"{(part.mpn.source.response_id or '')[:12]}"
    )
