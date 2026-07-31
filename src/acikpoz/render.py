"""Terminal rendering for the CLI's two report views.

These live here rather than inside the command bodies so that anything else
printing them — the demo image in the README, most of all — goes through the
same code the CLI runs. A screenshot that can drift from the tool is worse than
no screenshot, and this repository's whole claim is that the figures it shows
came from the source rather than from someone's imagination.
"""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from acikpoz.parser import ParseResult
from acikpoz.validate import ValidationReport

_MAX_ROWS = 200
_MAX_TANIM = 70


def fmt_try(value: float | None) -> str:
    """Turkish-style money, or a dash when the catalog printed no price."""
    if value is None:
        return "-"
    return f"{value:,.2f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def render_pozes(result: ParseResult, title: str, console: Console) -> None:
    """The `parse` view: the extracted rows, then how complete the extraction was."""
    pozes = result.pozes
    table = Table(title=f"{title} — {len(pozes)} poz", title_justify="left")
    table.add_column("poz")
    table.add_column("birim")
    table.add_column("fiyat TL", justify="right")
    table.add_column("tanım", overflow="fold")
    for p in pozes[:_MAX_ROWS]:
        tanim = p.tanim if len(p.tanim) <= _MAX_TANIM else p.tanim[: _MAX_TANIM - 1] + "…"
        table.add_row(p.poz_no, p.birim or "-", fmt_try(p.fiyat), tanim)
    console.print(table)

    rate = result.price_parse_rate
    rate_str = f"{rate:.0%}" if rate is not None else "—"
    console.print(
        f"[dim]{result.priced} priced · {result.group_headers} group headers · "
        f"{result.gaps} price gaps · grade [b]{result.grade}[/b] ({rate_str} of "
        f"non-header pozes priced) · {result.pages_read} page(s) read. "
        f"A gap is a poz the catalog printed no price for — surfaced, not invented.[/dim]"
    )
    if len(pozes) > _MAX_ROWS:
        console.print(
            f"[dim](showing first {_MAX_ROWS} of {len(pozes)}; use --json for all)[/dim]"
        )


def render_validation(report: ValidationReport, console: Console) -> None:
    """The `validate` view: what the parse is not confident about."""
    if not report.findings:
        console.print(
            f"[green]OK[/green] — {report.checked} poz(es) validated, no issues."
        )
        return

    table = Table(title="Validation findings", title_justify="left")
    table.add_column("severity")
    table.add_column("rule")
    table.add_column("poz")
    table.add_column("message", overflow="fold")
    for f in report.findings[:_MAX_ROWS]:
        colour = "red" if f.severity == "error" else "yellow"
        table.add_row(f"[{colour}]{f.severity}[/]", f.rule, f.poz_no, f.message)
    console.print(table)
    console.print(
        f"[dim]{report.errors} error(s), {report.warnings} warning(s) "
        f"over {report.checked} poz(es).[/dim]"
    )
