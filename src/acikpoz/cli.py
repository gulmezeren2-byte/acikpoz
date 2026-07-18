"""Command line interface.

    acikpoz parse bf2026.pdf --pages 8-20
    acikpoz parse bf2026.pdf --json > pozes.jsonl

`--pages` takes 0-based page indices (a range like 8-20, or a single number).
Every command prints the coverage behind the numbers; nothing is invented — a
poz with no printed price stays price-less, and the count of such gaps is shown.
"""

from __future__ import annotations

import contextlib
import csv
import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

import acikpoz as _acikpoz
from acikpoz.diff import diff_pozes
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
    group: str = typer.Option(
        None, "--group", help="Only pozes in this main group, e.g. 25 (Sıhhi Tesisat)."
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit pozes as JSONL."),
    csv_out: Path = typer.Option(
        None, "--csv", metavar="FILE.csv",
        help="Write pozes to a CSV file (utf-8-sig, ready for Excel with Turkish text).",
    ),
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

    try:
        result = parse_catalog(pdf, pages=page_range)
    except ValueError as exc:  # malformed / encrypted / non-PDF file
        _err.print(f"[bold red]error:[/bold red] {exc}")
        raise typer.Exit(2) from exc
    pozes = result.pozes
    if group:
        pozes = [p for p in pozes if p.grup == group]
    if priced_only:
        pozes = [p for p in pozes if p.is_priced]

    if csv_out is not None:
        # utf-8-sig so Excel opens Turkish characters correctly out of the box.
        with csv_out.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["poz_no", "grup", "tanim", "birim", "fiyat", "is_group_header"])
            for p in pozes:
                writer.writerow(
                    [
                        p.poz_no, p.grup, p.tanim, p.birim or "",
                        "" if p.fiyat is None else p.fiyat, p.is_group_header,
                    ]
                )
        _console.print(f"wrote {csv_out} — {len(pozes)} poz(es)")
        return

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
    rate = result.price_parse_rate
    rate_str = f"{rate:.0%}" if rate is not None else "—"
    _console.print(
        f"[dim]{result.priced} priced · {result.group_headers} group headers · "
        f"{result.gaps} price gaps · grade [b]{result.grade}[/b] ({rate_str} of "
        f"non-header pozes priced) · {result.pages_read} page(s) read. "
        f"A gap is a poz the catalog printed no price for — surfaced, not invented.[/dim]"
    )
    if len(pozes) > 200:
        _console.print(f"[dim](showing first 200 of {len(pozes)}; use --json for all)[/dim]")


@app.command()
def diff(
    old_pdf: Path = typer.Argument(..., metavar="OLD.pdf", help="Last year's catalog PDF."),
    new_pdf: Path = typer.Argument(..., metavar="NEW.pdf", help="This year's catalog PDF."),
    pages: str = typer.Option(None, "--pages", help="Same 0-based page range applied to both."),
    tolerance: float = typer.Option(
        0.0, "--tolerance", help="Hide price moves at or below this many TL."
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit the diff as JSON."),
) -> None:
    """Diff two catalog years by poz code: price moves, added/removed pozes, unit changes."""
    for pdf in (old_pdf, new_pdf):
        if not pdf.is_file():
            _err.print(f"[bold red]error:[/bold red] file not found: {pdf}")
            raise typer.Exit(2)
    try:
        page_range = _parse_pages(pages)
    except ValueError:
        _err.print(f"[bold red]error:[/bold red] bad --pages {pages!r} (use e.g. 8-20).")
        raise typer.Exit(2) from None
    try:
        old = parse_catalog(old_pdf, pages=page_range)
        new = parse_catalog(new_pdf, pages=page_range)
    except ValueError as exc:
        _err.print(f"[bold red]error:[/bold red] {exc}")
        raise typer.Exit(2) from exc

    result = diff_pozes(old.pozes, new.pozes, tolerance=tolerance)
    if as_json:
        typer.echo(json.dumps(result.to_dict(), ensure_ascii=True, indent=2))
        return

    price_changes = [c for c in result.changes if c.kind == "price_change"]
    if price_changes:
        table = Table(title="Price changes (poz priced in both years)", title_justify="left")
        table.add_column("poz")
        table.add_column("old TL", justify="right")
        table.add_column("new TL", justify="right")
        table.add_column("Δ", justify="right")
        table.add_column("%", justify="right")
        for c in price_changes[:200]:
            pct = f"{c.pct:+.1f}%" if c.pct is not None else "-"
            table.add_row(
                c.poz_no, _fmt_try(c.old_fiyat), _fmt_try(c.new_fiyat), _fmt_try(c.delta), pct
            )
        _console.print(table)

    mp = result.mean_price_pct
    mp_str = f"{mp:+.2f}%" if mp is not None else "—"
    _console.print(
        f"[dim]{result.count('price_change')} price changes (mean {mp_str}) · "
        f"{result.count('added')} added · {result.count('removed')} removed · "
        f"{result.count('unit_change')} unit changes · {old_pdf.name} → {new_pdf.name}.[/dim]"
    )


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with contextlib.suppress(Exception):  # pragma: no cover
                reconfigure(errors="replace")
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
