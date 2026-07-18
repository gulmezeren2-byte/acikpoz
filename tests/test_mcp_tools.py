"""MCP tool-logic tests. Exercise the plain function, not the transport, so they
run without the `mcp` extra installed."""

from __future__ import annotations

from acikpoz.mcp_server import _pages, tool_parse_catalog


def test_pages_parsing() -> None:
    assert list(_pages("8-10")) == [8, 9, 10]
    assert list(_pages("5")) == [5]
    assert _pages(None) is None
    assert _pages("") is None


def test_missing_file_returns_error() -> None:
    result = tool_parse_catalog("does-not-exist.pdf")
    assert "error" in result
    assert "not found" in result["error"].lower()
