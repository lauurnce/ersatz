"""Smoke tests: the package imports and the CLI prints its version."""

from typer.testing import CliRunner

import ersatz
from ersatz.cli import app


def test_version_is_set() -> None:
    assert ersatz.__version__ == "0.0.1"


def test_cli_prints_version() -> None:
    result = CliRunner().invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.output.strip() == f"ersatz {ersatz.__version__}"
