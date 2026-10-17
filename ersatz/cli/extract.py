"""ersatz extract: run datasheet extraction on one URL. Costs money."""

from typing import Annotated

import typer
from rich.markup import escape
from rich.table import Table

from ersatz.budget.spend import SpendCapError, SpendLedger
from ersatz.cache import SqliteCache
from ersatz.cli import output
from ersatz.datasheets.fetch import DatasheetFetchError, fetch
from ersatz.datasheets.pipeline import ExtractionResult, UnextractedError, extract_datasheet
from ersatz.llm import factory
from ersatz.llm.base import LLMError
from ersatz.match import display
from ersatz.model.category import Category
from ersatz.settings import get_settings


def show(result: ExtractionResult) -> None:
    out = output.console()
    ex = result.extraction
    ref = ex.datasheet
    out.print(f"Datasheet {escape(ref.url)}")
    out.print(
        f"  sha256 {ref.sha256[:16]}  revision {ref.revision or '-'}  category {ex.category.value}"
    )
    run = result.run
    cost = "cached reply, no cost" if result.cached else f"{run.call.cost_usd:.4f} USD"
    out.print(f"  model {run.model}  pages sent {', '.join(map(str, run.pages))}  {cost}")
    table = Table(title="Parameters", header_style="bold")
    for column in ("Parameter", "Value", "Confidence", "Page", "Quote", "Issues"):
        table.add_column(column, overflow="fold")
    for item in ex.parameters:
        p = item.parameter
        table.add_row(
            p.name.value + (f" ({item.variant})" if item.variant else ""),
            display.parameter(p),
            "[green]HIGH[/]" if item.confidence.value == "HIGH" else "[yellow]LOW[/]",
            str(p.source.page),
            escape(p.source.quote or ""),
            "; ".join(item.issues),
        )
    out.print(table)
    for pkg in ex.packages:
        group = pkg.group or "UNKNOWN"
        out.print(f"Package  {escape(pkg.raw_name)} -> {group}  [dim]p{pkg.source.page}[/]")
    for po in ex.pinouts:
        pins = ", ".join(f"{pin.number}={pin.function.value}" for pin in po.pinout.pins)
        out.print(f"Pinout   {escape(po.package)}: {pins}  [dim]p{po.pinout.source.page}[/]")
    for f in ex.features:
        out.print(f"Feature  {f.name} = {f.value}  [dim]p{f.source.page}[/]")
    out.print(f"Dropped by quote verification or validation: {len(ex.dropped)}")
    for d in ex.dropped:
        out.print(f"  - {d.kind} {escape(d.name)} p{d.page}: {escape(d.reason)}")
    output.notice_line(out)


def extract_command(
    url: Annotated[str, typer.Argument(help="Datasheet PDF URL.")],
    category: Annotated[Category, typer.Option(help="Component category.")],
    device: Annotated[
        str | None, typer.Option(help="Device or variant to report rows for.")
    ] = None,
    max_usd: Annotated[float, typer.Option(help="Spend cap for this run in USD.")] = 1.0,
    as_json: Annotated[bool, typer.Option("--json", help="Print JSON.")] = False,
) -> None:
    """Extract cited values from one datasheet. Calls the configured language model."""
    settings = get_settings()
    cache = SqliteCache(settings.ersatz_cache_dir / "ersatz.sqlite")
    try:
        llm = factory.make_llm(settings)
        file = fetch(url, cache, settings.ersatz_cache_dir)
        ledger = SpendLedger(cache, run_cap_usd=max_usd)
        result = extract_datasheet(file, category, llm, ledger, cache, device=device)
    except (LLMError, DatasheetFetchError, UnextractedError, SpendCapError) as exc:
        raise output.fail(str(exc)) from exc
    if as_json:
        output.emit_json(result)
    else:
        show(result)
