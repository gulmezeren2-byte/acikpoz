"""Year-over-year catalog diff: what changed between two ÇŞB catalog years?

Joins two parses by poz code and classifies each change — a price moved (with Δ
and %Δ), a poz was added or removed, a unit changed, or a poz gained/lost a
printed price. This is the construction analog of andon's workbook diff: the
question a single catalog can't answer is *how did this year's rates move from
last year's?* — the exact thing estimators and auditors track by hand.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from acikpoz.model import Poz

# Change kinds, ordered by how much a reader should care (most first).
KIND_ORDER = [
    "price_change",
    "unit_change",
    "added",
    "removed",
    "now_priced",
    "now_unpriced",
]


@dataclass
class PozChange:
    poz_no: str
    kind: str
    tanim: str | None = None
    old_fiyat: float | None = None
    new_fiyat: float | None = None
    old_birim: str | None = None
    new_birim: str | None = None
    delta: float | None = None  # new - old, for a price_change
    pct: float | None = None  # percent change, for a price_change

    def to_dict(self) -> dict[str, Any]:
        return {
            "poz_no": self.poz_no,
            "kind": self.kind,
            "tanim": self.tanim,
            "old_fiyat": self.old_fiyat,
            "new_fiyat": self.new_fiyat,
            "old_birim": self.old_birim,
            "new_birim": self.new_birim,
            "delta": self.delta,
            "pct": self.pct,
        }


@dataclass
class CatalogDiff:
    changes: list[PozChange] = field(default_factory=list)
    old_count: int = 0
    new_count: int = 0

    def count(self, kind: str) -> int:
        return sum(1 for c in self.changes if c.kind == kind)

    @property
    def mean_price_pct(self) -> float | None:
        """Average percent price move across the pozes present in both years and
        priced in both — a one-number read on the year's overall rate change."""
        pcts = [c.pct for c in self.changes if c.kind == "price_change" and c.pct is not None]
        return round(sum(pcts) / len(pcts), 2) if pcts else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "old_count": self.old_count,
            "new_count": self.new_count,
            "counts": {k: self.count(k) for k in KIND_ORDER},
            "mean_price_pct": self.mean_price_pct,
            "changes": [c.to_dict() for c in self.changes],
        }


def diff_pozes(
    old: list[Poz], new: list[Poz], *, tolerance: float = 0.0
) -> CatalogDiff:
    """Compare two catalog years by poz code. `tolerance` (in TL) hides price
    moves at or below it, so rounding noise stays out of the report."""
    old_map = {p.poz_no: p for p in old}
    new_map = {p.poz_no: p for p in new}
    changes: list[PozChange] = []

    for poz_no in set(old_map) | set(new_map):
        o = old_map.get(poz_no)
        n = new_map.get(poz_no)

        if o is None and n is not None:
            changes.append(
                PozChange(poz_no, "added", tanim=n.tanim, new_fiyat=n.fiyat, new_birim=n.birim)
            )
            continue
        if n is None and o is not None:
            changes.append(
                PozChange(poz_no, "removed", tanim=o.tanim, old_fiyat=o.fiyat, old_birim=o.birim)
            )
            continue
        assert o is not None and n is not None

        # A unit change means the poz was redefined; a price comparison across
        # different units is meaningless, so it's its own kind.
        if o.birim and n.birim and o.birim != n.birim:
            changes.append(
                PozChange(
                    poz_no, "unit_change", tanim=n.tanim,
                    old_birim=o.birim, new_birim=n.birim,
                    old_fiyat=o.fiyat, new_fiyat=n.fiyat,
                )
            )
            continue

        if o.fiyat is None and n.fiyat is not None:
            changes.append(PozChange(poz_no, "now_priced", tanim=n.tanim, new_fiyat=n.fiyat))
            continue
        if o.fiyat is not None and n.fiyat is None:
            changes.append(PozChange(poz_no, "now_unpriced", tanim=n.tanim, old_fiyat=o.fiyat))
            continue

        if o.fiyat is not None and n.fiyat is not None:
            delta = n.fiyat - o.fiyat
            if abs(delta) > tolerance:
                pct = round(100.0 * delta / o.fiyat, 2) if o.fiyat else None
                changes.append(
                    PozChange(
                        poz_no, "price_change", tanim=n.tanim,
                        old_fiyat=o.fiyat, new_fiyat=n.fiyat,
                        delta=round(delta, 2), pct=pct,
                    )
                )

    order = {k: i for i, k in enumerate(KIND_ORDER)}
    changes.sort(key=lambda c: (order.get(c.kind, 99), c.poz_no))
    return CatalogDiff(changes=changes, old_count=len(old), new_count=len(new))
