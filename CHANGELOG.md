# Changelog

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
- `Poz` model, `parse_words` / `parse_page` / `parse_catalog` API, a CLI
  (`acikpoz parse`, with `--json` for pipelines), and an optional MCP server
  (`pip install 'acikpoz[mcp]'`, `acikpoz-mcp`) exposing the parser as an agent
  tool.
- The parser ships; catalog PDFs do not. Point it at your own official catalog.
