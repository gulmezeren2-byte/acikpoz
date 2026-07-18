"""CLI tests via typer's runner — exercise the command surface and error paths
without needing a real PDF."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from acikpoz.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "acikpoz" in result.stdout


def test_parse_missing_file_exits_2() -> None:
    result = runner.invoke(app, ["parse", "does-not-exist.pdf"])
    assert result.exit_code == 2


def test_parse_non_pdf_exits_2(tmp_path: Path) -> None:
    bad = tmp_path / "not-really.pdf"
    bad.write_text("plain text, not a PDF", encoding="utf-8")
    result = runner.invoke(app, ["parse", str(bad)])
    assert result.exit_code == 2


def test_parse_bad_pages_exits_2(tmp_path: Path) -> None:
    # a real-enough path so the pages check is reached before the file check
    bad = tmp_path / "x.pdf"
    bad.write_text("x", encoding="utf-8")
    result = runner.invoke(app, ["parse", str(bad), "--pages", "not-a-range"])
    assert result.exit_code == 2
