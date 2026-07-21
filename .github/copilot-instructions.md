# Copilot instructions — acikpoz

Deterministic, offline Python tool that turns Turkish public-construction unit-price (ÇŞB *birim fiyat*) catalog PDFs into structured `Poz` records (code, description, unit, price), with year-over-year diff and validation, exposed as a CLI and an optional MCP server.

## Build, test, lint

Managed with `uv` (`uv.lock` committed); Python ≥3.10, hatchling build backend. These are the exact CI commands (`.github/workflows/ci.yml`):

```bash
uv sync --dev --extra mcp     # install core + dev tools + optional mcp extra
uv run pytest -q              # tests (config in [tool.pytest.ini_options], testpaths=tests)
uv run ruff check src tests   # lint
uv run mypy src               # type-check
uv build                      # build sdist/wheel (release.yml; publishes to PyPI on v* tags via OIDC)
```

Run the tools: `acikpoz parse FILE.pdf --pages 8-20` (also `diff OLD.pdf NEW.pdf`, `validate FILE.pdf`; `--json`/`--csv`/`--group`/`--priced-only`). MCP server entry point: `acikpoz-mcp`.

## Architecture

`src/` layout, one package `src/acikpoz/`. The pipeline is layered so parsing logic is testable without a real PDF:
- `model.py` — `Poz` dataclass; every possibly-missing field is `Optional`, defaulting to `None`.
- `parser.py` — coordinate/geometry parser, no ML. Pure `parse_words(word_dicts)` -> `parse_page(page)` -> `parse_catalog(path, pages)`; reads the price-column x from the page **header**; `ParseResult` reports coverage (`priced`/`group_headers`/`gaps`, `price_parse_rate`, `grade`); `tl()` parses Turkish money ("1.310,00" -> 1310.0).
- `diff.py` — `diff_pozes` -> `CatalogDiff`/`PozChange` (kinds: price_change/unit_change/added/removed/now_priced/now_unpriced).
- `validate.py` — `validate_pozes` -> `ValidationReport`/`Finding`; deterministic rules only, error vs warning severity, never mutates data.
- `cli.py` (typer + rich, entry `acikpoz`) and `mcp_server.py` (FastMCP, entry `acikpoz-mcp`) are thin wrappers: tool functions return plain dicts and know nothing about the runtime. `__init__.py` is the public API surface.

## Conventions

- **Honesty rule (core invariant):** a price is only ever a number the catalog printed in the price column — never coerce, borrow a neighbour's, or guess. A missing price is `None`, never `0`. A category-title poz (description ends `:`) is `is_group_header=True` with `fiyat=None`, counted as a header, not a gap. Preserve this in any change.
- Header-driven column detection must survive the two-price-column Sıhhi Tesisat layout (real *Birim Fiyat* vs *Montaj Bedeli*) — the canonical trap covered in `tests/test_parser.py`.
- Tests drive the parser with synthetic pdfplumber word dicts via the `w(text, x0, top)` helper; add cases there — no real PDF needed. Never commit catalog PDFs (`.gitignore` blocks `*.pdf`); the repo ships the parser, not the data.
- Every module starts with `from __future__ import annotations` and uses `X | None` types. mypy enforces `disallow_untyped_defs` and `no_implicit_optional` (all defs typed). ruff: line-length 100, target py310, rules `E,F,I,UP,B,SIM,RET,C4`.
- `--pages` is 0-based. CSV output is `utf-8-sig` (Excel + Turkish), JSON is `ensure_ascii`. Keep the `mcp` import optional and runtime-guarded — out of the core dependency set.
