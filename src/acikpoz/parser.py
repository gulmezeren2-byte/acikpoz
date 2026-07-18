"""Coordinate-based parser for ÇŞB unit-price (birim fiyat) catalog PDFs.

The approach is disciplined geometry, no ML — the same bet ihalent made on
markdown. A page is a table with stable-ish columns; we group words into visual
rows, then read the *price* column's x position from the page header ("Birim
Fiyat" / "Rayiç Fiyatı") rather than assuming a fixed threshold. That header
step matters: some sections (e.g. Sıhhi Tesisat) carry two numeric columns —
the real Birim Fiyat and a separate Montaj Bedeli — and a fixed threshold would
silently read the wrong one. Reading the header picks the right column.

Two honesty rules, inherited from andon/ihalent:
  * A group-header poz (a category title like "EVİYELER:") has no price of its
    own. We leave its fiyat None and flag is_group_header — we never borrow a
    price from a neighbour.
  * A price is only ever a token that parses as a Turkish-format number in the
    price column. We never coerce, never guess.

Layered so the logic is testable without a PDF: `parse_words` takes the plain
word dicts pdfplumber emits ({"text","x0","top"}); `parse_page`/`parse_catalog`
are thin pdfplumber wrappers.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from acikpoz.model import Poz

POZ_RE = re.compile(r"^\d{2}\.\d{3}\.\d{4}$")
PRICE_RE = re.compile(r"^\d{1,3}(\.\d{3})*,\d{2}$")
# Some sections (e.g. Sıhhi Tesisat) print the unit inline in the description as
# "(Ölçü: Ad.)" rather than in a column. When present, it is authoritative.
_OLCU_RE = re.compile(r"\(\s*Ölçü\s*:\s*([^)]+?)\s*\)", re.IGNORECASE)

_ROW_TOL = 3.0  # points; words within this vertical band are one visual row
_POZ_MAX_X = 70.0  # a poz-code cell sits in the left margin
_PRICE_MIN_X = 400.0  # the price column is always on the right half
_PRICE_WINDOW = 55.0  # a price token this close to the header x is the unit price
_UNIT_SPAN = 70.0  # the unit column sits just left of the price column


@dataclass
class ParseResult:
    """Parsed pozes plus the coverage that stands behind them — a number is only
    as trustworthy as the denominator next to it."""

    pozes: list[Poz] = field(default_factory=list)
    pages_read: int = 0

    @property
    def priced(self) -> int:
        return sum(1 for p in self.pozes if p.is_priced)

    @property
    def group_headers(self) -> int:
        return sum(1 for p in self.pozes if p.is_group_header)

    @property
    def gaps(self) -> int:
        """Non-header pozes with no printed price — a genuine data gap, surfaced
        rather than hidden."""
        return sum(1 for p in self.pozes if not p.is_priced and not p.is_group_header)

    @property
    def price_parse_rate(self) -> float | None:
        """Share of non-header pozes that got a price, in [0, 1]. None when there
        were no non-header pozes. This is the parser's confidence in a page-set:
        a low rate means either genuine catalog gaps or a layout the geometry
        missed — the reader should look, which is the whole point."""
        denom = len(self.pozes) - self.group_headers
        return round(self.priced / denom, 4) if denom else None

    @property
    def grade(self) -> str:
        """A coarse, glanceable quality grade from the parse rate, the way
        camelot exposes accuracy and docling a grade. `empty` means nothing to
        grade; below `good`, review the pages before trusting the output."""
        rate = self.price_parse_rate
        if rate is None:
            return "empty"
        if rate >= 0.98:
            return "excellent"
        if rate >= 0.90:
            return "good"
        if rate >= 0.75:
            return "fair"
        return "poor"

    def to_dict(self) -> dict[str, Any]:
        return {
            "pages_read": self.pages_read,
            "counts": {
                "total": len(self.pozes),
                "priced": self.priced,
                "group_headers": self.group_headers,
                "price_gaps": self.gaps,
            },
            "price_parse_rate": self.price_parse_rate,
            "grade": self.grade,
            "pozes": [p.to_dict() for p in self.pozes],
        }


def tl(s: str | None) -> float | None:
    """Turkish-format money string -> float. '1.310,00' -> 1310.0. None-safe.

    Rejects non-finite results (inf/nan): a catalog prints finite prices, and a
    price used in a cost total must never be inf or nan."""
    if not s:
        return None
    try:
        value = float(s.replace(".", "").replace(",", "."))
    except (ValueError, AttributeError):
        return None
    return value if math.isfinite(value) else None


def _group_rows(words: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    buckets: dict[int, list[dict[str, Any]]] = {}
    for w in words:
        buckets.setdefault(round(float(w["top"]) / _ROW_TOL), []).append(w)
    return [sorted(buckets[k], key=lambda w: float(w["x0"])) for k in sorted(buckets)]


def _price_column_x(rows: list[list[dict[str, Any]]]) -> float | None:
    """The x of the price column, read from the header row: a word starting with
    'Fiyat' that sits on the right (x>400), so a stray 'fiyat' in a left-column
    description is never mistaken for it. Returns None if no header is found."""
    for row in rows:
        if row and POZ_RE.match(row[0]["text"]):
            continue  # a data row, not a header
        for w in row:
            if str(w["text"]).startswith("Fiyat") and float(w["x0"]) > _PRICE_MIN_X:
                return float(w["x0"])
    return None


def _price_of(row: list[dict[str, Any]], px: float) -> str | None:
    cands = [
        w
        for w in row
        if PRICE_RE.match(w["text"]) and abs(float(w["x0"]) - px) < _PRICE_WINDOW
    ]
    if not cands:
        return None
    return min(cands, key=lambda w: abs(float(w["x0"]) - px))["text"]


def parse_words(words: list[dict[str, Any]]) -> list[Poz]:
    """Parse one page worth of pdfplumber word dicts into pozes.

    Each dict needs at least ``text`` and ``x0`` and ``top``. A row whose first
    cell is a poz code starts a new poz; indented continuation rows extend the
    running poz's description (and can carry the price if it spilled over)."""
    rows = _group_rows(words)
    px = _price_column_x(rows)
    pozes: list[Poz] = []
    cur: Poz | None = None

    for row in rows:
        if not row:
            continue
        first = row[0]
        is_poz = float(first["x0"]) < _POZ_MAX_X and POZ_RE.match(first["text"])

        if is_poz:
            if cur is not None:
                pozes.append(_finalize(cur))
            desc, unit = _split_desc_unit(row[1:], px)
            price = _price_of(row, px) if px is not None else None
            cur = Poz(poz_no=first["text"], tanim=desc, birim=unit, fiyat=tl(price))
        elif cur is not None and float(first["x0"]) >= _POZ_MAX_X:
            # continuation line: description spilled over, maybe the price too
            cont, unit = _split_desc_unit(row, px)
            if cont:
                cur.tanim = (cur.tanim + " " + cont).strip()
            if cur.birim is None and unit:
                cur.birim = unit
            if cur.fiyat is None and px is not None:
                cur.fiyat = tl(_price_of(row, px))

    if cur is not None:
        pozes.append(_finalize(cur))
    return pozes


def _split_desc_unit(cells: list[dict[str, Any]], px: float | None) -> tuple[str, str | None]:
    """Split a row's non-poz cells into (description, unit). The unit column sits
    just left of the price column; everything further left is description."""
    if px is None:
        desc = " ".join(str(w["text"]) for w in cells if float(w["x0"]) < _PRICE_MIN_X)
        return desc.strip(), None
    unit_lo = px - _UNIT_SPAN
    desc = " ".join(str(w["text"]) for w in cells if float(w["x0"]) < unit_lo)
    unit_cells = [
        str(w["text"])
        for w in cells
        if unit_lo <= float(w["x0"]) < px - 8 and not PRICE_RE.match(w["text"])
    ]
    unit = " ".join(unit_cells).strip() or None
    return desc.strip(), unit


def _finalize(p: Poz) -> Poz:
    """Two finishing touches:
    * An inline "(Ölçü: X)" in the description is the authoritative unit — trust it
      over the column-guessed one, which is unreliable in sections that print the
      unit inline rather than in a column.
    * A price-less poz whose description ends in ':' is a category title (a group
      header), priced None by design — not a data gap."""
    m = _OLCU_RE.search(p.tanim)
    if m:
        unit = m.group(1).strip().rstrip(".").strip()
        if unit:
            p.birim = unit
    if p.fiyat is None and p.tanim.rstrip().endswith(":"):
        p.is_group_header = True
    return p


def parse_page(page: Any) -> list[Poz]:
    """Parse a single pdfplumber page object."""
    return parse_words(page.extract_words())


def parse_catalog(path: str | Path, pages: range | list[int] | None = None) -> ParseResult:
    """Parse a ÇŞB catalog PDF. `pages` limits to a 0-based page range/list;
    None reads the whole document. Needs pdfplumber (the core dependency)."""
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("acikpoz needs pdfplumber: pip install acikpoz") from exc

    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Catalog PDF not found: {p}")

    result = ParseResult()
    try:
        with pdfplumber.open(str(p)) as pdf:
            indices = list(pages) if pages is not None else range(len(pdf.pages))
            for i in indices:
                if 0 <= i < len(pdf.pages):
                    result.pozes.extend(parse_page(pdf.pages[i]))
                    result.pages_read += 1
    except FileNotFoundError:
        raise
    except Exception as exc:
        # A malformed, encrypted or non-PDF file makes pdfminer/pdfplumber raise
        # a variety of errors; turn them into one clear ValueError so a caller
        # (or the MCP server) fails gracefully instead of crashing.
        raise ValueError(f"Could not read {p.name} as a PDF: {exc}") from exc
    return result
