"""Deterministic validation over parsed pozes — a rule-based quality check, no
ML, in the spirit of the DCMA/BoQ validators the research found.

Every finding is a plain fact about the data: a poz code that isn't a valid
code, the same code twice, a non-positive price, a priced poz with no unit, or a
unit outside the known set. Findings carry a severity (error/warning) but the
validator never *fixes* anything and never removes a poz — it surfaces, the way
andon surfaces and ihalent reports. Catching a parse or OCR slip deterministically
is the whole point; a hallucinated birim fiyat in a tender is unacceptable.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from acikpoz.model import Poz
from acikpoz.parser import POZ_RE

# Common ÇŞB units, casefolded. Unknown units are a *warning*, not an error, so a
# missing entry here is harmless — it flags for a look, never drops data.
KNOWN_UNITS = frozenset(
    {
        "m", "m²", "m³", "m2", "m3", "mtül", "cm", "cm²", "cm³", "dm", "dm³",
        "mm", "km", "km²", "kg", "ton", "gr", "g", "mg", "lt", "l", "ml",
        "ad", "adet", "tk", "takım", "sa", "saat", "dk", "%", "çift", "ay",
        "gün", "yıl", "kwh", "kw", "kva", "hp", "paket", "kutu", "rulo",
        "top", "boy", "düzine", "deste", "bağ", "demet", "torba", "1000 ad",
        "100 kg", "1000 adet",
    }
)

# Findings ordered by severity (errors first) then rule name.
_SEVERITY_ORDER = {"error": 0, "warning": 1}


@dataclass
class Finding:
    poz_no: str
    rule: str
    severity: str  # "error" | "warning"
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "poz_no": self.poz_no,
            "rule": self.rule,
            "severity": self.severity,
            "message": self.message,
        }


@dataclass
class ValidationReport:
    findings: list[Finding] = field(default_factory=list)
    checked: int = 0

    @property
    def errors(self) -> int:
        return sum(1 for f in self.findings if f.severity == "error")

    @property
    def warnings(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warning")

    @property
    def ok(self) -> bool:
        """True when nothing at error severity was found."""
        return self.errors == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "checked": self.checked,
            "ok": self.ok,
            "counts": {"errors": self.errors, "warnings": self.warnings},
            "findings": [f.to_dict() for f in self.findings],
        }


def validate_pozes(pozes: list[Poz]) -> ValidationReport:
    """Check a list of pozes against deterministic rules and report the findings.

    Rules: `duplicate_poz` (same code more than once), `bad_poz_format` (not an
    NN.NNN.NNNN code), `nonpositive_price` (a printed price ≤ 0), `priced_without_unit`
    (a price but no unit), `unusual_unit` (a unit outside the known set)."""
    findings: list[Finding] = []

    counts = Counter(p.poz_no for p in pozes)
    for poz_no, n in counts.items():
        if n > 1:
            findings.append(
                Finding(poz_no, "duplicate_poz", "error", f"poz appears {n} times")
            )

    for p in pozes:
        if not POZ_RE.match(p.poz_no):
            findings.append(
                Finding(p.poz_no, "bad_poz_format", "error", "not a NN.NNN.NNNN poz code")
            )
        if p.fiyat is not None:
            if p.fiyat <= 0:
                findings.append(
                    Finding(p.poz_no, "nonpositive_price", "error", f"price is {p.fiyat}")
                )
            if not p.birim:
                findings.append(
                    Finding(p.poz_no, "priced_without_unit", "warning", "priced but has no unit")
                )
            elif p.birim.strip().casefold() not in KNOWN_UNITS:
                findings.append(
                    Finding(
                        p.poz_no, "unusual_unit", "warning",
                        f"unit {p.birim!r} is not in the known set",
                    )
                )

    findings.sort(key=lambda f: (_SEVERITY_ORDER.get(f.severity, 9), f.rule, f.poz_no))
    return ValidationReport(findings=findings, checked=len(pozes))
