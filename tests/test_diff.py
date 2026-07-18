"""Diff tests on hand-made poz lists with known year-over-year changes."""

from __future__ import annotations

from acikpoz.diff import diff_pozes
from acikpoz.model import Poz


def test_price_change_with_delta_and_pct() -> None:
    d = diff_pozes(
        [Poz("15.100.1003", "taş", "m³", 100.0)],
        [Poz("15.100.1003", "taş", "m³", 120.0)],
    )
    assert d.count("price_change") == 1
    c = d.changes[0]
    assert c.delta == 20.0
    assert c.pct == 20.0


def test_added_and_removed() -> None:
    d = diff_pozes([Poz("1", "a", "m", 10.0)], [Poz("2", "b", "m", 20.0)])
    assert d.count("added") == 1
    assert d.count("removed") == 1


def test_unit_change_not_compared_as_price() -> None:
    d = diff_pozes([Poz("1", "a", "m³", 10.0)], [Poz("1", "a", "Ton", 15.0)])
    assert d.count("unit_change") == 1
    assert d.count("price_change") == 0  # different units -> price not comparable


def test_tolerance_hides_small_moves() -> None:
    d = diff_pozes(
        [Poz("1", "a", "m", 100.0)], [Poz("1", "a", "m", 100.5)], tolerance=1.0
    )
    assert d.count("price_change") == 0


def test_mean_price_pct() -> None:
    d = diff_pozes(
        [Poz("1", "a", "m", 100.0), Poz("2", "b", "m", 100.0)],
        [Poz("1", "a", "m", 110.0), Poz("2", "b", "m", 120.0)],
    )
    assert d.mean_price_pct == 15.0  # (10% + 20%) / 2


def test_now_priced() -> None:
    d = diff_pozes([Poz("1", "a", "m")], [Poz("1", "a", "m", 50.0)])
    assert d.count("now_priced") == 1


def test_unchanged_is_not_reported() -> None:
    d = diff_pozes([Poz("1", "a", "m", 100.0)], [Poz("1", "a", "m", 100.0)])
    assert d.changes == []


def test_to_dict_shape() -> None:
    out = diff_pozes(
        [Poz("1", "a", "m", 100.0)], [Poz("1", "a", "m", 110.0)]
    ).to_dict()
    assert out["counts"]["price_change"] == 1
    assert out["old_count"] == 1 and out["new_count"] == 1
    assert out["mean_price_pct"] == 10.0
