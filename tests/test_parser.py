"""Parser tests on synthetic word dicts — the same shape pdfplumber emits — so
the geometry logic is verified without a PDF. Covers the two-price-column trap
(Birim Fiyat vs Montaj Bedeli) and the group-header honesty rule."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from acikpoz.model import Poz
from acikpoz.parser import ParseResult, parse_catalog, parse_words, tl


def w(text: str, x0: float, top: float) -> dict[str, Any]:
    return {"text": text, "x0": float(x0), "top": float(top)}


# A single-price-column header (like the İşçilik / Rayiç sections).
HEADER = [
    w("Poz", 62, 10), w("No", 78, 10), w("Tanımı", 279, 10),
    w("Birim", 481, 10), w("Fiyatı", 540, 10),
]


def test_tl_turkish_money() -> None:
    assert tl("1.310,00") == 1310.0
    assert tl("633.190.545,70") == 633190545.70
    assert tl("54,88") == 54.88
    assert tl("") is None
    assert tl(None) is None
    assert tl("not a number") is None


def test_tl_rejects_non_finite() -> None:
    # float() would happily accept these; a price must never be inf/nan.
    assert tl("inf") is None
    assert tl("Infinity") is None
    assert tl("nan") is None


def test_parse_catalog_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        parse_catalog("does-not-exist.pdf")


def test_parse_catalog_rejects_non_pdf(tmp_path: Path) -> None:
    bad = tmp_path / "not-really.pdf"
    bad.write_text("this is plain text, not a PDF", encoding="utf-8")
    with pytest.raises(ValueError, match="Could not read"):
        parse_catalog(bad)


def test_single_priced_poz() -> None:
    words = HEADER + [
        w("15.100.1003", 45, 30), w("1 m³ taşın yüklemesi", 100, 30),
        w("m³", 470, 30), w("54,88", 535, 30),
    ]
    pozes = parse_words(words)
    assert len(pozes) == 1
    p = pozes[0]
    assert p.poz_no == "15.100.1003"
    assert "taşın yüklemesi" in p.tanim
    assert p.birim == "m³"
    assert p.fiyat == 54.88
    assert p.is_priced and not p.is_group_header


def test_group_header_is_priced_none() -> None:
    words = HEADER + [w("25.110.1000", 45, 30), w("ALATURKA HELA TESİSATI:", 100, 30)]
    pozes = parse_words(words)
    assert len(pozes) == 1
    assert pozes[0].fiyat is None
    assert pozes[0].is_group_header  # description ends with ':'


def test_two_price_columns_picks_birim_fiyat() -> None:
    # Sıhhi Tesisat layout: real Birim Fiyat @~484, constant Montaj Bedeli @~541.
    # A fixed threshold would grab the wrong one; the header read picks correctly.
    header = [
        w("Poz", 62, 10), w("Cinsi", 301, 10),
        w("Birim", 459, 10), w("Fiyat", 484, 10),
        w("Montaj", 512, 10), w("Bedeli", 543, 10),
    ]
    words = header + [
        w("25.100.1003", 45, 30), w("Lavabo tesisatı", 243, 30),
        w("1.310,00", 478, 30), w("388,75", 541, 30),
    ]
    pozes = parse_words(words)
    assert len(pozes) == 1
    assert pozes[0].fiyat == 1310.0  # Birim Fiyat, not the 388,75 Montaj Bedeli


def test_multiline_description_and_spilled_price() -> None:
    words = HEADER + [
        w("15.100.1005", 45, 30), w("1 ton çelik borunun", 100, 30), w("Ton", 470, 30),
        w("taşıtlara yükleme boşaltma", 100, 42),  # continuation row (lower, indented)
        w("434,05", 535, 42),  # price spilled onto the continuation
    ]
    pozes = parse_words(words)
    assert len(pozes) == 1
    assert "taşıtlara yükleme" in pozes[0].tanim
    assert pozes[0].fiyat == 434.05


def test_inline_olcu_is_authoritative_unit() -> None:
    # Sıhhi Tesisat prints the unit inline: "(Ölçü: Tk.)" — trust it over columns.
    words = HEADER + [
        w("25.114.1000", 45, 30), w("PİSUVAR (Ölçü: Tk.) tesisatı", 100, 30),
        w("50,00", 535, 30),
    ]
    pozes = parse_words(words)
    assert pozes[0].birim == "Tk"
    assert pozes[0].fiyat == 50.0


def test_no_header_leaves_prices_none() -> None:
    # Without a discoverable price column, we do not guess a price.
    words = [w("15.100.1003", 45, 30), w("bir iş", 100, 30), w("54,88", 535, 30)]
    pozes = parse_words(words)
    assert len(pozes) == 1
    assert pozes[0].fiyat is None


def test_parse_result_coverage() -> None:
    r = ParseResult(
        pozes=[
            Poz("1", "a", fiyat=10.0),
            Poz("2", "B:", is_group_header=True),
            Poz("3", "c gap"),
        ],
        pages_read=1,
    )
    assert r.priced == 1
    assert r.group_headers == 1
    assert r.gaps == 1
    d = r.to_dict()
    assert d["counts"] == {"total": 3, "priced": 1, "group_headers": 1, "price_gaps": 1}


def test_grade_and_parse_rate() -> None:
    # 3 priced + 1 header + 1 gap -> non-header 4, priced 3 -> rate 0.75 -> fair
    r = ParseResult(
        pozes=[
            Poz("1", "a", fiyat=10.0),
            Poz("2", "b", fiyat=20.0),
            Poz("3", "c", fiyat=30.0),
            Poz("4", "H:", is_group_header=True),
            Poz("5", "gap"),
        ]
    )
    assert r.price_parse_rate == 0.75
    assert r.grade == "fair"


def test_grade_edges() -> None:
    all_priced = ParseResult(pozes=[Poz(str(i), "x", fiyat=1.0) for i in range(20)])
    assert all_priced.grade == "excellent"
    assert ParseResult().grade == "empty"  # nothing to grade
    only_header = ParseResult(pozes=[Poz("1", "H:", is_group_header=True)])
    assert only_header.price_parse_rate is None
    assert only_header.grade == "empty"
