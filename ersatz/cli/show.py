"""Rich output for provider records and normalized parts. Values print verbatim."""

from rich.console import Console
from rich.markup import escape

from ersatz.cli.output import console, styled
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


def print_record(record: ProviderRecord, out: Console | None = None) -> None:
    out = out or console()
    s = record.source
    out.print(f"[bold]{escape(record.mpn)}[/]  ({escape(record.manufacturer)})")
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
            shown = styled(value) if label == "lifecycle" else escape(value)
            out.print(f"  {label:<10} {shown}")
    for name, value in record.raw_parameters.items():
        out.print(f"  - {name}: {value}", markup=False)
    out.print(
        f"  source     {s.provider} response {(s.response_id or '')[:12]} "
        f"retrieved {s.retrieved_at:%Y-%m-%d %H:%M} UTC"
    )
    if s.url:
        out.print(f"             {s.url}", markup=False)


def print_normalized(result: Normalized, out: Console | None = None) -> None:
    out = out or console()
    part = result.part
    category = part.category.value.value if part.category else result.category.status
    out.print("  normalized", markup=False)
    out.print(f"    category   {category} ({result.category.reason})", markup=False)
    out.print(f"    lifecycle  {', '.join(s.value.value for s in part.lifecycle)}", markup=False)
    if part.package is not None:
        group = part.package.group or "UNKNOWN"
        out.print(f"    package    {group} ({result.package.reason})", markup=False)
    for p in part.parameters.values():
        out.print(f"    {parameter_line(p)}", markup=False)
    for name, raw in part.unparsed.items():
        out.print(f"    unparsed   {name}: {raw.value}", markup=False)
    for note in result.notes:
        out.print(f"    note       {note}", markup=False)
    out.print(
        f"    source     every value above: {part.mpn.source.provider} response "
        f"{(part.mpn.source.response_id or '')[:12]}"
    )
