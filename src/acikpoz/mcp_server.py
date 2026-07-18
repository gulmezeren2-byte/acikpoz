"""MCP server: expose acikpoz's catalog parsing to an agent runtime.

Same structure as the rest of the family: the tool's work is a plain function
returning a dict and knowing nothing about MCP, so it is unit-testable without an
agent runtime. The FastMCP wrapper at the bottom is registered only when the
`mcp` extra is installed, keeping `mcp` out of the core dependency set.

This makes acikpoz a thing an agent can *call*: point it at a ÇŞB catalog PDF
and get back structured pozes with the honest coverage — priced, group headers,
and price gaps — never an invented number.
"""

from __future__ import annotations

from typing import Any

from acikpoz.parser import parse_catalog


def _pages(spec: str | None) -> range | None:
    if not spec:
        return None
    if "-" in spec:
        lo, hi = spec.split("-", 1)
        return range(int(lo), int(hi) + 1)
    n = int(spec)
    return range(n, n + 1)


def tool_parse_catalog(
    pdf_path: str, pages: str | None = None, priced_only: bool = False
) -> dict[str, Any]:
    """Parse a ÇŞB birim-fiyat catalog PDF into structured pozes: poz number,
    description, unit and unit price. `pages` is a 0-based page range like "8-20"
    (or a single index); omit it to read the whole document. Prices are only ever
    numbers the catalog actually printed in the price column; a category-title
    poz (e.g. "EVİYELER:") is left price-less on purpose. Returns per-page-set
    counts (priced / group_headers / price_gaps) plus the pozes."""
    try:
        result = parse_catalog(pdf_path, pages=_pages(pages))
    except (FileNotFoundError, ValueError) as exc:
        return {"error": str(exc)}
    data = result.to_dict()
    if priced_only:
        data["pozes"] = [p for p in data["pozes"] if p["fiyat"] is not None]
    return data


TOOLS = [tool_parse_catalog]


def build_server() -> Any:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise SystemExit(
            "The MCP server needs the optional dependency: pip install 'acikpoz[mcp]'"
        ) from exc

    server = FastMCP("acikpoz")
    for fn in TOOLS:
        server.tool()(fn)
    return server


def main() -> None:  # pragma: no cover - transport entry point
    build_server().run()


if __name__ == "__main__":  # pragma: no cover
    main()
