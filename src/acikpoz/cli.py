"""Command line interface.

    acikpoz parse bf2026.pdf --pages 8-20
    acikpoz parse bf2026.pdf --json > pozes.jsonl

`--pages` takes 0-based page indices (a range like 8-20, or a single number).
Every command prints the coverage behind the numbers; nothing is invented — a
poz with no printed price stays price-less, and the count of such gaps is shown.
"""

from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

import acikpoz as _acikpoz
from acikpoz.parser import parse_catalog

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Structured data from Turkish public construction unit-price catalogs.",
)
_console = Console()
_err = Console(stderr=True)


def _version_callback(value: bool) -> None:
    if value:
        _console.print(f"acikpoz {_acikpoz.__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False, "--version", "-V", callback=_version_callback, is_eager=True,
        help="Print the version and exit.",
    ),
) -> None:
    """acikpoz — parse ÇŞB birim-fiyat catalogs into structured pozes."""


def _parse_pages(spec: str | None) -> range | None:
    if not spec:
        return None
    if "-" in spec:
        lo, hi = spec.split("-", 1)
        return range(int(lo), int(hi) + 1)
    n = int(spec)
    return range(n, n + 1)


def _fmt_try(value: float | None) -> str:
    if value is None:
        return "-"
    s = f"{value:,.2f}"  # 1,234.56
    return s.replace(",", "_").replace(".", ",").replace("_", ".")  # -> 1.234,56


@app.command()
def parse(
    pdf: Path = typer.Argument(..., help="A ÇŞB birim-fiyat catalog PDF."),
    pages: str = typer.Option(
        None, "--pages", help="0-based page range, e.g. 8-20, or a single index."
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit pozes as JSONL."),
    priced_only: bool = typer.Option(
        False, "--priced-only", help="Only pozes that carry a printed price."
    ),
) -> None:
    """Parse a catalog PDF into structured pozes (poz no, description, unit, price)."""
    if not pdf.is_file():
        _err.print(f"[bold red]error:[/bold red] file not found: {pdf}")
        raise typer.Exit(2)
    try:
        page_range = _parse_pages(pages)
    except ValueError:
        _err.print(f"[bold red]error:[/bold red] bad --pages {pages!r} (use e.g. 8-20).")
        raise typer.Exit(2) from None

    result = parse_catalog(pdf, pages=page_range)
    pozes = [p for p in result.pozes if p.is_priced] if priced_only else result.pozes

    if as_json:
        for p in pozes:
            typer.echo(json.dumps(p.to_dict(), ensure_ascii=True))
        return

    table = Table(title=f"{pdf.name} — {len(pozes)} poz", title_justify="left")
    table.add_column("poz")
    table.add_column("birim")
    table.add_column("fiyat TL", justify="right")
    table.add_column("tanım", overflow="fold")
    for p in pozes[:200]:
        tanim = p.tanim if len(p.tanim) <= 70 else p.tanim[:69] + "…"
        table.add_row(p.poz_no, p.birim or "-", _fmt_try(p.fiyat), tanim)
    _console.print(table)
    _console.print(
        f"[dim]{result.priced} priced · {result.group_headers} group headers · "
        f"{result.gaps} price gaps · {result.pages_read} page(s) read. "
        f"A gap is a poz the catalog printed no price for — surfaced, not invented.[/dim]"
    )
    if len(pozes) > 200:
        _console.print(f"[dim](showing first 200 of {len(pozes)}; use --json for all)[/dim]")


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with contextlib.suppress(Exception):  # pragma: no cover
                reconfigure(errors="replace")
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
