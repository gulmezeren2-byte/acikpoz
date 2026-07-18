"""The data model for a unit-price catalog entry (poz).

One decision governs this file: every field the catalog might not print is
Optional, and a missing value is ``None`` — never zero, never a guess. A
group-header poz (a category title like "PİSUVAR VE TESİSATI:") carries no price
of its own; its ``fiyat`` is ``None`` and ``is_group_header`` is ``True``. Half
the value of this tool is refusing to invent a price the catalog did not print —
the same honesty discipline as andon and ihalent.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Poz:
    """A single unit-price line from a ÇŞB birim-fiyat catalog.

    Money is in Turkish Lira, nominal, as printed — no inflation adjustment is
    baked in; that is a choice the caller makes with knowledge of the year.
    """

    poz_no: str  # İş kalemi numarası, e.g. "15.100.1003" — the primary key
    tanim: str  # description (may span several printed lines, joined)
    birim: str | None = None  # unit of measure: m³, Ton, Ad, m², ...
    fiyat: float | None = None  # unit price in TL; None when the catalog prints none
    is_group_header: bool = False  # a category title (e.g. "EVİYELER:") — priced None by design

    @property
    def is_priced(self) -> bool:
        """True only when a real unit price was read. A group header is never
        priced; a normal poz without a printed price is a data gap, not a zero."""
        return self.fiyat is not None

    @property
    def grup(self) -> str:
        """Main group code — the first segment of the poz number (e.g. '15' for an
        İnşaat item, '25' for Sıhhi Tesisat). Lets a caller filter or aggregate by
        section without a lookup table."""
        return self.poz_no.split(".", 1)[0]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["grup"] = self.grup  # a property, so asdict() misses it
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Poz:
        return cls(
            poz_no=str(d["poz_no"]),
            tanim=str(d.get("tanim", "")),
            birim=d.get("birim"),
            fiyat=d.get("fiyat"),
            is_group_header=bool(d.get("is_group_header", False)),
        )
