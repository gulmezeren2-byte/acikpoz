# Changelog

## 0.2.0 — 2026-07-18

- **Validation** (`acikpoz validate`, and a `validate` MCP tool): deterministic
  quality rules over parsed pozes — duplicate poz codes, malformed codes,
  non-positive prices, priced pozes with no unit, and units outside the known set.
  Findings carry a severity (error/warning); `validate` exits non-zero on any error,
  so it can gate a pipeline. A rule-based check that catches parse/OCR slips without
  ML, and never fixes or invents anything — it only surfaces.
- Inline **"(Ölçü: X)"** units in a description are now read as authoritative, since
  some sections (Sıhhi Tesisat) print the unit inline rather than in a column.
- Known limitation, surfaced honestly: in sections where the unit is *inherited*
  from a group header rather than printed on each row, per-row unit detection is
  weak — `validate` flags those rows as `unusual_unit`/`priced_without_unit`.
  Price, poz code and description remain reliable; unit inheritance is planned.

## 0.1.0 — 2026-07-18

First public release.

- Coordinate-based parser for ÇŞB unit-price (birim fiyat) catalog PDFs: groups
  words into visual rows and reads the **price column's x from the page header**
  ("Birim Fiyat" / "Rayiç Fiyatı"), so sections with two numeric columns (real
  Birim Fiyat vs. a separate Montaj Bedeli) are read correctly instead of by a
  brittle fixed threshold.
- Honesty discipline, inherited from andon/ihalent: a price is only ever a number
  the catalog printed in the price column; a category-title poz (e.g. "EVİYELER:")
  is left price-less and flagged `is_group_header`; and every result carries the
  coverage — priced, group headers, and genuine price gaps — so nothing is hidden
  or invented.
- **Confidence grade + parsing report**: every result carries a `price_parse_rate`
  and a coarse `grade` (excellent/good/fair/poor/empty), the way camelot exposes
  accuracy and docling a grade — so a low-quality page-set is glanceable, not
  buried.
- **Section taxonomy**: `Poz.grup` derives the main group code from the poz number
  (e.g. `25` for Sıhhi Tesisat), and `acikpoz parse --group 25` filters to it — a
  navigable structure without a lookup table.
- **Year-over-year diff**: `acikpoz diff old.pdf new.pdf` (and a `diff` MCP tool)
  joins two catalog years by poz code and classifies each change — price move
  (Δ, %Δ), added/removed poz, unit change, gained/lost price — with the mean price
  %-change. The rate movement a single catalog can't show.
- **CSV export**: `acikpoz parse --csv pozes.csv` writes utf-8-sig so Excel opens
  Turkish text correctly out of the box — the format estimators actually work in.
- `Poz` model, `parse_words` / `parse_page` / `parse_catalog` / `diff_pozes` API,
  a CLI (`parse`, `diff`, `--json`, `--csv`), and an optional MCP server
  (`pip install 'acikpoz[mcp]'`, `acikpoz-mcp`) exposing `parse_catalog` and `diff`
  as agent tools.
- Hardened parsing: malformed/encrypted/non-PDF files fail as one clear
  `ValueError` (never a crash), and prices are always finite (`inf`/`nan` rejected).
- The parser ships; catalog PDFs do not. Point it at your own official catalog.
