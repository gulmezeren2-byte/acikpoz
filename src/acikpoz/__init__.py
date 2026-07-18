"""acikpoz — structured data from ÇŞB unit-price (birim fiyat) catalogs.

Small public surface:

    from acikpoz import parse_catalog, Poz
    result = parse_catalog("bf2026.pdf", pages=range(8, 20))

Deterministic, offline, honest: a price is only ever a number the catalog
printed in the price column; a category-title poz is left price-less on
purpose. The parser ships here; the catalog PDFs do not — point it at your own.
"""

from importlib.metadata import PackageNotFoundError, version

from acikpoz.model import Poz
from acikpoz.parser import ParseResult, parse_catalog, parse_page, parse_words, tl

try:
    # Single source of truth: the installed distribution version.
    __version__ = version("acikpoz")
except PackageNotFoundError:  # pragma: no cover - running from a source tree
    __version__ = "0.0.0+unknown"

__all__ = [
    "Poz",
    "ParseResult",
    "parse_catalog",
    "parse_page",
    "parse_words",
    "tl",
    "__version__",
]
