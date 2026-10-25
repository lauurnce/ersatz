"""Command line interface built with Typer."""

import typer

from ersatz import __version__

app = typer.Typer(
    name="ersatz",
    help="Find and verify replacements for discontinued parts.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Ersatz command line. Results must be validated by an engineer."""


@app.command()
def version() -> None:
    """Print the installed version."""
    typer.echo(f"ersatz {__version__}")
