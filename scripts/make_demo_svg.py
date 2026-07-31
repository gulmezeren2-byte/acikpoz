"""Regenerate docs/demo.svg from the official 2026 ÇŞB catalog.

The image in the README is not a mock-up: it is `parse` and `validate` running
against the real published catalog, through the same `acikpoz.render` functions
the CLI calls. Numbers invented for a screenshot would contradict the one rule
this parser is built around — never print a figure the source did not.

The PDF is not committed (it is 15 MB of someone else's copyright), so the
script downloads it on demand. Both panels are one page of it, chosen because
that page shows the two things worth seeing:

* three pozes the catalog printed **no price** for — surfaced as `-`, not
  guessed at;
* a handful of units the parser is **not confident about**, which `validate`
  reports rather than passing off as clean. The extraction is imperfect on some
  layouts and the tool says so itself; that is the point.

    uv run python scripts/make_demo_svg.py
"""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

from rich.console import Console

from acikpoz import render as _render
from acikpoz.cli import _parse_pages
from acikpoz.parser import parse_catalog
from acikpoz.validate import validate_pozes

ROOT = Path(__file__).parent.parent
PDF_URL = (
    "https://webdosya.csb.gov.tr/v2/yfk/2026/01/"
    "1-BF-202619011535-20260119155143.pdf"
)
PDF = ROOT / "bf2026.pdf"
PAGES = "400"
WIDTH = 100


def _catalog() -> Path:
    if not PDF.exists():
        print(f"downloading {PDF_URL} ...")
        # a fixed, official https URL published by the ministry
        with urllib.request.urlopen(PDF_URL) as r, PDF.open("wb") as f:  # noqa: S310
            f.write(r.read())
    return PDF


def main() -> None:
    pdf = _catalog()
    result = parse_catalog(pdf, pages=_parse_pages(PAGES))
    report = validate_pozes(result.pozes)

    console = Console(record=True, width=WIDTH, force_terminal=True)
    _render.render_pozes(result, pdf.name, console)
    console.print()
    _render.render_validation(report, console)

    svg = console.export_svg(title=f"acikpoz parse / validate bf2026.pdf --pages {PAGES}")
    # Drop the CDN font-face so the SVG is self-contained on GitHub, which blocks
    # external fetches inside an SVG and would otherwise render empty boxes —
    # and this catalog is full of Turkish characters that must survive.
    svg = re.sub(r"@font-face\s*\{[^}]*?\}", "", svg, flags=re.DOTALL)

    out = ROOT / "docs" / "demo.svg"
    out.parent.mkdir(exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(
        f"wrote {out} ({len(result.pozes)} pozes, {result.gaps} price gap(s), "
        f"grade {result.grade}; {report.warnings} validation warning(s))"
    )


if __name__ == "__main__":
    main()
