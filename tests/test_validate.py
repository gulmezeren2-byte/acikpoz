"""Validation tests on hand-made poz lists with known issues."""

from __future__ import annotations

from acikpoz.model import Poz
from acikpoz.validate import validate_pozes


def test_clean_pozes_ok() -> None:
    r = validate_pozes(
        [Poz("15.100.1003", "taş", "m³", 54.88), Poz("15.100.1004", "beton", "Ton", 100.0)]
    )
    assert r.ok
    assert r.findings == []
    assert r.checked == 2


def test_duplicate_poz_is_error() -> None:
    r = validate_pozes(
        [Poz("15.100.1003", "a", "m³", 10.0), Poz("15.100.1003", "b", "m³", 20.0)]
    )
    dups = [f for f in r.findings if f.rule == "duplicate_poz"]
    assert len(dups) == 1 and dups[0].severity == "error"
    assert not r.ok


def test_nonpositive_price_is_error() -> None:
    r = validate_pozes([Poz("15.100.1003", "a", "m³", 0.0)])
    assert any(f.rule == "nonpositive_price" for f in r.findings)
    assert not r.ok


def test_bad_poz_format_is_error() -> None:
    r = validate_pozes([Poz("not-a-code", "a", "m³", 10.0)])
    assert any(f.rule == "bad_poz_format" for f in r.findings)
    assert not r.ok


def test_priced_without_unit_is_warning() -> None:
    r = validate_pozes([Poz("15.100.1003", "a", None, 10.0)])
    fs = [f for f in r.findings if f.rule == "priced_without_unit"]
    assert len(fs) == 1 and fs[0].severity == "warning"
    assert r.ok  # warnings alone keep it ok


def test_unusual_unit_is_warning() -> None:
    r = validate_pozes([Poz("15.100.1003", "a", "flarb", 10.0)])
    assert any(f.rule == "unusual_unit" and f.severity == "warning" for f in r.findings)
    assert r.ok


def test_real_units_are_accepted() -> None:
    for unit in ("Ton", "m³", "Sa", "Ad", "Tk", "adet", "%", "kg"):
        r = validate_pozes([Poz("15.100.1003", "a", unit, 10.0)])
        assert not any(f.rule == "unusual_unit" for f in r.findings), unit


def test_group_header_triggers_no_price_rules() -> None:
    r = validate_pozes([Poz("25.110.1000", "EVİYELER:", None, None, is_group_header=True)])
    assert r.ok
    assert r.findings == []


def test_to_dict_shape() -> None:
    d = validate_pozes([Poz("15.100.1003", "a", "m³", 0.0)]).to_dict()
    assert d["ok"] is False
    assert d["counts"]["errors"] >= 1
    assert d["checked"] == 1
