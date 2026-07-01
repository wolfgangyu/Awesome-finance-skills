"""Market classification and name resolution utilities for TW / US fine-tuning.

Pure functions when possible: pass ``db`` and ``yfinance_module`` as dependency-
injection seams so that unit tests do not require network/database.
"""
from __future__ import annotations

import re
from typing import Literal

Market = Literal["TW", "US", "CRYPTO", "OTHER"]

_TW_SUFFIX = re.compile(r"\.TW$", re.IGNORECASE)
_US_LETTERS = re.compile(r"^[A-Z]{1,5}$")
_TW_FOUR_DIGIT = re.compile(r"^\d{4}$")
_CRYPTO_DASH = re.compile(r"-USD$|-USDT$|-BTC$|-ETH$", re.IGNORECASE)
_CRYPTO_SLASH = re.compile(r"/(USD|USDT)$", re.IGNORECASE)


def detect_market(ticker: str) -> Market:
    """Classify a ticker into TW / US / CRYPTO / OTHER.

    Rules (priority: TW > US > CRYPTO > OTHER):

      - ``.TW`` suffix or 4-digit numeric  -> ``TW``
      - 1-5 uppercase letters              -> ``US``
      - contains -USD/-USDT/-BTC/-ETH suffix or contains /USD\\|/USDT -> ``CRYPTO``
      - otherwise                           -> ``OTHER``
    """
    t = (ticker or "").strip()
    if not t:
        return "OTHER"
    if _TW_SUFFIX.search(t) or _TW_FOUR_DIGIT.match(t):
        return "TW"
    if _US_LETTERS.match(t):
        return "US"
    if _CRYPTO_DASH.search(t) or _CRYPTO_SLASH.search(t):
        return "CRYPTO"
    return "OTHER"


def resolve_name(
    ticker: str,
    market: Market | str,
    db=None,
    yfinance_module=None,
) -> str:
    """Resolve a human-readable company name for ``ticker``.

    Args:
        ticker: The original ticker string as the user typed it.
        market: One of ``"TW" | "US" | "CRYPTO" | "OTHER"`` (case-insensitive).
        db: Optional DatabaseManager-like object with ``get_stock_by_code``.
        yfinance_module: Optional ``yfinance``-like module with a ``Ticker`` class.

    Returns the original ticker if no source is available.
    """
    t = (ticker or "").strip()
    market_normalized = market.upper() if isinstance(market, str) else market
    if market_normalized == "TW" and db is not None:
        try:
            row = db.get_stock_by_code(t)
            if row and isinstance(row, dict) and row.get("name"):
                return str(row["name"])
        except Exception:
            pass
    if market_normalized == "US" and yfinance_module is not None:
        try:
            info = yfinance_module.Ticker(t).info
            long_name = info.get("longName") if isinstance(info, dict) else None
            if long_name:
                return str(long_name)
        except Exception:
            pass
    return t


def legacy_market_code(ticker: str) -> Literal["twse", "tpex", "us"]:
    """Translate ticker to the legacy twse/tpex/us codes used by StockTools.

    Used only at integration boundaries. Mirrors ``twse_client.detect_market``.
    """
    t = (ticker or "").strip()
    if t.isalpha():
        return "us"
    return "twse"
