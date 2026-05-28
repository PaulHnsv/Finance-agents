"""B3 ticker normalization — single source of truth for ticker formatting."""
import re

_B3_TICKER_RE = re.compile(r"^[A-Z]{4}(3|4|5|6|11)$")


def normalize_b3_ticker(ticker: str) -> str:
    """Strip whitespace, uppercase, remove trailing '.SA' if present."""
    t = (ticker or "").strip().upper()
    if t.endswith(".SA"):
        t = t[:-3]
    return t


def normalize_for_yfinance(ticker: str) -> str:
    """Return ticker with '.SA' suffix appropriate for yfinance lookups."""
    base = normalize_b3_ticker(ticker)
    return f"{base}.SA" if base else base


def is_valid_b3_ticker(ticker: str) -> bool:
    """True when ticker matches the canonical B3 format (e.g. ITUB4, ALUP11)."""
    return bool(_B3_TICKER_RE.match(ticker or ""))
