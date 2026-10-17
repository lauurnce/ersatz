"""CLI smoke tests over the synthetic catalog, through the real Digi-Key adapter."""

import json

from typer.testing import CliRunner, Result

from ersatz.cli import app
from ersatz.notice import NOTICE
from tests.cli.catalog import CatalogRouter, catalog

__all__ = ["catalog"]

ANSWER = """You can replace the TEST-LDO50-OLD with:
1. **TEST-LDO50-A** (Alpha Test Devices), a pin-compatible drop-in.
2. TEST-LDO50-X, same footprint.
3. TEST-LDO50-Q7, newer and cheaper.
"""


def run(*args: str, stdin: str | None = None) -> Result:
    return CliRunner().invoke(app, list(args), input=stdin)


def test_verify_partial_exits_1(catalog: CatalogRouter) -> None:
    result = run("verify", "TEST-LDO50-OLD", "TEST-LDO50-A")
    assert result.exit_code == 1, result.output
    assert "Verdict    PARTIAL" in result.output
    assert "fit UNKNOWN" in result.output
    assert "LDO-08" in result.output
    assert NOTICE in result.output


def test_verify_mismatch_exits_3(catalog: CatalogRouter) -> None:
    result = run("verify", "TEST-LDO50-OLD", "TEST-LDO50-X")
    assert result.exit_code == 3
    assert "lifecycle: OBSOLETE" in result.output


def test_verify_not_found_exits_4_and_keeps_text(catalog: CatalogRouter) -> None:
    result = run("verify", "TEST-LDO50-OLD", "TEST-LDO50-Q7")
    assert result.exit_code == 4
    assert "'TEST-LDO50-Q7' (as entered)" in result.output
    assert "NOT FOUND" in result.output


def test_verify_with_digikey_code_reports_the_rule(catalog: CatalogRouter) -> None:
    result = run("verify", "TEST-LDO50-OLD", "TEST-LDO50-ACT-ND", "--json")
    data = json.loads(result.output)
    assert data["candidate"]["query"] == "TEST-LDO50-A"
    assert data["candidate"]["rule"]["id"] == "SFX-DK"
    assert data["verdict"] == "PARTIAL"
    assert data["notice"] == NOTICE


def test_verify_unknown_original_exits_4(catalog: CatalogRouter) -> None:
    result = run("verify", "TEST-NOPE1", "TEST-LDO50-A")
    assert result.exit_code == 4
    assert "error: original" in result.output


def test_check_with_original(catalog: CatalogRouter) -> None:
    result = run("check", "--original", "TEST-LDO50-OLD", stdin=ANSWER)
    assert result.exit_code == 4, result.output
    rows = {
        mpn: next(line for line in result.output.splitlines() if f" {mpn} " in line)
        for mpn in ("TEST-LDO50-A", "TEST-LDO50-X", "TEST-LDO50-Q7")
    }
    assert "PARTIAL" in rows["TEST-LDO50-A"]
    assert "MISMATCH" in rows["TEST-LDO50-X"]
    assert "NOT FOUND" in rows["TEST-LDO50-Q7"]
    assert NOTICE in result.output


def test_check_json_without_original(catalog: CatalogRouter) -> None:
    result = run("check", "--json", stdin=ANSWER)
    data = json.loads(result.output)
    assert data["original"] is None
    assert {i["as_entered"]: i["status"] for i in data["items"]} == {
        "TEST-LDO50-OLD": "FOUND",
        "TEST-LDO50-A": "FOUND",
        "TEST-LDO50-X": "FOUND",
        "TEST-LDO50-Q7": "NOT FOUND",
    }
    assert result.exit_code == 4


def test_check_needs_text(catalog: CatalogRouter) -> None:
    assert run("check", stdin="   ").exit_code == 2


def test_find_json_and_text(catalog: CatalogRouter) -> None:
    result = run("find", "TEST-LDO50-OLD", "--json")
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert [c["mpn"] for c in data["top"]] == ["TEST-LDO50-A", "TEST-LDO50-B"]
    text = run("find", "TEST-LDO50-OLD", "--top", "1").output
    assert "1. TEST-LDO50-A" in text
    assert "TEST-LDO50-C (Test Semiconductor): form:" in text


def test_find_unknown_part_exits_4(catalog: CatalogRouter) -> None:
    assert run("find", "TEST-NOPE1").exit_code == 4


def test_lookup_found_and_not_found(catalog: CatalogRouter) -> None:
    assert run("lookup", "TEST-LDO50-A").exit_code == 0
    result = run("lookup", "TEST-LDO50-A", "TEST-LDO50-Q7")
    assert result.exit_code == 4
    assert "TEST-LDO50-Q7 (as entered)  NOT FOUND at digikey" in result.output
