"""MCP tool-logic tests. Exercise the plain function, not the transport, so they
run without the `mcp` extra installed."""

from __future__ import annotations

import builtins

import pytest

from acikpoz.mcp_server import (
    _pages,
    server_class,
    tool_diff,
    tool_parse_catalog,
    tool_validate,
)


def test_pages_parsing() -> None:
    assert list(_pages("8-10")) == [8, 9, 10]
    assert list(_pages("5")) == [5]
    assert _pages(None) is None
    assert _pages("") is None


def test_missing_file_returns_error() -> None:
    result = tool_parse_catalog("does-not-exist.pdf")
    assert "error" in result
    assert "not found" in result["error"].lower()


def test_diff_missing_file_returns_error() -> None:
    result = tool_diff("old-nope.pdf", "new-nope.pdf")
    assert "error" in result


def test_validate_missing_file_returns_error() -> None:
    result = tool_validate("nope.pdf")
    assert "error" in result


# --------------------------------------------------------------------------- #
# The SDK renamed its high-level server between majors — `FastMCP` in 1.x,
# `MCPServer` in 2.x — and deleted the old module outright, which broke every
# published server built on it. Both spellings are accepted, and the failure now
# says which problem it actually is.
# --------------------------------------------------------------------------- #
def test_the_server_class_resolves_against_whichever_sdk_is_installed() -> None:
    pytest.importorskip("mcp")
    resolved = server_class()
    assert resolved.__name__ in {"MCPServer", "FastMCP"}
    assert hasattr(resolved, "tool")


def test_an_sdk_exposing_neither_api_is_not_called_a_missing_install(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("mcp")
    real_import = builtins.__import__

    def without_a_server_api(name, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name in {"mcp.server", "mcp.server.fastmcp"}:
            raise ImportError(f"No module named {name!r}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_a_server_api)
    with pytest.raises(SystemExit) as caught:
        server_class()
    message = str(caught.value)
    # telling someone to install the extra they already installed is a dead end
    assert "pip install" not in message
    assert "incompatibility" in message
