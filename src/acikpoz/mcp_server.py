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

from acikpoz.diff import diff_pozes
from acikpoz.parser import parse_catalog
from acikpoz.validate import validate_pozes


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


def tool_diff(
    old_pdf_path: str,
    new_pdf_path: str,
    pages: str | None = None,
    tolerance: float = 0.0,
) -> dict[str, Any]:
    """Diff two ÇŞB catalog years by poz code: price moves (delta + percent),
    added and removed pozes, unit changes, and pozes that gained or lost a printed
    price. `pages` is a 0-based range applied to both PDFs; `tolerance` (in TL)
    hides small price moves. Returns per-kind counts, the mean price %-change, and
    the individual changes — the year-over-year rate movement a single catalog
    can't show."""
    try:
        old = parse_catalog(old_pdf_path, pages=_pages(pages))
        new = parse_catalog(new_pdf_path, pages=_pages(pages))
    except (FileNotFoundError, ValueError) as exc:
        return {"error": str(exc)}
    return diff_pozes(old.pozes, new.pozes, tolerance=tolerance).to_dict()


def tool_validate(pdf_path: str, pages: str | None = None) -> dict[str, Any]:
    """Validate a parsed ÇŞB catalog against deterministic quality rules: duplicate
    poz codes, malformed codes, non-positive prices, priced pozes with no unit, and
    units outside the known set. Returns findings with severity (error/warning) and
    an `ok` flag — a rule-based check that catches parse/OCR slips without ML, never
    fixing or inventing anything."""
    try:
        result = parse_catalog(pdf_path, pages=_pages(pages))
    except (FileNotFoundError, ValueError) as exc:
        return {"error": str(exc)}
    return validate_pozes(result.pozes).to_dict()


TOOLS = [tool_parse_catalog, tool_diff, tool_validate]


def server_class() -> Any:
    """The high-level server class, whichever major of the SDK is installed.

    The MCP Python SDK renamed it between majors: `mcp.server.fastmcp.FastMCP` in 1.x,
    `mcp.server.MCPServer` in 2.x, with the old module removed outright. The two are
    drop-in for what we use of them, so both are accepted rather than pinning users to
    one SDK generation.

    The failure is also reported honestly. Telling someone to install the extra when
    they already installed it — the old behaviour once 2.x shipped — sends them in a
    circle; a missing package and an SDK that moved are different problems.
    """
    try:
        from mcp.server import MCPServer  # mcp >= 2.0

        return MCPServer
    except ImportError:
        pass
    try:
        from mcp.server.fastmcp import FastMCP  # mcp 1.x

        return FastMCP
    except ImportError:
        pass

    try:
        import mcp
    except ImportError as exc:
        raise SystemExit(
            "The MCP server needs the optional dependency: pip install 'acikpoz[mcp]'"
        ) from exc
    installed = getattr(mcp, "__version__", None) or "unknown version"
    raise SystemExit(
        f"the installed mcp package ({installed}) exposes neither mcp.server.MCPServer "
        "(SDK 2.x) nor mcp.server.fastmcp.FastMCP (SDK 1.x), so the server cannot be "
        "built. This is an SDK incompatibility, not a missing install."
    )


def build_server() -> Any:
    server = server_class()("acikpoz")
    for fn in TOOLS:
        server.tool()(fn)
    return server


def main() -> None:  # pragma: no cover - transport entry point
    build_server().run()


if __name__ == "__main__":  # pragma: no cover
    main()
