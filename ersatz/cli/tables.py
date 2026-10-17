"""Rich tables shared by find, verify and check."""

from rich.table import Table

from ersatz.cli.output import styled
from ersatz.match.score import CandidateScore


def diff_table(score: CandidateScore, title: str | None = None) -> Table:
    table = Table(title=title, show_lines=False, header_style="bold")
    for column in (
        "Parameter",
        "Original",
        "Candidate",
        "Verdict",
        "Rule",
        "Source (original)",
        "Source (candidate)",
    ):
        table.add_column(column, overflow="fold")
    for row in score.diff:
        table.add_row(
            row.parameter,
            row.original,
            row.candidate,
            styled(row.verdict),
            row.rule,
            row.original_source,
            row.candidate_source,
        )
    return table
