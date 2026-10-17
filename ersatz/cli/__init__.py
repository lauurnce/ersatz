"""Command line interface built with Typer."""

import typer

from ersatz import __version__
from ersatz.cli.extract import extract_command
from ersatz.cli.find import find_command
from ersatz.cli.lookup import lookup as lookup_command
from ersatz.cli.verify import check_command, verify_command

app = typer.Typer(
    name="ersatz",
    help="Find and verify replacements for discontinued parts.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Ersatz command line. Results must be validated by an engineer.

    Exit codes: 0 success or VERIFIED, 1 PARTIAL, 2 error, 3 MISMATCH, 4 NOT FOUND.
    """


@app.command()
def version() -> None:
    """Print the installed version."""
    typer.echo(f"ersatz {__version__}")


app.command(name="lookup")(lookup_command)
app.command(name="find")(find_command)
app.command(name="verify")(verify_command)
app.command(name="check")(check_command)
app.command(name="extract")(extract_command)
