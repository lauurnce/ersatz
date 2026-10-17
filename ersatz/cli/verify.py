"""ersatz verify and ersatz check."""

import sys
from typing import Annotated

import typer
from rich.table import Table

from ersatz.cache import SqliteCache
from ersatz.cli import output
from ersatz.cli.output import EXIT_ERROR, EXIT_NOT_FOUND, EXIT_OK, SEVERITY, VERDICT_EXIT, styled
from ersatz.cli.tables import diff_table
from ersatz.providers import ProviderError
from ersatz.providers.base import Provider
from ersatz.resolve import Status
from ersatz.settings import get_settings
from ersatz.verify import CheckReport, VerifyError, VerifyResult, check_text, verify


def _providers() -> list[Provider]:
    settings = get_settings()
    cache = SqliteCache(settings.ersatz_cache_dir / "ersatz.sqlite")
    try:
        return output.build_providers(settings, cache)
    except ProviderError as exc:
        raise output.fail(str(exc)) from exc


def show_verify(result: VerifyResult) -> None:
    out = output.console()
    o = result.original.record
    out.print(
        f"Original   {result.original.query} ({o.manufacturer if o else '-'})"
        f"  [dim]{result.original.note}[/]"
    )
    c = result.candidate
    maker = c.record.manufacturer if c.record else "-"
    shown = (
        c.query
        if c.status is not Status.NOT_FOUND
        else f"{result.candidate_as_entered!r} (as entered)"
    )
    out.print(f"Candidate  {shown} ({maker})  [dim]{c.note}[/]")
    out.print(f"Verdict    {styled(result.verdict.value)}")
    for reason in result.reasons:
        out.print(f"  - {reason}")
    if result.score is not None:
        out.print(diff_table(result.score))
    output.notice_line(out)


def verify_command(
    original: Annotated[str, typer.Argument(help="Part number of the discontinued part.")],
    candidate: Annotated[str, typer.Argument(help="Suggested replacement, as entered.")],
    original_manufacturer: Annotated[
        str | None, typer.Option(help="Manufacturer of the original.")
    ] = None,
    candidate_manufacturer: Annotated[
        str | None, typer.Option(help="Manufacturer of the candidate.")
    ] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Print JSON.")] = False,
) -> None:
    """Verify one suggested replacement: VERIFIED, PARTIAL, MISMATCH or NOT FOUND."""
    providers = _providers()
    try:
        result = verify(
            original, candidate, providers, original_manufacturer, candidate_manufacturer
        )
    except VerifyError as exc:
        code = EXIT_NOT_FOUND if "NOT_FOUND" in str(exc) else EXIT_ERROR
        raise output.fail(str(exc), code) from exc
    except ProviderError as exc:
        raise output.fail(str(exc)) from exc
    if as_json:
        output.emit_json(result)
    else:
        show_verify(result)
    raise typer.Exit(VERDICT_EXIT[result.verdict.value])


def check_exit(report: CheckReport) -> int:
    statuses = {item.status for item in report.items}
    if report.original is None:
        return EXIT_NOT_FOUND if "NOT FOUND" in statuses else EXIT_OK
    for verdict in SEVERITY:
        if verdict in statuses:
            return VERDICT_EXIT[verdict]
    return EXIT_OK


def show_check(report: CheckReport) -> None:
    out = output.console()
    if report.original:
        out.print(f"Original: {report.original}")
    else:
        out.print(
            "No original given: each part number is only looked up. Pass --original to verify."
        )
    out.print(f"Part numbers found in the text: {len(report.mentions)}")
    table = Table(header_style="bold")
    for column in ("#", "As entered", "Status", "Manufacturer", "Lifecycle", "Main reason"):
        table.add_column(column, overflow="fold")
    for n, item in enumerate(report.items, start=1):
        table.add_row(
            str(n),
            item.as_entered,
            styled(item.status),
            item.manufacturer or "-",
            styled(item.lifecycle) if item.lifecycle else "-",
            item.reasons[0] if item.reasons else "",
        )
    out.print(table)
    output.notice_line(out)


def check_command(
    original: Annotated[str | None, typer.Option(help="Part number the answer was about.")] = None,
    original_manufacturer: Annotated[
        str | None, typer.Option(help="Manufacturer of the original.")
    ] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Print JSON.")] = False,
) -> None:
    """Check every part number in a chatbot answer read from stdin."""
    if sys.stdin.isatty():
        raise output.fail("pipe the chatbot answer into stdin, for example: pbpaste | ersatz check")
    text = sys.stdin.read()
    if not text.strip():
        raise output.fail("stdin is empty")
    providers = _providers()
    try:
        report = check_text(text, providers, original, original_manufacturer)
    except VerifyError as exc:
        code = EXIT_NOT_FOUND if "NOT_FOUND" in str(exc) else EXIT_ERROR
        raise output.fail(str(exc), code) from exc
    except ProviderError as exc:
        raise output.fail(str(exc)) from exc
    if as_json:
        output.emit_json(report)
    else:
        show_check(report)
    raise typer.Exit(check_exit(report))
