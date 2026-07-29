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


def test_utf8_guard_survives_a_legacy_code_page() -> None:
    """A piped stdout on Windows gets the legacy code page, where a Turkish poz description
    raises UnicodeEncodeError and kills the command. The guard must prevent that."""
    import io
    import sys

    from acikpoz.cli import _console, _use_utf8_output

    original = sys.stdout
    sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", newline="")
    try:
        _use_utf8_output()
        _console.print("ÖZKAN İNŞAAT LTD. ŞTİ. — Lavabo tesisatı (Ölçü: Ad.), kırım %32,5")
    finally:
        sys.stdout = original


def test_utf8_guard_tolerates_a_stream_without_reconfigure() -> None:
    import sys

    from acikpoz.cli import _use_utf8_output

    class Bare:
        encoding = "cp1252"

        def write(self, text: str) -> int:  # pragma: no cover - not exercised
            return len(text)

    original_out, original_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = Bare(), Bare()
    try:
        _use_utf8_output()  # must not raise
    finally:
        sys.stdout, sys.stderr = original_out, original_err
