"""Shared CLI pieces: exit codes, the console, JSON output and providers.

Exit codes, the same for every command:
  0  success, or VERIFIED
  1  PARTIAL
  2  usage, configuration or provider error
  3  MISMATCH
  4  NOT FOUND
"""

import json
import os
import sys
from typing import Any

import typer
from pydantic import BaseModel
from rich.console import Console

from ersatz.cache import Cache
from ersatz.notice import NOTICE
from ersatz.providers.base import Provider
from ersatz.providers.factory import build_digikey
from ersatz.settings import Settings

EXIT_OK = 0
EXIT_PARTIAL = 1
EXIT_ERROR = 2
EXIT_MISMATCH = 3
EXIT_NOT_FOUND = 4

VERDICT_EXIT = {
    "VERIFIED": EXIT_OK,
    "PARTIAL": EXIT_PARTIAL,
    "MISMATCH": EXIT_MISMATCH,
    "NOT FOUND": EXIT_NOT_FOUND,
}
# Worst first, for commands that report several verdicts.
SEVERITY = ("NOT FOUND", "MISMATCH", "PARTIAL", "VERIFIED")

STYLE = {
    "VERIFIED": "bold green",
    "PASS": "green",
    "DROP_IN": "green",
    "ACTIVE": "green",
    "FOUND": "green",
    "PARTIAL": "bold yellow",
    "WARN": "yellow",
    "UNKNOWN": "yellow",
    "SAME_PACKAGE_REWIRE": "yellow",
    "NRND": "yellow",
    "LAST_TIME_BUY": "yellow",
    "AMBIGUOUS": "yellow",
    "MISMATCH": "bold red",
    "FAIL": "red",
    "NO": "red",
    "OBSOLETE": "red",
    "NOT FOUND": "bold red",
    "N/A": "dim",
}


def styled(text: str) -> str:
    style = STYLE.get(text)
    return f"[{style}]{text}[/]" if style else text


def console() -> Console:
    """A console bound to the current stdout; wide when output is not a terminal."""
    width = None if sys.stdout.isatty() else int(os.environ.get("COLUMNS", "160"))
    return Console(file=sys.stdout, width=width, highlight=False, soft_wrap=False)


def emit_json(payload: BaseModel | dict[str, Any]) -> None:
    data = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    data.setdefault("notice", NOTICE)
    typer.echo(json.dumps(data, indent=2, ensure_ascii=False))


def notice_line(out: Console) -> None:
    out.print(f"\n[dim]Notice:[/] {NOTICE}")


def fail(message: str, code: int = EXIT_ERROR) -> typer.Exit:
    """Print an error to stderr and return the exit to raise."""
    typer.echo(f"error: {message}", err=True)
    return typer.Exit(code)


def build_providers(settings: Settings, cache: Cache) -> list[Provider]:
    """Every configured provider. Tests replace this one function."""
    return [build_digikey(settings, cache)]
