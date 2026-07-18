# acikpoz

<!-- mcp-name: io.github.gulmezeren2-byte/acikpoz -->

**Turkish public construction unit prices, turned from a PDF into data you can compute with.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Every public construction job in Turkey is priced against a government catalog: the ÇŞB
(Çevre, Şehircilik ve İklim Değişikliği Bakanlığı) *birim fiyat* books — thousands of unit
prices (a poz: a code, a description, a unit, a price) that estimators, contractors and
auditors all read. They ship as long PDFs. acikpoz turns those pages back into structured
records, deterministically, so a cost estimate or a tender preparation can be *computed*
instead of copied by hand.

It is disciplined geometry, not a language model: it groups the words on a page into visual
rows and reads the **price column's position from the page header** rather than guessing a
fixed spot. That one decision is what makes it trustworthy — some sections (Sıhhi Tesisat,
say) print two numbers per row, the real *Birim Fiyat* and a separate *Montaj Bedeli*, and a
naive parser silently reads the wrong one. acikpoz reads the header, so it reads the right
column.

Paired with [ihalent](https://github.com/gulmezeren2-byte/ihalent) (which structures tender
*results*), acikpoz covers the other half of Turkey's public construction economy: the
*prices* the results are measured against.

## The one rule it never breaks

A price is only ever a number the catalog actually printed in the price column. It never
coerces, never borrows a neighbour's figure, never guesses. Two consequences, both on
purpose:

- A **group-header poz** — a category title like `EVİYELER:` whose sub-items carry the real
  prices — has no price of its own. acikpoz leaves its `fiyat` as `None` and flags
  `is_group_header`. It does not invent a zero.
- A poz the catalog left without a printed price is a **gap**, surfaced and counted, not
  hidden. Every result reports its coverage: how many pozes were priced, how many were
  headers, how many were genuine gaps.

Half the value of a cost tool is refusing to make up the numbers the source did not print.
That is the same honesty discipline as [andon](https://github.com/gulmezeren2-byte/andon)
and ihalent.

## Install

```
pip install acikpoz          # add [mcp] for the MCP server: pip install "acikpoz[mcp]"
```

## Quick start

Point it at an official catalog PDF you have (acikpoz ships the parser, **not** the data):

```
acikpoz parse bf2026.pdf --pages 8-20
acikpoz parse bf2026.pdf --json > pozes.jsonl     # one poz per line, for pipelines
acikpoz parse bf2026.pdf --group 25               # only Sıhhi Tesisat pozes
acikpoz parse bf2026.pdf --priced-only            # drop headers and gaps
```

The table view (shape shown with illustrative values, not real catalog figures):

```
poz          birim  fiyat TL   tanım
15.100.1003  m³        54,88    1 m³ taşın taşıtlara yüklenmesi
15.100.1005  Ton      434,05    1 ton çelik borunun taşıtlara yüklenmesi
25.110.1000  -             -    ALATURKA HELA TESİSATI:            (group header)

407 priced · 6 group headers · 43 price gaps · grade good (90% of non-header
pozes priced) · 16 page(s) read.
```

The **grade** (excellent/good/fair/poor) is a glanceable confidence signal, the
way camelot exposes accuracy: below `good`, review the pages before trusting the
output. `--json` includes `price_parse_rate` and `grade` per parse.

Or from Python:

```python
from acikpoz import parse_catalog

result = parse_catalog("bf2026.pdf", pages=range(8, 20))
for p in result.pozes:
    if p.is_priced:
        print(p.poz_no, p.birim, p.fiyat)
print(result.to_dict()["counts"])   # priced / group_headers / price_gaps
```

## How it works

1. **Rows.** Words are grouped into visual rows by vertical position (a few points of
   tolerance), then sorted left-to-right.
2. **Price column, from the header.** The `Fiyat` header word on the right (x > 400) gives
   the price column's x. A stray "fiyat" in a left-column description can't be mistaken for
   it.
3. **Cells.** For each poz row: the leftmost cell is the poz code; the price is the
   number-shaped token nearest the price-column x; the unit sits just left of it; the rest is
   the description. Indented continuation lines extend the running description (and can carry
   a price that spilled over).
4. **Group headers.** A price-less poz whose description ends in `:` is a category title —
   flagged, not treated as a gap.

## Compare two catalog years

Catalogs are reissued regularly; the question estimators and auditors track by hand is *how
did this year's rates move from last year's?* `acikpoz diff` answers it — it joins two years
by poz code and classifies each change:

```
acikpoz diff bf2025.pdf bf2026.pdf --pages 8-400
acikpoz diff bf2025.pdf bf2026.pdf --tolerance 1   # hide sub-1-TL rounding noise
acikpoz diff bf2025.pdf bf2026.pdf --json
```

It reports price moves (with Δ and %Δ), added and removed pozes, unit changes, and pozes
that gained or lost a printed price — plus the **mean price %-change** for the year. As far
as the research found, no other open tool does year-over-year diffing for ÇŞB catalogs.

## Using acikpoz with AI agents

An MCP server (`pip install 'acikpoz[mcp]'`, then `acikpoz-mcp`) exposes two tools:
`parse_catalog` (a PDF → structured pozes with honest coverage) and `diff` (two catalog years
→ classified changes). The agent gets structured data back, not prose it has to parse. Pair
it with ihalent and an agent can reason across both a tender's result *and* the unit prices
it was measured against.

```jsonc
// e.g. Claude Desktop / Claude Code mcp config
{ "mcpServers": { "acikpoz": { "command": "acikpoz-mcp" } } }
```

## Scope, honestly

- **It reads the standard catalog layout.** The header-driven column detection handles the
  common single- and two-price-column pages well; an unusual layout may leave more gaps —
  which it reports rather than papering over. If a section parses badly, that's a bug worth a
  sample.
- **It is a parser, not a price database.** It does not bundle or redistribute the catalog.
  You bring the official PDF; acikpoz turns your copy into data.
- **Prices are nominal, as printed.** No inflation adjustment is baked in — that's an
  analysis choice the caller makes knowing the year.

## Data, and why the PDFs aren't here

The ÇŞB catalogs are official public documents, but this repository does not redistribute
them: it ships the parser and nothing else, and `.gitignore` keeps `*.pdf` out. Point acikpoz
at the catalog you obtained from the official source. This is the same line ihalent draws —
own the tool, not the data.

## How this project is built

I'm an industrial engineer working in construction; I read these catalogs. I designed the
parsing approach — geometry over machine learning, honest gaps over invented numbers — and I
review every line; I use AI agents heavily for implementation speed, and the commit trailers
say so. The contract is the tests: they encode the exact word geometry a real page emits,
including the two-column Sıhhi Tesisat trap and the group-header rule, so green tests mean the
parser handles the real thing.

## License

MIT — see [LICENSE](LICENSE).
